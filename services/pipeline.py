"""Core pipeline orchestrator — the central handoff controller for Rada AI."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import AsyncGenerator
from uuid import UUID, uuid4

from loguru import logger

from database.vector_store import AssetVectorStore
from models.schemas import (
    AnchorPoint,
    AssetMetadata,
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    SceneGraph,
    StyleTag,
    Vec3,
)
from services.assembly.scene_director import SceneDirector
from services.generation.diffusion_service import DiffusionService
from services.generation.mesh_service import MeshService
from services.semantic.tagger_service import TaggerService

# Singleton reference populated during app startup
_orchestrator: "PipelineOrchestrator | None" = None


def get_orchestrator() -> "PipelineOrchestrator":
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialised")
    return _orchestrator


class PipelineOrchestrator:
    """
    Coordinates the full Rada AI pipeline:
      1. Asset retrieval from vector DB  (or generation if missing)
      2. 2-D diffusion  →  image
      3. Image-to-3-D   →  GLB mesh
      4. VLM tagging    →  metadata
      5. Vector DB upsert
      6. Scene Director →  JSON scene graph
    """

    def __init__(
        self,
        vector_store: AssetVectorStore,
        diffusion: DiffusionService,
        mesh: MeshService,
        tagger: TaggerService,
        director: SceneDirector,
        min_assets_before_generation: int = 3,
    ) -> None:
        self.vector_store = vector_store
        self._diffusion = diffusion
        self._mesh = mesh
        self._tagger = tagger
        self._director = director
        self._min_assets = min_assets_before_generation

        # In-memory job store (replace with Redis for production)
        self._jobs: dict[UUID, GenerationResponse] = {}

    # ── Job management ────────────────────────────────────────────────────

    def create_job(self) -> UUID:
        job_id = uuid4()
        self._jobs[job_id] = GenerationResponse(
            job_id=job_id, status=GenerationStatus.PENDING
        )
        return job_id

    def get_job(self, job_id: UUID) -> GenerationResponse | None:
        return self._jobs.get(job_id)

    def _update_job(self, job_id: UUID, **kwargs) -> None:
        job = self._jobs.get(job_id)
        if job:
            self._jobs[job_id] = job.model_copy(update=kwargs)

    # ── Main pipeline ─────────────────────────────────────────────────────

    async def run_pipeline(
        self, job_id: UUID, request: GenerationRequest
    ) -> None:
        start = time.monotonic()
        try:
            scene = await self._execute(job_id, request)
            elapsed = round(time.monotonic() - start, 2)
            self._update_job(
                job_id,
                status=GenerationStatus.COMPLETE,
                scene_graph=scene,
                duration_seconds=elapsed,
            )
            logger.info("Job {} complete in {}s", job_id, elapsed)
        except Exception as exc:
            logger.exception("Job {} failed: {}", job_id, exc)
            self._update_job(
                job_id,
                status=GenerationStatus.FAILED,
                error=str(exc),
                duration_seconds=round(time.monotonic() - start, 2),
            )

    async def _execute(
        self, job_id: UUID, request: GenerationRequest
    ) -> SceneGraph:
        # ── Step 1: Retrieve existing assets from vector DB ────────────────
        logger.info("[{}] Step 1: searching vector DB…", job_id)
        cached = self.vector_store.search(
            query=request.prompt,
            limit=request.max_assets,
            style=request.style,
        )
        logger.info("[{}] Found {} cached assets", job_id, len(cached))

        # ── Step 2: Generate missing assets if below threshold ─────────────
        if len(cached) < self._min_assets or request.force_regenerate:
            needed = request.max_assets - len(cached)
            logger.info(
                "[{}] Step 2: generating {} new assets via diffusion…",
                job_id,
                needed,
            )
            new_assets = await self._generate_assets(
                request.prompt, request.style, count=needed, job_id=job_id
            )
            cached.extend(new_assets)

        assets = cached[: request.max_assets]

        # ── Step 3: Build scene graph ──────────────────────────────────────
        logger.info("[{}] Step 3: composing scene graph…", job_id)
        self._update_job(job_id, status=GenerationStatus.GENERATING_3D)
        room_dims = Vec3(
            x=request.room_width,
            y=request.room_height,
            z=request.room_depth,
        )
        scene = await self._director.compose(
            user_prompt=request.prompt,
            assets=assets,
            room_dimensions=room_dims,
            style=request.style,
        )
        return scene

    # ── Asset generation sub-pipeline ────────────────────────────────────

    async def _generate_assets(
        self,
        prompt: str,
        style: StyleTag | None,
        count: int,
        job_id: UUID,
    ) -> list[AssetMetadata]:
        self._update_job(job_id, status=GenerationStatus.GENERATING_2D)

        # Build individual sub-prompts for distinct assets
        sub_prompts = self._build_asset_prompts(prompt, style, count)
        tasks = [self._generate_single_asset(p, prompt) for p in sub_prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        assets: list[AssetMetadata] = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning("Asset generation failed: {}", r)
            else:
                assets.append(r)
        return assets

    async def _generate_single_asset(
        self, asset_prompt: str, source_prompt: str
    ) -> AssetMetadata:
        # 2-D generation
        image_path = await self._diffusion.generate(asset_prompt)

        # 2-D → 3-D
        glb_path = await self._mesh.image_to_glb(image_path)

        # Semantic tagging
        tag_data = await self._tagger.tag_asset(image_path, source_prompt)

        asset = AssetMetadata(
            name=tag_data.get("name", asset_prompt[:40]),
            description=tag_data.get("description", ""),
            category=tag_data.get("category", "prop"),
            anchor_point=tag_data.get("anchor_point", AnchorPoint.FLOOR),
            indoor=tag_data.get("indoor", True),
            style_tags=tag_data.get("style_tags", []),
            glb_path=str(glb_path),
            preview_image_path=str(image_path),
            source_prompt=source_prompt,
            generated=True,
        )

        # Index in vector DB
        self.vector_store.upsert(asset)
        return asset

    @staticmethod
    def _build_asset_prompts(
        scene_prompt: str, style: StyleTag | None, count: int
    ) -> list[str]:
        style_clause = f", {style} style" if style else ""
        base = f"single isolated 3D asset, white background, {scene_prompt}{style_clause}"
        # Simple heuristic: generate slightly varied prompts
        variants = [
            f"{base}, hero object",
            f"{base}, secondary prop",
            f"{base}, background detail",
            f"{base}, accent piece",
            f"{base}, structural element",
        ]
        return variants[:count]

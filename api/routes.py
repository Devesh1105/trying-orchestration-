"""FastAPI route definitions for Rada AI."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger

from models.schemas import (
    AssetMetadata,
    AssetSearchRequest,
    AssetSearchResponse,
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    SceneGraph,
)
from services.pipeline import PipelineOrchestrator, get_orchestrator

router = APIRouter(prefix="/api/v1", tags=["rada"])


# ── Scene generation ──────────────────────────────────────────────────────────


@router.post(
    "/generate",
    response_model=GenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a scene generation job",
)
async def generate_scene(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> GenerationResponse:
    job_id = orchestrator.create_job()
    background_tasks.add_task(orchestrator.run_pipeline, job_id, request)
    return GenerationResponse(job_id=job_id, status=GenerationStatus.PENDING)


@router.get(
    "/generate/{job_id}",
    response_model=GenerationResponse,
    summary="Poll job status and retrieve scene graph when complete",
)
async def get_job_status(
    job_id: UUID,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> GenerationResponse:
    response = orchestrator.get_job(job_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return response


# ── Asset search ──────────────────────────────────────────────────────────────


@router.post(
    "/assets/search",
    response_model=AssetSearchResponse,
    summary="Semantic search over the asset vector database",
)
async def search_assets(
    req: AssetSearchRequest,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> AssetSearchResponse:
    results = orchestrator.vector_store.search(
        query=req.query,
        limit=req.limit,
        style=req.style,
        anchor=req.anchor,
        indoor_only=req.indoor_only,
    )
    return AssetSearchResponse(results=results, total=len(results))


@router.get(
    "/assets/{asset_id}",
    response_model=AssetMetadata,
    summary="Retrieve a single asset by ID",
)
async def get_asset(
    asset_id: UUID,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> AssetMetadata:
    asset = orchestrator.vector_store.get(str(asset_id))
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# ── Health ────────────────────────────────────────────────────────────────────


@router.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok", "service": "rada-ai"}

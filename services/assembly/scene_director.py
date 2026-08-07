"""Scene Director: uses a local LLM to generate a JSON scene graph."""

from __future__ import annotations

import json

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from models.schemas import AssetMetadata, AssetPlacement, SceneGraph, Vec3

_OLLAMA_URL = "http://localhost:11434"
_DIRECTOR_MODEL = "llama3:8b"

_SYSTEM_PROMPT = """\
You are a spatial layout AI for an interior/exterior scene generator.
Given a list of 3D assets and a scene description, output ONLY a valid JSON array
(no markdown, no explanation) where each element has:
  asset_id     : string (the asset's UUID)
  asset_name   : string
  position     : {x, y, z} in metres (room origin at 0,0,0)
  rotation     : {x, y, z} Euler angles in degrees
  scale        : {x, y, z} — use 1,1,1 unless scaling is needed for realism
Rules:
- Floor-anchored items have y=0 (or y=half their height for proper grounding).
- Wall-anchored items should be placed near a room wall with correct rotation.
- No asset should clip through another; respect each asset's collision_radius.
- Distribute assets naturally; avoid clustering everything in the centre.
- Return ONLY the JSON array, nothing else.
"""


class SceneDirector:
    def __init__(
        self,
        ollama_url: str = _OLLAMA_URL,
        model: str = _DIRECTOR_MODEL,
    ) -> None:
        self._ollama_url = ollama_url
        self._model = model

    async def compose(
        self,
        user_prompt: str,
        assets: list[AssetMetadata],
        room_dimensions: Vec3,
        style: str | None = None,
    ) -> SceneGraph:
        if not assets:
            raise ValueError("Cannot compose a scene with zero assets")

        asset_summaries = self._format_assets(assets)
        llm_prompt = self._build_prompt(
            user_prompt, asset_summaries, room_dimensions, style
        )

        logger.info(
            "SceneDirector composing {} assets for '{}'",
            len(assets),
            user_prompt[:60],
        )
        raw_json = await self._call_llm(llm_prompt)
        placements = self._parse_placements(raw_json, assets)

        return SceneGraph(
            title=user_prompt[:80],
            description=user_prompt,
            style=style,
            assets=placements,
            room_dimensions=room_dimensions,
        )

    # ── LLM call ──────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=16))
    async def _call_llm(self, prompt: str) -> str:
        payload = {
            "model": self._model,
            "system": _SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 2048},
        }
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{self._ollama_url}/api/generate", json=payload
            )
            resp.raise_for_status()
        return resp.json()["response"]

    # ── Parsing & validation ──────────────────────────────────────────────

    @staticmethod
    def _format_assets(assets: list[AssetMetadata]) -> list[dict]:
        return [
            {
                "asset_id": str(a.id),
                "name": a.name,
                "category": a.category,
                "anchor_point": a.anchor_point,
                "collision_radius": a.collision_radius,
                "style_tags": a.style_tags,
            }
            for a in assets
        ]

    @staticmethod
    def _build_prompt(
        user_prompt: str,
        assets: list[dict],
        dims: Vec3,
        style: str | None,
    ) -> str:
        style_clause = f" The desired aesthetic style is {style}." if style else ""
        return (
            f"Scene request: {user_prompt!r}.{style_clause}\n"
            f"Room dimensions: {dims.x}m wide × {dims.z}m deep × {dims.y}m tall.\n"
            f"Available assets:\n{json.dumps(assets, indent=2)}\n\n"
            "Generate the placement JSON array now."
        )

    @staticmethod
    def _parse_placements(
        raw: str, assets: list[AssetMetadata]
    ) -> list[AssetPlacement]:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError(f"SceneDirector returned no JSON array: {raw!r}")

        data: list[dict] = json.loads(raw[start:end])
        asset_map = {str(a.id): a for a in assets}
        placements: list[AssetPlacement] = []

        for item in data:
            aid = item.get("asset_id", "")
            asset = asset_map.get(aid)
            if asset is None:
                logger.warning("Unknown asset_id '{}' from LLM; skipping", aid)
                continue

            def _vec(d: dict, default: float = 0.0) -> Vec3:
                return Vec3(
                    x=float(d.get("x", default)),
                    y=float(d.get("y", default)),
                    z=float(d.get("z", default)),
                )

            placements.append(
                AssetPlacement(
                    asset_id=asset.id,
                    asset_name=asset.name,
                    position=_vec(item.get("position", {})),
                    rotation=_vec(item.get("rotation", {})),
                    scale=_vec(item.get("scale", {}), default=1.0),
                    glb_url=asset.glb_path,
                )
            )

        return placements

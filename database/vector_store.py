"""ChromaDB-backed vector store for asset metadata."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from loguru import logger
from sentence_transformers import SentenceTransformer

from models.schemas import AnchorPoint, AssetMetadata, StyleTag

_COLLECTION_NAME = "rada_assets"
_EMBED_MODEL = "all-MiniLM-L6-v2"


class AssetVectorStore:
    def __init__(self, persist_dir: str = "./storage/chroma") -> None:
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = SentenceTransformer(_EMBED_MODEL)
        logger.info(
            "VectorStore ready — {} assets indexed", self._collection.count()
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def upsert(self, asset: AssetMetadata) -> None:
        text = self._asset_to_text(asset)
        embedding = self._embed(text)
        self._collection.upsert(
            ids=[str(asset.id)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[self._asset_to_meta(asset)],
        )
        logger.debug("Upserted asset '{}' ({})", asset.name, asset.id)

    def search(
        self,
        query: str,
        limit: int = 10,
        style: StyleTag | None = None,
        anchor: AnchorPoint | None = None,
        indoor_only: bool = True,
    ) -> list[AssetMetadata]:
        where: dict[str, Any] = {}
        if indoor_only:
            where["indoor"] = True
        if style:
            where["style_tags"] = {"$contains": str(style)}
        if anchor:
            where["anchor_point"] = str(anchor)

        results = self._collection.query(
            query_embeddings=[self._embed(query)],
            n_results=min(limit, max(self._collection.count(), 1)),
            where=where or None,
            include=["documents", "metadatas", "distances"],
        )

        assets: list[AssetMetadata] = []
        for meta in (results["metadatas"] or [[]])[0]:
            try:
                assets.append(self._meta_to_asset(meta))
            except Exception as exc:
                logger.warning("Failed to deserialise asset metadata: {}", exc)
        return assets

    def get(self, asset_id: str) -> AssetMetadata | None:
        result = self._collection.get(ids=[asset_id], include=["metadatas"])
        metas = result.get("metadatas") or []
        if not metas:
            return None
        return self._meta_to_asset(metas[0])

    def count(self) -> int:
        return self._collection.count()

    # ── Internal helpers ───────────────────────────────────────────────────

    def _embed(self, text: str) -> list[float]:
        return self._embedder.encode(text, normalize_embeddings=True).tolist()

    @staticmethod
    def _asset_to_text(asset: AssetMetadata) -> str:
        tags = " ".join(asset.style_tags)
        return (
            f"{asset.name}. {asset.description}. "
            f"Category: {asset.category}. Tags: {tags}. "
            f"Anchor: {asset.anchor_point}."
        )

    @staticmethod
    def _asset_to_meta(asset: AssetMetadata) -> dict[str, Any]:
        return {
            "id": str(asset.id),
            "name": asset.name,
            "description": asset.description,
            "glb_path": asset.glb_path or "",
            "obj_path": asset.obj_path or "",
            "preview_image_path": asset.preview_image_path or "",
            "style_tags": json.dumps(asset.style_tags),
            "category": asset.category,
            "anchor_point": asset.anchor_point,
            "indoor": asset.indoor,
            "collision_radius": asset.collision_radius,
            "source_prompt": asset.source_prompt,
            "generated": asset.generated,
        }

    @staticmethod
    def _meta_to_asset(meta: dict[str, Any]) -> AssetMetadata:
        style_tags = json.loads(meta.get("style_tags", "[]"))
        return AssetMetadata(
            id=uuid.UUID(meta["id"]),
            name=meta["name"],
            description=meta["description"],
            glb_path=meta.get("glb_path") or None,
            obj_path=meta.get("obj_path") or None,
            preview_image_path=meta.get("preview_image_path") or None,
            style_tags=style_tags,
            category=meta.get("category", ""),
            anchor_point=meta.get("anchor_point", AnchorPoint.FLOOR),
            indoor=bool(meta.get("indoor", True)),
            collision_radius=float(meta.get("collision_radius", 0.5)),
            source_prompt=meta.get("source_prompt", ""),
            generated=bool(meta.get("generated", True)),
        )

"""Rada AI — FastAPI application entry point."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

import services.pipeline as pipeline_module
from api.routes import router
from database.vector_store import AssetVectorStore
from services.assembly.scene_director import SceneDirector
from services.generation.diffusion_service import DiffusionService
from services.generation.mesh_service import MeshService
from services.pipeline import PipelineOrchestrator
from services.semantic.tagger_service import TaggerService

load_dotenv()

app = FastAPI(
    title="Rada AI",
    description=(
        "Spatial generative platform — 2D aesthetic fidelity "
        "meets semantic 3D world-building."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup() -> None:
    logger.info("Rada AI starting up…")

    vector_store = AssetVectorStore(
        persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./storage/chroma")
    )
    diffusion = DiffusionService(
        model_id=os.getenv("SDXL_MODEL_ID")
    )
    mesh = MeshService()
    tagger = TaggerService(
        use_ollama=os.getenv("USE_OLLAMA", "true").lower() == "true",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
    )
    director = SceneDirector(
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        model=os.getenv("DIRECTOR_MODEL", "llama3:8b"),
    )

    # Pre-load the diffusion pipeline (heavy — GPU warm-up)
    await diffusion.load()

    orchestrator = PipelineOrchestrator(
        vector_store=vector_store,
        diffusion=diffusion,
        mesh=mesh,
        tagger=tagger,
        director=director,
        min_assets_before_generation=int(
            os.getenv("MIN_CACHED_ASSETS", "3")
        ),
    )

    # Expose singleton to dependency injection
    pipeline_module._orchestrator = orchestrator
    logger.info("Rada AI ready — {} assets in vector DB", vector_store.count())


@app.on_event("shutdown")
async def shutdown() -> None:
    logger.info("Rada AI shutting down…")
    if pipeline_module._orchestrator:
        await pipeline_module._orchestrator._diffusion.unload()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level="info",
    )

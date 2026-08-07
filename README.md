# Rada AI

Spatial generative platform that merges the 2D aesthetic fidelity of Midjourney with the semantic 3D world-building of Promethean AI.

## Architecture

```
User Prompt
    │
    ▼
FastAPI Orchestrator
    ├─── Visual Assets Pipeline
    │        Stable Diffusion XL (2D)
    │            │
    │        TripoSR (3D Mesh)
    │            │ Geometry
    │
    └─── Semantic Processing
             LLaVA + ChromaDB
                 │ Context
    ┌────────────┘
    ▼
Scene Director LLM
    │ JSON Scene Graph
    ▼
Three.js Viewer / Unreal Export
```

## Stack

| Layer | Technology |
|---|---|
| API & Orchestration | FastAPI + Python 3.11 |
| 2D Generation | Stable Diffusion XL (Diffusers) |
| 2D → 3D | TripoSR + trimesh |
| Semantic Tagging | LLaVA 13B (Ollama) / GPT-4o fallback |
| Vector DB | ChromaDB + sentence-transformers |
| Scene Director | Llama 3 8B (Ollama) |
| Frontend | React + Three.js (@react-three/fiber) |
| Export | Unreal Engine 5 Python Editor API |

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/Devesh1105/rada-ai.git
cd rada-ai
cp .env.example .env
# Edit .env — add OPENAI_API_KEY if you want GPT-4o fallback
```

### 2. Install TripoSR and Ollama models

```bash
bash scripts/install_triposr.sh
bash scripts/pull_ollama_models.sh   # requires Ollama running locally
```

### 3a. Run with Docker Compose (recommended)

```bash
docker compose up --build
```

- API: http://localhost:8000
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

### 3b. Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# In a separate terminal:
cd frontend && npm install && npm run dev
```

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/generate` | Submit scene generation job |
| `GET` | `/api/v1/generate/{job_id}` | Poll job status / retrieve scene graph |
| `POST` | `/api/v1/assets/search` | Semantic asset search |
| `GET` | `/api/v1/assets/{id}` | Retrieve single asset |
| `GET` | `/api/v1/health` | Health check |

### Example

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A cozy cyberpunk reading nook", "style": "cyberpunk", "max_assets": 8}'
```

## Unreal Engine Export

```bash
# Dry run (no UE required)
python scripts/export_to_unreal.py scene_graph.json --dry-run

# Inside UE5 Python console
from scripts.export_to_unreal import export_scene
export_scene("scene_graph.json", "/Game/RadaAI/Scenes/MyScene")
```

## Project Structure

```
rada-ai/
├── main.py                          # FastAPI app + service wiring
├── api/routes.py                    # REST endpoints
├── models/schemas.py                # Pydantic schemas
├── database/vector_store.py         # ChromaDB asset store
├── services/
│   ├── pipeline.py                  # Central async orchestrator
│   ├── generation/
│   │   ├── diffusion_service.py     # SDXL wrapper
│   │   └── mesh_service.py          # TripoSR → GLB
│   ├── semantic/tagger_service.py   # LLaVA / GPT-4V tagger
│   └── assembly/scene_director.py  # LLM scene composer
├── frontend/                        # React + Three.js viewer
├── scripts/
│   ├── export_to_unreal.py         # UE5 export
│   ├── install_triposr.sh
│   └── pull_ollama_models.sh
└── tests/
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SDXL_MODEL_ID` | SDXL base 1.0 | HuggingFace model ID for 2D generation |
| `USE_OLLAMA` | `true` | Use local Ollama for VLM tagging |
| `OPENAI_API_KEY` | — | GPT-4o fallback for tagging / scene direction |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API endpoint |
| `DIRECTOR_MODEL` | `llama3:8b` | Ollama model for scene graph generation |
| `CHROMA_PERSIST_DIR` | `./storage/chroma` | ChromaDB persistence path |
| `MIN_CACHED_ASSETS` | `3` | Min cached assets before triggering generation |

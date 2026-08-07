"""API integration tests (no GPU required — services are mocked)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from main import app
from models.schemas import GenerationResponse, GenerationStatus, SceneGraph


@pytest.fixture
def mock_orchestrator():
    orch = MagicMock()
    orch.create_job.return_value = uuid4()
    orch.vector_store.search.return_value = []
    orch.vector_store.get.return_value = None
    orch.vector_store.count.return_value = 0
    return orch


@pytest.fixture
def client(mock_orchestrator):
    import services.pipeline as pm

    pm._orchestrator = mock_orchestrator
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_generate_returns_202(client, mock_orchestrator):
    r = client.post(
        "/api/v1/generate",
        json={"prompt": "A cozy reading nook"},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "pending"
    assert "job_id" in body


def test_get_job_not_found(client, mock_orchestrator):
    mock_orchestrator.get_job.return_value = None
    r = client.get(f"/api/v1/generate/{uuid4()}")
    assert r.status_code == 404


def test_asset_search(client, mock_orchestrator):
    r = client.post(
        "/api/v1/assets/search",
        json={"query": "cyberpunk desk", "limit": 5},
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0

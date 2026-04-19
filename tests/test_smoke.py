"""Smoke tests for the API."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health() -> None:
    """Health endpoint returns status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_providers_crud_roundtrip() -> None:
    """Exercise the providers CRUD lifecycle end to end."""
    payload = {
        "name": "local-ollama-test",
        "kind": "ollama",
        "base_url": "http://localhost:11434",
        "default_model": "llama3",
    }
    created = client.post("/api/v1/providers", json=payload)
    assert created.status_code == 201, created.text
    provider_id = created.json()["id"]

    fetched = client.get(f"/api/v1/providers/{provider_id}")
    assert fetched.status_code == 200

    updated = client.patch(
        f"/api/v1/providers/{provider_id}",
        json={"description": "Updated via test"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated via test"

    deleted = client.delete(f"/api/v1/providers/{provider_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_postman_collection() -> None:
    """Postman collection endpoint returns a v2.1 envelope."""
    response = client.get("/api/v1/postman/collection")
    assert response.status_code == 200
    body = response.json()
    assert "info" in body and "item" in body
    assert body["info"]["schema"].startswith("https://schema.getpostman.com")

"""Generate a Postman v2.1 collection from the running FastAPI schema."""

from typing import Any
from uuid import uuid4

from fastapi import FastAPI

from app.core.config import get_settings


def build_postman_collection(app: FastAPI) -> dict[str, Any]:
    """Generate a Postman collection matching the live OpenAPI schema."""
    settings = get_settings()
    openapi = app.openapi()
    base_url = settings.public_base_url.rstrip("/")

    groups: dict[str, list[dict[str, Any]]] = {}
    for path, methods in openapi.get("paths", {}).items():
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            folder = _folder_for(op, path)
            item = _build_request_item(base_url, path, method, op)
            groups.setdefault(folder, []).append(item)

    folders = [
        {"name": name, "item": groups[name]} for name in sorted(groups)
    ]

    return {
        "info": {
            "_postman_id": str(uuid4()),
            "name": settings.app_name,
            "description": openapi.get("info", {}).get("description", "brain-llm API"),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": folders,
        "variable": [{"key": "baseUrl", "value": base_url}],
    }


def _folder_for(op: dict, path: str) -> str:
    """Pick the folder name for an operation: OpenAPI tag, else path prefix."""
    tags = op.get("tags") or []
    if tags:
        return str(tags[0])

    for segment in path.strip("/").split("/"):
        if segment and not segment.startswith("{"):
            if segment not in {"api", "v1"}:
                return segment
    return "default"



def _build_request_item(base_url: str, path: str, method: str, op: dict) -> dict[str, Any]:
    """Build a single Postman request item from an OpenAPI operation."""
    url_path = path.replace("{", ":").replace("}", "")
    segments = [seg for seg in url_path.strip("/").split("/") if seg]

    request: dict[str, Any] = {
        "method": method.upper(),
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "url": {
            "raw": f"{base_url}{url_path}",
            "host": ["{{baseUrl}}"],
            "path": segments,
        },
    }

    body_example = _build_body_example(op)
    if body_example is not None:
        request["body"] = {
            "mode": "raw",
            "raw": body_example,
            "options": {"raw": {"language": "json"}},
        }

    return {
        "name": op.get("summary") or f"{method.upper()} {path}",
        "request": request,
        "response": [],
    }


def _build_body_example(op: dict) -> str | None:
    """Return a JSON body example for the operation, if one is defined."""
    request_body = op.get("requestBody")
    if not request_body:
        return None
    content = request_body.get("content", {}).get("application/json", {})
    example = content.get("example") or _first_example(content.get("examples"))
    if example is not None:
        return _to_json(example)
    schema = content.get("schema")
    return _to_json({}) if schema else None


def _first_example(examples: dict | None) -> Any | None:
    """Return the first example value from a Postman-style examples dict."""
    if not examples:
        return None
    first = next(iter(examples.values()), None)
    return first.get("value") if isinstance(first, dict) else None


def _to_json(value: Any) -> str:
    """JSON dump helper kept small so it fits the project style."""
    import json

    return json.dumps(value, indent=2)

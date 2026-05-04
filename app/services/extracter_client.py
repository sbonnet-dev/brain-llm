"""Client for the Extracter service.

Wraps ``POST /api/v1/extract`` on the Extracter (Apache Tika) microservice
so any file type (pdf, docx, pptx, xlsx, txt, md, csv, …) can be turned
into RAG-ready chunks before being embedded into a knowledge base.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedChunk:
    index: int
    text: str
    token_count: int = 0
    start_token: int = 0
    end_token: int = 0


@dataclass
class ExtractionResult:
    text: str
    char_count: int
    word_count: int
    cleaned: bool
    sha256: str = ""
    detected_mime_type: str | None = None
    chunks: list[ExtractedChunk] = field(default_factory=list)


def extract_chunks(
    file_path: str | Path,
    *,
    filename: str | None = None,
    chunk: bool = True,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    clean: bool = True,
    preserve_structure: bool = True,
    ocr_enabled: bool = True,
) -> ExtractionResult:
    """Send ``file_path`` to the Extracter service and return its output.

    The service is expected at :pyattr:`Settings.extracter_url`. ``chunk``
    defaults to ``True`` so callers get token-bounded chunks ready for
    embedding; pass ``chunk=False`` if only the cleaned text is needed.
    """
    settings = get_settings()
    base = settings.extracter_url.rstrip("/")
    url = f"{base}/api/v1/extract"

    headers: dict[str, str] = {}
    if settings.extracter_api_key:
        headers["x-api-key"] = settings.extracter_api_key

    cs = chunk_size if chunk_size is not None else settings.extracter_chunk_size
    co = chunk_overlap if chunk_overlap is not None else settings.extracter_chunk_overlap

    data: dict[str, str] = {
        "clean": _bool_str(clean),
        "preserve_structure": _bool_str(preserve_structure),
        "ocr_enabled": _bool_str(ocr_enabled),
        "chunk": _bool_str(chunk),
    }
    if chunk:
        data["chunk_size"] = str(cs)
        data["chunk_overlap"] = str(co)

    path = Path(file_path)
    if not path.exists():
        raise ValidationError(f"File not found at {path}")

    name = filename or path.name
    try:
        with path.open("rb") as fp:
            files = {"file": (name, fp)}
            with httpx.Client(timeout=settings.extracter_timeout_s) as client:
                resp = client.post(url, headers=headers, data=data, files=files)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500] if exc.response is not None else ""
        raise ValidationError(
            f"Extracter returned HTTP {exc.response.status_code}: {body}"
        ) from exc
    except httpx.HTTPError as exc:
        raise ValidationError(f"Extracter request failed: {exc}") from exc

    payload = resp.json()
    file_info = payload.get("file") or {}
    raw_chunks = payload.get("chunks") or []

    chunks = [
        ExtractedChunk(
            index=int(c.get("index", i)),
            text=str(c.get("text", "") or ""),
            token_count=int(c.get("token_count", 0) or 0),
            start_token=int(c.get("start_token", 0) or 0),
            end_token=int(c.get("end_token", 0) or 0),
        )
        for i, c in enumerate(raw_chunks)
    ]

    return ExtractionResult(
        text=str(payload.get("text", "") or ""),
        char_count=int(payload.get("char_count", 0) or 0),
        word_count=int(payload.get("word_count", 0) or 0),
        cleaned=bool(payload.get("cleaned", False)),
        sha256=str(file_info.get("sha256") or ""),
        detected_mime_type=file_info.get("detected_mime_type"),
        chunks=chunks,
    )


def _bool_str(value: bool) -> str:
    return "true" if value else "false"

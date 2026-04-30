"""Knowledge bases — CRUD, file storage and Qdrant ingestion."""

from __future__ import annotations

import mimetypes
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging_config import get_logger
from app.models.knowledge import (
    STATUS_FAILED,
    STATUS_PROCESSED,
    STATUS_PROCESSING,
    STATUS_TYPES,
    Knowledge,
    KnowledgeFile,
)
from app.models.model import Model
from app.models.provider import Provider
from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate
from app.services.base import CRUDBase

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Knowledge-base CRUD
# ---------------------------------------------------------------------------


class KnowledgeService(CRUDBase[Knowledge, KnowledgeCreate, KnowledgeUpdate]):
    """Knowledge-base CRUD with sensible defaults."""

    def create(self, db: Session, payload: KnowledgeCreate) -> Knowledge:
        _validate_references(db, embedder_model_id=payload.embedder_model_id)
        item = super().create(db, payload)
        # Default the Qdrant collection name to `kb_{id}` when not provided.
        if not item.collection_name:
            item.collection_name = f"kb_{item.id}"
            db.commit()
            db.refresh(item)
        return item

    def update(self, db: Session, item_id: int, payload: KnowledgeUpdate) -> Knowledge:
        _validate_references(db, embedder_model_id=payload.embedder_model_id)
        return super().update(db, item_id, payload)

    def delete(self, db: Session, item_id: int) -> int:
        """Delete a KB: also wipe its files from disk and its Qdrant collection."""
        item = self.get(db, item_id)
        collection = item.collection_name

        # Drop Qdrant collection first, best-effort.
        if collection:
            try:
                _drop_qdrant_collection(collection)
            except Exception as exc:  # pragma: no cover - depends on external service
                logger.warning("Could not drop Qdrant collection %s: %s", collection, exc)

        # Remove the KB's file directory on disk.
        kb_dir = _kb_storage_dir(item_id)
        if kb_dir.exists():
            shutil.rmtree(kb_dir, ignore_errors=True)

        return super().delete(db, item_id)


knowledge_service = KnowledgeService(Knowledge, "Knowledge")


# ---------------------------------------------------------------------------
# Knowledge-file management
# ---------------------------------------------------------------------------


class KnowledgeFileService:
    """Manage the files that back a knowledge base."""

    def list_for_kb(self, db: Session, kb_id: int) -> list[KnowledgeFile]:
        knowledge_service.get(db, kb_id)  # existence check
        stmt = select(KnowledgeFile).where(KnowledgeFile.knowledge_id == kb_id)
        return list(db.execute(stmt).scalars().all())

    def get(self, db: Session, kb_id: int, file_id: int) -> KnowledgeFile:
        knowledge_service.get(db, kb_id)
        kf = db.get(KnowledgeFile, file_id)
        if kf is None or kf.knowledge_id != kb_id:
            raise NotFoundError(
                f"File with id={file_id} not found in knowledge base {kb_id}"
            )
        return kf

    def add_file(
        self,
        db: Session,
        kb_id: int,
        *,
        filename: str,
        content: bytes,
        mime_type: str | None = None,
    ) -> KnowledgeFile:
        """Store an uploaded file on disk and register it in the DB."""
        knowledge_service.get(db, kb_id)

        if not filename:
            raise ValidationError("File name is required")

        kb_dir = _kb_storage_dir(kb_id)
        kb_dir.mkdir(parents=True, exist_ok=True)

        safe_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
        storage_path = kb_dir / safe_name
        storage_path.write_bytes(content)

        mt = mime_type or mimetypes.guess_type(filename)[0]

        kf = KnowledgeFile(
            knowledge_id=kb_id,
            filename=filename,
            mime_type=mt,
            size_bytes=len(content),
            storage_path=str(storage_path),
        )
        db.add(kf)
        db.commit()
        db.refresh(kf)
        logger.info("Added file id=%s to KB %s (%s bytes)", kf.id, kb_id, kf.size_bytes)
        return kf

    def update_content(
        self,
        db: Session,
        kb_id: int,
        file_id: int,
        *,
        content: str,
        mime_type: str | None = None,
    ) -> KnowledgeFile:
        """Replace the file's textual content on disk and bump its status."""
        from app.models.knowledge import STATUS_NOT_PROCESSED

        kf = self.get(db, kb_id, file_id)
        path = Path(kf.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        kf.size_bytes = path.stat().st_size
        if mime_type is not None:
            kf.mime_type = mime_type
        # Content has changed → re-ingestion is needed.
        kf.status_id = STATUS_NOT_PROCESSED
        kf.error_message = None
        db.commit()
        db.refresh(kf)
        return kf

    def read_content(self, db: Session, kb_id: int, file_id: int) -> str:
        """Return the file's textual content (decoded as UTF-8, best effort)."""
        kf = self.get(db, kb_id, file_id)
        path = Path(kf.storage_path)
        if not path.exists():
            raise NotFoundError(f"File {file_id} is missing on disk at {path}")
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError(
                f"File {file_id} is not a text file and cannot be returned as content"
            ) from exc

    def read_bytes(self, db: Session, kb_id: int, file_id: int) -> tuple[KnowledgeFile, bytes]:
        """Return the raw bytes of a file (used for the /source endpoint)."""
        kf = self.get(db, kb_id, file_id)
        path = Path(kf.storage_path)
        if not path.exists():
            raise NotFoundError(f"File {file_id} is missing on disk at {path}")
        return kf, path.read_bytes()

    def delete(self, db: Session, kb_id: int, file_id: int) -> int:
        kf = self.get(db, kb_id, file_id)
        path = Path(kf.storage_path)
        if path.exists():
            try:
                path.unlink()
            except OSError as exc:  # pragma: no cover
                logger.warning("Could not delete file %s: %s", path, exc)
        db.delete(kf)
        db.commit()
        return file_id


knowledge_file_service = KnowledgeFileService()


# ---------------------------------------------------------------------------
# Status types
# ---------------------------------------------------------------------------


def list_status_types() -> list[dict]:
    """Return the fixed list of KB/file status types."""
    return list(STATUS_TYPES)


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


class KnowledgeIngestionService:
    """Index knowledge-base files into Qdrant via Agno."""

    def ingest_kb(self, db: Session, kb_id: int) -> dict:
        kb = knowledge_service.get(db, kb_id)
        files = knowledge_file_service.list_for_kb(db, kb_id)

        kb.status_id = STATUS_PROCESSING
        db.commit()

        processed, failed = 0, 0
        last_error: str | None = None

        for kf in files:
            try:
                self._ingest_file(db, kb, kf)
                processed += 1
            except Exception as exc:  # pragma: no cover - external services
                failed += 1
                last_error = str(exc)
                logger.exception("Failed to ingest file %s: %s", kf.id, exc)

        kb.status_id = STATUS_FAILED if failed and not processed else STATUS_PROCESSED
        db.commit()

        return {
            "knowledge_id": kb_id,
            "status_id": kb.status_id,
            "files_processed": processed,
            "files_failed": failed,
            "message": last_error,
        }

    def ingest_file(self, db: Session, file_id: int) -> dict:
        kf = db.get(KnowledgeFile, file_id)
        if kf is None:
            raise NotFoundError(f"File with id={file_id} not found")
        kb = knowledge_service.get(db, kf.knowledge_id)

        try:
            self._ingest_file(db, kb, kf)
            return {
                "knowledge_id": kb.id,
                "file_id": kf.id,
                "status_id": kf.status_id,
                "files_processed": 1,
                "files_failed": 0,
            }
        except Exception as exc:
            logger.exception("Failed to ingest file %s: %s", file_id, exc)
            return {
                "knowledge_id": kb.id,
                "file_id": kf.id,
                "status_id": STATUS_FAILED,
                "files_processed": 0,
                "files_failed": 1,
                "message": str(exc),
            }

    def _ingest_file(self, db: Session, kb: Knowledge, kf: KnowledgeFile) -> None:
        """Index one file into the KB's Qdrant collection."""
        from app.agno_integration.knowledge_builder import ingest_file_into_kb

        kf.status_id = STATUS_PROCESSING
        kf.error_message = None
        db.commit()

        try:
            ingest_file_into_kb(db, kb, kf)
            kf.status_id = STATUS_PROCESSED
            db.commit()
        except Exception as exc:
            kf.status_id = STATUS_FAILED
            kf.error_message = str(exc)[:2000]
            db.commit()
            raise


knowledge_ingestion_service = KnowledgeIngestionService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kb_storage_dir(kb_id: int) -> Path:
    settings = get_settings()
    return Path(settings.knowledge_storage_dir) / str(kb_id)


def _drop_qdrant_collection(collection: str) -> None:
    """Best-effort drop of a Qdrant collection (used when deleting a KB)."""
    settings = get_settings()
    url = os.environ.get("QDRANT_URL", settings.qdrant_url)
    api_key = os.environ.get("QDRANT_API_KEY") or settings.qdrant_api_key
    try:
        from qdrant_client import QdrantClient  # type: ignore
    except ImportError:  # pragma: no cover
        logger.info("qdrant-client not installed — skipping drop of collection %s", collection)
        return

    client = QdrantClient(url=url, api_key=api_key or None)
    if client.collection_exists(collection):
        client.delete_collection(collection)
        logger.info("Dropped Qdrant collection %s", collection)


def resolve_vector_db_config(kb: Knowledge) -> dict[str, Any]:
    """Return the effective vector-db config for a KB (defaults → Qdrant)."""
    settings = get_settings()
    cfg = dict(kb.vector_db or {})
    cfg.setdefault("type", "qdrant")
    cfg.setdefault("url", settings.qdrant_url)
    if settings.qdrant_api_key:
        cfg.setdefault("api_key", settings.qdrant_api_key)
    cfg.setdefault("collection", kb.collection_name or f"kb_{kb.id}")
    return cfg


def resolve_embedder_config(db: Session, kb: Knowledge) -> dict[str, Any]:
    """Return the effective embedder config for a KB.

    If ``kb.embedder_model_id`` is set, the dict is built from the linked
    Model + Provider rows so that ``model.extra_config`` (dimensions, etc.)
    and provider credentials are picked up automatically. Otherwise we fall
    back to the env-defined defaults.
    """
    settings = get_settings()

    if kb.embedder_model_id is None:
        return {
            "provider": settings.knowledge_default_embedder_provider,
            "model": settings.knowledge_default_embedder_model,
        }

    model = db.get(Model, kb.embedder_model_id)
    if model is None:
        raise ValidationError(
            f"Embedder model with id={kb.embedder_model_id} no longer exists"
        )
    provider = db.get(Provider, model.provider_id)
    if provider is None:
        raise ValidationError(
            f"Provider with id={model.provider_id} no longer exists"
        )

    cfg: dict[str, Any] = {
        "provider": provider.provider_type,
        "model": model.name,
    }
    # OllamaEmbedder takes ``host``; OpenAI-compatible embedders take ``base_url`` + ``api_key``.
    if provider.provider_type == "ollama":
        cfg["host"] = provider.base_url
    else:
        cfg["base_url"] = provider.base_url
        if provider.api_key:
            cfg["api_key"] = provider.api_key
    # Per-model overrides (dimensions, custom kwargs, …) win last.
    if model.extra_config:
        cfg.update(model.extra_config)
    return cfg


def _validate_references(db: Session, *, embedder_model_id: int | None) -> None:
    """Ensure the embedder Model exists and has model_type='embedder'."""
    if embedder_model_id is None:
        return
    model = db.get(Model, embedder_model_id)
    if model is None:
        raise ValidationError(f"Model with id={embedder_model_id} does not exist")
    if model.model_type != "embedder":
        raise ValidationError(
            f"Model id={embedder_model_id} has model_type='{model.model_type}', "
            "expected 'embedder'"
        )

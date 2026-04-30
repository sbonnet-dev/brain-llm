"""Build Agno knowledge bases from stored KnowledgeBase records.

The vector store is Qdrant by default. Each KB owns one Qdrant collection
whose name is ``kb.collection_name`` (``kb_{id}`` if unset).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.logging_config import get_logger
from app.models.knowledge import Knowledge, KnowledgeFile

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------


def build_vector_db(config: dict | None) -> Any:
    """Return an Agno vector-db instance for ``config`` (defaults to Qdrant)."""
    cfg = dict(config or {})
    db_type = (cfg.pop("type", "qdrant") or "qdrant").lower()

    if db_type == "qdrant":
        from agno.vectordb.qdrant import Qdrant  # type: ignore

        collection = cfg.pop("collection", None) or cfg.pop("collection_name", None)
        if not collection:
            raise ValidationError("Qdrant configuration requires a 'collection' name")
        # Agno's Qdrant accepts `url`, `api_key`, `https`, `prefix`, ...
        return Qdrant(collection=collection, **cfg)

    if db_type == "lancedb":
        from agno.vectordb.lancedb import LanceDb  # type: ignore

        return LanceDb(**cfg)

    if db_type == "pgvector":
        from agno.vectordb.pgvector import PgVector  # type: ignore

        return PgVector(**cfg)

    if db_type == "chromadb":
        from agno.vectordb.chroma import ChromaDb  # type: ignore

        return ChromaDb(**cfg)

    raise ValidationError(f"Unsupported vector_db type: {db_type}")


# ---------------------------------------------------------------------------
# Embedder
# ---------------------------------------------------------------------------


def build_embedder(config: dict | None) -> Any | None:
    """Instantiate an Agno embedder from a generic ``{provider, model, ...}`` dict."""
    if not config:
        return None

    cfg = dict(config)
    provider = (cfg.pop("provider", "") or "").lower()
    model = cfg.pop("model", None)

    if not provider or not model:
        return None

    if provider == "ollama":
        from agno.knowledge.embedder.ollama import OllamaEmbedder  # type: ignore

        return OllamaEmbedder(id=model, **cfg)

    if provider in {"openai", "mistral", "openai_compatible", "vllm"}:
        from agno.knowledge.embedder.openai import OpenAIEmbedder  # type: ignore

        # AdminLLM passes the provider URL as `host`; Agno's OpenAIEmbedder expects `base_url`.
        if "host" in cfg and "base_url" not in cfg:
            cfg["base_url"] = cfg.pop("host")
        return OpenAIEmbedder(id=model, **cfg)

    logger.warning("Unknown embedder provider '%s' — falling back to default", provider)
    return None


# ---------------------------------------------------------------------------
# Knowledge bases
# ---------------------------------------------------------------------------


def build_knowledge(db: Session, knowledge: Knowledge) -> Any:
    """Build a runnable Agno Knowledge instance for ``knowledge``.

    This wires the KB to its Qdrant collection so that an agent using it can
    perform similarity searches, but does not ingest anything. ``db`` is used
    to resolve the linked embedder Model + Provider rows.
    """
    from app.services.knowledge_service import (
        resolve_embedder_config,
        resolve_vector_db_config,
    )

    vector_cfg = resolve_vector_db_config(knowledge)
    embedder_cfg = resolve_embedder_config(db, knowledge)

    embedder = build_embedder(embedder_cfg)
    if embedder is not None:
        # Pass the embedder to the vector DB so Qdrant uses it for queries too.
        vector_cfg["embedder"] = embedder

    vector_db = build_vector_db(vector_cfg)

    try:
        from agno.knowledge.knowledge import Knowledge as AgnoKnowledge  # type: ignore

        return AgnoKnowledge(
            name=knowledge.name,
            description=knowledge.description,
            vector_db=vector_db,
        )
    except ImportError:
        # Older Agno layouts expose a generic knowledge base under a different path.
        from agno.knowledge.text import TextKnowledgeBase  # type: ignore

        return TextKnowledgeBase(vector_db=vector_db)


def ingest_file_into_kb(db: Session, knowledge: Knowledge, file: KnowledgeFile) -> None:
    """Load ``file`` into the KB's vector store."""
    kb = build_knowledge(db, knowledge)
    path = file.storage_path

    # Agno's newer Knowledge class exposes add_content(path=...).
    if hasattr(kb, "add_content"):
        kb.add_content(path=path, name=file.filename)
        return

    # Fall back to the older `.load()` style used by *KnowledgeBase classes.
    if hasattr(kb, "load_document"):
        kb.load_document(path=path)
        return
    if hasattr(kb, "load"):
        kb.path = path  # type: ignore[attr-defined]
        kb.load(recreate=False, upsert=True)  # type: ignore[attr-defined]
        return

    raise ValidationError(
        "The installed Agno version does not expose a supported ingestion API "
        "(expected Knowledge.add_content or *KnowledgeBase.load)."
    )

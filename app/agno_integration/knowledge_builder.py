"""Build Agno knowledge bases from stored KnowledgeBase records.

The vector store is Qdrant by default. Each KB owns one Qdrant collection
whose name is ``kb.collection_name`` (``kb_{id}`` if unset).
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.logging_config import get_logger
from app.models.knowledge import Knowledge, KnowledgeFile

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Multi-KB wrapper
# ---------------------------------------------------------------------------


class MultiKnowledge:
    """Aggregate several Agno ``Knowledge`` instances behind a single protocol.

    Agno's ``Agent.knowledge`` is typed as a single ``KnowledgeProtocol``, so we
    expose a wrapper that fans ``retrieve``/``aretrieve`` out to every attached
    KB and merges the results by score. The protocol methods
    (``build_context``, ``get_tools``, ``aget_tools``) are also delegated so
    the agent's system prompt and tool list stay consistent.
    """

    def __init__(self, knowledges: list[Any]) -> None:
        self.knowledges = list(knowledges)
        names = [getattr(k, "name", None) for k in self.knowledges]
        self.name = ", ".join(n for n in names if n) or "knowledge"

    def build_context(self, enable_agentic_filters: bool = False, **_: Any) -> str:
        blocks: list[str] = []
        seen: set[str] = set()
        for kb in self.knowledges:
            fn = getattr(kb, "build_context", None)
            if not callable(fn):
                continue
            ctx = fn(enable_agentic_filters=enable_agentic_filters)
            if ctx and ctx not in seen:
                seen.add(ctx)
                blocks.append(ctx)
        names = [getattr(k, "name", None) for k in self.knowledges]
        names = [n for n in names if n]
        if names:
            blocks.append(
                "<available_knowledge_bases>\n"
                + "\n".join(f"- {n}" for n in names)
                + "\n</available_knowledge_bases>"
            )
        return "\n".join(blocks)

    def get_tools(self, **kwargs: Any) -> list[Any]:
        tools: list[Any] = []
        for kb in self.knowledges:
            fn = getattr(kb, "get_tools", None)
            if callable(fn):
                tools.extend(fn(**kwargs) or [])
        return tools

    async def aget_tools(self, **kwargs: Any) -> list[Any]:
        tools: list[Any] = []
        for kb in self.knowledges:
            if not hasattr(kb, "aget_tools"):
                continue
            result = await kb.aget_tools(**kwargs)
            tools.extend(result or [])
        return tools

    def retrieve(
        self,
        query: str,
        max_results: int | None = None,
        filters: Any | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        results: list[Any] = []
        for kb in self.knowledges:
            fn = getattr(kb, "retrieve", None)
            if not callable(fn):
                continue
            try:
                docs = fn(query=query, max_results=max_results, filters=filters, **kwargs)
            except Exception as exc:
                logger.warning(
                    "retrieve failed for KB '%s': %s", getattr(kb, "name", "?"), exc
                )
                continue
            if docs:
                results.extend(docs)
        return _rank_and_cap(results, max_results)

    async def aretrieve(
        self,
        query: str,
        max_results: int | None = None,
        filters: Any | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        async def _one(kb: Any) -> list[Any]:
            if not hasattr(kb, "aretrieve"):
                return []
            try:
                docs = await kb.aretrieve(
                    query=query, max_results=max_results, filters=filters, **kwargs
                )
                return docs or []
            except Exception as exc:
                logger.warning(
                    "aretrieve failed for KB '%s': %s", getattr(kb, "name", "?"), exc
                )
                return []

        per_kb = await asyncio.gather(*(_one(kb) for kb in self.knowledges))
        return _rank_and_cap([doc for batch in per_kb for doc in batch], max_results)


def _rank_and_cap(docs: list[Any], max_results: int | None) -> list[Any]:
    """Sort docs by score desc (when present) and truncate to ``max_results``."""
    docs.sort(key=lambda d: getattr(d, "score", 0.0) or 0.0, reverse=True)
    if max_results:
        return docs[:max_results]
    return docs


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------


def _instrument_search(vector_db: Any, collection: str) -> None:
    """Wrap a vector-db's search methods so search results are logged at INFO."""

    def _summarize(results: Any) -> str:
        try:
            items = list(results) if results is not None else []
        except TypeError:
            return repr(results)
        parts = []
        for i, doc in enumerate(items[:5]):
            name = getattr(doc, "name", None) or getattr(doc, "id", None) or ""
            score = getattr(doc, "score", None)
            content = getattr(doc, "content", "") or ""
            snippet = content[:120].replace("\n", " ")
            score_s = f" score={score:.3f}" if isinstance(score, (int, float)) else ""
            parts.append(f"  [{i}]{score_s} {name}: {snippet}")
        more = f"\n  ... (+{len(items) - 5} more)" if len(items) > 5 else ""
        return f"{len(items)} hit(s)\n" + "\n".join(parts) + more

    for method_name in ("search", "async_search"):
        original = getattr(vector_db, method_name, None)
        if original is None or not callable(original):
            continue

        if method_name == "async_search":
            async def _wrapped(*args, _orig=original, **kwargs):  # type: ignore
                query = args[0] if args else kwargs.get("query", "")
                results = await _orig(*args, **kwargs)
                logger.info(
                    "Qdrant search [%s] query=%r -> %s",
                    collection, query, _summarize(results),
                )
                return results
        else:
            def _wrapped(*args, _orig=original, **kwargs):  # type: ignore
                query = args[0] if args else kwargs.get("query", "")
                results = _orig(*args, **kwargs)
                logger.info(
                    "Qdrant search [%s] query=%r -> %s",
                    collection, query, _summarize(results),
                )
                return results

        try:
            setattr(vector_db, method_name, _wrapped)
        except Exception:
            pass


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
        vdb = Qdrant(collection=collection, **cfg)
        _instrument_search(vdb, collection)
        return vdb

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
    """Index one file into the KB's vector store.

    The file is sent to the Extracter microservice to produce cleaned text
    and token-bounded chunks (pdf, docx, pptx, xlsx, txt, md, csv, …). Each
    chunk becomes a Document, is embedded with the KB's embedder, and is
    upserted into the configured vector DB.
    """
    Document = _resolve_document_class()
    from app.services.extracter_client import extract_chunks
    from app.services.knowledge_service import (
        resolve_embedder_config,
        resolve_vector_db_config,
    )

    extraction = extract_chunks(file.storage_path, filename=file.filename)
    if not extraction.chunks:
        logger.warning(
            "Extracter returned no chunks for file id=%s (%s) — skipping ingestion",
            file.id,
            file.filename,
        )
        return

    vector_cfg = resolve_vector_db_config(knowledge)
    embedder_cfg = resolve_embedder_config(db, knowledge)
    embedder = build_embedder(embedder_cfg)
    if embedder is not None:
        vector_cfg["embedder"] = embedder

    vector_db = build_vector_db(vector_cfg)

    # Make sure the collection exists (create() is a no-op if it does).
    if hasattr(vector_db, "create"):
        try:
            vector_db.create()
        except Exception as exc:  # pragma: no cover - external service
            logger.warning("Could not ensure vector collection exists: %s", exc)

    documents = [
        Document(
            id=f"kb{knowledge.id}_f{file.id}_c{c.index}",
            name=f"{file.filename}#chunk{c.index}",
            content=c.text,
            meta_data={
                "knowledge_id": knowledge.id,
                "file_id": file.id,
                "filename": file.filename,
                "chunk_index": c.index,
                "token_count": c.token_count,
            },
        )
        for c in extraction.chunks
        if c.text.strip()
    ]
    if not documents:
        logger.warning(
            "All extracted chunks were empty for file id=%s (%s) — nothing to ingest",
            file.id,
            file.filename,
        )
        return

    content_hash = extraction.sha256 or f"file_{file.id}_{file.size_bytes}"
    filters = {"knowledge_id": knowledge.id, "file_id": file.id}

    upsert_available = (
        hasattr(vector_db, "upsert_available") and callable(vector_db.upsert_available)
        and vector_db.upsert_available()
    )
    if upsert_available and hasattr(vector_db, "upsert"):
        vector_db.upsert(content_hash, documents, filters)
    elif hasattr(vector_db, "insert"):
        vector_db.insert(content_hash, documents=documents, filters=filters)
    else:
        raise ValidationError(
            "Configured vector DB does not expose insert/upsert; cannot ingest chunks."
        )

    logger.info(
        "Ingested %d chunks into KB %s for file %s (%s)",
        len(documents),
        knowledge.id,
        file.id,
        file.filename,
    )


def _resolve_document_class():
    """Locate Agno's Document dataclass across versions."""
    try:
        from agno.knowledge.document.base import Document  # type: ignore

        return Document
    except ImportError:
        pass
    try:
        from agno.knowledge.document import Document  # type: ignore

        return Document
    except ImportError as exc:  # pragma: no cover - defensive
        raise ValidationError(
            "Agno Document class not found; cannot ingest chunks into the vector store."
        ) from exc

"""Build Agno knowledge bases from stored Knowledge records."""

from typing import Any

from app.core.exceptions import ValidationError
from app.core.logging_config import get_logger
from app.models.knowledge import Knowledge

logger = get_logger(__name__)


def build_knowledge(knowledge: Knowledge) -> Any:
    """Instantiate an Agno knowledge base for ``knowledge``.

    The concrete Agno class depends on the source type. We only import
    the relevant module lazily to keep startup fast.
    """
    sources = knowledge.sources or []
    vector_db = _build_vector_db(knowledge.vector_db)

    if knowledge.source_type == "url":
        from agno.knowledge.url import UrlKnowledge  # type: ignore

        return UrlKnowledge(urls=sources, vector_db=vector_db)

    if knowledge.source_type == "pdf":
        from agno.knowledge.pdf import PDFKnowledgeBase  # type: ignore

        return PDFKnowledgeBase(path=sources[0] if sources else None, vector_db=vector_db)

    if knowledge.source_type == "text":
        from agno.knowledge.text import TextKnowledgeBase  # type: ignore

        return TextKnowledgeBase(path=sources[0] if sources else None, vector_db=vector_db)

    if knowledge.source_type == "markdown":
        from agno.knowledge.markdown import MarkdownKnowledgeBase  # type: ignore

        return MarkdownKnowledgeBase(path=sources[0] if sources else None, vector_db=vector_db)

    if knowledge.source_type == "website":
        from agno.knowledge.website import WebsiteKnowledgeBase  # type: ignore

        return WebsiteKnowledgeBase(urls=sources, vector_db=vector_db)

    raise ValidationError(f"Unsupported knowledge source_type: {knowledge.source_type}")


def _build_vector_db(config: dict | None) -> Any | None:
    """Instantiate the vector database described by ``config`` if provided."""
    if not config:
        return None

    db_type = config.get("type", "").lower()
    options = {k: v for k, v in config.items() if k != "type"}

    if db_type == "lancedb":
        from agno.vectordb.lancedb import LanceDb  # type: ignore

        return LanceDb(**options)
    if db_type == "pgvector":
        from agno.vectordb.pgvector import PgVector  # type: ignore

        return PgVector(**options)
    if db_type == "chromadb":
        from agno.vectordb.chroma import ChromaDb  # type: ignore

        return ChromaDb(**options)

    raise ValidationError(f"Unsupported vector_db type: {db_type}")

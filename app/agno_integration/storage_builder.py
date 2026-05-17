"""Build and cache the Agno persistence backend (``EncryptedPostgresDb``)."""

from typing import Any

from app.agno_integration.encrypted_postgres_db import EncryptedPostgresDb
from app.core.config import get_settings
from app.core.crypto import ensure_key_loaded
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_SESSION_DB: Any | None = None

_SCHEMA = "brain"
_SESSION_TABLE = "agno_sessions"


def get_session_db() -> Any:
    """Return the singleton encrypted ``PostgresDb`` shared by every agent and team."""
    global _SESSION_DB
    if _SESSION_DB is None:
        ensure_key_loaded()
        settings = get_settings()
        logger.info(
            "Initializing EncryptedPostgresDb session_table=%s schema=%s",
            _SESSION_TABLE,
            _SCHEMA,
        )
        _SESSION_DB = EncryptedPostgresDb(
            db_url=settings.database_url,
            db_schema=_SCHEMA,
            session_table=_SESSION_TABLE,
            create_schema=True,
        )
    return _SESSION_DB

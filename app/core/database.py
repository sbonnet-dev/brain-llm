"""SQLAlchemy database setup."""

from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False}
    if _settings.database_url.startswith("sqlite")
    else {},
    future=True,
)

# SQLite does not support named schemas — use None to keep tables in
# the default schema.  PostgreSQL and other engines use "brain".
_DB_SCHEMA: str | None = (
    None if _settings.database_url.startswith("sqlite") else "brain"
)

# For SQLite, enable FK enforcement so CASCADE deletes work correctly.
if _settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    """Declarative base for all ORM models.

    Tables are placed in the 'brain' schema on PostgreSQL (and any other
    engine that supports named schemas).  SQLite uses the default schema.
    """

    metadata = MetaData(schema=_DB_SCHEMA)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create the schema (if needed) and all tables at application startup."""
    # For SQLite, ensure the parent directory exists before the engine tries
    # to open the file — SQLAlchemy won't create intermediate directories.
    if _settings.database_url.startswith("sqlite"):
        import os

        db_path = _settings.database_url.split("sqlite:///", 1)[-1]
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    if _DB_SCHEMA is not None:
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_DB_SCHEMA}"))
            conn.commit()

    # Import every ORM module so its classes are registered on Base.metadata
    # before create_all() is called.
    from app.models import (  # noqa: F401  pylint: disable=import-outside-toplevel
        agent,
        knowledge,
        model,
        provider,
        suggestion,
        team,
        tool,
    )

    Base.metadata.create_all(bind=engine)

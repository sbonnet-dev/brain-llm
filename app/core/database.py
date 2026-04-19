"""SQLAlchemy database setup."""

from collections.abc import Iterator

from sqlalchemy import create_engine, event, text
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

# For SQLite, enable FK enforcement (required for CASCADE deletes to work).
if _settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    """Declarative base class for ORM models.

    All tables are created in the 'brain' schema (or ignored for SQLite).
    """

    schema = "brain"


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create schema and all tables. Called at application startup."""
    # For PostgreSQL, ensure the 'brain' schema exists.
    if not _settings.database_url.startswith("sqlite"):
        with engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS brain"))
            conn.commit()

    # Import models so that they are registered on the metadata.
    from app.models import (  # noqa: F401  pylint: disable=import-outside-toplevel
        agent,
        knowledge,
        model,
        provider,
        team,
        tool,
    )

    Base.metadata.create_all(bind=engine)

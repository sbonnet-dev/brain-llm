"""Alembic migration environment.

Reads the database URL from app.core.config (so DATABASE_URL env var works
out of the box) and uses Base.metadata for autogenerate. On PostgreSQL
(and any engine that supports schemas), tables live in the ``brain``
schema and the ``alembic_version`` bookkeeping table is placed there too.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

from alembic import context

# Make sure every ORM model is imported so its tables show up in Base.metadata.
from app.core.config import get_settings
from app.core.database import Base
from app.models import (  # noqa: F401
    agent,
    knowledge,
    model,
    provider,
    suggestion,
    team,
    tool,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the runtime DATABASE_URL (overrides the placeholder in alembic.ini).
_settings = get_settings()
config.set_main_option("sqlalchemy.url", _settings.database_url)

target_metadata = Base.metadata

_USES_SCHEMA = not _settings.database_url.startswith("sqlite")
_DB_SCHEMA: str | None = "brain" if _USES_SCHEMA else None


def _include_object(obj, name, type_, reflected, compare_to):
    """Restrict autogenerate to objects in our schema (avoid pg_catalog/etc.)."""
    if type_ == "table" and _USES_SCHEMA and obj.schema != _DB_SCHEMA:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=_USES_SCHEMA,
        version_table_schema=_DB_SCHEMA,
        include_object=_include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        if _DB_SCHEMA is not None:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_DB_SCHEMA}"))
            connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=_USES_SCHEMA,
            version_table_schema=_DB_SCHEMA,
            include_object=_include_object,
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

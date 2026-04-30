# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`brain-llm` is a FastAPI service that manages AI agents built with [Agno / AgentOS](https://docs.agno.com). It exposes a REST API to CRUD **Providers**, **Models**, **Tools**, **Knowledges**, **Agents** and **Teams**, plus endpoints to run them against a configured LLM backend (Ollama, VLLM, OpenAI or any OpenAI-compatible endpoint).

## Common commands

```bash
make install          # create .venv and install requirements.txt
make dev              # uvicorn with --reload and LOG_LEVEL=DEBUG
make run              # uvicorn without reload
make test             # pytest -q
make lint             # python -m compileall -q app
make postman          # download /api/v1/postman/collection to ./brain-llm.postman_collection.json

make docker-up        # docker compose up -d --build (brain-llm + ollama)
make docker-logs      # tail brain-llm container logs
make docker-down

make migrate                      # alembic upgrade head
make migrate-revision M="msg"     # alembic revision --autogenerate -m "msg"
make migrate-stamp                # alembic stamp head (mark current state as up-to-date)

# Run one test
.venv/bin/pytest tests/test_smoke.py::test_health -v

# Bootstrap providers/models/agents/teams from scripts/agents-config.yaml
python scripts/init-agents.py [--config PATH] [--base-url URL]
```

Swagger UI at `/docs`, ReDoc at `/redoc`, OpenAPI JSON at `/openapi.json`, health at `/health`.

## Architecture

Four layers, strict direction of dependency (top → bottom):

```
app/api/v1/*.py          # FastAPI routers — one per resource, thin, delegate to services
app/services/*.py        # Business logic + referential-integrity checks
app/schemas/*.py         # Pydantic request/response DTOs
app/models/*.py          # SQLAlchemy ORM
app/core/                # config, database, logging, exception envelope
app/agno_integration/    # Translate ORM rows into runnable Agno objects
```

### Generic CRUD pattern

`app/services/base.py` defines `CRUDBase[ModelT, CreateT, UpdateT]` with `list/get/create/update/delete`. Concrete services (e.g. `agent_service.py`) subclass it only to add referential-integrity checks via a `_validate_references` helper before delegating to `super()`. When adding a new resource, follow this pattern — don't reimplement CRUD.

### Resource dependency chain

```
Provider  ←—  Model  ←—  Agent / Team
```

- `Agent.model_id` and `Team.model_id` are FKs to `models.id` (not to `providers.id` — that change was made deliberately; do not reintroduce a `provider_id + model` string pair on Agent/Team).
- When building an Agno runnable, `app/agno_integration/factory.py` resolves `model_id → Model → Provider` and calls `build_model(provider, model_row.name)` (see `model_builder.py`, which dispatches on `provider.provider_type` to `Ollama`, `VLLM` or `OpenAILike`).
- Tools and knowledges are attached to agents/teams via JSON arrays of ids (`tool_ids`, `knowledge_ids`), not via relational joins.

### Database

- Default: SQLite at `./data/brain_llm.db`; the `data/` directory is auto-created by `init_db()` since SQLAlchemy will not create intermediate directories.
- PostgreSQL: tables live in a named `brain` schema (`Base.metadata = MetaData(schema="brain")`). SQLite falls back to the default schema. `init_db()` runs `CREATE SCHEMA IF NOT EXISTS brain` on non-SQLite engines.
- SQLite has `PRAGMA foreign_keys=ON` enabled via an event listener so `ondelete=CASCADE/RESTRICT/SET NULL` actually fires.
- Tables are created at startup via `Base.metadata.create_all()` (idempotent — only creates missing tables) **and** via Alembic migrations under `alembic/versions/`. Alembic is the source of truth for schema changes; `create_all()` remains a convenience for fresh installs.

### Migrations (Alembic)

- Apply pending migrations: `make migrate` (= `alembic upgrade head`).
- Add a new migration after editing ORM: `make migrate-revision M="describe change"`. Always review the generated file before committing.
- Mark an existing DB as up-to-date without running anything (e.g. when introducing Alembic on a DB that already matches the ORM, or after a manual `ALTER`): `make migrate-stamp`.
- Roll back one revision: `make migrate-down`.
- The DB URL comes from `Settings.database_url` (env var `DATABASE_URL`); the placeholder in `alembic.ini` is overridden at runtime by `alembic/env.py`.
- `env.py` puts both ORM tables and the `alembic_version` bookkeeping table in the `brain` schema on PostgreSQL; SQLite uses the default schema. SQLite migrations are rendered with `render_as_batch=True` so column-level ALTERs work.

### Running agents/teams

- `POST /api/v1/agents/{id}/run` and `POST /api/v1/teams/{id}/run` accept a `RunRequest` (`app/schemas/run.py`).
- `stream: true` in the payload switches the response to `text/event-stream` (SSE). Each SSE frame is `data: {"content": "..."}\n\n`, followed by a terminal `data: {"done": true, "id": ..., "kind": ...}\n\n`. Implemented in `stream_agent` / `stream_team` in `run_service.py`.
- Non-streaming responses go through `_to_run_response`, which calls `_jsonable()` to recursively coerce Agno's metrics (which contain types like `agno.utils.timer.Timer`) into JSON-safe primitives — Pydantic cannot serialize them otherwise.

### Error envelope

All application errors subclass `BrainLLMError` (`app/core/exceptions.py`: `NotFoundError`, `ValidationError`, `ConflictError`, `ProviderError`). They are rendered as `{"error": {"code": ..., "message": ..., "details": ...}}` with the matching HTTP status. A catch-all handler returns 500 `internal_error` for anything else.

### Postman collection

`app/services/postman_service.py` introspects the live FastAPI OpenAPI schema at request time and groups requests into folders by tag. No static collection file is checked in — regenerate via `GET /api/v1/postman/collection` or `make postman`.

### Bootstrap script

`scripts/init-agents.py` + `scripts/agents-config.yaml` replace the previous `init-agents.sh`. The YAML declares providers, models, agents and teams; entities reference each other by name (e.g. `agents[].model` + `agents[].provider`), and the script resolves those to ids when calling the API. The script is idempotent — it looks up each resource by name first and only creates missing ones.

## Git workflow

Feature work happens on `claude/ai-agent-manager-XLI7d`. After committing there and pushing, fast-forward merge into `dev` and push `dev` too:

```bash
git push -u origin claude/ai-agent-manager-XLI7d
git checkout dev && git pull origin dev
git merge claude/ai-agent-manager-XLI7d
git push -u origin dev
git checkout claude/ai-agent-manager-XLI7d
```

Do not push to `main`.

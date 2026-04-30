# brain-llm

Central hub to manage AI agents built with [Agno / AgentOS](https://docs.agno.com).
It exposes a REST API to CRUD **Providers**, **Tools**, **Knowledges**,
**Agents** and **Teams**, and to generate a ready-to-import **Postman** collection.

Local models are supported out of the box through:

* **Ollama** (`agno.models.ollama.Ollama`)
* **VLLM** (`agno.models.vllm.VLLM`, falls back to OpenAI-compatible)
* **OpenAI** (`agno.models.openai.OpenAIChat`)
* Any **OpenAI-compatible** endpoint (`agno.models.openai.like.OpenAILike`)

---

## Project layout

```
app/
├── api/v1/           # FastAPI routers (one file per resource)
├── core/             # Config, logging, DB, error handling
├── models/           # SQLAlchemy ORM models
├── schemas/          # Pydantic request/response schemas
├── services/         # CRUD business logic (generic base + resource services)
├── agno_integration/ # Build Agno Agent/Team/Model/Tool/Knowledge objects
└── main.py           # FastAPI entry point
```

## Quick start (local Python)

```bash
make install
cp .env.example .env
make dev
```

Swagger UI: <http://localhost:8000/docs>
ReDoc: <http://localhost:8000/redoc>
OpenAPI JSON: <http://localhost:8000/openapi.json>

## Quick start (Docker)

```bash
cp .env.example .env
make docker-up
make docker-logs
```

## Logging

All logging is configured from the `.env` file via [app/core/logging_config.py](app/core/logging_config.py).

| Variable | Default | Description |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | Root verbosity. Accepted values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `LOG_FORMAT` | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | Standard `logging` format string. |
| `LOG_USE_COLORS` | `true` | Colorize the level name (cyan/green/yellow/red) and dim the logger name. Auto-disabled when stdout is not a TTY (e.g. piped to a file or running under Docker without `-t`). |
| `LOG_API_CALLS` | `true` | When enabled, every HTTP request is logged as `METHOD /path -> status (duration ms)` via a FastAPI middleware. |
| `LOG_SILENCED_LOGGERS` | `hpack,hpack.hpack,hpack.table,h2,h2.connection,h2.stream,httpcore,httpcore.http11,httpcore.http2,httpcore.connection,httpx,urllib3,urllib3.connectionpool,asyncio,agno.telemetry,openai._base_client,openai._client` | Comma-separated list of loggers that are forced to `WARNING`, regardless of `LOG_LEVEL`. These libraries emit unreadable wire-level DEBUG (HPACK byte streams, HTTP/2 frames). To re-enable them, set this variable to an empty value or to a different list. |

### Example: noisy debug session without HTTP-2 spam

```env
LOG_LEVEL=DEBUG
LOG_USE_COLORS=true
LOG_API_CALLS=true
# Keep the default silenced list — DEBUG stays readable.
```

### Example: full wire-level debugging

```env
LOG_LEVEL=DEBUG
LOG_SILENCED_LOGGERS=
```

### Qdrant search results

When an agent uses a knowledge base, vector searches against Qdrant are logged
at `INFO` with a readable summary:

```
Qdrant search [kb_3] query='how do I deploy?' -> 4 hit(s)
  [0] score=0.812 deploy.md: To deploy the service, run make docker-up...
  [1] score=0.774 README.md: Local development uses uvicorn with --reload...
  ...
```

This wrapping is installed in [app/agno_integration/knowledge_builder.py](app/agno_integration/knowledge_builder.py) and applies to both sync and async search paths.

## Error handling

Every error is returned with the following JSON envelope:

```json
{
  "error": {
    "code": "not_found",
    "message": "Agent with id=42 not found",
    "details": null
  }
}
```

## Provider types

The allowed values for the `provider_type` field when creating a provider can
be discovered at runtime:

```
GET /api/v1/providers/types
```

Supported values: `ollama`, `vllm`, `openai_compatible`.

## Running an agent or a team

```
POST /api/v1/agents/{agent_id}/run
POST /api/v1/teams/{team_id}/run
```

Body:

```json
{
  "message": "Summarize the latest news about AI.",
  "session_id": "optional-session-id",
  "user_id": "optional-user-id",
  "extra": {}
}
```

Response:

```json
{
  "id": 1,
  "kind": "agent",
  "content": "...",
  "run_id": "...",
  "metrics": {}
}
```

## Postman collection

```
GET /api/v1/postman/collection
```

or

```bash
make postman
```

## Testing

```bash
make test
```

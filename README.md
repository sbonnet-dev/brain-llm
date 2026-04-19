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

Set the desired verbosity via the `LOG_LEVEL` environment variable. Accepted
values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. The format can
also be customised through `LOG_FORMAT`.

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

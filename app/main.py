"""FastAPI application entry point.

Exposes REST endpoints for managing AI agents, teams, providers, tools
and knowledge bases. A Swagger UI is served at ``/docs`` and ReDoc at
``/redoc`` thanks to FastAPI's built-in OpenAPI generator.
"""

from fastapi import FastAPI

from app.api.v1 import router as api_v1_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Brain-LLM is the central hub that manages AI agents built on top of "
            "Agno / AgentOS. It supports local models through Ollama, VLLM, and "
            "any OpenAI-compatible endpoint."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    register_exception_handlers(app)
    app.include_router(api_v1_router)

    @app.on_event("startup")
    def _on_startup() -> None:
        """Initialize the database and log readiness."""
        logger.info("Starting %s on %s:%s", settings.app_name, settings.app_host, settings.app_port)
        init_db()

    @app.get("/health", tags=["health"], summary="Service health check")
    def health() -> dict[str, str]:
        """Return a simple liveness payload."""
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()

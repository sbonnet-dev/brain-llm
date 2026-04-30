"""FastAPI application entry point.

Exposes REST endpoints for managing AI agents, teams, providers, tools
and knowledge bases. A Swagger UI is served at ``/docs`` and ReDoc at
``/redoc`` thanks to FastAPI's built-in OpenAPI generator.
"""

import time

from fastapi import FastAPI, Request

from app.api.v1 import router as api_v1_router
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import get_logger
from app.services.dependency_installer import install_all_tool_dependencies

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

    if settings.log_api_calls:

        @app.middleware("http")
        async def _log_api_calls(request: Request, call_next):
            start = time.perf_counter()
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "%s %s -> %s (%.1f ms)",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
            return response

    app.include_router(api_v1_router)

    @app.on_event("startup")
    def _on_startup() -> None:
        """Initialize the database and log readiness."""
        logger.info("Starting %s on %s:%s", settings.app_name, settings.app_host, settings.app_port)
        init_db()
        db = SessionLocal()
        try:
            install_all_tool_dependencies(db)
        finally:
            db.close()

    @app.get("/health", tags=["health"], summary="Service health check")
    def health() -> dict[str, str]:
        """Return a simple liveness payload."""
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()

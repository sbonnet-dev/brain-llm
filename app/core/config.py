"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings sourced from the environment."""

    # General application
    app_name: str = "brain-llm"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Logging configuration (configurable via LOG_LEVEL env var)
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_use_colors: bool = True
    log_api_calls: bool = True
    # Comma-separated list of logger names that are always silenced (set to WARNING),
    # regardless of LOG_LEVEL. These produce binary/unreadable spam.
    log_silenced_loggers: str = (
        "hpack,hpack.hpack,hpack.table,h2,h2.connection,h2.stream,"
        "httpcore,httpcore.http11,httpcore.http2,httpcore.connection,"
        "httpx,urllib3,urllib3.connectionpool,asyncio,"
        "agno.telemetry,openai._base_client,openai._client"
    )

    # Persistence
    database_url: str = "sqlite:///./data/brain_llm.db"

    # Default provider endpoints
    ollama_base_url: str = "http://localhost:11434"
    vllm_base_url: str = "http://localhost:8001/v1"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str | None = None

    # Used when generating the Postman collection
    public_base_url: str = "http://localhost:8000"

    # Vector store (Qdrant) and knowledge-base file storage
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    knowledge_storage_dir: str = "./data/knowledge"
    tool_storage_dir: str = "./data/tools"
    knowledge_default_embedder_provider: str = "ollama"
    knowledge_default_embedder_model: str = "qwen3-embedding:0.6b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()

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

    # Persistence
    database_url: str = "sqlite:///./data/brain_llm.db"

    # Default provider endpoints
    ollama_base_url: str = "http://localhost:11434"
    vllm_base_url: str = "http://localhost:8001/v1"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str | None = None

    # Used when generating the Postman collection
    public_base_url: str = "http://localhost:8000"

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

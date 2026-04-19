"""CRUD service for providers."""

from app.models.provider import Provider
from app.schemas.provider import ProviderCreate, ProviderTypeInfo, ProviderUpdate
from app.services.base import CRUDBase

provider_service: CRUDBase[Provider, ProviderCreate, ProviderUpdate] = CRUDBase(
    Provider, "Provider"
)


_PROVIDER_TYPE_CATALOG: tuple[ProviderTypeInfo, ...] = (
    ProviderTypeInfo(
        value="ollama",
        label="Ollama",
        description="Local Ollama server exposing models on its native API.",
    ),
    ProviderTypeInfo(
        value="vllm",
        label="vLLM",
        description="vLLM inference server (uses the OpenAI Chat Completions protocol).",
    ),
    ProviderTypeInfo(
        value="openai_compatible",
        label="OpenAI-compatible",
        description=(
            "Any endpoint speaking the OpenAI Chat Completions API: OpenAI itself, "
            "Groq, Together, LM Studio, Mistral, Azure OpenAI, ..."
        ),
    ),
)


def list_provider_types() -> list[ProviderTypeInfo]:
    """Return the static catalog of supported provider_type values."""
    return list(_PROVIDER_TYPE_CATALOG)

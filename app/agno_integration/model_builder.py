"""Build Agno model instances from stored Provider records.

Supports:
* Ollama       -> ``agno.models.ollama.Ollama``
* VLLM         -> ``agno.models.vllm.VLLM`` (falls back to OpenAI-compatible)
* OpenAI       -> ``agno.models.openai.OpenAIChat``
* OpenAI-compatible generic -> ``agno.models.openai.like.OpenAILike``
"""

from typing import Any

from app.core.exceptions import ProviderError
from app.core.logging_config import get_logger
from app.models.provider import Provider

logger = get_logger(__name__)


def build_model(provider: Provider, model_id: str | None = None) -> Any:
    """Instantiate and return an Agno model object for ``provider``."""
    model_name = model_id or provider.default_model
    if not model_name:
        raise ProviderError(
            f"No model specified and provider '{provider.name}' has no default_model"
        )

    logger.debug("Building model kind=%s model=%s", provider.kind, model_name)

    builders = {
        "ollama": _build_ollama,
        "vllm": _build_vllm,
        "openai": _build_openai,
        "openai_compatible": _build_openai_like,
    }

    try:
        builder = builders[provider.kind]
    except KeyError as exc:
        raise ProviderError(f"Unsupported provider kind: {provider.kind}") from exc

    try:
        return builder(provider, model_name)
    except ImportError as exc:
        raise ProviderError(f"Agno dependency missing for {provider.kind}: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise ProviderError(f"Failed to build model for {provider.name}: {exc}") from exc


def _build_ollama(provider: Provider, model_id: str) -> Any:
    """Build an Ollama-backed Agno model."""
    from agno.models.ollama import Ollama  # type: ignore

    return Ollama(id=model_id, host=provider.base_url)


def _build_vllm(provider: Provider, model_id: str) -> Any:
    """Build a VLLM-backed Agno model (OpenAI-compatible under the hood)."""
    try:
        from agno.models.vllm import VLLM  # type: ignore
    except ImportError:
        return _build_openai_like(provider, model_id)
    return VLLM(id=model_id, base_url=provider.base_url, api_key=provider.api_key or "EMPTY")


def _build_openai(provider: Provider, model_id: str) -> Any:
    """Build an OpenAI-backed Agno model."""
    from agno.models.openai import OpenAIChat  # type: ignore

    return OpenAIChat(id=model_id, base_url=provider.base_url, api_key=provider.api_key)


def _build_openai_like(provider: Provider, model_id: str) -> Any:
    """Build a generic OpenAI-compatible Agno model."""
    from agno.models.openai.like import OpenAILike  # type: ignore

    return OpenAILike(
        id=model_id,
        base_url=provider.base_url,
        api_key=provider.api_key or "EMPTY",
    )

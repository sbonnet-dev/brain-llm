"""Build Agno model instances from stored Provider records.

Supports three provider types:
* ``ollama``             -> ``agno.models.ollama.Ollama``
* ``vllm``               -> ``agno.models.vllm.VLLM`` (falls back to OpenAI-compatible)
* ``openai_compatible``  -> ``agno.models.openai.like.OpenAILike``
"""

from typing import Any

from app.core.exceptions import ProviderError
from app.core.logging_config import get_logger
from app.models.provider import Provider

logger = get_logger(__name__)


def build_model(
    provider: Provider,
    model_id: str | None = None,
    extra_config: dict[str, Any] | None = None,
) -> Any:
    """Instantiate and return an Agno model object for ``provider``.

    ``extra_config`` is the per-model parameter dict (temperature, top_p,
    top_k, max_tokens, …) stored on the Model row. It is forwarded as keyword
    arguments to the Agno model constructor.
    """
    model_name = model_id or provider.default_model
    if not model_name:
        raise ProviderError(
            f"No model specified and provider '{provider.name}' has no default_model"
        )

    logger.debug(
        "Building model provider_type=%s model=%s", provider.provider_type, model_name
    )

    params = _normalize_model_params(provider.provider_type, extra_config)

    builders = {
        "ollama": _build_ollama,
        "vllm": _build_vllm,
        "openai_compatible": _build_openai_like,
        "mistral": _build_mistral,
    }

    try:
        builder = builders[provider.provider_type]
    except KeyError as exc:
        raise ProviderError(
            f"Unsupported provider_type: {provider.provider_type}"
        ) from exc

    try:
        return builder(provider, model_name, params)
    except ImportError as exc:
        raise ProviderError(
            f"Agno dependency missing for {provider.provider_type}: {exc}"
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise ProviderError(f"Failed to build model for {provider.name}: {exc}") from exc


def _normalize_model_params(
    provider_type: str, extra_config: dict[str, Any] | None
) -> dict[str, Any]:
    """Drop empty/None values and rename keys per backend conventions."""
    if not extra_config:
        return {}
    cleaned = {k: v for k, v in extra_config.items() if v not in (None, "")}
    # Ollama uses ``num_predict`` for the equivalent of ``max_tokens``.
    if provider_type == "ollama" and "max_tokens" in cleaned and "num_predict" not in cleaned:
        cleaned["num_predict"] = cleaned.pop("max_tokens")
    return cleaned


def _build_ollama(provider: Provider, model_id: str, params: dict[str, Any]) -> Any:
    """Build an Ollama-backed Agno model."""
    from agno.models.ollama import Ollama  # type: ignore

    return Ollama(id=model_id, host=provider.base_url, **params)


def _build_vllm(provider: Provider, model_id: str, params: dict[str, Any]) -> Any:
    """Build a VLLM-backed Agno model (OpenAI-compatible under the hood)."""
    try:
        from agno.models.vllm import VLLM  # type: ignore
    except ImportError:
        return _build_openai_like(provider, model_id, params)
    return VLLM(
        id=model_id,
        base_url=provider.base_url,
        api_key=provider.api_key or "EMPTY",
        **params,
    )


def _build_mistral(provider: Provider, model_id: str, params: dict[str, Any]) -> Any:
    """Build a Mistral-backed Agno model using the native Mistral SDK."""
    from agno.models.mistral import MistralChat  # type: ignore

    return MistralChat(id=model_id, api_key=provider.api_key, **params)


def _build_openai_like(provider: Provider, model_id: str, params: dict[str, Any]) -> Any:
    """Build a generic OpenAI-compatible Agno model.

    Use this type for OpenAI itself, Together, Groq, LM Studio, vLLM OpenAI
    servers, or any other endpoint that speaks the OpenAI Chat Completions API.
    """
    from agno.models.openai.like import OpenAILike  # type: ignore

    return OpenAILike(
        id=model_id,
        base_url=provider.base_url,
        api_key=provider.api_key or "EMPTY",
        **params,
    )

"""Provider-types REST API.

Exposes the catalog of supported backend types that can be used when
creating or updating a provider.
"""

from fastapi import APIRouter

from app.schemas.provider import ProviderTypeInfo
from app.services.provider_service import list_provider_types

router = APIRouter(prefix="/provider-types", tags=["provider-types"])


@router.get(
    "",
    response_model=list[ProviderTypeInfo],
    summary="List all supported provider types",
    description=(
        "Return the complete catalog of provider_type values that can be used "
        "when creating or updating a provider. Each entry includes the value to "
        "send in the payload, a human-friendly label, and a description of the "
        "underlying backend."
    ),
)
def list_types() -> list[ProviderTypeInfo]:
    """Return the static catalog of supported provider types."""
    return list_provider_types()


@router.get(
    "/{value}",
    response_model=ProviderTypeInfo,
    summary="Get a single provider type by value",
    description=(
        "Return the description of a specific provider_type "
        "(e.g. 'ollama', 'vllm', 'openai_compatible')."
    ),
)
def get_type(value: str) -> ProviderTypeInfo:
    """Fetch one provider type description or return 404."""
    from fastapi import HTTPException, status

    matches = [t for t in list_provider_types() if t.value == value]
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider type '{value}' is not supported.",
        )
    return matches[0]

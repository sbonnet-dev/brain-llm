"""Model-types REST API.

Exposes the catalog of supported model_type values (llm, vlm, embedder,
reranker, audio) that can be used when creating or updating a model.
"""

from fastapi import APIRouter, HTTPException, status

from app.schemas.model import ModelTypeInfo
from app.services.model_service import list_model_types

router = APIRouter(prefix="/model-types", tags=["model-types"])


@router.get(
    "",
    response_model=list[ModelTypeInfo],
    summary="List all supported model types",
    description=(
        "Return every model_type value accepted when creating or updating a "
        "model. Each entry includes the value to send in the payload, a "
        "human-friendly label and a short description."
    ),
)
def list_types() -> list[ModelTypeInfo]:
    """Return the static catalog of supported model types."""
    return list_model_types()


@router.get(
    "/{value}",
    response_model=ModelTypeInfo,
    summary="Get a single model type by value",
    description=(
        "Return the description of a specific model_type "
        "(e.g. 'llm', 'vlm', 'embedder', 'reranker', 'audio')."
    ),
)
def get_type(value: str) -> ModelTypeInfo:
    """Fetch one model type description or return 404."""
    matches = [t for t in list_model_types() if t.value == value]
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model type '{value}' is not supported.",
        )
    return matches[0]

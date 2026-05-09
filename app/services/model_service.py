"""CRUD service for models."""

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.model import Model
from app.models.provider import Provider
from app.schemas.model import ModelCreate, ModelTypeInfo, ModelUpdate
from app.services.base import CRUDBase


class ModelService(CRUDBase[Model, ModelCreate, ModelUpdate]):
    """Model CRUD with provider FK validation."""

    def create(self, db: Session, payload: ModelCreate) -> Model:
        """Validate provider then delegate to the generic creator."""
        _validate_provider(db, payload.provider_id)
        return super().create(db, payload)

    def update(self, db: Session, item_id: int, payload: ModelUpdate) -> Model:
        """Validate provider on update if provided."""
        if payload.provider_id is not None:
            _validate_provider(db, payload.provider_id)
        return super().update(db, item_id, payload)


def _validate_provider(db: Session, provider_id: int) -> None:
    """Ensure the referenced provider exists."""
    if db.get(Provider, provider_id) is None:
        raise ValidationError(f"Provider with id={provider_id} does not exist")


model_service = ModelService(Model, "Model")


_MODEL_TYPE_CATALOG: tuple[ModelTypeInfo, ...] = (
    ModelTypeInfo(
        value="llm",
        label="Large Language Model",
        description="Text-to-text generative model (chat / completions).",
    ),
    ModelTypeInfo(
        value="vlm",
        label="Vision-Language Model",
        description="Multimodal model handling both images and text as input.",
    ),
    ModelTypeInfo(
        value="embedder",
        label="Embedding Model",
        description="Produces dense vector embeddings used for semantic search.",
    ),
    ModelTypeInfo(
        value="reranker",
        label="Reranker",
        description="Re-scores candidate documents to improve retrieval quality.",
    ),
    ModelTypeInfo(
        value="audio",
        label="Audio Model",
        description="Speech-to-text (ASR) or text-to-speech (TTS) model.",
    ),
)


def list_model_types() -> list[ModelTypeInfo]:
    """Return the static catalog of supported model_type values."""
    return list(_MODEL_TYPE_CATALOG)

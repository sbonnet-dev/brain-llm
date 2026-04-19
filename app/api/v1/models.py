"""Models REST API."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import DeleteResponse, ErrorResponse
from app.schemas.model import ModelCreate, ModelRead, ModelUpdate
from app.services.model_service import model_service

router = APIRouter(prefix="/models", tags=["models"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


@router.get("", response_model=list[ModelRead], summary="List models")
def list_models(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[ModelRead]:
    """Return a paginated list of models."""
    return model_service.list(db, skip=skip, limit=limit)


@router.get(
    "/{model_id}",
    response_model=ModelRead,
    responses=_ERROR_RESPONSES,
    summary="Get a model",
)
def get_model(model_id: int, db: Session = Depends(get_db)) -> ModelRead:
    """Fetch a single model by id."""
    return model_service.get(db, model_id)


@router.post(
    "",
    response_model=ModelRead,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
    summary="Create a model",
)
def create_model(payload: ModelCreate, db: Session = Depends(get_db)) -> ModelRead:
    """Register a new model exposed by a provider."""
    return model_service.create(db, payload)


@router.patch(
    "/{model_id}",
    response_model=ModelRead,
    responses=_ERROR_RESPONSES,
    summary="Update a model",
)
def update_model(
    model_id: int,
    payload: ModelUpdate,
    db: Session = Depends(get_db),
) -> ModelRead:
    """Partially update an existing model."""
    return model_service.update(db, model_id, payload)


@router.delete(
    "/{model_id}",
    response_model=DeleteResponse,
    responses=_ERROR_RESPONSES,
    summary="Delete a model",
)
def delete_model(model_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    """Delete a model by id."""
    return DeleteResponse(id=model_service.delete(db, model_id))

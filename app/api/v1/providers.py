"""Providers REST API."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import DeleteResponse, ErrorResponse
from app.schemas.provider import (
    ProviderCreate,
    ProviderRead,
    ProviderTypeInfo,
    ProviderUpdate,
)
from app.services.provider_service import list_provider_types, provider_service

router = APIRouter(prefix="/providers", tags=["providers"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


@router.get(
    "/types",
    response_model=list[ProviderTypeInfo],
    summary="List supported provider_type values",
    description=(
        "Return the list of values accepted by the 'provider_type' field when "
        "creating or updating a provider."
    ),
)
def get_provider_types() -> list[ProviderTypeInfo]:
    """Return the static catalog of supported provider types."""
    return list_provider_types()


@router.get("", response_model=list[ProviderRead], summary="List providers")
def list_providers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[ProviderRead]:
    """Return a paginated list of providers."""
    return provider_service.list(db, skip=skip, limit=limit)


@router.get(
    "/{provider_id}",
    response_model=ProviderRead,
    responses=_ERROR_RESPONSES,
    summary="Get a provider by id",
)
def get_provider(provider_id: int, db: Session = Depends(get_db)) -> ProviderRead:
    """Fetch a single provider by id."""
    return provider_service.get(db, provider_id)


@router.post(
    "",
    response_model=ProviderRead,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
    summary="Create a provider",
)
def create_provider(payload: ProviderCreate, db: Session = Depends(get_db)) -> ProviderRead:
    """Create a new provider."""
    return provider_service.create(db, payload)


@router.patch(
    "/{provider_id}",
    response_model=ProviderRead,
    responses=_ERROR_RESPONSES,
    summary="Update a provider",
)
def update_provider(
    provider_id: int,
    payload: ProviderUpdate,
    db: Session = Depends(get_db),
) -> ProviderRead:
    """Partially update an existing provider."""
    return provider_service.update(db, provider_id, payload)


@router.delete(
    "/{provider_id}",
    response_model=DeleteResponse,
    responses=_ERROR_RESPONSES,
    summary="Delete a provider",
)
def delete_provider(provider_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    """Delete a provider by id."""
    return DeleteResponse(id=provider_service.delete(db, provider_id))

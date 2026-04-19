"""Knowledges REST API."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import DeleteResponse, ErrorResponse
from app.schemas.knowledge import KnowledgeCreate, KnowledgeRead, KnowledgeUpdate
from app.services.knowledge_service import knowledge_service

router = APIRouter(prefix="/knowledges", tags=["knowledges"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


@router.get("", response_model=list[KnowledgeRead], summary="List knowledges")
def list_knowledges(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[KnowledgeRead]:
    """Return a paginated list of knowledge bases."""
    return knowledge_service.list(db, skip=skip, limit=limit)


@router.get(
    "/{knowledge_id}",
    response_model=KnowledgeRead,
    responses=_ERROR_RESPONSES,
    summary="Get a knowledge base",
)
def get_knowledge(knowledge_id: int, db: Session = Depends(get_db)) -> KnowledgeRead:
    """Fetch a single knowledge base by id."""
    return knowledge_service.get(db, knowledge_id)


@router.post(
    "",
    response_model=KnowledgeRead,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
    summary="Create a knowledge base",
)
def create_knowledge(payload: KnowledgeCreate, db: Session = Depends(get_db)) -> KnowledgeRead:
    """Create a new knowledge base."""
    return knowledge_service.create(db, payload)


@router.patch(
    "/{knowledge_id}",
    response_model=KnowledgeRead,
    responses=_ERROR_RESPONSES,
    summary="Update a knowledge base",
)
def update_knowledge(
    knowledge_id: int,
    payload: KnowledgeUpdate,
    db: Session = Depends(get_db),
) -> KnowledgeRead:
    """Partially update an existing knowledge base."""
    return knowledge_service.update(db, knowledge_id, payload)


@router.delete(
    "/{knowledge_id}",
    response_model=DeleteResponse,
    responses=_ERROR_RESPONSES,
    summary="Delete a knowledge base",
)
def delete_knowledge(knowledge_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    """Delete a knowledge base by id."""
    return DeleteResponse(id=knowledge_service.delete(db, knowledge_id))

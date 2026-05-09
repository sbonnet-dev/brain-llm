"""Skills REST API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import DeleteResponse, ErrorResponse
from app.schemas.skill import SkillCreate, SkillRead, SkillUpdate
from app.services.skill_service import skill_service

router = APIRouter(prefix="/skills", tags=["skills"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


@router.get("", response_model=list[SkillRead], summary="List skills")
def list_skills(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[SkillRead]:
    """Return a paginated list of skills."""
    return skill_service.list(db, skip=skip, limit=limit)


@router.get(
    "/{skill_id}",
    response_model=SkillRead,
    responses=_ERROR_RESPONSES,
    summary="Get a skill",
)
def get_skill(skill_id: int, db: Session = Depends(get_db)) -> SkillRead:
    """Fetch a single skill by id."""
    return skill_service.get(db, skill_id)


@router.post(
    "",
    response_model=SkillRead,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
    summary="Create a skill",
)
def create_skill(payload: SkillCreate, db: Session = Depends(get_db)) -> SkillRead:
    """Persist a new skill."""
    return skill_service.create(db, payload)


@router.put(
    "/{skill_id}",
    response_model=SkillRead,
    responses=_ERROR_RESPONSES,
    summary="Update a skill",
)
def update_skill(
    skill_id: int,
    payload: SkillUpdate,
    db: Session = Depends(get_db),
) -> SkillRead:
    """Replace mutable fields of an existing skill."""
    return skill_service.update(db, skill_id, payload)


@router.patch(
    "/{skill_id}",
    response_model=SkillRead,
    responses=_ERROR_RESPONSES,
    summary="Partially update a skill",
)
def patch_skill(
    skill_id: int,
    payload: SkillUpdate,
    db: Session = Depends(get_db),
) -> SkillRead:
    """Partially update an existing skill."""
    return skill_service.update(db, skill_id, payload)


@router.delete(
    "/{skill_id}",
    response_model=DeleteResponse,
    responses=_ERROR_RESPONSES,
    summary="Delete a skill",
)
def delete_skill(skill_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    """Delete a skill by id."""
    return DeleteResponse(id=skill_service.delete(db, skill_id))

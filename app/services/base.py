"""Generic CRUD base service used by every resource."""

from typing import Generic, Sequence, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging_config import get_logger

ModelT = TypeVar("ModelT")
CreateT = TypeVar("CreateT", bound=BaseModel)
UpdateT = TypeVar("UpdateT", bound=BaseModel)

logger = get_logger(__name__)


class CRUDBase(Generic[ModelT, CreateT, UpdateT]):
    """Reusable CRUD helper built on top of SQLAlchemy."""

    def __init__(self, model: type[ModelT], resource_name: str) -> None:
        self.model = model
        self.resource_name = resource_name

    def list(self, db: Session, *, skip: int = 0, limit: int = 100) -> Sequence[ModelT]:
        """Return a paginated list of items."""
        stmt = select(self.model).offset(skip).limit(limit)
        return db.execute(stmt).scalars().all()

    def get(self, db: Session, item_id: int) -> ModelT:
        """Return one item by id or raise NotFoundError."""
        item = db.get(self.model, item_id)
        if item is None:
            raise NotFoundError(f"{self.resource_name} with id={item_id} not found")
        return item

    def create(self, db: Session, payload: CreateT) -> ModelT:
        """Persist a new item."""
        item = self.model(**payload.model_dump(exclude_unset=False))
        db.add(item)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            logger.warning("Integrity error creating %s: %s", self.resource_name, exc)
            raise ConflictError(f"{self.resource_name} already exists or violates a constraint") from exc
        db.refresh(item)
        logger.info("Created %s id=%s", self.resource_name, getattr(item, "id", None))
        return item

    def update(self, db: Session, item_id: int, payload: UpdateT) -> ModelT:
        """Partially update an existing item."""
        item = self.get(db, item_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            logger.warning("Integrity error updating %s: %s", self.resource_name, exc)
            raise ConflictError(f"{self.resource_name} update conflicts with an existing record") from exc
        db.refresh(item)
        logger.info("Updated %s id=%s", self.resource_name, item_id)
        return item

    def delete(self, db: Session, item_id: int) -> int:
        """Delete an item by id and return its id."""
        item = self.get(db, item_id)
        db.delete(item)
        db.commit()
        logger.info("Deleted %s id=%s", self.resource_name, item_id)
        return item_id

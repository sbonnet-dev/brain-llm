"""CRUD service for knowledge bases."""

from app.models.knowledge import Knowledge
from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate
from app.services.base import CRUDBase

knowledge_service: CRUDBase[Knowledge, KnowledgeCreate, KnowledgeUpdate] = CRUDBase(
    Knowledge, "Knowledge"
)

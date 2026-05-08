"""CRUD service for skills."""

from app.models.skill import Skill
from app.schemas.skill import SkillCreate, SkillUpdate
from app.services.base import CRUDBase

skill_service: CRUDBase[Skill, SkillCreate, SkillUpdate] = CRUDBase(Skill, "Skill")

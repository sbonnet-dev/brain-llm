"""CRUD service for providers."""

from app.models.provider import Provider
from app.schemas.provider import ProviderCreate, ProviderUpdate
from app.services.base import CRUDBase

provider_service: CRUDBase[Provider, ProviderCreate, ProviderUpdate] = CRUDBase(
    Provider, "Provider"
)

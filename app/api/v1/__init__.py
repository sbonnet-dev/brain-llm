"""Version 1 of the REST API."""

from fastapi import APIRouter

from app.api.v1 import (
    agents,
    knowledges,
    postman,
    provider_types,
    providers,
    teams,
    tools,
)

router = APIRouter(prefix="/api/v1")
router.include_router(provider_types.router)
router.include_router(providers.router)
router.include_router(tools.router)
router.include_router(knowledges.router)
router.include_router(agents.router)
router.include_router(teams.router)
router.include_router(postman.router)

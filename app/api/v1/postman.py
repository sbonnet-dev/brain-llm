"""Postman collection generator endpoint."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.services.postman_service import build_postman_collection

router = APIRouter(prefix="/postman", tags=["postman"])


@router.get(
    "/collection",
    summary="Generate a Postman collection",
    description=(
        "Return a ready-to-import Postman v2.1 collection that exercises every "
        "endpoint exposed by this API."
    ),
)
def get_postman_collection(request: Request) -> JSONResponse:
    """Return the generated Postman collection as JSON."""
    collection = build_postman_collection(request.app)
    headers = {"Content-Disposition": 'attachment; filename="brain-llm.postman_collection.json"'}
    return JSONResponse(content=collection, headers=headers)

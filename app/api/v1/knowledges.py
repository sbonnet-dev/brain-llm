"""Knowledge REST API.

Exposes the three resource groups listed in the spec:
  - /knowledge/bases           — KB CRUD
  - /knowledge/bases/{id}/files — file management within a KB
  - /knowledge/ingest/...       — trigger Qdrant ingestion
  - /knowledge/status-types     — list the status codes used by KBs/files
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import DeleteResponse, ErrorResponse
from app.schemas.knowledge import (
    IngestionResult,
    KnowledgeCreate,
    KnowledgeFileContent,
    KnowledgeFileContentUpdate,
    KnowledgeFileRead,
    KnowledgeRead,
    KnowledgeStatusType,
    KnowledgeUpdate,
)
from app.services.knowledge_service import (
    knowledge_file_service,
    knowledge_ingestion_service,
    knowledge_service,
    list_status_types,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}


# ---------------------------------------------------------------------------
# Knowledge Bases
# ---------------------------------------------------------------------------


@router.get(
    "/bases",
    response_model=list[KnowledgeRead],
    summary="List Knowledge Bases",
    tags=["Knowledge Bases"],
)
def list_knowledge_bases(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[KnowledgeRead]:
    return knowledge_service.list(db, skip=skip, limit=limit)


@router.post(
    "/bases",
    response_model=KnowledgeRead,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
    summary="Create Knowledge Base",
    tags=["Knowledge Bases"],
)
def create_knowledge_base(payload: KnowledgeCreate, db: Session = Depends(get_db)) -> KnowledgeRead:
    return knowledge_service.create(db, payload)


@router.get(
    "/bases/{kb_id}",
    response_model=KnowledgeRead,
    responses=_ERROR_RESPONSES,
    summary="Get Knowledge Base",
    tags=["Knowledge Bases"],
)
def get_knowledge_base(kb_id: int, db: Session = Depends(get_db)) -> KnowledgeRead:
    return knowledge_service.get(db, kb_id)


@router.put(
    "/bases/{kb_id}",
    response_model=KnowledgeRead,
    responses=_ERROR_RESPONSES,
    summary="Update Knowledge Base",
    tags=["Knowledge Bases"],
)
def update_knowledge_base(
    kb_id: int,
    payload: KnowledgeUpdate,
    db: Session = Depends(get_db),
) -> KnowledgeRead:
    return knowledge_service.update(db, kb_id, payload)


@router.delete(
    "/bases/{kb_id}",
    response_model=DeleteResponse,
    responses=_ERROR_RESPONSES,
    summary="Delete Knowledge Base",
    tags=["Knowledge Bases"],
)
def delete_knowledge_base(kb_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    return DeleteResponse(id=knowledge_service.delete(db, kb_id))


# ---------------------------------------------------------------------------
# Knowledge Files
# ---------------------------------------------------------------------------


@router.get(
    "/bases/{kb_id}/files",
    response_model=list[KnowledgeFileRead],
    responses=_ERROR_RESPONSES,
    summary="List files in a Knowledge Base",
    tags=["Knowledge Files"],
)
def list_files(kb_id: int, db: Session = Depends(get_db)) -> list[KnowledgeFileRead]:
    return knowledge_file_service.list_for_kb(db, kb_id)


@router.post(
    "/bases/{kb_id}/files",
    response_model=KnowledgeFileRead,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
    summary="Add File To KB",
    tags=["Knowledge Files"],
)
async def add_file_to_kb(
    kb_id: int,
    file: UploadFile = File(..., description="Document to upload"),
    db: Session = Depends(get_db),
) -> KnowledgeFileRead:
    content = await file.read()
    return knowledge_file_service.add_file(
        db,
        kb_id,
        filename=file.filename or "untitled",
        content=content,
        mime_type=file.content_type,
    )


@router.get(
    "/bases/{kb_id}/files/{file_id}",
    response_model=KnowledgeFileContent,
    responses=_ERROR_RESPONSES,
    summary="Get File Content",
    tags=["Knowledge Files"],
)
def get_file_content(kb_id: int, file_id: int, db: Session = Depends(get_db)) -> KnowledgeFileContent:
    kf = knowledge_file_service.get(db, kb_id, file_id)
    return KnowledgeFileContent(
        id=kf.id,
        filename=kf.filename,
        mime_type=kf.mime_type,
        content=knowledge_file_service.read_content(db, kb_id, file_id),
    )


@router.put(
    "/bases/{kb_id}/files/{file_id}",
    response_model=KnowledgeFileRead,
    responses=_ERROR_RESPONSES,
    summary="Update File Content",
    tags=["Knowledge Files"],
)
def update_file_content(
    kb_id: int,
    file_id: int,
    payload: KnowledgeFileContentUpdate,
    db: Session = Depends(get_db),
) -> KnowledgeFileRead:
    return knowledge_file_service.update_content(
        db,
        kb_id,
        file_id,
        content=payload.content,
        mime_type=payload.mime_type,
    )


@router.delete(
    "/bases/{kb_id}/files/{file_id}",
    response_model=DeleteResponse,
    responses=_ERROR_RESPONSES,
    summary="Delete File From KB",
    tags=["Knowledge Files"],
)
def delete_file(kb_id: int, file_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    return DeleteResponse(id=knowledge_file_service.delete(db, kb_id, file_id))


@router.get(
    "/bases/{kb_id}/files/{file_id}/source",
    responses={**_ERROR_RESPONSES, 200: {"content": {"application/octet-stream": {}}}},
    summary="Get File Source",
    tags=["Knowledge Files"],
)
def get_file_source(kb_id: int, file_id: int, db: Session = Depends(get_db)) -> Response:
    kf, data = knowledge_file_service.read_bytes(db, kb_id, file_id)
    media_type = kf.mime_type or "application/octet-stream"
    headers = {"Content-Disposition": f'attachment; filename="{kf.filename}"'}
    return Response(content=data, media_type=media_type, headers=headers)


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


@router.post(
    "/ingest/kb/{kb_id}",
    response_model=IngestionResult,
    responses=_ERROR_RESPONSES,
    summary="Ingest Knowledge Base",
    tags=["Knowledge Ingestion"],
)
def ingest_kb(kb_id: int, db: Session = Depends(get_db)) -> IngestionResult:
    return IngestionResult(**knowledge_ingestion_service.ingest_kb(db, kb_id))


@router.post(
    "/ingest/file/{file_id}",
    response_model=IngestionResult,
    responses=_ERROR_RESPONSES,
    summary="Ingest File Only",
    tags=["Knowledge Ingestion"],
)
def ingest_file(file_id: int, db: Session = Depends(get_db)) -> IngestionResult:
    return IngestionResult(**knowledge_ingestion_service.ingest_file(db, file_id))


# ---------------------------------------------------------------------------
# Status types
# ---------------------------------------------------------------------------


@router.get(
    "/status-types",
    response_model=list[KnowledgeStatusType],
    summary="Get Status Types",
    tags=["Knowledge Status"],
)
def get_status_types() -> list[KnowledgeStatusType]:
    return [KnowledgeStatusType(**s) for s in list_status_types()]

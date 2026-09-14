import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.document import DocumentRead, DocumentUpdate, DocumentUploaderSummary
from app.services.auth_service import RequestMeta
from app.services.document_service import DEFAULT_SORT_FIELD, DocumentService
from app.storage import StorageProvider, get_storage_provider
from app.utils.file_validation import safe_content_disposition

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_read_model(document: Document) -> DocumentRead:
    return DocumentRead(
        id=document.id,
        original_filename=document.original_filename,
        document_type=document.document_type,
        status=document.status,
        mime_type=document.mime_type,
        file_extension=document.file_extension,
        file_size=document.file_size,
        checksum=document.checksum,
        description=document.description,
        uploaded_by=DocumentUploaderSummary.model_validate(document.uploader),
        uploaded_at=document.uploaded_at,
        updated_at=document.updated_at,
        archived_at=document.archived_at,
    )


@router.post("", response_model=SuccessResponse[DocumentRead], status_code=201)
async def upload_document(
    company_id: uuid.UUID,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    description: str | None = Form(default=None, max_length=1000),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.DOCUMENT_UPLOAD.value)),
):
    service = DocumentService(db, storage)
    document = await service.upload_document(
        company_id=company_id,
        current_user=current_user,
        file=file,
        document_type=document_type,
        description=description,
        meta=meta,
    )
    await db.commit()
    return SuccessResponse(data=_to_read_model(document), message="Document uploaded successfully")


@router.get("", response_model=SuccessResponse[PaginatedData[DocumentRead]])
async def list_documents(
    company_id: uuid.UUID,
    document_type: DocumentType | None = Query(default=None),
    status: DocumentStatus | None = Query(default=None),
    uploaded_by: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    sort_by: str = Query(default=DEFAULT_SORT_FIELD),
    sort_dir: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    _membership=Depends(require_permission(PermissionCode.DOCUMENT_VIEW.value)),
):
    service = DocumentService(db, storage)
    items, total = await service.list_documents(
        company_id=company_id,
        document_type=document_type,
        status=status,
        uploaded_by=uploaded_by,
        search=search,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    data = PaginatedData(
        items=[_to_read_model(d) for d in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{document_id}", response_model=SuccessResponse[DocumentRead])
async def get_document(
    document_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    _membership=Depends(require_permission(PermissionCode.DOCUMENT_VIEW.value)),
):
    service = DocumentService(db, storage)
    document = await service.get_document(company_id=company_id, document_id=document_id)
    return SuccessResponse(data=_to_read_model(document))


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.DOCUMENT_DOWNLOAD.value)),
):
    service = DocumentService(db, storage)
    document, storage_key = await service.get_document_content(
        company_id=company_id, document_id=document_id, current_user=current_user, meta=meta
    )
    await db.commit()

    local_path = await storage.get_local_path(storage_key)
    if local_path is not None:
        return FileResponse(
            path=local_path,
            media_type=document.mime_type,
            filename=document.original_filename,
        )

    content = await storage.get(storage_key)
    return Response(
        content=content,
        media_type=document.mime_type,
        headers={"Content-Disposition": safe_content_disposition(document.original_filename)},
    )


@router.patch("/{document_id}", response_model=SuccessResponse[DocumentRead])
async def update_document(
    document_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.DOCUMENT_UPDATE.value)),
):
    service = DocumentService(db, storage)
    payload_fields = payload.model_dump(exclude_unset=True)
    document = await service.update_document(
        company_id=company_id,
        document_id=document_id,
        document_type=payload.document_type,
        description=payload.description,
        description_provided="description" in payload_fields,
        current_user=current_user,
        meta=meta,
    )
    await db.commit()
    return SuccessResponse(data=_to_read_model(document), message="Document updated")


@router.patch("/{document_id}/archive", response_model=SuccessResponse[DocumentRead])
async def archive_document(
    document_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.DOCUMENT_ARCHIVE.value)),
):
    service = DocumentService(db, storage)
    document = await service.archive_document(
        company_id=company_id, document_id=document_id, current_user=current_user, meta=meta
    )
    await db.commit()
    return SuccessResponse(data=_to_read_model(document), message="Document archived")


@router.patch("/{document_id}/restore", response_model=SuccessResponse[DocumentRead])
async def restore_document(
    document_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.DOCUMENT_RESTORE.value)),
):
    service = DocumentService(db, storage)
    document = await service.restore_document(
        company_id=company_id, document_id=document_id, current_user=current_user, meta=meta
    )
    await db.commit()
    return SuccessResponse(data=_to_read_model(document), message="Document restored")

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    ConflictError,
    DuplicateResourceError,
    InvalidStateError,
    NotFoundError,
    ValidationAppError,
)
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.user import User
from app.repositories.document_repository import SORTABLE_FIELDS, DocumentRepository
from app.storage.base import StorageProvider
from app.utils.file_validation import FileValidationError, validate_file
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

DEFAULT_SORT_FIELD = "uploaded_at"


class DocumentService:
    def __init__(self, db: AsyncSession, storage: StorageProvider) -> None:
        self.db = db
        self.storage = storage
        self.documents = DocumentRepository(db)
        self.audit = AuditService(db)

    async def upload_document(
        self,
        *,
        company_id: uuid.UUID,
        current_user: User,
        file: UploadFile,
        document_type: DocumentType,
        description: str | None,
        meta: RequestMeta,
    ) -> Document:
        if not file.filename:
            raise ValidationAppError("A file is required", code="INVALID_FILE")
        if len(file.filename) > 255:
            raise ValidationAppError("Filename is too long (max 255 characters)", code="INVALID_FILE")

        content = await file.read()

        if len(content) > settings.max_upload_size_bytes:
            raise ValidationAppError(
                f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB upload limit",
                code="DOCUMENT_TOO_LARGE",
            )

        try:
            spec = validate_file(
                filename=file.filename,
                declared_mime_type=file.content_type,
                content=content,
                allowed_extensions=settings.allowed_document_extensions,
            )
        except FileValidationError as exc:
            raise ValidationAppError(str(exc), code=exc.code) from exc

        checksum = hashlib.sha256(content).hexdigest()

        existing = await self.documents.get_by_checksum_for_company(checksum, company_id)
        if existing is not None:
            await self.audit.log(
                action=AuditAction.DOCUMENT_DUPLICATE_ATTEMPT,
                user_id=current_user.id,
                company_id=company_id,
                resource_type="document",
                resource_id=str(existing.id),
                description=f"Duplicate upload attempt for '{file.filename}'",
                ip_address=meta.ip_address,
                user_agent=meta.user_agent,
            )
            raise DuplicateResourceError(
                "An identical document already exists in this company",
                code="DOCUMENT_DUPLICATE",
                details={"existing_document_id": str(existing.id)},
            )

        document_id = uuid.uuid4()
        stored_filename = f"{document_id.hex}.{spec.extension}"
        storage_key = f"companies/{company_id}/documents/{document_id}/{stored_filename}"

        try:
            await self.storage.save(storage_key, content)
        except Exception as exc:  # noqa: BLE001 - never leak raw filesystem errors to clients
            raise AppException(
                "Could not store the uploaded file", code="DOCUMENT_STORAGE_ERROR"
            ) from exc

        document = Document(
            id=document_id,
            company_id=company_id,
            uploaded_by=current_user.id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            storage_path=storage_key,
            mime_type=file.content_type or "application/octet-stream",
            file_extension=spec.extension,
            file_size=len(content),
            checksum=checksum,
            document_type=document_type,
            status=DocumentStatus.READY,
            description=description,
        )

        try:
            await self.documents.create(document)
        except Exception as exc:
            # The DB record failed — never leave an orphaned file behind,
            # never leave the session in an aborted-transaction state, and
            # never leak a raw DB/driver error to the client.
            await self.storage.delete(storage_key)
            await self.db.rollback()
            raise AppException(
                "Could not save document metadata", code="DOCUMENT_STORAGE_ERROR"
            ) from exc

        await self.documents.db.refresh(document, attribute_names=["uploaded_at", "updated_at"])
        document.uploader = current_user

        await self.audit.log(
            action=AuditAction.DOCUMENT_UPLOAD,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="document",
            resource_id=str(document.id),
            description=f"Document '{document.original_filename}' uploaded",
            metadata={"document_type": document_type.value, "file_size": document.file_size},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        return document

    async def list_documents(
        self,
        *,
        company_id: uuid.UUID,
        document_type: DocumentType | None,
        status: DocumentStatus | None,
        uploaded_by: uuid.UUID | None,
        search: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        sort_by: str,
        sort_dir: str,
        page: int,
        page_size: int,
    ) -> tuple[list[Document], int]:
        if sort_by not in SORTABLE_FIELDS:
            raise ValidationAppError(
                f"Cannot sort by '{sort_by}'. Allowed fields: {', '.join(sorted(SORTABLE_FIELDS))}",
                code="VALIDATION_ERROR",
            )
        if sort_dir not in ("asc", "desc"):
            raise ValidationAppError("sort_dir must be 'asc' or 'desc'", code="VALIDATION_ERROR")

        offset = (page - 1) * page_size
        return await self.documents.list_filtered(
            company_id=company_id,
            document_type=document_type,
            status=status,
            uploaded_by=uploaded_by,
            search=search,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_dir=sort_dir,
            offset=offset,
            limit=page_size,
        )

    async def get_document(self, *, company_id: uuid.UUID, document_id: uuid.UUID) -> Document:
        document = await self.documents.get_by_id_for_company(document_id, company_id)
        if document is None:
            # Deliberately identical whether the document truly doesn't
            # exist or belongs to another company — distinguishing the two
            # would let a caller enumerate other tenants' document ids.
            raise NotFoundError("Document not found", code="DOCUMENT_NOT_FOUND")
        return document

    async def get_document_content(
        self, *, company_id: uuid.UUID, document_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> tuple[Document, str]:
        """Returns the document and its storage key for the API layer to
        stream. Raises DOCUMENT_STORAGE_ERROR if the DB record exists but
        the underlying file is missing (a corrupted/tampered store), which
        is a safe, generic error rather than a raw filesystem message.
        """
        document = await self.get_document(company_id=company_id, document_id=document_id)

        if not await self.storage.exists(document.storage_path):
            raise AppException(
                "The stored file for this document could not be found",
                code="DOCUMENT_STORAGE_ERROR",
            )

        await self.audit.log(
            action=AuditAction.DOCUMENT_DOWNLOAD,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="document",
            resource_id=str(document.id),
            description=f"Document '{document.original_filename}' downloaded",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return document, document.storage_path

    async def update_document(
        self,
        *,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
        document_type: DocumentType | None,
        description: str | None,
        description_provided: bool,
        current_user: User,
        meta: RequestMeta,
    ) -> Document:
        document = await self.get_document(company_id=company_id, document_id=document_id)

        updated_fields: list[str] = []
        if document_type is not None:
            document.document_type = document_type
            updated_fields.append("document_type")
        if description_provided:
            document.description = description
            updated_fields.append("description")

        if updated_fields:
            await self.db.flush()
            await self.db.refresh(document, attribute_names=["updated_at"])
            await self.audit.log(
                action=AuditAction.DOCUMENT_UPDATE,
                user_id=current_user.id,
                company_id=company_id,
                resource_type="document",
                resource_id=str(document.id),
                description=f"Document '{document.original_filename}' metadata updated",
                metadata={"updated_fields": updated_fields},
                ip_address=meta.ip_address,
                user_agent=meta.user_agent,
            )
        return document

    async def archive_document(
        self, *, company_id: uuid.UUID, document_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> Document:
        document = await self.get_document(company_id=company_id, document_id=document_id)

        if document.status == DocumentStatus.ARCHIVED:
            raise ConflictError("Document is already archived", code="DOCUMENT_ARCHIVED")

        document.status = DocumentStatus.ARCHIVED
        document.archived_at = datetime.now(timezone.utc)
        document.archived_by = current_user.id

        await self.db.flush()
        await self.db.refresh(document, attribute_names=["updated_at"])

        await self.audit.log(
            action=AuditAction.DOCUMENT_ARCHIVE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="document",
            resource_id=str(document.id),
            description=f"Document '{document.original_filename}' archived",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return document

    async def restore_document(
        self, *, company_id: uuid.UUID, document_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> Document:
        document = await self.get_document(company_id=company_id, document_id=document_id)

        if document.status != DocumentStatus.ARCHIVED:
            raise InvalidStateError("Document is not archived", code="DOCUMENT_NOT_ARCHIVED")

        document.status = DocumentStatus.READY
        document.archived_at = None
        document.archived_by = None

        await self.db.flush()
        await self.db.refresh(document, attribute_names=["updated_at"])

        await self.audit.log(
            action=AuditAction.DOCUMENT_RESTORE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="document",
            resource_id=str(document.id),
            description=f"Document '{document.original_filename}' restored",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return document

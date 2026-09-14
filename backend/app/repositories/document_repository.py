import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.document import Document, DocumentStatus, DocumentType

SORTABLE_FIELDS: dict[str, "object"] = {
    "uploaded_at": Document.uploaded_at,
    "file_name": Document.original_filename,
    "file_size": Document.file_size,
    "document_type": Document.document_type,
    "status": Document.status,
}


class DocumentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, document: Document) -> Document:
        self.db.add(document)
        await self.db.flush()
        return document

    async def get_by_id_for_company(
        self, document_id: uuid.UUID, company_id: uuid.UUID
    ) -> Document | None:
        """The tenant-isolation primitive for documents: every lookup by id
        must also match company_id, or a user could reach another tenant's
        document simply by guessing/enumerating a UUID.
        """
        result = await self.db.execute(
            select(Document)
            .options(joinedload(Document.uploader), joinedload(Document.archiver))
            .where(Document.id == document_id, Document.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_by_checksum_for_company(
        self, checksum: str, company_id: uuid.UUID
    ) -> Document | None:
        result = await self.db.execute(
            select(Document)
            .options(joinedload(Document.uploader))
            .where(
                Document.checksum == checksum,
                Document.company_id == company_id,
                Document.status != DocumentStatus.ARCHIVED,
            )
        )
        return result.scalars().first()

    async def list_filtered(
        self,
        *,
        company_id: uuid.UUID,
        document_type: DocumentType | None = None,
        status: DocumentStatus | None = None,
        uploaded_by: uuid.UUID | None = None,
        search: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str = "uploaded_at",
        sort_dir: str = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Document], int]:
        query = select(Document).where(Document.company_id == company_id)

        if document_type is not None:
            query = query.where(Document.document_type == document_type)
        if status is not None:
            query = query.where(Document.status == status)
        if uploaded_by is not None:
            query = query.where(Document.uploaded_by == uploaded_by)
        if date_from is not None:
            query = query.where(Document.uploaded_at >= date_from)
        if date_to is not None:
            query = query.where(Document.uploaded_at <= date_to)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    Document.original_filename.ilike(pattern),
                    Document.description.ilike(pattern),
                    Document.document_type.ilike(pattern),
                )
            )

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        # sort_by is validated against SORTABLE_FIELDS by the caller (API
        # layer) before reaching here — never interpolate a client-supplied
        # column name directly into the query.
        sort_column = SORTABLE_FIELDS.get(sort_by, Document.uploaded_at)
        order_clause = sort_column.desc() if sort_dir == "desc" else sort_column.asc()

        result = await self.db.execute(
            query.options(joinedload(Document.uploader))
            .order_by(order_clause)
            .offset(offset)
            .limit(limit)
        )
        return list(result.unique().scalars().all()), total

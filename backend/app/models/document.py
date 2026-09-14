from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.user import User


class DocumentType(StrEnum):
    """Controlled document categories.

    A future module adding a new document category extends this enum (and
    the seed/permission catalogue if it needs its own permission) — upload,
    storage, and validation logic never branch on document type, so nothing
    else needs to change.
    """

    SALES_INVOICE = "SALES_INVOICE"
    PURCHASE_INVOICE = "PURCHASE_INVOICE"
    EXPENSE_BILL = "EXPENSE_BILL"
    BANK_STATEMENT = "BANK_STATEMENT"
    GST_REPORT = "GST_REPORT"
    TDS_DOCUMENT = "TDS_DOCUMENT"
    INCOME_TAX_DOCUMENT = "INCOME_TAX_DOCUMENT"
    FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT"
    OTHER = "OTHER"


class DocumentStatus(StrEnum):
    """Document lifecycle. Phase 2 only ever sets UPLOADED -> READY (or
    FAILED on a storage error). PROCESSING, REVIEW_REQUIRED, and VERIFIED
    are reserved for a future extraction/review pipeline (see
    app/services/document_processor.py) and are never set automatically.
    """

    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    VERIFIED = "VERIFIED"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"


class Document(UUIDPrimaryKeyMixin, Base):
    """Metadata for one uploaded file. The actual bytes live behind the
    StorageProvider abstraction (app/storage/) at `storage_path`, which is a
    storage-relative key — never an absolute filesystem path — and is never
    serialized to API clients.
    """

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_company_uploaded_at", "company_id", "uploaded_at"),
        Index("ix_documents_company_checksum", "company_id", "checksum"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_by: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    archived_by: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)

    mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, native_enum=False, length=30), nullable=False, index=True
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False, length=20),
        default=DocumentStatus.UPLOADED,
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship("Company")
    uploader: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by])
    archiver: Mapped["User | None"] = relationship("User", foreign_keys=[archived_by])
    links: Mapped[list["DocumentLink"]] = relationship(
        "DocumentLink", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentLink(UUIDPrimaryKeyMixin, Base):
    """Generic foundation for linking a document to a future business record
    (a sales invoice, a bank transaction, a GST return, ...) without those
    tables existing yet. `resource_type` + `resource_id` is a loose pointer
    rather than a foreign key, precisely because the target table is a
    future module's responsibility; once that module exists it can query
    this table by (company_id, resource_type, resource_id) to find every
    document attached to one of its records.
    """

    __tablename__ = "document_links"
    __table_args__ = (
        Index(
            "ix_document_links_unique",
            "document_id",
            "resource_type",
            "resource_id",
            unique=True,
        ),
        Index("ix_document_links_resource", "company_id", "resource_type", "resource_id"),
    )

    document_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str] = mapped_column(GUID(), nullable=False)

    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False)
    link_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    document: Mapped["Document"] = relationship("Document", back_populates="links")

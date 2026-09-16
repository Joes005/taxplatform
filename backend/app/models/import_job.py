from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.accounting_enums import ImportStatus, ImportType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class ImportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One upload-to-commit lifecycle. `document_id` links back to the
    Phase 2 Document that stores the actual uploaded file — the import
    system never re-implements file storage. `column_mapping` persists the
    user's source-column -> system-field choices from the mapping step so
    re-parsing (or re-showing the wizard) doesn't lose them.
    """

    __tablename__ = "import_jobs"

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    financial_year_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="SET NULL"), nullable=True
    )
    return_period_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("gst_return_periods.id", ondelete="SET NULL"), nullable=True
    )
    import_type: Mapped[ImportType] = mapped_column(
        Enum(ImportType, native_enum=False, length=20), nullable=False, index=True
    )
    status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, native_enum=False, length=30),
        default=ImportStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    column_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    rows: Mapped[list["ImportRow"]] = relationship(
        "ImportRow", back_populates="import_job", cascade="all, delete-orphan"
    )
    errors: Mapped[list["ImportError"]] = relationship(
        "ImportError", back_populates="import_job", cascade="all, delete-orphan"
    )


class ImportRowStatus:
    VALID = "VALID"
    ERROR = "ERROR"
    DUPLICATE = "DUPLICATE"
    COMMITTED = "COMMITTED"


class ImportRow(UUIDPrimaryKeyMixin, Base):
    """One parsed source row, staged between parsing and commit.
    `raw_data` is exactly what the file contained (source column names);
    `normalized_data` is that same row after column mapping + type
    normalization (dates/amounts) — the preview shows normalized_data, and
    commit reads from it to build the real accounting record.
    """

    __tablename__ = "import_rows"
    __table_args__ = (Index("ix_import_rows_job_row", "import_job_id", "row_number"),)

    import_job_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    normalized_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ImportRowStatus.VALID, nullable=False)
    created_record_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)

    import_job: Mapped["ImportJob"] = relationship("ImportJob", back_populates="rows")


class ImportError(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "import_errors"

    import_job_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_code: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    import_job: Mapped["ImportJob"] = relationship("ImportJob", back_populates="errors")

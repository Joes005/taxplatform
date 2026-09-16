from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.gst_enums import GSTR2BDocumentType
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class GSTR2BRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row from an imported GSTR-2B statement (local file upload only —
    never fetched live from the government portal, PHASE4 section 26).
    `import_job_id`/`source`/`source_reference` preserve exactly where this
    record came from for auditor traceability (PHASE4 section 29).
    """

    __tablename__ = "gstr2b_records"
    __table_args__ = (
        Index(
            "ix_gstr2b_records_supplier_invoice",
            "company_id",
            "return_period_id",
            "supplier_gstin",
            "invoice_number",
        ),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    return_period_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("gst_return_periods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    import_job_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True
    )

    supplier_gstin: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    document_type: Mapped[GSTR2BDocumentType] = mapped_column(
        Enum(GSTR2BDocumentType, native_enum=False, length=15),
        default=GSTR2BDocumentType.INVOICE,
        nullable=False,
    )

    taxable_value: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    igst_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    cess_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    total_tax: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

    source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

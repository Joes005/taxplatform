from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A buyer the company issues Sales Invoices to. GSTIN/state/state_code
    are preserved specifically so a future GST module can determine
    intra-state (CGST+SGST) vs inter-state (IGST) treatment and populate
    GSTR-1 without re-collecting this data.
    """

    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_company_code", "company_id", "code", unique=True),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True, index=True)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    billing_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    shipping_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

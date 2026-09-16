from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import RATE, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class GSTTaxRate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A configurable GST slab (0/5/12/18/28% and any CESS/other rate a
    company needs). `company_id` is nullable so a set of platform-wide
    default rates can be seeded without belonging to any one tenant; a
    company may additionally define its own. This is deliberately not an
    authoritative HSN-to-rate master (PHASE4 section 7) — rates are picked
    by the user, not looked up automatically.
    """

    __tablename__ = "gst_tax_rates"
    __table_args__ = (Index("ix_gst_tax_rates_company_rate", "company_id", "rate"),)

    company_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    rate: Mapped[Decimal] = mapped_column(RATE, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

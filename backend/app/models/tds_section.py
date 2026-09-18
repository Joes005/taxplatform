from datetime import date

from sqlalchemy import Boolean, Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TDSSection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A section of the Income Tax Act that imposes a TDS obligation
    (194C, 194J, 194Q, ...). Platform-wide, not company-scoped — the
    sections themselves are the same for every company; only the *rate*
    applicable under a section is configurable per company (`TDSRule`).
    This is deliberately not claimed to be an exhaustive statutory list
    (PHASE5 section 10) — more sections can be added without a schema
    change.
    """

    __tablename__ = "tds_sections"
    __table_args__ = (Index("ix_tds_sections_code_unique", "section_code", unique=True),)

    section_code: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    payment_nature: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

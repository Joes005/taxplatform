from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import MONEY, RATE, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tds_enums import DeducteeType, TDSRateType
from app.utils.types import GUID


class TDSRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The configurable rate/threshold configuration for one TDS section,
    effective for a date range (PHASE5 section 12) — a transaction always
    looks up the rule whose [effective_from, effective_to] window covers
    its deduction date, never "the current rule". `company_id` is
    nullable so a small set of platform-wide sample rules can be seeded
    (PHASE5 section 11 — this is documented sample configuration for
    development/testing, not an authoritative rate table) alongside any
    company-specific override.

    `no_pan_rate` implements Income Tax Act Section 206AA: when a
    deductee's PAN is unavailable, tax must be deducted at the higher of
    the normal rate or this rate (typically 20%). Leaving it unset means
    the calculation engine cannot resolve a missing-PAN case on its own
    and must return REVIEW_REQUIRED rather than guess.
    """

    __tablename__ = "tds_rules"
    __table_args__ = (
        Index("ix_tds_rules_section_company", "tds_section_id", "company_id"),
    )

    tds_section_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("tds_sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )

    rate: Mapped[Decimal] = mapped_column(RATE, nullable=False)
    rate_type: Mapped[TDSRateType] = mapped_column(
        Enum(TDSRateType, native_enum=False, length=10),
        default=TDSRateType.PERCENTAGE,
        nullable=False,
    )
    no_pan_rate: Mapped[Decimal | None] = mapped_column(RATE, nullable=True)

    threshold_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    aggregate_threshold_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)

    deductee_type: Mapped[DeducteeType | None] = mapped_column(
        Enum(DeducteeType, native_enum=False, length=15), nullable=True
    )
    pan_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    special_condition: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

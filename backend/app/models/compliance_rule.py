from datetime import date
from typing import Any

from sqlalchemy import JSON, Boolean, Date, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.compliance_enums import ComplianceCategory, ComplianceFrequency, ComplianceModule, CompliancePriority
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class ComplianceRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A versioned, configurable definition of one recurring or one-time
    compliance obligation (PHASE9 §6-7) — platform-wide by default
    (`company_id IS NULL`), the same shape `GSTTaxRate`/`TDSSection`
    already use for statutory configuration, with an optional
    company-specific override. `due_date_rule` is a small typed JSON
    document (`{"type": "DAYS_AFTER_PERIOD_END", "days": 20}` or
    `{"type": "DAY_OF_MONTH_AFTER_PERIOD_END", "month_offset": 1, "day": 20}`
    or `{"type": "DAYS_AFTER_START", "days": 30}`) that
    `ComplianceDeadlineService` interprets — no due-date arithmetic is
    ever hard-coded in Python. Every `ComplianceObligation` generated from
    a rule stores that rule's `version` so a later rule change never
    rewrites a historical obligation's due date (PHASE9 §7).
    """

    __tablename__ = "compliance_rules"
    __table_args__ = (
        Index("ix_compliance_rules_unique_version", "code", "company_id", "version", unique=True),
    )

    company_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[ComplianceCategory] = mapped_column(
        Enum(ComplianceCategory, native_enum=False, length=15), nullable=False, index=True
    )
    module: Mapped[ComplianceModule] = mapped_column(
        Enum(ComplianceModule, native_enum=False, length=25), nullable=False, index=True
    )
    frequency: Mapped[ComplianceFrequency] = mapped_column(
        Enum(ComplianceFrequency, native_enum=False, length=10), nullable=False
    )
    due_date_rule: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    priority: Mapped[CompliancePriority] = mapped_column(
        Enum(CompliancePriority, native_enum=False, length=10), default=CompliancePriority.MEDIUM, nullable=False
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

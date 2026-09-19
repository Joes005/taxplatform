import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.compliance_enums import (
    ComplianceCategory,
    ComplianceFrequency,
    ComplianceModule,
    ComplianceObligationStatus,
    CompliancePriority,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class ComplianceObligation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One company's instance of a compliance requirement for one period
    (PHASE9 §5) — either generated from an active `ComplianceRule`
    (`rule_id`/`rule_version` set) or created manually (both null).
    `ComplianceTask` rows are what get worked on; an obligation is the
    "this is due" record a task traces back to via `source_type=MANUAL`-
    style `ComplianceTask.obligation_id`.
    """

    __tablename__ = "compliance_obligations"
    __table_args__ = (
        Index(
            "ix_compliance_obligations_unique",
            "company_id",
            "code",
            "financial_year_id",
            "tax_period",
            unique=True,
        ),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
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
    financial_year_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    tax_period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    grace_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[CompliancePriority] = mapped_column(
        Enum(CompliancePriority, native_enum=False, length=10), default=CompliancePriority.MEDIUM, nullable=False
    )
    status: Mapped[ComplianceObligationStatus] = mapped_column(
        Enum(ComplianceObligationStatus, native_enum=False, length=15),
        default=ComplianceObligationStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rule_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("compliance_rules.id", ondelete="SET NULL"), nullable=True
    )
    rule_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

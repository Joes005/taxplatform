import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.income_tax_enums import ITRFormType, ITRPreparationStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class ITRPreparation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A structured internal preparation record for one tax computation
    (PHASE8 §43-45) — never a government filing schema or a submission.
    `itr_form_type` is determined by `ITRFormRuleService` and can resolve
    to `NOT_DETERMINED` (surfaced as `REVIEW_REQUIRED`) rather than a
    guess (PHASE8 §44).
    """

    __tablename__ = "itr_preparations"
    __table_args__ = (Index("ix_itr_preparations_computation", "tax_computation_id", unique=True),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tax_computation_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("tax_computations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    itr_form_type: Mapped[ITRFormType] = mapped_column(
        Enum(ITRFormType, native_enum=False, length=20), default=ITRFormType.NOT_DETERMINED, nullable=False
    )
    assessment_year: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[ITRPreparationStatus] = mapped_column(
        Enum(ITRPreparationStatus, native_enum=False, length=20),
        default=ITRPreparationStatus.DRAFT,
        nullable=False,
        index=True,
    )
    prepared_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.gst_enums import GSTRegistrationType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class GSTProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A company's GST registration details. One company has at most one
    active profile — GSTIN format is checked structurally on write
    (`app.utils.gstin`), never verified against the government portal.
    """

    __tablename__ = "gst_profiles"
    __table_args__ = (Index("ix_gst_profiles_company_unique", "company_id", unique=True),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gstin: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    registration_type: Mapped[GSTRegistrationType] = mapped_column(
        Enum(GSTRegistrationType, native_enum=False, length=15),
        default=GSTRegistrationType.REGULAR,
        nullable=False,
    )
    state_code: Mapped[str] = mapped_column(String(2), nullable=False)
    state_name: Mapped[str] = mapped_column(String(100), nullable=False)
    registration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

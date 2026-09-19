from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.income_tax_enums import ResidentialStatus, TaxpayerType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class IncomeTaxProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A company's Income Tax taxpayer profile. One company has at most
    one profile — the same "one profile per company" shape as `TDSProfile`
    and `GSTProfile`. PAN format is checked structurally on write
    (`app.utils.pan`), never verified against the e-filing portal
    (PHASE8 §10).
    """

    __tablename__ = "income_tax_profiles"
    __table_args__ = (Index("ix_income_tax_profiles_company_unique", "company_id", unique=True),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pan: Mapped[str] = mapped_column(String(10), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    taxpayer_type: Mapped[TaxpayerType] = mapped_column(
        Enum(TaxpayerType, native_enum=False, length=15), default=TaxpayerType.COMPANY, nullable=False
    )
    residential_status: Mapped[ResidentialStatus] = mapped_column(
        Enum(ResidentialStatus, native_enum=False, length=35),
        default=ResidentialStatus.RESIDENT,
        nullable=False,
    )
    date_of_birth_or_incorporation: Mapped[date | None] = mapped_column(Date, nullable=True)
    business_nature: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)

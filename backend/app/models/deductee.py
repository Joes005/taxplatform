from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tds_enums import DeducteeType, PANStatus
from app.utils.types import GUID

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.vendor import Vendor


class Deductee(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The person/entity TDS is deducted from when the company pays them.
    Optionally linked to an existing Vendor/Customer (PHASE5 section 9) so
    a deductee doesn't duplicate party data the accounting layer already
    has, but can also exist standalone for a payee that isn't otherwise
    tracked as a Vendor/Customer (e.g. a one-off professional fee).
    """

    __tablename__ = "deductees"
    __table_args__ = (Index("ix_deductees_company_code", "company_id", "code", unique=True),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    pan: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    pan_status: Mapped[PANStatus] = mapped_column(
        Enum(PANStatus, native_enum=False, length=15),
        default=PANStatus.NOT_AVAILABLE,
        nullable=False,
    )
    deductee_type: Mapped[DeducteeType] = mapped_column(
        Enum(DeducteeType, native_enum=False, length=15),
        default=DeducteeType.OTHER,
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    vendor: Mapped["Vendor | None"] = relationship("Vendor")
    customer: Mapped["Customer | None"] = relationship("Customer")

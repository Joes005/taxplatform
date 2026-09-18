from datetime import date
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tds_enums import TDSChallanStatus
from app.utils.types import GUID


class TDSChallan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A record of one TDS payment challan the deductor has already paid
    to the bank/government — tracking and allocation only. This platform
    never initiates or submits a challan payment itself (PHASE5 section
    21); `challan_number` is whatever reference the user enters after
    paying it elsewhere.
    """

    __tablename__ = "tds_challans"
    __table_args__ = (
        Index(
            "ix_tds_challans_unique_number",
            "company_id",
            "financial_year_id",
            "challan_number",
            unique=True,
        ),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    challan_number: Mapped[str] = mapped_column(String(50), nullable=False)
    challan_date: Mapped[date] = mapped_column(nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    status: Mapped[TDSChallanStatus] = mapped_column(
        Enum(TDSChallanStatus, native_enum=False, length=15),
        default=TDSChallanStatus.DRAFT,
        nullable=False,
        index=True,
    )
    bank_reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    allocations: Mapped[list["TDSChallanAllocation"]] = relationship(
        "TDSChallanAllocation", back_populates="challan", cascade="all, delete-orphan"
    )


class TDSChallanAllocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One TDS transaction's claim against one challan's payment. A
    challan can cover many transactions and a transaction's TDS can in
    principle be split across challans (a correction/topping-up payment);
    `TDSChallanService.allocate` enforces both never exceeding their
    balance (PHASE5 section 22).
    """

    __tablename__ = "tds_challan_allocations"
    __table_args__ = (
        Index("ix_tds_challan_allocations_challan", "challan_id"),
        Index("ix_tds_challan_allocations_transaction", "tds_transaction_id"),
    )

    challan_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("tds_challans.id", ondelete="CASCADE"), nullable=False
    )
    tds_transaction_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("tds_transactions.id", ondelete="RESTRICT"), nullable=False
    )
    allocated_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)

    challan: Mapped["TDSChallan"] = relationship("TDSChallan", back_populates="allocations")

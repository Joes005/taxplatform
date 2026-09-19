from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.income_tax_enums import CapitalAssetType, CapitalGainType
from app.models.mixins import MONEY, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class IncomeTaxCapitalGain(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One capital asset transfer (PHASE8 §27). `gain_type` is always
    chosen explicitly by the preparer rather than derived from a holding-
    period rule — the short/long-term threshold differs by asset class
    (12/24/36 months) and this platform does not encode that table, to
    avoid asserting a rule that could be wrong for a specific asset type
    or a future financial year (PHASE8 §27, §98). `indexed_cost`, when
    provided, is a manual entry — this platform does not encode a
    Cost Inflation Index table either.
    """

    __tablename__ = "income_tax_capital_gains"
    __table_args__ = (Index("ix_income_tax_capital_gains_company_fy", "company_id", "financial_year_id"),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("financial_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    asset_type: Mapped[CapitalAssetType] = mapped_column(
        Enum(CapitalAssetType, native_enum=False, length=20), nullable=False
    )
    asset_description: Mapped[str] = mapped_column(String(500), nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_cost: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    improvement_cost: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    sale_consideration: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    transfer_expenses: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    indexed_cost: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    gain_type: Mapped[CapitalGainType] = mapped_column(
        Enum(CapitalGainType, native_enum=False, length=10), nullable=False
    )
    gain_amount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.income_tax_enums import LedgerTaxClassification
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class IncomeTaxLedgerClassification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Maps one Phase 3 `Ledger` to a tax treatment (PHASE8 §25) — a thin
    side table referencing `Ledger` by id, never a column added to the
    shared Phase 3 model. A ledger with no row here is `NOT_CLASSIFIED`
    (the service layer's default), so nothing is ever silently added back
    or disallowed without a human having set it explicitly.
    """

    __tablename__ = "income_tax_ledger_classifications"
    __table_args__ = (Index("ix_income_tax_ledger_classifications_unique", "company_id", "ledger_id", unique=True),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ledger_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("ledgers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    classification: Mapped[LedgerTaxClassification] = mapped_column(
        Enum(LedgerTaxClassification, native_enum=False, length=20),
        default=LedgerTaxClassification.NOT_CLASSIFIED,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.accounting_enums import BalanceType


class SalesPurchaseSummary(BaseModel):
    date_from: date | None
    date_to: date | None
    invoice_count: int
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_tax: Decimal
    grand_total: Decimal


class PartyOutstanding(BaseModel):
    party_id: uuid.UUID
    party_name: str
    invoiced_total: Decimal
    settled_total: Decimal
    outstanding: Decimal


class LedgerBalance(BaseModel):
    ledger_id: uuid.UUID
    ledger_name: str
    ledger_type: str
    debit: Decimal
    credit: Decimal
    balance: Decimal
    balance_type: BalanceType


class TrialBalance(BaseModel):
    as_of: date | None
    lines: list[LedgerBalance]
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool

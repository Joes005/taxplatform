import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.bank_enums import BankMatchSourceType, BankMatchType, BankTransactionReconciliationStatus


class UnmatchedBankTransactionRow(BaseModel):
    bank_transaction_id: uuid.UUID
    transaction_date: date
    description: str
    reference_number: str | None
    amount: Decimal
    status: BankTransactionReconciliationStatus


class UnmatchedBookTransactionRow(BaseModel):
    source_type: BankMatchSourceType
    source_id: uuid.UUID
    source_label: str
    source_date: date
    amount: Decimal
    unmatched_amount: Decimal


class MatchReportRow(BaseModel):
    match_id: uuid.UUID
    bank_transaction_id: uuid.UUID
    bank_transaction_date: date
    bank_transaction_description: str
    source_type: BankMatchSourceType
    source_id: uuid.UUID
    matched_amount: Decimal
    match_type: BankMatchType
    match_score: int | None
    matched_by: uuid.UUID
    matched_at: datetime

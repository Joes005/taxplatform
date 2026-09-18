import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.bank_enums import BankTransactionReconciliationStatus, BankTransactionType


class BankTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    bank_statement_id: uuid.UUID
    bank_account_id: uuid.UUID
    transaction_date: date
    value_date: date | None
    description: str
    reference_number: str | None
    cheque_number: str | None
    debit_amount: Decimal
    credit_amount: Decimal
    amount: Decimal
    balance_after_transaction: Decimal | None
    transaction_type: BankTransactionType
    normalized_description: str | None
    normalized_reference: str | None
    external_transaction_id: str | None
    reconciliation_status: BankTransactionReconciliationStatus
    created_at: datetime
    updated_at: datetime

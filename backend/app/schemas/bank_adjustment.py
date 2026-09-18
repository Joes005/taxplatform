import uuid

from pydantic import BaseModel, Field


class BankAdjustmentCreate(BaseModel):
    """Creates a real Phase 3 JournalEntry offsetting a bank transaction
    against another ledger (e.g. Bank Charges, Interest Income) — never a
    parallel adjustment ledger (PHASE6 §24)."""

    financial_year_id: uuid.UUID
    journal_number: str = Field(min_length=1, max_length=50)
    offset_ledger_id: uuid.UUID
    narration: str | None = Field(default=None, max_length=500)

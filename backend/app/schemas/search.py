from decimal import Decimal
from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    id: str
    type: str  # CUSTOMER, VENDOR, SALES_INVOICE, PURCHASE_INVOICE, RECEIPT, PAYMENT, LEDGER, DOCUMENT, BANK_TRANSACTION, AUDIT_FINDING, COMPLIANCE_OBLIGATION
    identifier: str
    title: str
    subtitle: str | None = None
    status: str | None = None
    date: str | None = None
    amount: Decimal | None = None
    target_url: str


class SearchResponse(BaseModel):
    query: str
    total: int
    items: list[SearchResultItem] = Field(default_factory=list)

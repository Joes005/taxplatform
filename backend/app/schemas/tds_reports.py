import uuid
from decimal import Decimal

from pydantic import BaseModel


class TDSQuarterlySummary(BaseModel):
    transaction_count: int
    deductee_count: int
    gross_amount: Decimal
    tds_deducted: Decimal
    tds_paid: Decimal
    tds_outstanding: Decimal
    review_required_count: int


class TDSSectionSummaryRow(BaseModel):
    tds_section_id: uuid.UUID
    section_code: str
    transaction_count: int
    gross_amount: Decimal
    tds_deducted: Decimal
    tds_paid: Decimal
    tds_outstanding: Decimal


class TDSDeducteeSummaryRow(BaseModel):
    deductee_id: uuid.UUID
    deductee_name: str
    pan: str | None
    transaction_count: int
    gross_amount: Decimal
    tds_deducted: Decimal
    tds_paid: Decimal
    tds_outstanding: Decimal


class TDSChallanSummaryRow(BaseModel):
    challan_id: uuid.UUID
    challan_number: str
    amount: Decimal
    allocated_amount: Decimal
    unallocated_amount: Decimal
    status: str


class TDSReturnPreparationSummary(BaseModel):
    """Everything a TDSReturnSnapshot freezes for one quarter — always
    labeled a *preparation*, never a filed return (PHASE5 sections 26,
    60)."""

    quarterly: TDSQuarterlySummary
    by_section: list[TDSSectionSummaryRow]
    by_deductee: list[TDSDeducteeSummaryRow]
    challans: list[TDSChallanSummaryRow]

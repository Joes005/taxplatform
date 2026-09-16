import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.gst_enums import ITCCategory, ITCReviewStatus, ReconciliationStatus


class GSTReconciliationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    return_period_id: uuid.UUID
    run_at: datetime
    run_by: uuid.UUID
    total_purchase_invoices: int
    matched_count: int
    partially_matched_count: int
    mismatch_count: int
    books_only_count: int
    gstr2b_only_count: int
    duplicate_count: int
    review_required_count: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def match_percentage(self) -> Decimal:
        if self.total_purchase_invoices == 0:
            return Decimal("0")
        matched = self.matched_count + self.partially_matched_count
        return (Decimal(matched) / Decimal(self.total_purchase_invoices) * 100).quantize(Decimal("0.01"))


class GSTReconciliationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reconciliation_id: uuid.UUID
    purchase_invoice_id: uuid.UUID | None
    gstr2b_record_id: uuid.UUID | None
    status: ReconciliationStatus
    books_taxable_value: Decimal | None
    books_cgst_amount: Decimal | None
    books_sgst_amount: Decimal | None
    books_igst_amount: Decimal | None
    books_cess_amount: Decimal | None
    gstr2b_taxable_value: Decimal | None
    gstr2b_cgst_amount: Decimal | None
    gstr2b_sgst_amount: Decimal | None
    gstr2b_igst_amount: Decimal | None
    gstr2b_cess_amount: Decimal | None
    taxable_value_diff: Decimal | None
    tax_diff: Decimal | None
    itc_category: ITCCategory | None
    itc_review_status: ITCReviewStatus
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    review_comment: str | None


class ITCReviewRequest(BaseModel):
    status: ITCReviewStatus
    comment: str | None = Field(default=None, max_length=500)


class ITCReviewCommentRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=500)


class ITCApprovalRequest(BaseModel):
    approved: bool
    comment: str | None = Field(default=None, max_length=500)


class ITCSummaryEntry(BaseModel):
    count: int
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_itc: Decimal


ITCSummaryResponse = dict[ITCCategory, ITCSummaryEntry]

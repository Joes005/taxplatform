import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.tds_enums import TDSReconciliationStatus


class TDSPaymentReconciliationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    tds_transaction_id: uuid.UUID | None
    tds_challan_id: uuid.UUID | None
    status: TDSReconciliationStatus
    expected_amount: Decimal | None
    allocated_amount: Decimal | None
    variance_amount: Decimal | None
    notes: str | None
    run_at: datetime

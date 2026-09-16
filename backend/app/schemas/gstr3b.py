import uuid
from decimal import Decimal

from pydantic import BaseModel


class GSTR3BOutwardSupplies(BaseModel):
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal


class GSTR3BInputTaxCredit(BaseModel):
    itc_matched: Decimal
    itc_approved: Decimal
    itc_review_required: Decimal
    cgst_available: Decimal
    sgst_available: Decimal
    igst_available: Decimal
    cess_available: Decimal


class GSTR3BNetLiability(BaseModel):
    output_tax: Decimal
    eligible_itc: Decimal
    net_liability: Decimal
    cgst_net: Decimal
    sgst_net: Decimal
    igst_net: Decimal
    cess_net: Decimal


class GSTR3BSummary(BaseModel):
    return_period_id: uuid.UUID
    outward_supplies: GSTR3BOutwardSupplies
    input_tax_credit: GSTR3BInputTaxCredit
    net_liability: GSTR3BNetLiability
    error_count: int
    warning_count: int

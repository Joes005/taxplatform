"""The single place GST tax amounts are computed from a taxable value, a
rate, and a supply type. GSTR-1, GSTR-3B, and any other GST view must read
already-persisted amounts or call this service — never re-derive tax
arithmetic with their own formula (PHASE4 section 11).

Reuses `round_money` from `AccountingCalculationService` so paise rounding
is identical everywhere in the platform, not merely "similar."
"""

from dataclasses import dataclass
from decimal import Decimal

from app.core.exceptions import ValidationAppError
from app.models.gst_enums import SupplyType
from app.services.accounting_calculation_service import round_money


@dataclass
class GSTTaxBreakdown:
    taxable_value: Decimal
    supply_type: SupplyType
    cgst_rate: Decimal
    cgst_amount: Decimal
    sgst_rate: Decimal
    sgst_amount: Decimal
    igst_rate: Decimal
    igst_amount: Decimal
    cess_rate: Decimal
    cess_amount: Decimal
    total_tax: Decimal
    total_value: Decimal


class GSTCalculationService:
    @staticmethod
    def calculate_tax_breakdown(
        *,
        taxable_value: Decimal,
        rate: Decimal,
        supply_type: SupplyType,
        cess_rate: Decimal = Decimal("0"),
    ) -> GSTTaxBreakdown:
        if taxable_value < 0:
            raise ValidationAppError("Taxable value cannot be negative", code="INVALID_AMOUNT")
        if rate < 0:
            raise ValidationAppError("GST rate cannot be negative", code="INVALID_TAX_RATE")

        if supply_type == SupplyType.INTRA_STATE:
            cgst_rate = round_money(rate / 2)
            sgst_rate = round_money(rate / 2)
            igst_rate = Decimal("0")
        else:
            cgst_rate = Decimal("0")
            sgst_rate = Decimal("0")
            igst_rate = rate

        cgst_amount = round_money(taxable_value * cgst_rate / 100)
        sgst_amount = round_money(taxable_value * sgst_rate / 100)
        igst_amount = round_money(taxable_value * igst_rate / 100)
        cess_amount = round_money(taxable_value * cess_rate / 100)
        total_tax = cgst_amount + sgst_amount + igst_amount + cess_amount

        return GSTTaxBreakdown(
            taxable_value=taxable_value,
            supply_type=supply_type,
            cgst_rate=cgst_rate,
            cgst_amount=cgst_amount,
            sgst_rate=sgst_rate,
            sgst_amount=sgst_amount,
            igst_rate=igst_rate,
            igst_amount=igst_amount,
            cess_rate=cess_rate,
            cess_amount=cess_amount,
            total_tax=total_tax,
            total_value=taxable_value + total_tax,
        )

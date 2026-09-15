"""Reusable tax/total arithmetic shared by Sales Invoices, Purchase
Invoices, Credit Notes, and Debit Notes — see the module docstring context
in accounting_guards.py for why this lives in one place. All computation
happens in Decimal, rounded to 2 places (paise) at each step, matching how
real invoices round line-by-line rather than only at the very end.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.core.exceptions import ValidationAppError

TWO_PLACES = Decimal("0.01")


def round_money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class LineItemInput:
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal = Decimal("0")
    cgst_rate: Decimal = Decimal("0")
    sgst_rate: Decimal = Decimal("0")
    igst_rate: Decimal = Decimal("0")
    cess_rate: Decimal = Decimal("0")

    @property
    def tax_rate(self) -> Decimal:
        return self.cgst_rate + self.sgst_rate + self.igst_rate


@dataclass
class LineItemResult:
    taxable_value: Decimal
    tax_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_amount: Decimal


@dataclass
class DocumentTotals:
    subtotal: Decimal
    discount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    total_tax: Decimal
    grand_total: Decimal
    round_off: Decimal
    line_results: list[LineItemResult] = field(default_factory=list)


class AccountingCalculationService:
    @staticmethod
    def calculate_line_item(item: LineItemInput) -> LineItemResult:
        if item.quantity <= 0:
            raise ValidationAppError("Quantity must be greater than zero", code="INVALID_QUANTITY")
        if item.unit_price < 0:
            raise ValidationAppError("Unit price cannot be negative", code="INVALID_AMOUNT")
        if item.igst_rate > 0 and (item.cgst_rate > 0 or item.sgst_rate > 0):
            raise ValidationAppError(
                "A line item cannot have both IGST and CGST/SGST rates set — "
                "a sale is either intra-state (CGST+SGST) or inter-state (IGST), never both",
                code="INVALID_TAX_SPLIT",
            )

        gross = item.quantity * item.unit_price
        taxable_value = round_money(gross - item.discount)
        if taxable_value < 0:
            raise ValidationAppError(
                "Discount cannot exceed the line item's value", code="INVALID_AMOUNT"
            )

        cgst_amount = round_money(taxable_value * item.cgst_rate / 100)
        sgst_amount = round_money(taxable_value * item.sgst_rate / 100)
        igst_amount = round_money(taxable_value * item.igst_rate / 100)
        cess_amount = round_money(taxable_value * item.cess_rate / 100)
        total_amount = taxable_value + cgst_amount + sgst_amount + igst_amount + cess_amount

        return LineItemResult(
            taxable_value=taxable_value,
            tax_rate=item.tax_rate,
            cgst_amount=cgst_amount,
            sgst_amount=sgst_amount,
            igst_amount=igst_amount,
            cess_amount=cess_amount,
            total_amount=total_amount,
        )

    @classmethod
    def calculate_document(
        cls, items: list[LineItemInput], *, document_discount: Decimal = Decimal("0")
    ) -> DocumentTotals:
        if not items:
            raise ValidationAppError("A document must have at least one line item", code="NO_ITEMS")

        line_results = [cls.calculate_line_item(item) for item in items]

        subtotal = round_money(sum((i.quantity * i.unit_price for i in items), Decimal("0")))
        item_discount = round_money(sum((i.discount for i in items), Decimal("0")))
        discount = item_discount + document_discount

        taxable_amount = round_money(sum((r.taxable_value for r in line_results), Decimal("0")))
        cgst_amount = round_money(sum((r.cgst_amount for r in line_results), Decimal("0")))
        sgst_amount = round_money(sum((r.sgst_amount for r in line_results), Decimal("0")))
        igst_amount = round_money(sum((r.igst_amount for r in line_results), Decimal("0")))
        cess_amount = round_money(sum((r.cess_amount for r in line_results), Decimal("0")))
        total_tax = cgst_amount + sgst_amount + igst_amount + cess_amount

        raw_total = taxable_amount + total_tax - document_discount
        grand_total = raw_total.to_integral_value(rounding=ROUND_HALF_UP)
        round_off = round_money(grand_total - raw_total)

        return DocumentTotals(
            subtotal=subtotal,
            discount=discount,
            taxable_amount=taxable_amount - document_discount,
            cgst_amount=cgst_amount,
            sgst_amount=sgst_amount,
            igst_amount=igst_amount,
            cess_amount=cess_amount,
            total_tax=total_tax,
            grand_total=round_money(grand_total),
            round_off=round_off,
            line_results=line_results,
        )

    @staticmethod
    def validate_journal_balance(debit_total: Decimal, credit_total: Decimal) -> None:
        if round_money(debit_total) != round_money(credit_total):
            raise ValidationAppError(
                f"Journal entry is not balanced: total debit {debit_total} != "
                f"total credit {credit_total}",
                code="UNBALANCED_JOURNAL",
            )

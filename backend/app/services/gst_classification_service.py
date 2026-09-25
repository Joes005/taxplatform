"""Classifies a sales transaction into a GSTR-1 category from the data
already on the SalesInvoice/Customer — it never guesses. EXPORT and SEZ
require an explicit indicator (a customer flagged as SEZ, a shipping
country outside India, ...) that Phase 3's Customer/SalesInvoice models do
not currently capture; until that data exists, transactions that are not
clearly B2B or B2C fall back to REVIEW_REQUIRED rather than a wrong guess
(PHASE4 section 12).
"""

from dataclasses import dataclass

from app.models.gst_enums import GSTTransactionCategory
from app.utils.gstin import is_valid_gstin


@dataclass
class GSTClassificationResult:
    category: GSTTransactionCategory
    reason: str | None = None


class GSTTransactionClassificationService:
    @staticmethod
    def classify_sales_transaction(
        *,
        customer_gstin: str | None,
        customer_state_code: str | None,
        place_of_supply_state_code: str | None,
        is_export: bool = False,
        is_sez: bool = False,
        export_type: str | None = None,
    ) -> GSTClassificationResult:
        if is_export or (export_type in ("WITH_PAYMENT", "WITHOUT_PAYMENT", "DEEMED_EXPORT")):
            return GSTClassificationResult(category=GSTTransactionCategory.EXPORT)

        if is_sez or (export_type in ("SEZ_WITH_PAYMENT", "SEZ_WITHOUT_PAYMENT")):
            return GSTClassificationResult(category=GSTTransactionCategory.SEZ)

        if not place_of_supply_state_code:
            return GSTClassificationResult(
                category=GSTTransactionCategory.REVIEW_REQUIRED,
                reason="Place of supply is missing",
            )

        if customer_gstin:
            if not is_valid_gstin(customer_gstin):
                return GSTClassificationResult(
                    category=GSTTransactionCategory.REVIEW_REQUIRED,
                    reason="Customer GSTIN is present but not a structurally valid GSTIN",
                )
            return GSTClassificationResult(category=GSTTransactionCategory.B2B)

        if not customer_state_code:
            return GSTClassificationResult(
                category=GSTTransactionCategory.REVIEW_REQUIRED,
                reason="Customer has no GSTIN and no state code to classify as B2C",
            )

        return GSTClassificationResult(category=GSTTransactionCategory.B2C)

"""GSTR-3B preparation — a summary built from GSTR-1 outward-supply data
and the latest reconciliation's ITC results (PHASE4 sections 39-42). Only
ITC results an accountant/auditor has explicitly ACCEPTED reduce the net
liability; PENDING or REJECTED amounts are shown separately and never
netted in automatically, matching the spec's "do not automatically claim
disputed amounts" rule.
"""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.gst_enums import ITCCategory, ITCReviewStatus
from app.repositories.gst_reconciliation_repository import GSTReconciliationRepository
from app.schemas.gstr3b import (
    GSTR3BInputTaxCredit,
    GSTR3BNetLiability,
    GSTR3BOutwardSupplies,
    GSTR3BSummary,
)
from app.services.gstr1_service import GSTR1Service
from app.services.itc_service import ITCService

ZERO = Decimal("0.00")


class GSTR3BService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.gstr1 = GSTR1Service(db)
        self.itc = ITCService(db)
        self.recon_repo = GSTReconciliationRepository(db)

    async def generate(self, company_id: uuid.UUID, return_period_id: uuid.UUID) -> GSTR3BSummary:
        b2b = await self.gstr1.get_b2b(company_id, return_period_id)
        b2c_large = await self.gstr1.get_b2c_large(company_id, return_period_id)
        b2c_others = await self.gstr1.get_b2c_others(company_id, return_period_id)
        credit_notes = await self.gstr1.get_credit_notes(company_id, return_period_id)
        debit_notes = await self.gstr1.get_debit_notes(company_id, return_period_id)

        outward_taxable = sum((r.taxable_value for r in b2b + b2c_large), ZERO) + sum(
            (r.taxable_value for r in b2c_others), ZERO
        )
        outward_cgst = sum((r.cgst_amount for r in b2b + b2c_large), ZERO) + sum(
            (r.cgst_amount for r in b2c_others), ZERO
        )
        outward_sgst = sum((r.sgst_amount for r in b2b + b2c_large), ZERO) + sum(
            (r.sgst_amount for r in b2c_others), ZERO
        )
        outward_igst = sum((r.igst_amount for r in b2b + b2c_large), ZERO) + sum(
            (r.igst_amount for r in b2c_others), ZERO
        )
        outward_cess = sum((r.cess_amount for r in b2b + b2c_large), ZERO) + sum(
            (r.cess_amount for r in b2c_others), ZERO
        )

        # Credit notes reduce outward tax liability, debit notes increase it.
        outward_taxable += sum((n.taxable_value for n in debit_notes), ZERO) - sum(
            (n.taxable_value for n in credit_notes), ZERO
        )
        outward_cgst += sum((n.cgst_amount for n in debit_notes), ZERO) - sum(
            (n.cgst_amount for n in credit_notes), ZERO
        )
        outward_sgst += sum((n.sgst_amount for n in debit_notes), ZERO) - sum(
            (n.sgst_amount for n in credit_notes), ZERO
        )
        outward_igst += sum((n.igst_amount for n in debit_notes), ZERO) - sum(
            (n.igst_amount for n in credit_notes), ZERO
        )
        outward_cess += sum((n.cess_amount for n in debit_notes), ZERO) - sum(
            (n.cess_amount for n in credit_notes), ZERO
        )

        findings = await self.gstr1.validate(company_id, return_period_id)
        from app.models.gst_enums import ValidationSeverity

        error_count = sum(1 for f in findings if f.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for f in findings if f.severity == ValidationSeverity.WARNING)

        try:
            itc_category_summary = await self.itc.get_summary(company_id, return_period_id)
            itc_matched = itc_category_summary[ITCCategory.MATCHED_ITC]["total_itc"]
        except NotFoundError:
            # No reconciliation has been run yet for this period — outward
            # supplies can still be prepared, ITC simply shows as zero
            # rather than blocking GSTR-3B preparation entirely.
            itc_matched = ZERO

        run = await self.recon_repo.get_latest_run(company_id, return_period_id)
        by_review_status = (
            await self.recon_repo.summary_by_review_status(run.id) if run else {}
        )
        accepted = by_review_status.get(
            ITCReviewStatus.ACCEPTED,
            {"cgst_amount": ZERO, "sgst_amount": ZERO, "igst_amount": ZERO, "cess_amount": ZERO},
        )
        pending = by_review_status.get(
            ITCReviewStatus.PENDING,
            {"cgst_amount": ZERO, "sgst_amount": ZERO, "igst_amount": ZERO, "cess_amount": ZERO},
        )
        reviewed = by_review_status.get(
            ITCReviewStatus.REVIEWED,
            {"cgst_amount": ZERO, "sgst_amount": ZERO, "igst_amount": ZERO, "cess_amount": ZERO},
        )

        itc_approved = accepted["cgst_amount"] + accepted["sgst_amount"] + accepted["igst_amount"] + accepted["cess_amount"]
        itc_review_required = sum(
            (
                s["cgst_amount"] + s["sgst_amount"] + s["igst_amount"] + s["cess_amount"]
                for s in (pending, reviewed)
            ),
            ZERO,
        )

        output_tax = outward_cgst + outward_sgst + outward_igst + outward_cess
        net_cgst = max(outward_cgst - accepted["cgst_amount"], ZERO)
        net_sgst = max(outward_sgst - accepted["sgst_amount"], ZERO)
        net_igst = max(outward_igst - accepted["igst_amount"], ZERO)
        net_cess = max(outward_cess - accepted["cess_amount"], ZERO)

        return GSTR3BSummary(
            return_period_id=return_period_id,
            outward_supplies=GSTR3BOutwardSupplies(
                taxable_value=outward_taxable,
                cgst_amount=outward_cgst,
                sgst_amount=outward_sgst,
                igst_amount=outward_igst,
                cess_amount=outward_cess,
            ),
            input_tax_credit=GSTR3BInputTaxCredit(
                itc_matched=itc_matched,
                itc_approved=itc_approved,
                itc_review_required=itc_review_required,
                cgst_available=accepted["cgst_amount"],
                sgst_available=accepted["sgst_amount"],
                igst_available=accepted["igst_amount"],
                cess_available=accepted["cess_amount"],
            ),
            net_liability=GSTR3BNetLiability(
                output_tax=output_tax,
                eligible_itc=itc_approved,
                net_liability=net_cgst + net_sgst + net_igst + net_cess,
                cgst_net=net_cgst,
                sgst_net=net_sgst,
                igst_net=net_igst,
                cess_net=net_cess,
            ),
            error_count=error_count,
            warning_count=warning_count,
        )

"""Read-only TDS reporting — aggregates transactions/challans already in
the database into the summary shapes both the return-preparation snapshot
(`TDSReturnService`) and the standalone report endpoints use, so the two
never compute the same numbers two different ways (PHASE5 sections 20,
27, 59).
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tds_enums import TDSApplicabilityStatus, TDSTransactionStatus
from app.models.tds_transaction import TDSTransaction
from app.repositories.deductee_repository import DeducteeRepository
from app.repositories.tds_challan_repository import TDSChallanRepository
from app.repositories.tds_section_repository import TDSSectionRepository
from app.repositories.tds_transaction_repository import TDSTransactionRepository
from app.schemas.tds_reports import (
    TDSChallanSummaryRow,
    TDSDeducteeSummaryRow,
    TDSQuarterlySummary,
    TDSSectionSummaryRow,
)


class TDSReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.transactions = TDSTransactionRepository(db)
        self.challans = TDSChallanRepository(db)
        self.sections = TDSSectionRepository(db)
        self.deductees = DeducteeRepository(db)

    async def _transactions_for_period(
        self, company_id: uuid.UUID, period_start: date, period_end: date
    ) -> list[TDSTransaction]:
        return await self.transactions.list_for_period(
            company_id, period_start=period_start, period_end=period_end
        )

    def _paid_amount(self, txn: TDSTransaction) -> Decimal:
        return txn.tds_amount if txn.status == TDSTransactionStatus.PAID else Decimal("0")

    async def quarterly_summary(
        self, company_id: uuid.UUID, period_start: date, period_end: date
    ) -> TDSQuarterlySummary:
        txns = await self._transactions_for_period(company_id, period_start, period_end)
        deducted = sum((t.tds_amount for t in txns), Decimal("0"))
        paid = sum((self._paid_amount(t) for t in txns), Decimal("0"))
        review_required = sum(
            1 for t in txns if t.status == TDSTransactionStatus.REVIEW_REQUIRED
        )
        return TDSQuarterlySummary(
            transaction_count=len(txns),
            deductee_count=len({t.deductee_id for t in txns}),
            gross_amount=sum((t.gross_amount for t in txns), Decimal("0")),
            tds_deducted=deducted,
            tds_paid=paid,
            tds_outstanding=deducted - paid,
            review_required_count=review_required,
        )

    async def section_summary(
        self, company_id: uuid.UUID, period_start: date, period_end: date
    ) -> list[TDSSectionSummaryRow]:
        txns = await self._transactions_for_period(company_id, period_start, period_end)
        by_section: dict[uuid.UUID, list[TDSTransaction]] = {}
        for t in txns:
            by_section.setdefault(t.tds_section_id, []).append(t)

        rows: list[TDSSectionSummaryRow] = []
        for section_id, group in by_section.items():
            section = await self.sections.get_by_id(section_id)
            deducted = sum((t.tds_amount for t in group), Decimal("0"))
            paid = sum((self._paid_amount(t) for t in group), Decimal("0"))
            rows.append(
                TDSSectionSummaryRow(
                    tds_section_id=section_id,
                    section_code=section.section_code if section else "UNKNOWN",
                    transaction_count=len(group),
                    gross_amount=sum((t.gross_amount for t in group), Decimal("0")),
                    tds_deducted=deducted,
                    tds_paid=paid,
                    tds_outstanding=deducted - paid,
                )
            )
        return sorted(rows, key=lambda r: r.section_code)

    async def deductee_summary(
        self, company_id: uuid.UUID, period_start: date, period_end: date
    ) -> list[TDSDeducteeSummaryRow]:
        txns = await self._transactions_for_period(company_id, period_start, period_end)
        by_deductee: dict[uuid.UUID, list[TDSTransaction]] = {}
        for t in txns:
            by_deductee.setdefault(t.deductee_id, []).append(t)

        rows: list[TDSDeducteeSummaryRow] = []
        for deductee_id, group in by_deductee.items():
            deductee = await self.deductees.get_by_id_for_company(deductee_id, company_id)
            deducted = sum((t.tds_amount for t in group), Decimal("0"))
            paid = sum((self._paid_amount(t) for t in group), Decimal("0"))
            rows.append(
                TDSDeducteeSummaryRow(
                    deductee_id=deductee_id,
                    deductee_name=deductee.name if deductee else "Unknown",
                    pan=deductee.pan if deductee else None,
                    transaction_count=len(group),
                    gross_amount=sum((t.gross_amount for t in group), Decimal("0")),
                    tds_deducted=deducted,
                    tds_paid=paid,
                    tds_outstanding=deducted - paid,
                )
            )
        return sorted(rows, key=lambda r: r.deductee_name)

    async def challan_summary(
        self, company_id: uuid.UUID, financial_year_id: uuid.UUID
    ) -> list[TDSChallanSummaryRow]:
        challans = await self.challans.list_active_for_fy(company_id, financial_year_id)
        rows: list[TDSChallanSummaryRow] = []
        for challan in challans:
            allocated = await self.challans.sum_allocated(challan.id)
            rows.append(
                TDSChallanSummaryRow(
                    challan_id=challan.id,
                    challan_number=challan.challan_number,
                    amount=challan.amount,
                    allocated_amount=allocated,
                    unallocated_amount=challan.amount - allocated,
                    status=challan.status.value,
                )
            )
        return sorted(rows, key=lambda r: r.challan_number)

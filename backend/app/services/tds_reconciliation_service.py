import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.models.tds_enums import TDSChallanStatus, TDSReconciliationStatus
from app.models.tds_reconciliation import TDSPaymentReconciliation
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.tds_challan_repository import TDSChallanRepository
from app.repositories.tds_reconciliation_repository import TDSReconciliationRepository
from app.repositories.tds_transaction_repository import TDSTransactionRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class TDSReconciliationService:
    """Compares TDS deducted against challan allocations for one financial
    year (PHASE5 section 23). Fully recomputed on every run — never edited
    directly — so it always reflects the current state of transactions and
    challans rather than drifting from it.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TDSReconciliationRepository(db)
        self.transactions = TDSTransactionRepository(db)
        self.challans = TDSChallanRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def run(
        self,
        company_id: uuid.UUID,
        financial_year_id: uuid.UUID,
        current_user: User,
        meta: RequestMeta,
    ) -> list[TDSPaymentReconciliation]:
        financial_year = await self.fy_repo.get_by_id_for_company(financial_year_id, company_id)
        if financial_year is None:
            raise ValidationAppError(
                "Financial year not found for this company", code="INVALID_FINANCIAL_YEAR"
            )

        await self.repo.clear_for_financial_year(company_id, financial_year_id)
        run_at = datetime.now(timezone.utc)
        rows: list[TDSPaymentReconciliation] = []

        transactions = await self.transactions.list_deducted_or_paid_for_fy(company_id, financial_year_id)
        for transaction in transactions:
            allocated = await self.challans.sum_allocated_for_transaction(transaction.id)
            expected = transaction.tds_amount

            if allocated == 0:
                status = TDSReconciliationStatus.MISSING_CHALLAN
            elif allocated == expected:
                status = TDSReconciliationStatus.MATCHED
            elif allocated < expected:
                status = TDSReconciliationStatus.PARTIALLY_MATCHED
            else:
                status = TDSReconciliationStatus.AMOUNT_MISMATCH

            rows.append(
                TDSPaymentReconciliation(
                    company_id=company_id,
                    financial_year_id=financial_year_id,
                    tds_transaction_id=transaction.id,
                    status=status,
                    expected_amount=expected,
                    allocated_amount=allocated,
                    variance_amount=expected - allocated,
                    run_at=run_at,
                )
            )

        challans = await self.challans.list_active_for_fy(company_id, financial_year_id)
        for challan in challans:
            allocated = await self.challans.sum_allocated(challan.id)
            if allocated < challan.amount and challan.status in (
                TDSChallanStatus.GENERATED,
                TDSChallanStatus.PAID,
            ):
                rows.append(
                    TDSPaymentReconciliation(
                        company_id=company_id,
                        financial_year_id=financial_year_id,
                        tds_challan_id=challan.id,
                        status=TDSReconciliationStatus.UNALLOCATED_PAYMENT,
                        expected_amount=challan.amount,
                        allocated_amount=allocated,
                        variance_amount=challan.amount - allocated,
                        run_at=run_at,
                    )
                )
            elif allocated == challan.amount and challan.status == TDSChallanStatus.PAID:
                challan.status = TDSChallanStatus.RECONCILED

        for row in rows:
            await self.repo.create(row)
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.TDS_CHALLAN_RECONCILED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_reconciliation",
            resource_id=str(financial_year_id),
            description=f"TDS reconciliation run for FY {financial_year.name}: {len(rows)} findings",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return rows

    async def list(
        self,
        company_id: uuid.UUID,
        *,
        financial_year_id: uuid.UUID | None,
        status: TDSReconciliationStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[TDSPaymentReconciliation], int]:
        return await self.repo.list_for_company(
            company_id,
            financial_year_id=financial_year_id,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

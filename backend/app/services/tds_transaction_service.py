import uuid
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.tds_enums import TDSApplicabilityStatus, TDSTransactionStatus
from app.models.tds_transaction import TDSTransaction
from app.models.user import User
from app.repositories.deductee_repository import DeducteeRepository
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.tds_section_repository import TDSSectionRepository
from app.repositories.tds_transaction_repository import TDSTransactionRepository
from app.schemas.tds_transaction import (
    TDSTransactionCreate,
    TDSTransactionOverride,
    TDSTransactionUpdate,
)
from app.services.accounting_calculation_service import round_money
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.tds_rule_engine import TDSRuleEngine

# A transaction may only be calculated from DRAFT (first calculation) or
# from CALCULATED/REVIEW_REQUIRED (recalculation after the underlying data
# changed) — never once it's been DEDUCTED/PAID/CANCELLED (PHASE5 §19).
_CALCULABLE_FROM = {
    TDSTransactionStatus.DRAFT,
    TDSTransactionStatus.CALCULATED,
    TDSTransactionStatus.REVIEW_REQUIRED,
}
_CANCELLABLE_FROM = {TDSTransactionStatus.DRAFT, TDSTransactionStatus.CALCULATED}


class TDSTransactionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TDSTransactionRepository(db)
        self.deductees = DeducteeRepository(db)
        self.sections = TDSSectionRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.engine = TDSRuleEngine(db)
        self.audit = AuditService(db)

    async def create(
        self,
        company_id: uuid.UUID,
        payload: TDSTransactionCreate,
        current_user: User,
        meta: RequestMeta,
    ) -> TDSTransaction:
        deductee = await self.deductees.get_by_id_for_company(payload.deductee_id, company_id)
        if deductee is None:
            raise ValidationAppError("Deductee not found for this company", code="DEDUCTEE_NOT_FOUND")

        section = await self.sections.get_by_id(payload.tds_section_id)
        if section is None:
            raise ValidationAppError("TDS section not found", code="TDS_SECTION_NOT_FOUND")

        financial_year = await self.fy_repo.get_for_date(company_id, payload.transaction_date)
        if financial_year is None:
            raise ValidationAppError(
                "No financial year covers this transaction date", code="NO_FINANCIAL_YEAR_FOR_DATE"
            )

        transaction = TDSTransaction(
            company_id=company_id,
            financial_year_id=financial_year.id,
            deductee_id=deductee.id,
            tds_section_id=section.id,
            source_type=payload.source_type,
            source_id=payload.source_id,
            transaction_date=payload.transaction_date,
            gross_amount=round_money(payload.gross_amount),
            taxable_amount=round_money(payload.gross_amount),
            pan_status=deductee.pan_status,
            status=TDSTransactionStatus.DRAFT,
        )
        await self.repo.create(transaction)

        await self.audit.log(
            action=AuditAction.TDS_TRANSACTION_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_transaction",
            resource_id=str(transaction.id),
            description=f"TDS transaction created for deductee '{deductee.name}' "
            f"({section.section_code}, {transaction.gross_amount})",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return transaction

    async def get(self, company_id: uuid.UUID, transaction_id: uuid.UUID) -> TDSTransaction:
        transaction = await self.repo.get_by_id_for_company(transaction_id, company_id)
        if transaction is None:
            raise NotFoundError("TDS transaction not found", code="TDS_TRANSACTION_NOT_FOUND")
        return transaction

    async def list(
        self,
        company_id: uuid.UUID,
        *,
        deductee_id: uuid.UUID | None = None,
        tds_section_id: uuid.UUID | None = None,
        status: TDSTransactionStatus | None = None,
        financial_year_id: uuid.UUID | None = None,
        page: int,
        page_size: int,
    ) -> tuple[list[TDSTransaction], int]:
        return await self.repo.list_for_company(
            company_id,
            deductee_id=deductee_id,
            tds_section_id=tds_section_id,
            status=status,
            financial_year_id=financial_year_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    async def update(
        self,
        company_id: uuid.UUID,
        transaction_id: uuid.UUID,
        payload: TDSTransactionUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> TDSTransaction:
        transaction = await self.get(company_id, transaction_id)
        if transaction.status != TDSTransactionStatus.DRAFT:
            raise ConflictError(
                "Only a DRAFT TDS transaction can be edited", code="INVALID_TDS_TRANSACTION_STATUS"
            )

        updates = payload.model_dump(exclude_unset=True)
        if "gross_amount" in updates:
            updates["gross_amount"] = round_money(updates["gross_amount"])
            updates["taxable_amount"] = updates["gross_amount"]
        for field, value in updates.items():
            setattr(transaction, field, value)

        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def calculate(
        self, company_id: uuid.UUID, transaction_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> TDSTransaction:
        transaction = await self.get(company_id, transaction_id)
        if transaction.status not in _CALCULABLE_FROM:
            raise ConflictError(
                f"TDS transaction cannot be calculated from status {transaction.status.value}",
                code="INVALID_TDS_TRANSACTION_STATUS",
            )

        deductee = await self.deductees.get_by_id_for_company(transaction.deductee_id, company_id)
        aggregate = await self.repo.sum_gross_amount_for_deductee_section_fy(
            company_id,
            deductee_id=transaction.deductee_id,
            tds_section_id=transaction.tds_section_id,
            financial_year_id=transaction.financial_year_id,
            exclude_transaction_id=transaction.id,
            as_of=transaction.transaction_date,
        )

        result = await self.engine.evaluate(
            company_id,
            tds_section_id=transaction.tds_section_id,
            deductee=deductee,
            transaction_date=transaction.transaction_date,
            amount=transaction.gross_amount,
            aggregate_paid_this_year=aggregate,
        )

        transaction.applicability_status = result.status
        transaction.applicability_reason = result.reason
        transaction.tds_rule_id = result.tds_rule_id
        transaction.pan_status = deductee.pan_status

        if result.status == TDSApplicabilityStatus.APPLICABLE:
            calc = result.calculation
            assert calc is not None
            transaction.tds_rate = calc.rate_used
            transaction.tds_amount = calc.tds_amount
            transaction.net_amount = calc.net_amount
            transaction.system_calculated_amount = calc.tds_amount
            transaction.status = TDSTransactionStatus.CALCULATED
        elif result.status == TDSApplicabilityStatus.NOT_APPLICABLE:
            transaction.tds_rate = 0
            transaction.tds_amount = 0
            transaction.net_amount = transaction.gross_amount
            transaction.system_calculated_amount = 0
            transaction.status = TDSTransactionStatus.CALCULATED
        else:
            transaction.status = TDSTransactionStatus.REVIEW_REQUIRED

        await self.db.flush()
        await self.db.refresh(transaction)

        await self.audit.log(
            action=AuditAction.TDS_TRANSACTION_CALCULATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_transaction",
            resource_id=str(transaction.id),
            description=f"TDS transaction calculated: {result.status.value} — {result.reason}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return transaction

    async def override(
        self,
        company_id: uuid.UUID,
        transaction_id: uuid.UUID,
        payload: TDSTransactionOverride,
        current_user: User,
        meta: RequestMeta,
    ) -> TDSTransaction:
        transaction = await self.get(company_id, transaction_id)
        if transaction.status != TDSTransactionStatus.CALCULATED:
            raise ConflictError(
                "Only a CALCULATED TDS transaction can be manually overridden",
                code="INVALID_TDS_TRANSACTION_STATUS",
            )

        transaction.tds_amount = round_money(payload.tds_amount)
        transaction.net_amount = transaction.gross_amount - transaction.tds_amount
        transaction.is_manual_override = True
        transaction.override_reason = payload.override_reason
        transaction.overridden_by = current_user.id
        transaction.overridden_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def deduct(
        self,
        company_id: uuid.UUID,
        transaction_id: uuid.UUID,
        current_user: User,
        meta: RequestMeta,
        *,
        deduction_date: date | None = None,
    ) -> TDSTransaction:
        transaction = await self.get(company_id, transaction_id)
        if transaction.status != TDSTransactionStatus.CALCULATED:
            raise ConflictError(
                "Only a CALCULATED TDS transaction can be deducted",
                code="INVALID_TDS_TRANSACTION_STATUS",
            )

        transaction.status = TDSTransactionStatus.DEDUCTED
        transaction.deduction_date = deduction_date or transaction.transaction_date
        await self.db.flush()
        await self.db.refresh(transaction)

        await self.audit.log(
            action=AuditAction.TDS_TRANSACTION_DEDUCTED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_transaction",
            resource_id=str(transaction.id),
            description=f"TDS of {transaction.tds_amount} deducted",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return transaction

    async def cancel(
        self, company_id: uuid.UUID, transaction_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> TDSTransaction:
        transaction = await self.get(company_id, transaction_id)
        if transaction.status not in _CANCELLABLE_FROM:
            raise ConflictError(
                f"TDS transaction cannot be cancelled from status {transaction.status.value}",
                code="INVALID_TDS_TRANSACTION_STATUS",
            )

        transaction.status = TDSTransactionStatus.CANCELLED
        await self.db.flush()
        await self.db.refresh(transaction)

        await self.audit.log(
            action=AuditAction.TDS_TRANSACTION_CANCELLED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_transaction",
            resource_id=str(transaction.id),
            description="TDS transaction cancelled",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return transaction

    async def payable_summary(
        self, company_id: uuid.UUID, *, financial_year_id: uuid.UUID | None = None
    ) -> dict:
        return await self.repo.payable_summary(company_id, financial_year_id=financial_year_id)

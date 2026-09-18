import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.bank_enums import BankTransactionReconciliationStatus
from app.models.bank_transaction import BankTransaction
from app.models.user import User
from app.repositories.bank_transaction_repository import BankTransactionRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

# A transaction can only be excluded/flagged while it has no active claim
# on it — once any match exists (even a partial one) the match must be
# reversed first, so a bank transaction's reconciliation state and its
# match history can never silently disagree.
_EXCLUDABLE_FROM = {
    BankTransactionReconciliationStatus.UNMATCHED,
    BankTransactionReconciliationStatus.MATCH_SUGGESTED,
    BankTransactionReconciliationStatus.REVIEW_REQUIRED,
}


class BankTransactionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BankTransactionRepository(db)
        self.audit = AuditService(db)

    async def get(self, company_id: uuid.UUID, transaction_id: uuid.UUID) -> BankTransaction:
        transaction = await self.repo.get_by_id_for_company(transaction_id, company_id)
        if transaction is None:
            raise NotFoundError("Bank transaction not found", code="BANK_TRANSACTION_NOT_FOUND")
        return transaction

    async def list(
        self,
        company_id: uuid.UUID,
        *,
        bank_account_id: uuid.UUID | None = None,
        bank_statement_id: uuid.UUID | None = None,
        reconciliation_status: BankTransactionReconciliationStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        page: int,
        page_size: int,
    ) -> tuple[list[BankTransaction], int]:
        return await self.repo.list_for_company(
            company_id,
            bank_account_id=bank_account_id,
            bank_statement_id=bank_statement_id,
            reconciliation_status=reconciliation_status,
            date_from=date_from,
            date_to=date_to,
            search=search,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    async def exclude(
        self, company_id: uuid.UUID, transaction_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> BankTransaction:
        transaction = await self.get(company_id, transaction_id)
        if transaction.reconciliation_status not in _EXCLUDABLE_FROM:
            raise ConflictError(
                f"Cannot exclude a transaction in status {transaction.reconciliation_status.value}",
                code="INVALID_BANK_TRANSACTION_STATUS",
            )
        transaction.reconciliation_status = BankTransactionReconciliationStatus.EXCLUDED
        await self.db.flush()
        await self.db.refresh(transaction)

        await self.audit.log(
            action=AuditAction.BANK_TRANSACTION_EXCLUDED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="bank_transaction",
            resource_id=str(transaction.id),
            description="Bank transaction excluded from reconciliation",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return transaction

    async def mark_review_required(
        self, company_id: uuid.UUID, transaction_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> BankTransaction:
        transaction = await self.get(company_id, transaction_id)
        if transaction.reconciliation_status not in _EXCLUDABLE_FROM:
            raise ConflictError(
                f"Cannot flag a transaction in status {transaction.reconciliation_status.value} for review",
                code="INVALID_BANK_TRANSACTION_STATUS",
            )
        transaction.reconciliation_status = BankTransactionReconciliationStatus.REVIEW_REQUIRED
        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.bank_enums import BankStatementStatus
from app.models.bank_statement import BankStatement
from app.models.user import User
from app.repositories.bank_account_repository import BankAccountRepository
from app.repositories.bank_statement_repository import BankStatementRepository
from app.repositories.bank_transaction_repository import BankTransactionRepository
from app.schemas.bank_statement import BankStatementBalanceCheck, BankStatementCreate
from app.services.accounting_calculation_service import round_money
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

_ARCHIVABLE_FROM = {BankStatementStatus.READY, BankStatementStatus.RECONCILED, BankStatementStatus.FAILED}


class BankStatementService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BankStatementRepository(db)
        self.accounts = BankAccountRepository(db)
        self.transactions = BankTransactionRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: BankStatementCreate, current_user: User, meta: RequestMeta
    ) -> BankStatement:
        account = await self.accounts.get_by_id_for_company(payload.bank_account_id, company_id)
        if account is None:
            raise ValidationAppError("Bank account not found for this company", code="BANK_ACCOUNT_NOT_FOUND")

        statement = BankStatement(
            company_id=company_id,
            bank_account_id=account.id,
            statement_name=payload.statement_name,
            period_start=payload.period_start,
            period_end=payload.period_end,
            opening_balance=round_money(payload.opening_balance),
            closing_balance=round_money(payload.closing_balance),
            source_type=payload.source_type,
            status=BankStatementStatus.PROCESSING,
            created_by=current_user.id,
        )
        await self.repo.create(statement)

        await self.audit.log(
            action=AuditAction.BANK_STATEMENT_IMPORTED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="bank_statement",
            resource_id=str(statement.id),
            description=f"Bank statement '{statement.statement_name}' registered for {account.account_name}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return statement

    async def get(self, company_id: uuid.UUID, statement_id: uuid.UUID) -> BankStatement:
        statement = await self.repo.get_by_id_for_company(statement_id, company_id)
        if statement is None:
            raise NotFoundError("Bank statement not found", code="BANK_STATEMENT_NOT_FOUND")
        return statement

    async def list(
        self, company_id: uuid.UUID, *, bank_account_id: uuid.UUID | None, page: int, page_size: int
    ) -> tuple[list[BankStatement], int]:
        return await self.repo.list_for_company(
            company_id, bank_account_id=bank_account_id, offset=(page - 1) * page_size, limit=page_size
        )

    async def mark_ready(self, statement: BankStatement) -> None:
        """Called by the import commit handler once its BankTransaction
        rows exist — never by an API route directly."""
        statement.status = BankStatementStatus.READY
        await self.db.flush()

    async def validate_balance(self, company_id: uuid.UUID, statement_id: uuid.UUID) -> BankStatementBalanceCheck:
        statement = await self.get(company_id, statement_id)
        total_debits, total_credits = await self.transactions.sum_debits_credits_for_statement(statement.id)
        expected_closing = round_money(statement.opening_balance + total_credits - total_debits)
        difference = round_money(statement.closing_balance - expected_closing)
        return BankStatementBalanceCheck(
            opening_balance=statement.opening_balance,
            closing_balance=statement.closing_balance,
            total_debits=total_debits,
            total_credits=total_credits,
            expected_closing_balance=expected_closing,
            difference=difference,
            balanced=(difference == Decimal("0.00")),
        )

    async def archive(
        self, company_id: uuid.UUID, statement_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> BankStatement:
        statement = await self.get(company_id, statement_id)
        if statement.status not in _ARCHIVABLE_FROM:
            raise ConflictError(
                f"A statement in status {statement.status.value} cannot be archived",
                code="INVALID_BANK_STATEMENT_STATUS",
            )
        statement.status = BankStatementStatus.ARCHIVED
        await self.db.flush()
        await self.db.refresh(statement)

        await self.audit.log(
            action=AuditAction.BANK_STATEMENT_ARCHIVED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="bank_statement",
            resource_id=str(statement.id),
            description=f"Bank statement '{statement.statement_name}' archived",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return statement

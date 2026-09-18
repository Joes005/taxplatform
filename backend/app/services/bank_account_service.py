import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.models.bank_account import BankAccount
from app.models.user import User
from app.repositories.bank_account_repository import BankAccountRepository
from app.repositories.ledger_repository import LedgerRepository
from app.schemas.bank_account import BankAccountCreate, BankAccountUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.base_master_data_service import SimpleMasterDataService


class BankAccountService(SimpleMasterDataService[BankAccount]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(
            db,
            BankAccountRepository(db),
            model_cls=BankAccount,
            resource_type="bank_account",
            display_field="account_name",
            not_found_code="BANK_ACCOUNT_NOT_FOUND",
        )
        self.ledgers = LedgerRepository(db)

    async def _validate_ledger(self, company_id: uuid.UUID, ledger_id: uuid.UUID | None) -> None:
        if ledger_id is None:
            return
        ledger = await self.ledgers.get_by_id_for_company(ledger_id, company_id)
        if ledger is None:
            raise ValidationAppError("Ledger not found for this company", code="INVALID_LEDGER")

    async def create(
        self, company_id: uuid.UUID, payload: BankAccountCreate, current_user: User, meta: RequestMeta
    ) -> BankAccount:
        await self._validate_ledger(company_id, payload.ledger_id)
        account = BankAccount(company_id=company_id, **payload.model_dump())
        await self.repo.create(account)

        await self.audit.log(
            action=AuditAction.BANK_ACCOUNT_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="bank_account",
            resource_id=str(account.id),
            description=f"Bank account '{account.account_name}' ({account.bank_name}) created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return account

    async def update(
        self,
        company_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: BankAccountUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> BankAccount:
        updates = payload.model_dump(exclude_unset=True)
        if "ledger_id" in updates:
            await self._validate_ledger(company_id, updates["ledger_id"])

        account = await self.get(company_id, entity_id)
        for field, value in updates.items():
            setattr(account, field, value)

        await self.db.flush()
        await self.db.refresh(account)

        await self.audit.log(
            action=AuditAction.BANK_ACCOUNT_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="bank_account",
            resource_id=str(account.id),
            description=f"Bank account '{account.account_name}' updated",
            metadata={"updated_fields": list(updates.keys())},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return account

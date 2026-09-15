import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.ledger import Ledger
from app.models.user import User
from app.repositories.ledger_repository import LedgerRepository
from app.schemas.ledger import LedgerCreate, LedgerUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class LedgerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = LedgerRepository(db)
        self.audit = AuditService(db)

    async def _validate_parent(
        self, company_id: uuid.UUID, parent_id: uuid.UUID | None, self_id: uuid.UUID | None
    ) -> None:
        if parent_id is None:
            return
        if self_id is not None and parent_id == self_id:
            raise ValidationAppError("A ledger cannot be its own parent", code="INVALID_LEDGER_PARENT")
        parent = await self.repo.get_by_id_for_company(parent_id, company_id)
        if parent is None:
            raise ValidationAppError(
                "Parent ledger not found in this company", code="INVALID_LEDGER_PARENT"
            )

    async def create(
        self, company_id: uuid.UUID, payload: LedgerCreate, current_user: User, meta: RequestMeta
    ) -> Ledger:
        await self._validate_parent(company_id, payload.parent_ledger_id, None)

        ledger = Ledger(company_id=company_id, **payload.model_dump())
        await self.repo.create(ledger)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_CREATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="ledger",
            resource_id=str(ledger.id),
            description=f"Ledger '{ledger.name}' created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return ledger

    async def get(self, company_id: uuid.UUID, ledger_id: uuid.UUID) -> Ledger:
        ledger = await self.repo.get_by_id_for_company(ledger_id, company_id)
        if ledger is None:
            raise NotFoundError("Ledger not found", code="LEDGER_NOT_FOUND")
        return ledger

    async def list(
        self,
        company_id: uuid.UUID,
        *,
        search: str | None,
        is_active: bool | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Ledger], int]:
        return await self.repo.list_for_company(
            company_id,
            search=search,
            is_active=is_active,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    async def update(
        self,
        company_id: uuid.UUID,
        ledger_id: uuid.UUID,
        payload: LedgerUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> Ledger:
        ledger = await self.get(company_id, ledger_id)
        updates = payload.model_dump(exclude_unset=True)

        if "parent_ledger_id" in updates:
            await self._validate_parent(company_id, updates["parent_ledger_id"], ledger_id)

        for field, value in updates.items():
            setattr(ledger, field, value)

        await self.db.flush()
        await self.db.refresh(ledger)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_UPDATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="ledger",
            resource_id=str(ledger.id),
            description=f"Ledger '{ledger.name}' updated",
            metadata={"updated_fields": list(updates.keys())},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return ledger

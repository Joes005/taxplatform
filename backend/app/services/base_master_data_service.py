import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.base import CompanyScopedRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

ModelT = TypeVar("ModelT")


class SimpleMasterDataService(Generic[ModelT]):
    """Shared create/get/list/update for Customer, Vendor, and
    ProductService — three entities with identical shape and no cross-field
    business rules beyond tenant isolation (unlike Ledger, which validates
    its parent-ledger hierarchy, or FinancialYear, which manages the
    single-current-year invariant, and so keeps its own service).
    """

    def __init__(
        self,
        db: AsyncSession,
        repo: CompanyScopedRepository[ModelT],
        *,
        model_cls: type[ModelT],
        resource_type: str,
        display_field: str = "name",
        not_found_code: str,
    ) -> None:
        self.db = db
        self.repo = repo
        self.model_cls = model_cls
        self.resource_type = resource_type
        self.display_field = display_field
        self.not_found_code = not_found_code
        self.audit = AuditService(db)

    def _display_name(self, entity: ModelT) -> str:
        return getattr(entity, self.display_field, str(getattr(entity, "id", "")))

    async def create(
        self, company_id: uuid.UUID, payload: BaseModel, current_user: User, meta: RequestMeta
    ) -> ModelT:
        entity = self.model_cls(company_id=company_id, **payload.model_dump())
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_CREATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type=self.resource_type,
            resource_id=str(entity.id),
            description=f"{self.resource_type.replace('_', ' ').title()} "
            f"'{self._display_name(entity)}' created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def get(self, company_id: uuid.UUID, entity_id: uuid.UUID) -> ModelT:
        entity = await self.repo.get_by_id_for_company(entity_id, company_id)
        if entity is None:
            raise NotFoundError(
                f"{self.resource_type.replace('_', ' ').title()} not found",
                code=self.not_found_code,
            )
        return entity

    async def list(
        self,
        company_id: uuid.UUID,
        *,
        search: str | None,
        is_active: bool | None,
        page: int,
        page_size: int,
    ) -> tuple[list[ModelT], int]:
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
        entity_id: uuid.UUID,
        payload: BaseModel,
        current_user: User,
        meta: RequestMeta,
    ) -> ModelT:
        entity = await self.get(company_id, entity_id)
        updates = payload.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(entity, field, value)

        await self.db.flush()
        await self.db.refresh(entity)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_UPDATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type=self.resource_type,
            resource_id=str(entity.id),
            description=f"{self.resource_type.replace('_', ' ').title()} "
            f"'{self._display_name(entity)}' updated",
            metadata={"updated_fields": list(updates.keys())},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

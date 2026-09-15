import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.financial_year import FinancialYear
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.schemas.financial_year import FinancialYearCreate, FinancialYearUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class FinancialYearService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: FinancialYearCreate, current_user: User, meta: RequestMeta
    ) -> FinancialYear:
        if payload.is_current:
            await self.repo.unset_current_for_company(company_id)

        fy = FinancialYear(company_id=company_id, **payload.model_dump())
        await self.repo.create(fy)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_CREATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="financial_year",
            resource_id=str(fy.id),
            description=f"Financial year '{fy.name}' created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return fy

    async def get(self, company_id: uuid.UUID, fy_id: uuid.UUID) -> FinancialYear:
        fy = await self.repo.get_by_id_for_company(fy_id, company_id)
        if fy is None:
            raise NotFoundError("Financial year not found", code="FINANCIAL_YEAR_NOT_FOUND")
        return fy

    async def list(
        self, company_id: uuid.UUID, *, page: int, page_size: int
    ) -> tuple[list[FinancialYear], int]:
        return await self.repo.list_for_company(
            company_id, offset=(page - 1) * page_size, limit=page_size
        )

    async def update(
        self,
        company_id: uuid.UUID,
        fy_id: uuid.UUID,
        payload: FinancialYearUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> FinancialYear:
        fy = await self.get(company_id, fy_id)
        updates = payload.model_dump(exclude_unset=True)

        if updates.get("is_current") is True:
            await self.repo.unset_current_for_company(company_id)

        for field, value in updates.items():
            setattr(fy, field, value)

        await self.db.flush()
        await self.db.refresh(fy)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_UPDATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="financial_year",
            resource_id=str(fy.id),
            description=f"Financial year '{fy.name}' updated",
            metadata={"updated_fields": list(updates.keys())},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return fy

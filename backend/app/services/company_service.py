import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.company import Company
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.membership_repository import MembershipRepository
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class CompanyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.companies = CompanyRepository(db)
        self.memberships = MembershipRepository(db)
        self.audit = AuditService(db)

    async def create_company(
        self, payload: CompanyCreate, current_user: User, meta: RequestMeta
    ) -> Company:
        from app.services.company_initialization_service import CompanyInitializationService

        init_service = CompanyInitializationService(self.db)
        return await init_service.initialize_new_company(payload, current_user, meta)

    async def list_companies(
        self, current_user: User, *, page: int, page_size: int
    ) -> tuple[list[Company], int]:
        offset = (page - 1) * page_size

        if current_user.is_platform_super_admin:
            return await self.companies.list_all(offset=offset, limit=page_size)

        memberships = await self.memberships.list_for_user(current_user.id)
        company_ids = [m.company_id for m in memberships]
        if not company_ids:
            return [], 0
        return await self.companies.list_by_ids(company_ids, offset=offset, limit=page_size)

    async def get_company(self, company_id: uuid.UUID) -> Company:
        company = await self.companies.get_by_id(company_id)
        if company is None:
            raise NotFoundError("Company not found")
        return company

    async def update_company(
        self,
        company_id: uuid.UUID,
        payload: CompanyUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> Company:
        company = await self.get_company(company_id)

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(company, field, value)

        await self.db.flush()
        await self.db.refresh(company)

        await self.audit.log(
            action=AuditAction.COMPANY_UPDATE,
            user_id=current_user.id,
            company_id=company.id,
            resource_type="company",
            resource_id=str(company.id),
            description=f"Company '{company.legal_name}' updated",
            metadata={"updated_fields": list(updates.keys())},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return company

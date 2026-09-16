import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.gst_tax_rate import GSTTaxRate
from app.models.user import User
from app.repositories.gst_tax_rate_repository import GSTTaxRateRepository
from app.schemas.gst_tax_rate import GSTTaxRateCreate, GSTTaxRateUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class GSTTaxRateService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GSTTaxRateRepository(db)
        self.audit = AuditService(db)

    async def create(
        self,
        company_id: uuid.UUID,
        payload: GSTTaxRateCreate,
        current_user: User,
        meta: RequestMeta,
    ) -> GSTTaxRate:
        rate = GSTTaxRate(company_id=company_id, **payload.model_dump())
        await self.repo.create(rate)

        await self.audit.log(
            action=AuditAction.GST_TAX_RATE_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="gst_tax_rate",
            resource_id=str(rate.id),
            description=f"GST tax rate {rate.rate}% created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return rate

    async def list(
        self, company_id: uuid.UUID, *, is_active: bool | None = None, as_of: date | None = None
    ) -> list[GSTTaxRate]:
        return await self.repo.list_for_company(company_id, is_active=is_active, as_of=as_of)

    async def update(
        self,
        company_id: uuid.UUID,
        rate_id: uuid.UUID,
        payload: GSTTaxRateUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> GSTTaxRate:
        rate = await self.repo.get_by_id_for_company(rate_id, company_id)
        if rate is None:
            raise NotFoundError("GST tax rate not found", code="GST_TAX_RATE_NOT_FOUND")
        if rate.company_id is None:
            raise ValidationAppError(
                "Platform default tax rates cannot be modified", code="GST_TAX_RATE_READ_ONLY"
            )

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(rate, field, value)

        await self.db.flush()
        await self.db.refresh(rate)

        await self.audit.log(
            action=AuditAction.GST_TAX_RATE_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="gst_tax_rate",
            resource_id=str(rate.id),
            description=f"GST tax rate {rate.rate}% updated",
            metadata={"updated_fields": list(updates.keys())},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return rate

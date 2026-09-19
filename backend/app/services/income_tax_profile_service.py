import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.income_tax_profile import IncomeTaxProfile
from app.models.user import User
from app.repositories.income_tax_profile_repository import IncomeTaxProfileRepository
from app.schemas.income_tax_profile import IncomeTaxProfileCreate, IncomeTaxProfileUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.utils.pan import validate_pan


class IncomeTaxProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxProfileRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: IncomeTaxProfileCreate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxProfile:
        if await self.repo.get_for_company(company_id) is not None:
            raise ValidationAppError(
                "This company already has an Income Tax profile", code="INCOME_TAX_PROFILE_ALREADY_EXISTS"
            )

        pan_result = validate_pan(payload.pan)
        if not pan_result.is_valid:
            raise ValidationAppError(pan_result.error_message or "Invalid PAN", code=pan_result.error_code)

        profile = IncomeTaxProfile(
            company_id=company_id,
            pan=payload.pan.strip().upper(),
            legal_name=payload.legal_name,
            trade_name=payload.trade_name,
            taxpayer_type=payload.taxpayer_type,
            residential_status=payload.residential_status,
            date_of_birth_or_incorporation=payload.date_of_birth_or_incorporation,
            business_nature=payload.business_nature,
            address=payload.address,
            city=payload.city,
            state=payload.state,
            pincode=payload.pincode,
        )
        await self.repo.create(profile)

        await self.audit.log(
            action=AuditAction.INCOME_TAX_PROFILE_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_profile",
            resource_id=str(profile.id),
            description=f"Income Tax profile created for PAN {profile.pan}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return profile

    async def get(self, company_id: uuid.UUID) -> IncomeTaxProfile:
        profile = await self.repo.get_for_company(company_id)
        if profile is None:
            raise NotFoundError("Income Tax profile not found for this company", code="INCOME_TAX_PROFILE_NOT_FOUND")
        return profile

    async def get_optional(self, company_id: uuid.UUID) -> IncomeTaxProfile | None:
        return await self.repo.get_for_company(company_id)

    async def update(
        self, company_id: uuid.UUID, payload: IncomeTaxProfileUpdate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxProfile:
        profile = await self.get(company_id)
        updates = payload.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(profile, field, value)

        await self.db.flush()
        await self.db.refresh(profile)

        await self.audit.log(
            action=AuditAction.INCOME_TAX_PROFILE_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_profile",
            resource_id=str(profile.id),
            description="Income Tax profile updated",
            metadata={"updated_fields": list(updates.keys())},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return profile

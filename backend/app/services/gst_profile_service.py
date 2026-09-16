import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.gst_profile import GSTProfile
from app.models.user import User
from app.repositories.gst_profile_repository import GSTProfileRepository
from app.schemas.gst_profile import GSTProfileCreate, GSTProfileUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.utils.gstin import validate_gstin


class GSTProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GSTProfileRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: GSTProfileCreate, current_user: User, meta: RequestMeta
    ) -> GSTProfile:
        if await self.repo.get_for_company(company_id) is not None:
            raise ValidationAppError(
                "This company already has a GST profile", code="GST_PROFILE_ALREADY_EXISTS"
            )

        result = validate_gstin(payload.gstin)
        if not result.is_valid:
            raise ValidationAppError(result.error_message or "Invalid GSTIN", code=result.error_code)

        profile = GSTProfile(
            company_id=company_id,
            gstin=payload.gstin.strip().upper(),
            legal_name=payload.legal_name,
            trade_name=payload.trade_name,
            registration_type=payload.registration_type,
            registration_date=payload.registration_date,
            state_code=result.state_code,
            state_name=result.state_name,
        )
        await self.repo.create(profile)

        await self.audit.log(
            action=AuditAction.GST_PROFILE_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="gst_profile",
            resource_id=str(profile.id),
            description=f"GST profile created for GSTIN {profile.gstin}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return profile

    async def get(self, company_id: uuid.UUID) -> GSTProfile:
        profile = await self.repo.get_for_company(company_id)
        if profile is None:
            raise NotFoundError("GST profile not found for this company", code="GST_PROFILE_NOT_FOUND")
        return profile

    async def update(
        self,
        company_id: uuid.UUID,
        payload: GSTProfileUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> GSTProfile:
        profile = await self.get(company_id)
        updates = payload.model_dump(exclude_unset=True)

        if "gstin" in updates and updates["gstin"]:
            result = validate_gstin(updates["gstin"])
            if not result.is_valid:
                raise ValidationAppError(
                    result.error_message or "Invalid GSTIN", code=result.error_code
                )
            updates["gstin"] = updates["gstin"].strip().upper()
            profile.state_code = result.state_code
            profile.state_name = result.state_name

        for field, value in updates.items():
            setattr(profile, field, value)

        await self.db.flush()
        await self.db.refresh(profile)

        await self.audit.log(
            action=AuditAction.GST_PROFILE_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="gst_profile",
            resource_id=str(profile.id),
            description="GST profile updated",
            metadata={"updated_fields": list(updates.keys())},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return profile

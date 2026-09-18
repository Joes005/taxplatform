import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.tds_profile import TDSProfile
from app.models.user import User
from app.repositories.tds_profile_repository import TDSProfileRepository
from app.schemas.tds_profile import TDSProfileCreate, TDSProfileUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.utils.pan import validate_pan
from app.utils.tan import validate_tan


class TDSProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TDSProfileRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: TDSProfileCreate, current_user: User, meta: RequestMeta
    ) -> TDSProfile:
        if await self.repo.get_for_company(company_id) is not None:
            raise ValidationAppError(
                "This company already has a TDS profile", code="TDS_PROFILE_ALREADY_EXISTS"
            )

        tan_result = validate_tan(payload.tan)
        if not tan_result.is_valid:
            raise ValidationAppError(tan_result.error_message or "Invalid TAN", code=tan_result.error_code)

        pan_result = validate_pan(payload.pan)
        if not pan_result.is_valid:
            raise ValidationAppError(pan_result.error_message or "Invalid PAN", code=pan_result.error_code)

        profile = TDSProfile(
            company_id=company_id,
            tan=payload.tan.strip().upper(),
            pan=payload.pan.strip().upper(),
            legal_name=payload.legal_name,
            trade_name=payload.trade_name,
            deductor_type=payload.deductor_type,
            state_code=payload.state_code,
            state_name=payload.state_name,
        )
        await self.repo.create(profile)

        await self.audit.log(
            action=AuditAction.TDS_PROFILE_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_profile",
            resource_id=str(profile.id),
            description=f"TDS profile created for TAN {profile.tan}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return profile

    async def get(self, company_id: uuid.UUID) -> TDSProfile:
        profile = await self.repo.get_for_company(company_id)
        if profile is None:
            raise NotFoundError("TDS profile not found for this company", code="TDS_PROFILE_NOT_FOUND")
        return profile

    async def update(
        self,
        company_id: uuid.UUID,
        payload: TDSProfileUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> TDSProfile:
        profile = await self.get(company_id)
        updates = payload.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(profile, field, value)

        await self.db.flush()
        await self.db.refresh(profile)

        await self.audit.log(
            action=AuditAction.TDS_PROFILE_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_profile",
            resource_id=str(profile.id),
            description="TDS profile updated",
            metadata={"updated_fields": list(updates.keys())},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return profile

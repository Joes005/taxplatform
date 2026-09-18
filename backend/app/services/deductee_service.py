import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.models.deductee import Deductee
from app.models.tds_enums import PANStatus
from app.models.user import User
from app.repositories.deductee_repository import DeducteeRepository
from app.schemas.deductee import DeducteeCreate, DeducteeUpdate
from app.services.audit_service import AuditAction
from app.services.auth_service import RequestMeta
from app.services.base_master_data_service import SimpleMasterDataService
from app.utils.pan import validate_pan


class DeducteeService(SimpleMasterDataService[Deductee]):
    """Deductee shares Vendor/Customer's flat CRUD shape but adds one rule
    those don't need: PAN is structurally validated on write, and
    `pan_status` is derived automatically from whether a PAN was supplied
    — never left for the caller to get out of sync (PHASE5 section 8).
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(
            db,
            DeducteeRepository(db),
            model_cls=Deductee,
            resource_type="deductee",
            not_found_code="DEDUCTEE_NOT_FOUND",
        )

    def _resolve_pan_status(self, pan: str | None) -> tuple[str | None, PANStatus]:
        if not pan:
            return None, PANStatus.NOT_AVAILABLE
        result = validate_pan(pan)
        if not result.is_valid:
            raise ValidationAppError(
                result.error_message or "Invalid PAN", code=result.error_code
            )
        return pan.strip().upper(), PANStatus.AVAILABLE

    async def create(
        self, company_id: uuid.UUID, payload: DeducteeCreate, current_user: User, meta: RequestMeta
    ) -> Deductee:
        data = payload.model_dump()
        data["pan"], data["pan_status"] = self._resolve_pan_status(data.get("pan"))
        entity = Deductee(company_id=company_id, **data)
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.DEDUCTEE_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="deductee",
            resource_id=str(entity.id),
            description=f"Deductee '{entity.name}' created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def update(
        self,
        company_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: DeducteeUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> Deductee:
        entity = await self.get(company_id, entity_id)
        updates = payload.model_dump(exclude_unset=True)

        if "pan" in updates:
            updates["pan"], updates["pan_status"] = self._resolve_pan_status(updates["pan"])

        for field, value in updates.items():
            setattr(entity, field, value)

        await self.db.flush()
        await self.db.refresh(entity)

        await self.audit.log(
            action=AuditAction.DEDUCTEE_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="deductee",
            resource_id=str(entity.id),
            description=f"Deductee '{entity.name}' updated",
            metadata={"updated_fields": list(updates.keys())},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

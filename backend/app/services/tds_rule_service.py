import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.tds_rule import TDSRule
from app.models.user import User
from app.repositories.tds_rule_repository import TDSRuleRepository
from app.repositories.tds_section_repository import TDSSectionRepository
from app.schemas.tds_rule import TDSRuleCreate, TDSRuleUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class TDSRuleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TDSRuleRepository(db)
        self.sections = TDSSectionRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: TDSRuleCreate, current_user: User, meta: RequestMeta
    ) -> TDSRule:
        section = await self.sections.get_by_id(payload.tds_section_id)
        if section is None:
            raise ValidationAppError("TDS section not found", code="TDS_SECTION_NOT_FOUND")

        rule = TDSRule(company_id=company_id, **payload.model_dump())
        await self.repo.create(rule)

        await self.audit.log(
            action=AuditAction.TDS_RULE_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_rule",
            resource_id=str(rule.id),
            description=f"TDS rule created for section {section.section_code} ({rule.rate}%)",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return rule

    async def list(
        self,
        company_id: uuid.UUID,
        *,
        tds_section_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        as_of: date | None = None,
    ) -> list[TDSRule]:
        return await self.repo.list_for_company(
            company_id, tds_section_id=tds_section_id, is_active=is_active, as_of=as_of
        )

    async def update(
        self,
        company_id: uuid.UUID,
        rule_id: uuid.UUID,
        payload: TDSRuleUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> TDSRule:
        rule = await self.repo.get_by_id_for_company(rule_id, company_id)
        if rule is None:
            raise NotFoundError("TDS rule not found", code="TDS_RULE_NOT_FOUND")
        if rule.company_id is None:
            raise ValidationAppError(
                "Platform default TDS rules cannot be modified", code="TDS_RULE_READ_ONLY"
            )

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(rule, field, value)

        await self.db.flush()
        await self.db.refresh(rule)

        await self.audit.log(
            action=AuditAction.TDS_RULE_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_rule",
            resource_id=str(rule.id),
            description="TDS rule updated",
            metadata={"updated_fields": list(updates.keys())},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return rule

"""Compliance rule CRUD and versioning (PHASE9 §6-7, §24). Creating or
updating a rule never mutates an existing version in place — `update()`
only touches descriptive fields and `effective_to`/`priority`, and a
materially different rule (a new `due_date_rule`) is always a brand new
version, so any `ComplianceObligation` that already recorded the old
`rule_version` keeps its original due date reproducible forever.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationAppError
from app.models.compliance_enums import ComplianceCategory, ComplianceModule
from app.models.compliance_rule import ComplianceRule
from app.models.user import User
from app.repositories.compliance_rule_repository import ComplianceRuleRepository
from app.schemas.compliance_rule import ComplianceRuleCreate, ComplianceRuleUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class ComplianceRuleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ComplianceRuleRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: ComplianceRuleCreate, current_user: User, meta: RequestMeta
    ) -> ComplianceRule:
        rule_company_id = company_id if payload.company_specific else None
        if rule_company_id is None and not current_user.is_platform_super_admin:
            raise PermissionDeniedError(
                "Only a platform administrator may create a platform-wide compliance rule"
            )

        version = await self.repo.next_version(payload.code, rule_company_id)
        rule = ComplianceRule(
            company_id=rule_company_id,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            module=payload.module,
            frequency=payload.frequency,
            due_date_rule=payload.due_date_rule,
            priority=payload.priority,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            version=version,
            is_active=True,
        )
        await self.repo.create(rule)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_RULE_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_rule",
            resource_id=str(rule.id),
            description=f"Compliance rule {rule.code} v{rule.version} created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return rule

    async def get(self, company_id: uuid.UUID, rule_id: uuid.UUID) -> ComplianceRule:
        rule = await self.repo.get_by_id_visible_to_company(rule_id, company_id)
        if rule is None:
            raise NotFoundError("Compliance rule not found", code="COMPLIANCE_RULE_NOT_FOUND")
        return rule

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        category: ComplianceCategory | None = None,
        module: ComplianceModule | None = None,
        active_only: bool = False,
    ) -> list[ComplianceRule]:
        return await self.repo.list_visible_to_company(
            company_id, category=category, module=module, active_only=active_only
        )

    async def _require_manageable(self, company_id: uuid.UUID, rule_id: uuid.UUID, current_user: User) -> ComplianceRule:
        rule = await self.get(company_id, rule_id)
        if rule.company_id is None and not current_user.is_platform_super_admin:
            raise PermissionDeniedError("Only a platform administrator may modify a platform-wide compliance rule")
        if rule.company_id is not None and rule.company_id != company_id and not current_user.is_platform_super_admin:
            raise ValidationAppError("This rule does not belong to this company", code="COMPLIANCE_RULE_NOT_FOUND")
        return rule

    async def update(
        self, company_id: uuid.UUID, rule_id: uuid.UUID, payload: ComplianceRuleUpdate, current_user: User, meta: RequestMeta
    ) -> ComplianceRule:
        rule = await self._require_manageable(company_id, rule_id, current_user)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)

        await self.db.flush()
        await self.db.refresh(rule)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_RULE_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_rule",
            resource_id=str(rule.id),
            description=f"Compliance rule {rule.code} v{rule.version} updated",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return rule

    async def set_active(
        self, company_id: uuid.UUID, rule_id: uuid.UUID, is_active: bool, current_user: User, meta: RequestMeta
    ) -> ComplianceRule:
        rule = await self._require_manageable(company_id, rule_id, current_user)
        rule.is_active = is_active
        await self.db.flush()
        await self.db.refresh(rule)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_RULE_ACTIVATED if is_active else AuditAction.COMPLIANCE_RULE_DEACTIVATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_rule",
            resource_id=str(rule.id),
            description=f"Compliance rule {rule.code} v{rule.version} {'activated' if is_active else 'deactivated'}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return rule

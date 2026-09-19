"""Compliance obligation CRUD and rule-driven generation (PHASE9 §5,
§25). `generate_from_rule()` is idempotent by construction: the natural
key `(company_id, code, financial_year_id, tax_period)` is unique at the
database layer, so calling it twice for the same period returns the
existing obligation rather than ever creating a duplicate.
"""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.compliance_enums import ComplianceCategory, ComplianceModule, ComplianceObligationStatus
from app.models.compliance_obligation import ComplianceObligation
from app.models.compliance_task import ComplianceTask
from app.models.user import User
from app.repositories.compliance_obligation_repository import ComplianceObligationRepository
from app.repositories.compliance_rule_repository import ComplianceRuleRepository
from app.repositories.compliance_task_repository import ComplianceTaskRepository
from app.repositories.financial_year_repository import FinancialYearRepository
from app.schemas.compliance_obligation import ComplianceObligationCreate, ComplianceObligationUpdate, GenerateTaskRequest
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.compliance_deadline_service import compute_due_date


class ComplianceObligationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ComplianceObligationRepository(db)
        self.rules = ComplianceRuleRepository(db)
        self.tasks = ComplianceTaskRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: ComplianceObligationCreate, current_user: User, meta: RequestMeta
    ) -> ComplianceObligation:
        if payload.financial_year_id is not None:
            if await self.fy_repo.get_by_id_for_company(payload.financial_year_id, company_id) is None:
                raise ValidationAppError("Financial year not found for this company", code="INVALID_FINANCIAL_YEAR")

        existing = await self.repo.get_by_natural_key(
            company_id, payload.code, payload.financial_year_id, payload.tax_period
        )
        if existing is not None:
            raise ValidationAppError(
                "An obligation for this code/financial-year/period already exists",
                code="COMPLIANCE_OBLIGATION_ALREADY_EXISTS",
            )

        obligation = ComplianceObligation(
            company_id=company_id,
            created_by=current_user.id,
            **payload.model_dump(),
        )
        await self.repo.create(obligation)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Compliance obligation {obligation.code} created (due {obligation.due_date})",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return obligation

    async def generate_from_rule(
        self,
        company_id: uuid.UUID,
        *,
        rule_code: str,
        financial_year_id: uuid.UUID | None,
        tax_period: str | None,
        period_start: date,
        period_end: date,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceObligation:
        existing = await self.repo.get_by_natural_key(company_id, rule_code, financial_year_id, tax_period)
        if existing is not None:
            return existing

        rule = await self.rules.get_active_version(rule_code, company_id)
        if rule is None:
            raise ValidationAppError(
                f"No active compliance rule configured for code {rule_code!r}",
                code="COMPLIANCE_RULE_NOT_CONFIGURED",
            )

        due_date = compute_due_date(rule.due_date_rule, period_start=period_start, period_end=period_end)

        obligation = ComplianceObligation(
            company_id=company_id,
            code=rule.code,
            name=rule.name,
            description=rule.description,
            category=rule.category,
            module=rule.module,
            frequency=rule.frequency,
            financial_year_id=financial_year_id,
            tax_period=tax_period,
            start_date=period_start,
            due_date=due_date,
            priority=rule.priority,
            is_recurring=rule.frequency.value != "ONE_TIME",
            rule_id=rule.id,
            rule_version=rule.version,
            created_by=current_user.id,
        )
        await self.repo.create(obligation)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Compliance obligation {obligation.code} generated from rule v{rule.version} (due {due_date})",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return obligation

    async def get(self, company_id: uuid.UUID, obligation_id: uuid.UUID) -> ComplianceObligation:
        obligation = await self.repo.get_by_id_for_company(obligation_id, company_id)
        if obligation is None:
            raise NotFoundError("Compliance obligation not found", code="COMPLIANCE_OBLIGATION_NOT_FOUND")
        return obligation

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        category: ComplianceCategory | None,
        module: ComplianceModule | None,
        active_only: bool,
        page: int,
        page_size: int,
    ) -> tuple[list[ComplianceObligation], int]:
        return await self.repo.list_for_company(
            company_id,
            category=category,
            module=module,
            active_only=active_only,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    async def update(
        self,
        company_id: uuid.UUID,
        obligation_id: uuid.UUID,
        payload: ComplianceObligationUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceObligation:
        obligation = await self.get(company_id, obligation_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(obligation, field, value)

        await self.db.flush()
        await self.db.refresh(obligation)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_OBLIGATION_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_obligation",
            resource_id=str(obligation.id),
            description=f"Compliance obligation {obligation.code} updated",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return obligation

    async def generate_task(
        self,
        company_id: uuid.UUID,
        obligation_id: uuid.UUID,
        payload: GenerateTaskRequest,
        current_user: User,
        meta: RequestMeta,
    ) -> ComplianceTask:
        obligation = await self.get(company_id, obligation_id)
        if obligation.status != ComplianceObligationStatus.ACTIVE:
            raise ValidationAppError(
                "Cannot generate a task from an obligation that is not ACTIVE", code="COMPLIANCE_OBLIGATION_NOT_ACTIVE"
            )

        task = ComplianceTask(
            company_id=company_id,
            obligation_id=obligation.id,
            title=payload.title or obligation.name,
            description=obligation.description,
            category=obligation.category,
            module=obligation.module,
            priority=obligation.priority,
            assigned_to=payload.assigned_to,
            reviewer_id=payload.reviewer_id,
            due_date=obligation.due_date,
            created_by=current_user.id,
        )
        await self.tasks.create(task)

        await self.audit.log(
            action=AuditAction.COMPLIANCE_TASK_GENERATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="compliance_task",
            resource_id=str(task.id),
            description=f"Task generated from obligation {obligation.code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return task

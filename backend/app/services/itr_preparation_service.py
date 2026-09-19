"""ITR preparation lifecycle (PHASE8 §43-47, §52). `approve` is the one
hard gate: it re-runs `ITRValidationService` and refuses if any `ERROR`-
severity issue remains, so an internal approval can never be granted over
a known blocking problem — the same "flag and block" principle
`AuditEngagementService._check_can_approve()` already applies to audit
engagements.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.income_tax_enums import ITRPreparationStatus, ValidationSeverity
from app.models.itr_preparation import ITRPreparation
from app.models.user import User
from app.repositories.itr_preparation_repository import ITRPreparationRepository
from app.schemas.tax_computation import ValidationIssue
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.income_tax_computation_service import IncomeTaxComputationService
from app.services.income_tax_profile_service import IncomeTaxProfileService
from app.services.itr_validation_service import ITRValidationService, determine_itr_form_type

_TRANSITIONS: dict[tuple[ITRPreparationStatus, str], ITRPreparationStatus] = {
    (ITRPreparationStatus.IN_PROGRESS, "submit_review"): ITRPreparationStatus.READY_FOR_REVIEW,
    (ITRPreparationStatus.VALIDATION_REQUIRED, "submit_review"): ITRPreparationStatus.READY_FOR_REVIEW,
    (ITRPreparationStatus.READY_FOR_REVIEW, "approve"): ITRPreparationStatus.APPROVED,
    (ITRPreparationStatus.APPROVED, "lock"): ITRPreparationStatus.LOCKED,
}


class ITRPreparationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ITRPreparationRepository(db)
        self.computations = IncomeTaxComputationService(db)
        self.profiles = IncomeTaxProfileService(db)
        self.validator = ITRValidationService(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, tax_computation_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> ITRPreparation:
        computation = await self.computations.get(company_id, tax_computation_id)
        if await self.repo.get_for_computation(company_id, tax_computation_id) is not None:
            raise ConflictError(
                "An ITR preparation already exists for this tax computation",
                code="ITR_PREPARATION_ALREADY_EXISTS",
            )

        profile = await self.profiles.get_optional(company_id)
        if profile is None:
            raise ValidationAppError(
                "An Income Tax profile is required before preparing an ITR", code="INCOME_TAX_PROFILE_REQUIRED"
            )

        form_type = determine_itr_form_type(
            profile.taxpayer_type,
            has_business_income=computation.business_income != 0,
            has_capital_gains=computation.capital_gains_income != 0,
        )

        preparation = ITRPreparation(
            company_id=company_id,
            tax_computation_id=computation.id,
            itr_form_type=form_type,
            assessment_year=computation.assessment_year,
            status=ITRPreparationStatus.DRAFT,
            prepared_by=current_user.id,
        )
        await self.repo.create(preparation)

        await self.audit.log(
            action=AuditAction.ITR_PREPARATION_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="itr_preparation",
            resource_id=str(preparation.id),
            description=f"ITR preparation created ({form_type.value}) for AY {preparation.assessment_year}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return preparation

    async def get(self, company_id: uuid.UUID, preparation_id: uuid.UUID) -> ITRPreparation:
        preparation = await self.repo.get_by_id_for_company(preparation_id, company_id)
        if preparation is None:
            raise NotFoundError("ITR preparation not found", code="ITR_PREPARATION_NOT_FOUND")
        return preparation

    async def list_for_company(self, company_id: uuid.UUID, *, page: int, page_size: int):
        return await self.repo.list_for_company(company_id, offset=(page - 1) * page_size, limit=page_size)

    async def validate(
        self, company_id: uuid.UUID, preparation_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> tuple[ITRPreparation, list[ValidationIssue]]:
        preparation = await self.get(company_id, preparation_id)
        computation = await self.computations.get(company_id, preparation.tax_computation_id)
        profile = await self.profiles.get_optional(company_id)

        issues = await self.validator.validate(profile, computation, preparation)
        has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in issues)
        preparation.status = (
            ITRPreparationStatus.VALIDATION_REQUIRED if has_errors else ITRPreparationStatus.IN_PROGRESS
        )
        await self.db.flush()
        await self.db.refresh(preparation)

        await self.audit.log(
            action=AuditAction.ITR_VALIDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="itr_preparation",
            resource_id=str(preparation.id),
            description=f"ITR validated: {len(issues)} issue(s), {'errors present' if has_errors else 'no errors'}",
            metadata={"issue_count": len(issues)},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return preparation, issues

    async def _transition(
        self, company_id: uuid.UUID, preparation_id: uuid.UUID, action: str, current_user: User, meta: RequestMeta
    ) -> ITRPreparation:
        preparation = await self.get(company_id, preparation_id)
        key = (preparation.status, action)
        if key not in _TRANSITIONS:
            raise ConflictError(
                f"Cannot {action.replace('_', ' ')} an ITR preparation in status {preparation.status.value}",
                code="INVALID_ITR_PREPARATION_TRANSITION",
            )

        if action == "approve":
            computation = await self.computations.get(company_id, preparation.tax_computation_id)
            profile = await self.profiles.get_optional(company_id)
            issues = await self.validator.validate(profile, computation, preparation)
            if any(issue.severity == ValidationSeverity.ERROR for issue in issues):
                raise ConflictError(
                    "Cannot approve: one or more validation errors remain unresolved",
                    code="ITR_VALIDATION_ERRORS_BLOCK_APPROVAL",
                )

        preparation.status = _TRANSITIONS[key]
        if action == "approve":
            preparation.reviewed_by = current_user.id
            preparation.approved_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(preparation)

        action_map = {
            "submit_review": AuditAction.ITR_SUBMITTED_FOR_REVIEW,
            "approve": AuditAction.ITR_APPROVED,
            "lock": AuditAction.ITR_LOCKED,
        }
        await self.audit.log(
            action=action_map[action],
            user_id=current_user.id,
            company_id=company_id,
            resource_type="itr_preparation",
            resource_id=str(preparation.id),
            description=f"ITR preparation moved to {preparation.status.value}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return preparation

    async def submit_for_review(self, company_id, preparation_id, current_user, meta) -> ITRPreparation:
        return await self._transition(company_id, preparation_id, "submit_review", current_user, meta)

    async def approve(self, company_id, preparation_id, current_user, meta) -> ITRPreparation:
        return await self._transition(company_id, preparation_id, "approve", current_user, meta)

    async def lock(self, company_id, preparation_id, current_user, meta) -> ITRPreparation:
        return await self._transition(company_id, preparation_id, "lock", current_user, meta)

"""Current-year loss recording and set-off, plus a tracked (not yet
auto-consumed) carry-forward balance (PHASE8 §30).

Real sett-off ordering rules are genuinely intricate (a capital loss may
only offset a capital gain; a business loss cannot offset salary; etc.)
and differ by loss type in ways this platform does not encode. Rather
than risk applying an incorrect ordering silently, `setoff_amount` is a
value the preparer enters explicitly — the computation service only sums
whatever has been recorded as set off for the computation's own financial
year and reduces gross total income by that amount; it never decides
*which* loss to set off against *which* head on its own.
"""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.income_tax_loss import IncomeTaxLoss
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.income_tax_loss_repository import IncomeTaxLossRepository
from app.schemas.income_tax_loss import IncomeTaxLossCreate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

ZERO = Decimal("0")


class IncomeTaxLossService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxLossRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: IncomeTaxLossCreate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxLoss:
        if await self.fy_repo.get_by_id_for_company(payload.origin_financial_year_id, company_id) is None:
            raise ValidationAppError("Financial year not found for this company", code="INVALID_FINANCIAL_YEAR")

        entity = IncomeTaxLoss(
            company_id=company_id,
            created_by=current_user.id,
            carried_forward_amount=payload.amount,
            **payload.model_dump(),
        )
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.TAX_LOSS_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_loss",
            resource_id=str(entity.id),
            description=f"{entity.loss_type.value} loss of {entity.amount} recorded",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def list_for_company(self, company_id: uuid.UUID) -> list[IncomeTaxLoss]:
        return await self.repo.list_for_company(company_id)

    async def list_for_origin_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxLoss]:
        return await self.repo.list_for_origin_fy(company_id, financial_year_id)

    async def set_setoff_amount(
        self, company_id: uuid.UUID, loss_id: uuid.UUID, setoff_amount: Decimal, current_user: User, meta: RequestMeta
    ) -> IncomeTaxLoss:
        loss = await self.repo.get_by_id_for_company(loss_id, company_id)
        if loss is None:
            raise NotFoundError("Loss not found", code="TAX_LOSS_NOT_FOUND")
        if setoff_amount < ZERO or setoff_amount > loss.amount:
            raise ValidationAppError(
                "Set-off amount must be between 0 and the original loss amount", code="INVALID_LOSS_SETOFF"
            )

        loss.setoff_amount = setoff_amount
        loss.carried_forward_amount = loss.amount - setoff_amount
        await self.db.flush()
        await self.db.refresh(loss)

        await self.audit.log(
            action=AuditAction.TAX_LOSS_SET_OFF,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_loss",
            resource_id=str(loss.id),
            description=f"Loss set-off updated to {setoff_amount}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return loss

    async def total_setoff_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> Decimal:
        losses = await self.repo.list_for_origin_fy(company_id, financial_year_id)
        return sum((loss.setoff_amount for loss in losses), ZERO)

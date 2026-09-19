import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.income_tax_enums import LedgerTaxClassification
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.income_tax_adjustment import IncomeTaxAdjustmentCreate, IncomeTaxAdjustmentRead
from app.schemas.income_tax_deduction import IncomeTaxDeductionCreate, IncomeTaxDeductionRead, IncomeTaxDeductionUpdate
from app.services.auth_service import RequestMeta
from app.services.business_income_service import (
    BusinessIncomeCalculationService,
    IncomeTaxAdjustmentService,
    IncomeTaxLedgerClassificationService,
)
from app.services.deduction_service import DeductionService

router = APIRouter(prefix="/income-tax", tags=["income-tax-deductions"])


@router.post("/deductions", response_model=SuccessResponse[IncomeTaxDeductionRead], status_code=201)
async def create_deduction(
    company_id: uuid.UUID,
    payload: IncomeTaxDeductionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = DeductionService(db)
    entity = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxDeductionRead.model_validate(entity), message="Deduction recorded")


@router.get("/deductions", response_model=SuccessResponse[list[IncomeTaxDeductionRead]])
async def list_deductions(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = DeductionService(db)
    items = await service.list_for_fy(company_id, financial_year_id)
    return SuccessResponse(data=[IncomeTaxDeductionRead.model_validate(i) for i in items])


@router.patch("/deductions/{entity_id}", response_model=SuccessResponse[IncomeTaxDeductionRead])
async def update_deduction(
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: IncomeTaxDeductionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = DeductionService(db)
    entity = await service.update(company_id, entity_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxDeductionRead.model_validate(entity), message="Deduction updated")


@router.delete("/deductions/{entity_id}", response_model=SuccessResponse[None])
async def delete_deduction(
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = DeductionService(db)
    await service.delete(company_id, entity_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=None, message="Deduction deleted")


@router.post("/adjustments", response_model=SuccessResponse[IncomeTaxAdjustmentRead], status_code=201)
async def create_adjustment(
    company_id: uuid.UUID,
    payload: IncomeTaxAdjustmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = IncomeTaxAdjustmentService(db)
    entity = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxAdjustmentRead.model_validate(entity), message="Adjustment recorded")


@router.get("/adjustments", response_model=SuccessResponse[list[IncomeTaxAdjustmentRead]])
async def list_adjustments(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxAdjustmentService(db)
    items = await service.list_for_fy(company_id, financial_year_id)
    return SuccessResponse(data=[IncomeTaxAdjustmentRead.model_validate(i) for i in items])


@router.delete("/adjustments/{entity_id}", response_model=SuccessResponse[None])
async def delete_adjustment(
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = IncomeTaxAdjustmentService(db)
    await service.delete(company_id, entity_id)
    await db.commit()
    return SuccessResponse(data=None, message="Adjustment deleted")


class LedgerClassificationRequest(BaseModel):
    ledger_id: uuid.UUID
    classification: LedgerTaxClassification
    notes: str | None = None


@router.post("/ledger-classifications", response_model=SuccessResponse[None])
async def set_ledger_classification(
    company_id: uuid.UUID,
    payload: LedgerClassificationRequest,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = IncomeTaxLedgerClassificationService(db)
    await service.set_classification(company_id, payload.ledger_id, payload.classification, payload.notes)
    await db.commit()
    return SuccessResponse(data=None, message="Ledger classification saved")


@router.get("/business-income-preview", response_model=SuccessResponse[dict])
async def preview_business_income(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = BusinessIncomeCalculationService(db)
    breakdown = await service.calculate(company_id, financial_year_id)
    return SuccessResponse(
        data={
            "revenue": str(breakdown.revenue),
            "purchases": str(breakdown.purchases),
            "ledger_income": str(breakdown.ledger_income),
            "ledger_expense_total": str(breakdown.ledger_expense_total),
            "gross_business_income": str(breakdown.gross_business_income),
            "eligible_expenses": str(breakdown.eligible_expenses),
            "disallowances": str(breakdown.disallowances),
            "other_adjustments": str(breakdown.other_adjustments),
            "depreciation_adjustments": str(breakdown.depreciation_adjustments),
            "taxable_business_income": str(breakdown.taxable_business_income),
            "review_required_ledger_ids": [str(i) for i in breakdown.review_required_ledger_ids],
        }
    )

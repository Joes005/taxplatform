import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.income_tax_credit import IncomeTaxCreditEntryCreate, IncomeTaxCreditEntryRead
from app.schemas.income_tax_payment import IncomeTaxPaymentCreate, IncomeTaxPaymentRead
from app.services.auth_service import RequestMeta
from app.services.tax_credit_service import (
    IncomeTaxAdvanceTaxPaymentService,
    IncomeTaxSelfAssessmentTaxPaymentService,
    TaxCreditService,
)

router = APIRouter(prefix="/income-tax", tags=["income-tax-payments"])


@router.post("/advance-tax", response_model=SuccessResponse[IncomeTaxPaymentRead], status_code=201)
async def create_advance_tax_payment(
    company_id: uuid.UUID,
    payload: IncomeTaxPaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = IncomeTaxAdvanceTaxPaymentService(db)
    entity = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxPaymentRead.model_validate(entity), message="Advance tax payment recorded")


@router.get("/advance-tax", response_model=SuccessResponse[list[IncomeTaxPaymentRead]])
async def list_advance_tax_payments(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxAdvanceTaxPaymentService(db)
    items = await service.list_for_fy(company_id, financial_year_id)
    return SuccessResponse(data=[IncomeTaxPaymentRead.model_validate(i) for i in items])


@router.post("/self-assessment-tax", response_model=SuccessResponse[IncomeTaxPaymentRead], status_code=201)
async def create_self_assessment_tax_payment(
    company_id: uuid.UUID,
    payload: IncomeTaxPaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = IncomeTaxSelfAssessmentTaxPaymentService(db)
    entity = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=IncomeTaxPaymentRead.model_validate(entity), message="Self-assessment tax payment recorded"
    )


@router.get("/self-assessment-tax", response_model=SuccessResponse[list[IncomeTaxPaymentRead]])
async def list_self_assessment_tax_payments(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxSelfAssessmentTaxPaymentService(db)
    items = await service.list_for_fy(company_id, financial_year_id)
    return SuccessResponse(data=[IncomeTaxPaymentRead.model_validate(i) for i in items])


@router.post("/credits", response_model=SuccessResponse[IncomeTaxCreditEntryRead], status_code=201)
async def create_credit_entry(
    company_id: uuid.UUID,
    payload: IncomeTaxCreditEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = TaxCreditService(db)
    entity = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxCreditEntryRead.model_validate(entity), message="TDS/TCS credit recorded")


@router.get("/credits", response_model=SuccessResponse[list[IncomeTaxCreditEntryRead]])
async def list_credit_entries(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = TaxCreditService(db)
    items = await service.list_for_fy(company_id, financial_year_id)
    return SuccessResponse(data=[IncomeTaxCreditEntryRead.model_validate(i) for i in items])

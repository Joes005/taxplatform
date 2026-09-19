import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.income_tax_income import (
    IncomeTaxExemptIncomeCreate,
    IncomeTaxExemptIncomeRead,
    IncomeTaxHousePropertyIncomeCreate,
    IncomeTaxHousePropertyIncomeRead,
    IncomeTaxHousePropertyIncomeUpdate,
    IncomeTaxOtherIncomeCreate,
    IncomeTaxOtherIncomeRead,
    IncomeTaxOtherIncomeUpdate,
    IncomeTaxSalaryIncomeCreate,
    IncomeTaxSalaryIncomeRead,
    IncomeTaxSalaryIncomeUpdate,
)
from app.services.auth_service import RequestMeta
from app.services.income_tax_income_service import (
    IncomeTaxExemptIncomeService,
    IncomeTaxHousePropertyIncomeService,
    IncomeTaxOtherIncomeService,
    IncomeTaxSalaryIncomeService,
)

router = APIRouter(prefix="/income-tax", tags=["income-tax-income"])


@router.post("/salary-income", response_model=SuccessResponse[IncomeTaxSalaryIncomeRead], status_code=201)
async def create_salary_income(
    company_id: uuid.UUID,
    payload: IncomeTaxSalaryIncomeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = IncomeTaxSalaryIncomeService(db)
    entity = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxSalaryIncomeRead.model_validate(entity), message="Salary income recorded")


@router.get("/salary-income", response_model=SuccessResponse[list[IncomeTaxSalaryIncomeRead]])
async def list_salary_income(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxSalaryIncomeService(db)
    items = await service.list_for_fy(company_id, financial_year_id)
    return SuccessResponse(data=[IncomeTaxSalaryIncomeRead.model_validate(i) for i in items])


@router.patch("/salary-income/{entity_id}", response_model=SuccessResponse[IncomeTaxSalaryIncomeRead])
async def update_salary_income(
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: IncomeTaxSalaryIncomeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = IncomeTaxSalaryIncomeService(db)
    entity = await service.update(company_id, entity_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxSalaryIncomeRead.model_validate(entity), message="Salary income updated")


@router.delete("/salary-income/{entity_id}", response_model=SuccessResponse[None])
async def delete_salary_income(
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = IncomeTaxSalaryIncomeService(db)
    await service.delete(company_id, entity_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=None, message="Salary income deleted")


@router.post(
    "/house-property-income", response_model=SuccessResponse[IncomeTaxHousePropertyIncomeRead], status_code=201
)
async def create_house_property_income(
    company_id: uuid.UUID,
    payload: IncomeTaxHousePropertyIncomeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = IncomeTaxHousePropertyIncomeService(db)
    entity = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=IncomeTaxHousePropertyIncomeRead.model_validate(entity), message="House property income recorded"
    )


@router.get("/house-property-income", response_model=SuccessResponse[list[IncomeTaxHousePropertyIncomeRead]])
async def list_house_property_income(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxHousePropertyIncomeService(db)
    items = await service.list_for_fy(company_id, financial_year_id)
    return SuccessResponse(data=[IncomeTaxHousePropertyIncomeRead.model_validate(i) for i in items])


@router.patch("/house-property-income/{entity_id}", response_model=SuccessResponse[IncomeTaxHousePropertyIncomeRead])
async def update_house_property_income(
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: IncomeTaxHousePropertyIncomeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = IncomeTaxHousePropertyIncomeService(db)
    entity = await service.update(company_id, entity_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=IncomeTaxHousePropertyIncomeRead.model_validate(entity), message="House property income updated"
    )


@router.delete("/house-property-income/{entity_id}", response_model=SuccessResponse[None])
async def delete_house_property_income(
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = IncomeTaxHousePropertyIncomeService(db)
    await service.delete(company_id, entity_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=None, message="House property income deleted")


@router.post("/other-income", response_model=SuccessResponse[IncomeTaxOtherIncomeRead], status_code=201)
async def create_other_income(
    company_id: uuid.UUID,
    payload: IncomeTaxOtherIncomeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = IncomeTaxOtherIncomeService(db)
    entity = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxOtherIncomeRead.model_validate(entity), message="Other income recorded")


@router.get("/other-income", response_model=SuccessResponse[list[IncomeTaxOtherIncomeRead]])
async def list_other_income(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxOtherIncomeService(db)
    items = await service.list_for_fy(company_id, financial_year_id)
    return SuccessResponse(data=[IncomeTaxOtherIncomeRead.model_validate(i) for i in items])


@router.patch("/other-income/{entity_id}", response_model=SuccessResponse[IncomeTaxOtherIncomeRead])
async def update_other_income(
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: IncomeTaxOtherIncomeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = IncomeTaxOtherIncomeService(db)
    entity = await service.update(company_id, entity_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxOtherIncomeRead.model_validate(entity), message="Other income updated")


@router.delete("/other-income/{entity_id}", response_model=SuccessResponse[None])
async def delete_other_income(
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = IncomeTaxOtherIncomeService(db)
    await service.delete(company_id, entity_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=None, message="Other income deleted")


@router.post("/exempt-income", response_model=SuccessResponse[IncomeTaxExemptIncomeRead], status_code=201)
async def create_exempt_income(
    company_id: uuid.UUID,
    payload: IncomeTaxExemptIncomeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = IncomeTaxExemptIncomeService(db)
    entity = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxExemptIncomeRead.model_validate(entity), message="Exempt income recorded")


@router.get("/exempt-income", response_model=SuccessResponse[list[IncomeTaxExemptIncomeRead]])
async def list_exempt_income(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxExemptIncomeService(db)
    items = await service.list_for_fy(company_id, financial_year_id)
    return SuccessResponse(data=[IncomeTaxExemptIncomeRead.model_validate(i) for i in items])


@router.delete("/exempt-income/{entity_id}", response_model=SuccessResponse[None])
async def delete_exempt_income(
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = IncomeTaxExemptIncomeService(db)
    await service.delete(company_id, entity_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=None, message="Exempt income deleted")

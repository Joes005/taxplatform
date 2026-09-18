import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.bank_match import BankMatchCandidate, BankTransactionMatchRead, ManualMatchCreate
from app.schemas.common import SuccessResponse
from app.services.auth_service import RequestMeta
from app.services.bank_match_service import BankMatchService
from app.services.bank_matching_service import BankMatchingService
from app.services.bank_transaction_service import BankTransactionService

router = APIRouter(tags=["bank-matches"])


@router.get(
    "/bank/transactions/{transaction_id}/candidates",
    response_model=SuccessResponse[list[BankMatchCandidate]],
)
async def get_match_candidates(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_MATCH_VIEW.value)),
):
    transaction = await BankTransactionService(db).get(company_id, transaction_id)
    candidates = await BankMatchingService(db).find_candidates(company_id, transaction)
    return SuccessResponse(data=candidates)


@router.get(
    "/bank/transactions/{transaction_id}/matches",
    response_model=SuccessResponse[list[BankTransactionMatchRead]],
)
async def list_matches_for_transaction(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.BANK_MATCH_VIEW.value)),
):
    matches = await BankMatchService(db).list_for_bank_transaction(company_id, transaction_id)
    return SuccessResponse(data=[BankTransactionMatchRead.model_validate(m) for m in matches])


@router.post(
    "/bank/transactions/{transaction_id}/match",
    response_model=SuccessResponse[BankTransactionMatchRead],
    status_code=201,
)
async def create_match(
    transaction_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ManualMatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_MATCH_CREATE.value)),
):
    service = BankMatchService(db)
    match = await service.create_manual_match(company_id, transaction_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=BankTransactionMatchRead.model_validate(match), message="Match created")


@router.post("/bank/matches/{match_id}/reverse", response_model=SuccessResponse[BankTransactionMatchRead])
async def reverse_match(
    match_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.BANK_MATCH_REVERSE.value)),
):
    service = BankMatchService(db)
    match = await service.reverse(company_id, match_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=BankTransactionMatchRead.model_validate(match), message="Match reversed")

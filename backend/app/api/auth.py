from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta
from app.models.user import User
from app.schemas.auth import (
    ActiveCompanyContext,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    SelectCompanyRequest,
    TokenPair,
)
from app.schemas.common import SuccessResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService, RequestMeta

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=SuccessResponse[UserRead], status_code=201)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    meta: RequestMeta = Depends(get_request_meta),
):
    service = AuthService(db)
    user = await service.register(payload, meta)
    await db.commit()
    return SuccessResponse(data=UserRead.model_validate(user), message="Registration successful")


@router.post("/login", response_model=SuccessResponse[LoginResponse])
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    meta: RequestMeta = Depends(get_request_meta),
):
    service = AuthService(db)
    result = await service.login(payload, meta)
    await db.commit()
    return SuccessResponse(data=result, message="Login successful")


@router.post("/refresh", response_model=SuccessResponse[TokenPair])
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    meta: RequestMeta = Depends(get_request_meta),
):
    service = AuthService(db)
    result = await service.refresh(payload.refresh_token, meta)
    await db.commit()
    return SuccessResponse(data=result, message="Token refreshed")


@router.post("/logout", response_model=SuccessResponse[None])
async def logout(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
):
    service = AuthService(db)
    await service.logout(payload.refresh_token, current_user.id, meta)
    await db.commit()
    return SuccessResponse(data=None, message="Logged out successfully")


@router.post("/select-company", response_model=SuccessResponse[ActiveCompanyContext])
async def select_company(
    payload: SelectCompanyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
):
    service = AuthService(db)
    result = await service.select_company(current_user, payload.company_id, meta)
    await db.commit()
    return SuccessResponse(data=result, message="Active company updated")


@router.get("/me", response_model=SuccessResponse[UserRead])
async def get_me(current_user: User = Depends(get_current_user)):
    return SuccessResponse(data=UserRead.model_validate(current_user))

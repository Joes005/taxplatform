import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.exceptions import PermissionDeniedError
from app.core.permissions import PermissionCode
from app.models.membership import CompanyMembership
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.user import CompanyUserCreate, CompanyUserRead, CompanyUserUpdate
from app.services.auth_service import RequestMeta
from app.services.user_service import UserService

router = APIRouter(prefix="/companies/{company_id}/users", tags=["users"])


def _to_read_model(membership: CompanyMembership) -> CompanyUserRead:
    return CompanyUserRead(
        membership_id=membership.id,
        user_id=membership.user.id,
        email=membership.user.email,
        first_name=membership.user.first_name,
        last_name=membership.user.last_name,
        is_active=membership.user.is_active,
        role_code=membership.role.code,
        role_name=membership.role.name,
        status=membership.status,
        joined_at=membership.joined_at,
    )


async def _assert_can_assign_roles(
    membership: CompanyMembership | None, current_user: User, db: AsyncSession
) -> None:
    """Role assignment requires ROLE_ASSIGN in addition to USER_CREATE/UPDATE.

    A platform super admin (membership is None) always passes.
    """
    if current_user.is_platform_super_admin:
        return
    codes = await RoleRepository(db).get_permission_codes_for_role(membership.role_id)
    if PermissionCode.ROLE_ASSIGN.value not in codes:
        raise PermissionDeniedError("You do not have permission to assign roles")


@router.get("", response_model=SuccessResponse[PaginatedData[CompanyUserRead]])
async def list_company_users(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.USER_VIEW.value)),
):
    service = UserService(db)
    memberships, total = await service.list_company_users(
        company_id, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[_to_read_model(m) for m in memberships],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.post("", response_model=SuccessResponse[CompanyUserRead], status_code=201)
async def create_company_user(
    company_id: uuid.UUID,
    payload: CompanyUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    membership=Depends(require_permission(PermissionCode.USER_CREATE.value)),
):
    await _assert_can_assign_roles(membership, current_user, db)

    service = UserService(db)
    new_membership = await service.create_company_user(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=_to_read_model(new_membership), message="User added to company")


@router.patch("/{user_id}", response_model=SuccessResponse[CompanyUserRead])
async def update_company_user(
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: CompanyUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    membership=Depends(require_permission(PermissionCode.USER_UPDATE.value)),
):
    if payload.role_code is not None:
        await _assert_can_assign_roles(membership, current_user, db)

    service = UserService(db)
    updated = await service.update_company_user(company_id, user_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=_to_read_model(updated), message="User updated")


@router.delete("/{user_id}", response_model=SuccessResponse[CompanyUserRead])
async def deactivate_company_user(
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.USER_DEACTIVATE.value)),
):
    service = UserService(db)
    deactivated = await service.deactivate_company_user(company_id, user_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=_to_read_model(deactivated), message="User deactivated")

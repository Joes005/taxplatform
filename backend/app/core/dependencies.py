import uuid

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import TokenType, decode_token
from app.models.membership import CompanyMembership
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import RequestMeta

_bearer_scheme = HTTPBearer(auto_error=False)


def get_request_meta(request: Request) -> RequestMeta:
    ip_address = request.client.host if request.client else None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    user_agent = request.headers.get("user-agent")
    return RequestMeta(ip_address=ip_address, user_agent=user_agent)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise AuthenticationError("Not authenticated")

    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise AuthenticationError("Invalid or expired access token") from exc

    if payload.get("type") != TokenType.ACCESS.value:
        raise AuthenticationError("Invalid token type")

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise AuthenticationError("Invalid access token")

    user = await UserRepository(db).get_by_id(uuid.UUID(user_id_raw))
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    return user


async def require_platform_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_platform_super_admin:
        raise PermissionDeniedError("This action requires platform administrator privileges")
    return current_user


async def get_current_membership(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyMembership | None:
    """Resolves the caller's active membership for the {company_id} path param.

    Returns None for a platform super admin, who is authorized across every
    tenant without holding a per-company membership row. For every other
    user, membership must exist and be ACTIVE or access is denied — the
    company_id from the URL is never trusted on its own.
    """
    if current_user.is_platform_super_admin:
        return None

    membership = await MembershipRepository(db).get_active_membership(
        user_id=current_user.id, company_id=company_id
    )
    if membership is None:
        raise PermissionDeniedError("You do not have access to this company")
    if not membership.company.is_active:
        raise PermissionDeniedError("This company is not active")
    return membership


def require_permission(permission_code: str):
    """Dependency factory enforcing a permission within the {company_id} path
    scope. Usage: Depends(require_permission("COMPANY_MANAGE_USERS")).
    """

    async def dependency(
        current_user: User = Depends(get_current_user),
        membership: CompanyMembership | None = Depends(get_current_membership),
        db: AsyncSession = Depends(get_db),
    ) -> CompanyMembership | None:
        if current_user.is_platform_super_admin:
            return membership

        assert membership is not None  # guaranteed by get_current_membership for non-super-admins
        codes = await RoleRepository(db).get_permission_codes_for_role(membership.role_id)
        if permission_code not in codes:
            raise PermissionDeniedError(
                f"You do not have permission to perform this action ({permission_code})"
            )
        return membership

    return dependency

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    DuplicateResourceError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.permissions import ALL_PERMISSION_CODES
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.membership import MembershipStatus
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ActiveCompanyContext,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TokenPair,
)
from app.schemas.user import MembershipCompanySummary, UserRead
from app.services.audit_service import AuditAction, AuditService


class RequestMeta:
    def __init__(self, ip_address: str | None = None, user_agent: str | None = None) -> None:
        self.ip_address = ip_address
        self.user_agent = user_agent


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.companies = CompanyRepository(db)
        self.memberships = MembershipRepository(db)
        self.roles = RoleRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.audit = AuditService(db)

    async def register(self, payload: RegisterRequest, meta: RequestMeta) -> User:
        if await self.users.email_exists(payload.email):
            raise DuplicateResourceError("An account with this email already exists")

        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            first_name=payload.first_name,
            last_name=payload.last_name,
            is_active=True,
            is_verified=False,
        )
        await self.users.create(user)
        await self.audit.log(
            action=AuditAction.REGISTER,
            user_id=user.id,
            resource_type="user",
            resource_id=str(user.id),
            description=f"User {user.email} registered",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return user

    async def _permission_codes_for(self, user: User, role_id: uuid.UUID | None) -> list[str]:
        if user.is_platform_super_admin:
            return [code.value for code in ALL_PERMISSION_CODES]
        if role_id is None:
            return []
        return await self.roles.get_permission_codes_for_role(role_id)

    async def _build_login_response(
        self, user: User, access_token: str, refresh_token: str, expires_in: int
    ) -> LoginResponse:
        memberships = await self.memberships.list_for_user(user.id)

        company_summaries = [
            MembershipCompanySummary(
                company_id=m.company_id,
                company_name=m.company.legal_name,
                role_code=m.role.code,
                role_name=m.role.name,
                status=m.status,
            )
            for m in memberships
        ]

        if user.is_platform_super_admin and not company_summaries:
            all_comps, _ = await self.companies.list_all(offset=0, limit=50)
            company_summaries = [
                MembershipCompanySummary(
                    company_id=c.id,
                    company_name=c.legal_name,
                    role_code="SUPER_ADMIN",
                    role_name="Platform Super Admin",
                    status="ACTIVE",
                )
                for c in all_comps
            ]

        active_company: ActiveCompanyContext | None = None
        if len(memberships) == 1:
            m = memberships[0]
            permissions = await self._permission_codes_for(user, m.role_id)
            active_company = ActiveCompanyContext(
                company_id=m.company_id,
                company_name=m.company.legal_name,
                role_code=m.role.code,
                role_name=m.role.name,
                permissions=permissions,
            )
        elif user.is_platform_super_admin and len(company_summaries) == 1:
            c = company_summaries[0]
            active_company = ActiveCompanyContext(
                company_id=c.company_id,
                company_name=c.company_name,
                role_code="SUPER_ADMIN",
                role_name="Platform Super Admin",
                permissions=[code.value for code in ALL_PERMISSION_CODES],
            )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            user=UserRead.model_validate(user),
            companies=company_summaries,
            active_company=active_company,
        )

    async def login(self, payload: LoginRequest, meta: RequestMeta) -> LoginResponse:
        user = await self.users.get_by_email(payload.email)

        if user is None or not verify_password(payload.password, user.password_hash):
            await self.audit.log(
                action=AuditAction.LOGIN_FAILED,
                user_id=user.id if user else None,
                description=f"Failed login attempt for {payload.email}",
                ip_address=meta.ip_address,
                user_agent=meta.user_agent,
            )
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("This account has been deactivated")

        user.last_login_at = datetime.now(timezone.utc)

        access_token, _, access_expires_at = create_access_token(user_id=user.id)
        raw_refresh_token, refresh_hash, refresh_expires_at = generate_refresh_token()
        await self.refresh_tokens.create(
            RefreshToken(
                user_id=user.id,
                token_hash=refresh_hash,
                expires_at=refresh_expires_at,
                ip_address=meta.ip_address,
                user_agent=meta.user_agent,
            )
        )

        await self.audit.log(
            action=AuditAction.LOGIN,
            user_id=user.id,
            resource_type="user",
            resource_id=str(user.id),
            description=f"User {user.email} logged in",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        expires_in = int((access_expires_at - datetime.now(timezone.utc)).total_seconds())
        return await self._build_login_response(user, access_token, raw_refresh_token, expires_in)

    async def refresh(self, raw_refresh_token: str, meta: RequestMeta) -> TokenPair:
        token_hash = hash_refresh_token(raw_refresh_token)
        existing = await self.refresh_tokens.get_by_hash(token_hash)

        if existing is None or not existing.is_active:
            raise AuthenticationError("Invalid or expired refresh token")

        user = await self.users.get_by_id(existing.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid or expired refresh token")

        # Rotate: revoke the presented token and issue a new one.
        await self.refresh_tokens.revoke(existing)

        access_token, _, access_expires_at = create_access_token(user_id=user.id)
        raw_new_refresh, new_hash, new_expires_at = generate_refresh_token()
        new_token = await self.refresh_tokens.create(
            RefreshToken(
                user_id=user.id,
                token_hash=new_hash,
                expires_at=new_expires_at,
                ip_address=meta.ip_address,
                user_agent=meta.user_agent,
            )
        )
        existing.replaced_by_token_id = new_token.id

        await self.audit.log(
            action=AuditAction.TOKEN_REFRESH,
            user_id=user.id,
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        expires_in = int((access_expires_at - datetime.now(timezone.utc)).total_seconds())
        return TokenPair(
            access_token=access_token,
            refresh_token=raw_new_refresh,
            expires_in=expires_in,
        )

    async def logout(self, raw_refresh_token: str, user_id: uuid.UUID, meta: RequestMeta) -> None:
        token_hash = hash_refresh_token(raw_refresh_token)
        existing = await self.refresh_tokens.get_by_hash(token_hash)

        if existing is not None and existing.user_id == user_id and existing.revoked_at is None:
            await self.refresh_tokens.revoke(existing)

        await self.audit.log(
            action=AuditAction.LOGOUT,
            user_id=user_id,
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

    async def select_company(
        self, user: User, company_id: uuid.UUID, meta: RequestMeta
    ) -> ActiveCompanyContext:
        membership = await self.memberships.get_active_membership(
            user_id=user.id, company_id=company_id
        )
        if membership is None:
            if user.is_platform_super_admin:
                company = await self.companies.get_by_id(company_id)
                if company is None:
                    raise NotFoundError("Company not found")
                if not company.is_active:
                    raise PermissionDeniedError("This company is not active")
                permissions = [code.value for code in ALL_PERMISSION_CODES]
                await self.audit.log(
                    action=AuditAction.COMPANY_SWITCH,
                    user_id=user.id,
                    company_id=company_id,
                    resource_type="company",
                    resource_id=str(company_id),
                    description=f"Super admin {user.email} switched active company",
                    ip_address=meta.ip_address,
                    user_agent=meta.user_agent,
                )
                return ActiveCompanyContext(
                    company_id=company.id,
                    company_name=company.legal_name,
                    role_code="SUPER_ADMIN",
                    role_name="Platform Super Admin",
                    permissions=permissions,
                )
            raise PermissionDeniedError("You are not a member of this company")
        if not membership.company.is_active:
            raise PermissionDeniedError("This company is not active")

        permissions = await self._permission_codes_for(user, membership.role_id)

        await self.audit.log(
            action=AuditAction.COMPANY_SWITCH,
            user_id=user.id,
            company_id=company_id,
            resource_type="company",
            resource_id=str(company_id),
            description=f"User {user.email} switched active company",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        return ActiveCompanyContext(
            company_id=membership.company_id,
            company_name=membership.company.legal_name,
            role_code=membership.role.code,
            role_name=membership.role.name,
            permissions=permissions,
        )

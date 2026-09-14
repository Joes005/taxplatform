import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError, NotFoundError, ValidationAppError
from app.core.permissions import RoleCode
from app.core.security import hash_password
from app.models.membership import CompanyMembership, MembershipStatus
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CompanyUserCreate, CompanyUserUpdate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.memberships = MembershipRepository(db)
        self.roles = RoleRepository(db)
        self.audit = AuditService(db)

    async def list_company_users(
        self, company_id: uuid.UUID, *, page: int, page_size: int
    ) -> tuple[list[CompanyMembership], int]:
        offset = (page - 1) * page_size
        return await self.memberships.list_for_company(company_id, offset=offset, limit=page_size)

    async def create_company_user(
        self,
        company_id: uuid.UUID,
        payload: CompanyUserCreate,
        current_user: User,
        meta: RequestMeta,
    ) -> CompanyMembership:
        role = await self.roles.get_by_code(payload.role_code)
        if role is None:
            raise ValidationAppError(f"Unknown role code: {payload.role_code}")

        user = await self.users.get_by_email(payload.email)
        if user is None:
            user = User(
                email=payload.email,
                password_hash=hash_password(payload.password),
                first_name=payload.first_name,
                last_name=payload.last_name,
                is_active=True,
                is_verified=False,
            )
            await self.users.create(user)

        existing_membership = await self.memberships.get_for_user_in_company(
            user_id=user.id, company_id=company_id
        )
        if existing_membership is not None and existing_membership.status == MembershipStatus.ACTIVE:
            raise ValidationAppError("This user is already a member of the company")

        if existing_membership is not None:
            existing_membership.status = MembershipStatus.ACTIVE
            existing_membership.role_id = role.id
            existing_membership.joined_at = datetime.now(timezone.utc)
            membership = existing_membership
        else:
            membership = CompanyMembership(
                user_id=user.id,
                company_id=company_id,
                role_id=role.id,
                status=MembershipStatus.ACTIVE,
                joined_at=datetime.now(timezone.utc),
            )
            await self.memberships.create(membership)

        await self.db.flush()

        await self.audit.log(
            action=AuditAction.USER_CREATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="user",
            resource_id=str(user.id),
            description=f"User {user.email} added to company with role {role.code}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        membership.user = user
        membership.role = role
        return membership

    async def _ensure_not_last_admin(
        self, company_id: uuid.UUID, membership: CompanyMembership
    ) -> None:
        admin_role = await self.roles.get_by_code(RoleCode.COMPANY_ADMIN.value)
        if admin_role is None or membership.role_id != admin_role.id:
            return
        active_admin_count = await self.memberships.count_active_admins(company_id, admin_role.id)
        if active_admin_count <= 1:
            raise InvalidStateError(
                "Cannot remove or demote the last active Company Admin for this company"
            )

    async def update_company_user(
        self,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: CompanyUserUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> CompanyMembership:
        membership = await self.memberships.get_for_user_in_company(
            user_id=user_id, company_id=company_id
        )
        if membership is None:
            raise NotFoundError("This user is not a member of the company")

        role_changed = payload.role_code is not None and payload.role_code != membership.role.code
        deactivating = payload.status is not None and payload.status != MembershipStatus.ACTIVE

        if role_changed or deactivating:
            await self._ensure_not_last_admin(company_id, membership)

        if payload.role_code is not None:
            new_role = await self.roles.get_by_code(payload.role_code)
            if new_role is None:
                raise ValidationAppError(f"Unknown role code: {payload.role_code}")
            membership.role_id = new_role.id
            membership.role = new_role

        if payload.status is not None:
            membership.status = payload.status

        user = membership.user or await self.users.get_by_id(user_id)
        if payload.first_name is not None:
            user.first_name = payload.first_name
        if payload.last_name is not None:
            user.last_name = payload.last_name

        await self.db.flush()

        await self.audit.log(
            action=AuditAction.USER_UPDATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="user",
            resource_id=str(user_id),
            description=f"Membership for {user.email} updated",
            metadata={"fields": list(payload.model_dump(exclude_unset=True).keys())},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        membership.user = user
        return membership

    async def deactivate_company_user(
        self,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        current_user: User,
        meta: RequestMeta,
    ) -> CompanyMembership:
        membership = await self.memberships.get_for_user_in_company(
            user_id=user_id, company_id=company_id
        )
        if membership is None:
            raise NotFoundError("This user is not a member of the company")

        await self._ensure_not_last_admin(company_id, membership)

        membership.status = MembershipStatus.INACTIVE

        await self.db.flush()

        await self.audit.log(
            action=AuditAction.USER_DEACTIVATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="user",
            resource_id=str(user_id),
            description=f"Membership for user {user_id} deactivated",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return membership

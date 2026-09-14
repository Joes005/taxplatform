from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.schemas.common import SuccessResponse
from app.schemas.role import RoleWithPermissions

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=SuccessResponse[list[RoleWithPermissions]])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    repo = RoleRepository(db)
    roles = await repo.list_all()

    data = []
    for role in roles:
        permission_codes = await repo.get_permission_codes_for_role(role.id)
        data.append(
            RoleWithPermissions(
                id=role.id,
                code=role.code,
                name=role.name,
                description=role.description,
                is_system_role=role.is_system_role,
                permissions=permission_codes,
            )
        )

    return SuccessResponse(data=data)

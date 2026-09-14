import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.membership import MembershipStatus
from app.utils.validators import validate_password_strength


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    phone: str | None = None
    is_active: bool
    is_verified: bool
    is_platform_super_admin: bool
    last_login_at: datetime | None = None
    created_at: datetime


class MembershipCompanySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: uuid.UUID
    company_name: str
    role_code: str
    role_name: str
    status: MembershipStatus


class CompanyUserRead(BaseModel):
    """A user as seen within the context of one company's membership list."""

    model_config = ConfigDict(from_attributes=True)

    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    is_active: bool
    role_code: str
    role_name: str
    status: MembershipStatus
    joined_at: datetime | None = None


class CompanyUserCreate(BaseModel):
    email: EmailStr
    first_name: Annotated[str, Field(min_length=1, max_length=100)]
    last_name: Annotated[str, Field(min_length=1, max_length=100)]
    password: Annotated[str, Field(min_length=8, max_length=128)]
    role_code: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower().strip()

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class CompanyUserUpdate(BaseModel):
    first_name: Annotated[str | None, Field(default=None, min_length=1, max_length=100)]
    last_name: Annotated[str | None, Field(default=None, min_length=1, max_length=100)]
    role_code: str | None = None
    status: MembershipStatus | None = None

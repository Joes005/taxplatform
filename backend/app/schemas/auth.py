import uuid
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import MembershipCompanySummary, UserRead
from app.utils.validators import validate_password_strength


class RegisterRequest(BaseModel):
    first_name: Annotated[str, Field(min_length=1, max_length=100)]
    last_name: Annotated[str, Field(min_length=1, max_length=100)]
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower().strip()

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower().strip()


class ActiveCompanyContext(BaseModel):
    company_id: uuid.UUID
    company_name: str
    role_code: str
    role_name: str
    permissions: list[str]


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
    companies: list[MembershipCompanySummary]
    active_company: ActiveCompanyContext | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class SelectCompanyRequest(BaseModel):
    company_id: uuid.UUID

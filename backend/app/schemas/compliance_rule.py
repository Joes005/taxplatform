import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.compliance_enums import ComplianceCategory, ComplianceFrequency, ComplianceModule, CompliancePriority


class ComplianceRuleCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    category: ComplianceCategory
    module: ComplianceModule
    frequency: ComplianceFrequency
    due_date_rule: dict[str, Any]
    priority: CompliancePriority = CompliancePriority.MEDIUM
    effective_from: date
    effective_to: date | None = None
    company_specific: bool = Field(
        default=False, description="True creates a company-scoped override rather than a platform-wide rule"
    )


class ComplianceRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    due_date_rule: dict[str, Any] | None = None
    priority: CompliancePriority | None = None
    effective_to: date | None = None


class ComplianceRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    code: str
    name: str
    description: str | None
    category: ComplianceCategory
    module: ComplianceModule
    frequency: ComplianceFrequency
    due_date_rule: dict[str, Any]
    priority: CompliancePriority
    effective_from: date
    effective_to: date | None
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

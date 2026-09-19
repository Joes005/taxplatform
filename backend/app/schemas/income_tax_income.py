import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.income_tax_enums import HousePropertyType, IncomeTaxSourceType


class IncomeTaxSalaryIncomeCreate(BaseModel):
    financial_year_id: uuid.UUID
    employer_name: str = Field(min_length=1, max_length=255)
    gross_salary: Decimal = Decimal("0")
    allowances: Decimal = Decimal("0")
    perquisites: Decimal = Decimal("0")
    profit_in_lieu: Decimal = Decimal("0")
    standard_deduction: Decimal = Decimal("0")
    professional_tax: Decimal = Decimal("0")
    tds: Decimal = Decimal("0")


class IncomeTaxSalaryIncomeUpdate(BaseModel):
    employer_name: str | None = Field(default=None, min_length=1, max_length=255)
    gross_salary: Decimal | None = None
    allowances: Decimal | None = None
    perquisites: Decimal | None = None
    profit_in_lieu: Decimal | None = None
    standard_deduction: Decimal | None = None
    professional_tax: Decimal | None = None
    tds: Decimal | None = None


class IncomeTaxSalaryIncomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    employer_name: str
    gross_salary: Decimal
    allowances: Decimal
    perquisites: Decimal
    profit_in_lieu: Decimal
    standard_deduction: Decimal
    professional_tax: Decimal
    tds: Decimal
    taxable_amount: Decimal


class IncomeTaxHousePropertyIncomeCreate(BaseModel):
    financial_year_id: uuid.UUID
    property_type: HousePropertyType
    address: str | None = Field(default=None, max_length=500)
    gross_rent: Decimal = Decimal("0")
    municipal_tax: Decimal = Decimal("0")
    interest_on_home_loan: Decimal = Decimal("0")


class IncomeTaxHousePropertyIncomeUpdate(BaseModel):
    property_type: HousePropertyType | None = None
    address: str | None = Field(default=None, max_length=500)
    gross_rent: Decimal | None = None
    municipal_tax: Decimal | None = None
    interest_on_home_loan: Decimal | None = None


class IncomeTaxHousePropertyIncomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    property_type: HousePropertyType
    address: str | None
    gross_rent: Decimal
    municipal_tax: Decimal
    net_annual_value: Decimal
    standard_deduction: Decimal
    interest_on_home_loan: Decimal
    income_or_loss: Decimal


class IncomeTaxOtherIncomeCreate(BaseModel):
    financial_year_id: uuid.UUID
    income_type: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    gross_amount: Decimal = Decimal("0")
    tds: Decimal = Decimal("0")
    source_type: IncomeTaxSourceType | None = None
    source_id: uuid.UUID | None = None


class IncomeTaxOtherIncomeUpdate(BaseModel):
    income_type: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    gross_amount: Decimal | None = None
    tds: Decimal | None = None


class IncomeTaxOtherIncomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    income_type: str
    description: str | None
    gross_amount: Decimal
    tds: Decimal
    net_amount: Decimal
    source_type: IncomeTaxSourceType | None
    source_id: uuid.UUID | None


class IncomeTaxExemptIncomeCreate(BaseModel):
    financial_year_id: uuid.UUID
    section_code: str = Field(min_length=1, max_length=20)
    description: str | None = Field(default=None, max_length=255)
    amount: Decimal = Decimal("0")
    source_reference: str | None = Field(default=None, max_length=255)


class IncomeTaxExemptIncomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    financial_year_id: uuid.UUID
    section_code: str
    description: str | None
    amount: Decimal
    source_reference: str | None

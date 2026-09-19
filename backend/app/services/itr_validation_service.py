"""ITR form-type determination and preparation validation (PHASE8 §44,
§46-47). Form applicability that can't be confidently determined resolves
to `NOT_DETERMINED` rather than a guess; validation never silently drops
an issue — every check either passes or appends an `ERROR`/`WARNING`/
`REVIEW_REQUIRED` item, and the caller decides what to do with them
(only `ERROR` blocks approval, per PHASE8 §52).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_account import BankAccount
from app.models.income_tax_enums import ITRFormType, TaxpayerType, ValidationSeverity
from app.models.income_tax_profile import IncomeTaxProfile
from app.models.itr_preparation import ITRPreparation
from app.models.tax_computation import TaxComputation
from app.repositories.income_tax_credit_repository import IncomeTaxCreditRepository
from app.schemas.tax_computation import ValidationIssue
from app.utils.pan import validate_pan


def determine_itr_form_type(
    taxpayer_type: TaxpayerType, *, has_business_income: bool, has_capital_gains: bool
) -> ITRFormType:
    if taxpayer_type == TaxpayerType.COMPANY:
        return ITRFormType.ITR_6
    if taxpayer_type in (TaxpayerType.PARTNERSHIP, TaxpayerType.LLP):
        return ITRFormType.ITR_5
    if taxpayer_type == TaxpayerType.TRUST:
        return ITRFormType.ITR_7
    if taxpayer_type in (TaxpayerType.INDIVIDUAL, TaxpayerType.HUF):
        if has_business_income:
            return ITRFormType.ITR_3
        if has_capital_gains:
            return ITRFormType.ITR_2
        return ITRFormType.ITR_1
    return ITRFormType.NOT_DETERMINED


class ITRValidationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.credits = IncomeTaxCreditRepository(db)

    async def validate(
        self, profile: IncomeTaxProfile | None, computation: TaxComputation, preparation: ITRPreparation
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if profile is None:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="PROFILE_MISSING",
                    message="Income Tax profile is missing.",
                    field="profile",
                )
            )
        else:
            pan_result = validate_pan(profile.pan)
            if not pan_result.is_valid:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code=pan_result.error_code or "INVALID_PAN",
                        message=pan_result.error_message or "PAN is invalid.",
                        field="pan",
                    )
                )

        if preparation.itr_form_type == ITRFormType.NOT_DETERMINED:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.REVIEW_REQUIRED,
                    code="ITR_FORM_NOT_DETERMINED",
                    message="ITR form applicability could not be determined automatically.",
                    field="itr_form_type",
                )
            )

        has_any_income = any(
            [
                computation.salary_income,
                computation.house_property_income,
                computation.business_income,
                computation.capital_gains_income,
                computation.other_income,
            ]
        )
        if not has_any_income:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="NO_INCOME_RECORDED",
                    message="No income has been recorded for this financial year.",
                    field="income",
                )
            )

        if computation.tds_credit_total > 0:
            credit_entries = await self.credits.list_for_fy(computation.company_id, computation.financial_year_id)
            incomplete = [c for c in credit_entries if not c.deductor_tan and not c.certificate_reference]
            if incomplete:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="TDS_CREDIT_SOURCE_INCOMPLETE",
                        message=f"{len(incomplete)} TDS credit entr{'y is' if len(incomplete) == 1 else 'ies are'} "
                        "missing a TAN or certificate reference.",
                        field="tds_credits",
                    )
                )

        bank_account_count = (
            await self.db.execute(
                select(BankAccount).where(BankAccount.company_id == computation.company_id, BankAccount.is_active.is_(True))
            )
        ).scalars().first()
        if bank_account_count is None:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="BANK_ACCOUNT_MISSING",
                    message="At least one active bank account is required for refund/payment processing.",
                    field="bank_accounts",
                )
            )

        if computation.taxable_income > 5_000_000:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="SURCHARGE_MARGINAL_RELIEF_NOT_COMPUTED",
                    message="Taxable income is high enough that surcharge marginal relief may apply — "
                    "this platform does not compute marginal relief; verify the surcharge figure manually.",
                    field="surcharge",
                )
            )

        return issues

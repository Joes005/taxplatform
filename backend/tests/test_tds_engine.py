from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import ValidationAppError
from app.models.tds_enums import PANStatus, TDSApplicabilityStatus, TDSRateType
from app.models.tds_rule import TDSRule
from app.seed import seed_default_tds_sections_and_rules
from app.services.tds_applicability_service import TDSApplicabilityService
from app.services.tds_calculation_service import TDSCalculationService
from app.services.tds_rule_engine import TDSRuleEngine
from tests.conftest import create_vendor


async def _get_section_and_rule(db_session, code: str):
    from sqlalchemy import select

    from app.models.tds_section import TDSSection

    section = (
        await db_session.execute(select(TDSSection).where(TDSSection.section_code == code))
    ).scalar_one()
    rule = (
        await db_session.execute(
            select(TDSRule).where(TDSRule.tds_section_id == section.id, TDSRule.company_id.is_(None))
        )
    ).scalar_one()
    return section, rule


async def _create_deductee(db_session, company_id, *, name="Test Deductee", pan="AAAPA1234A", pan_status=PANStatus.AVAILABLE):
    from app.models.deductee import Deductee

    deductee = Deductee(company_id=company_id, name=name, pan=pan, pan_status=pan_status)
    db_session.add(deductee)
    await db_session.flush()
    return deductee


class TestTDSCalculationService:
    async def test_percentage_rate_calculated(self, db_session, company_a_with_admin):
        await seed_default_tds_sections_and_rules(db_session)
        _section, rule = await _get_section_and_rule(db_session, "194J")

        result = TDSCalculationService.calculate(
            amount=Decimal("100000"), rule=rule, pan_status=PANStatus.AVAILABLE
        )
        assert result.tds_amount == Decimal("10000.00")
        assert result.net_amount == Decimal("90000.00")
        assert result.used_no_pan_rate is False

    async def test_missing_pan_uses_no_pan_rate(self, db_session):
        await seed_default_tds_sections_and_rules(db_session)
        _section, rule = await _get_section_and_rule(db_session, "194J")

        result = TDSCalculationService.calculate(
            amount=Decimal("100000"), rule=rule, pan_status=PANStatus.NOT_AVAILABLE
        )
        assert result.used_no_pan_rate is True
        assert result.rate_used == Decimal("20")
        assert result.tds_amount == Decimal("20000.00")

    async def test_missing_pan_without_no_pan_rate_raises(self):
        rule = TDSRule(
            tds_section_id="00000000-0000-0000-0000-000000000000",
            company_id=None,
            rate=Decimal("10"),
            rate_type=TDSRateType.PERCENTAGE,
            no_pan_rate=None,
            threshold_amount=Decimal("0"),
            effective_from=date(2021, 4, 1),
        )
        with pytest.raises(ValidationAppError):
            TDSCalculationService.calculate(
                amount=Decimal("1000"), rule=rule, pan_status=PANStatus.NOT_AVAILABLE
            )

    async def test_fixed_rate_clamped_to_amount(self):
        rule = TDSRule(
            tds_section_id="00000000-0000-0000-0000-000000000000",
            company_id=None,
            rate=Decimal("500"),
            rate_type=TDSRateType.FIXED,
            threshold_amount=Decimal("0"),
            effective_from=date(2021, 4, 1),
        )
        result = TDSCalculationService.calculate(
            amount=Decimal("200"), rule=rule, pan_status=PANStatus.AVAILABLE
        )
        assert result.tds_amount == Decimal("200.00")
        assert result.net_amount == Decimal("0.00")


class TestTDSApplicabilityService:
    async def test_missing_data_when_deductee_missing(self, db_session, company_a_with_admin):
        await seed_default_tds_sections_and_rules(db_session)
        company, _admin = company_a_with_admin
        section, _rule = await _get_section_and_rule(db_session, "194J")

        service = TDSApplicabilityService(db_session)
        result = await service.evaluate(
            company.id,
            tds_section_id=section.id,
            deductee=None,
            transaction_date=date(2025, 5, 1),
            amount=Decimal("50000"),
        )
        assert result.status == TDSApplicabilityStatus.MISSING_DATA

    async def test_below_threshold_not_applicable(self, db_session, company_a_with_admin):
        await seed_default_tds_sections_and_rules(db_session)
        company, _admin = company_a_with_admin
        section, _rule = await _get_section_and_rule(db_session, "194J")
        deductee = await _create_deductee(db_session, company.id)

        service = TDSApplicabilityService(db_session)
        result = await service.evaluate(
            company.id,
            tds_section_id=section.id,
            deductee=deductee,
            transaction_date=date(2025, 5, 1),
            amount=Decimal("20000"),
        )
        assert result.status == TDSApplicabilityStatus.NOT_APPLICABLE

    async def test_above_threshold_applicable(self, db_session, company_a_with_admin):
        await seed_default_tds_sections_and_rules(db_session)
        company, _admin = company_a_with_admin
        section, _rule = await _get_section_and_rule(db_session, "194J")
        deductee = await _create_deductee(db_session, company.id)

        service = TDSApplicabilityService(db_session)
        result = await service.evaluate(
            company.id,
            tds_section_id=section.id,
            deductee=deductee,
            transaction_date=date(2025, 5, 1),
            amount=Decimal("50000"),
        )
        assert result.status == TDSApplicabilityStatus.APPLICABLE

    async def test_aggregate_threshold_missing_data_needs_review(self, db_session, company_a_with_admin):
        await seed_default_tds_sections_and_rules(db_session)
        company, _admin = company_a_with_admin
        section, _rule = await _get_section_and_rule(db_session, "194Q")
        deductee = await _create_deductee(db_session, company.id)

        service = TDSApplicabilityService(db_session)
        result = await service.evaluate(
            company.id,
            tds_section_id=section.id,
            deductee=deductee,
            transaction_date=date(2025, 5, 1),
            amount=Decimal("100000"),
            aggregate_paid_this_year=None,
        )
        assert result.status == TDSApplicabilityStatus.REVIEW_REQUIRED

    async def test_aggregate_threshold_crossed_applicable(self, db_session, company_a_with_admin):
        await seed_default_tds_sections_and_rules(db_session)
        company, _admin = company_a_with_admin
        section, _rule = await _get_section_and_rule(db_session, "194Q")
        deductee = await _create_deductee(db_session, company.id)

        service = TDSApplicabilityService(db_session)
        result = await service.evaluate(
            company.id,
            tds_section_id=section.id,
            deductee=deductee,
            transaction_date=date(2025, 5, 1),
            amount=Decimal("100000"),
            aggregate_paid_this_year=Decimal("4950000"),
        )
        assert result.status == TDSApplicabilityStatus.APPLICABLE

    async def test_invalid_pan_needs_review(self, db_session, company_a_with_admin):
        await seed_default_tds_sections_and_rules(db_session)
        company, _admin = company_a_with_admin
        section, _rule = await _get_section_and_rule(db_session, "194J")
        deductee = await _create_deductee(db_session, company.id, pan_status=PANStatus.INVALID)

        service = TDSApplicabilityService(db_session)
        result = await service.evaluate(
            company.id,
            tds_section_id=section.id,
            deductee=deductee,
            transaction_date=date(2025, 5, 1),
            amount=Decimal("50000"),
        )
        assert result.status == TDSApplicabilityStatus.REVIEW_REQUIRED

    async def test_no_effective_rule_needs_review(self, db_session, company_a_with_admin):
        await seed_default_tds_sections_and_rules(db_session)
        company, _admin = company_a_with_admin
        section, _rule = await _get_section_and_rule(db_session, "194J")
        deductee = await _create_deductee(db_session, company.id)

        service = TDSApplicabilityService(db_session)
        result = await service.evaluate(
            company.id,
            tds_section_id=section.id,
            deductee=deductee,
            transaction_date=date(2019, 5, 1),  # before any rule's effective_from
            amount=Decimal("50000"),
        )
        assert result.status == TDSApplicabilityStatus.REVIEW_REQUIRED


class TestTDSRuleEngine:
    async def test_applicable_transaction_returns_calculation_trace(self, db_session, company_a_with_admin):
        await seed_default_tds_sections_and_rules(db_session)
        company, _admin = company_a_with_admin
        section, _rule = await _get_section_and_rule(db_session, "194J")
        deductee = await _create_deductee(db_session, company.id)

        engine = TDSRuleEngine(db_session)
        result = await engine.evaluate(
            company.id,
            tds_section_id=section.id,
            deductee=deductee,
            transaction_date=date(2025, 5, 1),
            amount=Decimal("100000"),
        )
        assert result.status == TDSApplicabilityStatus.APPLICABLE
        assert result.calculation is not None
        assert result.calculation.tds_amount == Decimal("10000.00")

    async def test_not_applicable_transaction_has_no_calculation(self, db_session, company_a_with_admin):
        await seed_default_tds_sections_and_rules(db_session)
        company, _admin = company_a_with_admin
        section, _rule = await _get_section_and_rule(db_session, "194J")
        deductee = await _create_deductee(db_session, company.id)

        engine = TDSRuleEngine(db_session)
        result = await engine.evaluate(
            company.id,
            tds_section_id=section.id,
            deductee=deductee,
            transaction_date=date(2025, 5, 1),
            amount=Decimal("5000"),
        )
        assert result.status == TDSApplicabilityStatus.NOT_APPLICABLE
        assert result.calculation is None

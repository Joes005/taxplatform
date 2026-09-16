from datetime import date
from decimal import Decimal

from app.models.gst_enums import GSTTransactionCategory, SupplyType
from app.services.gst_calculation_service import GSTCalculationService
from app.services.gst_classification_service import GSTTransactionClassificationService
from app.services.gst_place_of_supply_service import GSTPlaceOfSupplyService
from app.seed import seed_gst_default_tax_rates
from app.utils.gstin import compute_gstin_check_digit, validate_gstin
from tests.conftest import auth_headers, create_financial_year, login


class TestGSTINValidation:
    def test_valid_gstin_accepted(self):
        result = validate_gstin("27AAPFU0939F1ZV")
        assert result.is_valid is True
        assert result.state_code == "27"
        assert result.state_name == "Maharashtra"

    def test_second_known_valid_gstin_accepted(self):
        assert validate_gstin("29AABCU9603R1ZJ").is_valid is True

    def test_wrong_length_rejected(self):
        result = validate_gstin("27AAPFU0939F1Z")
        assert result.is_valid is False
        assert result.error_code == "INVALID_GSTIN_FORMAT"

    def test_bad_format_rejected(self):
        result = validate_gstin("XX-NOT-A-GSTIN-")
        assert result.is_valid is False
        assert result.error_code == "INVALID_GSTIN_FORMAT"

    def test_unknown_state_code_rejected(self):
        # 00 is not an allotted GST state/UT code.
        prefix = "00AAPFU0939F1Z"
        gstin = prefix + compute_gstin_check_digit(prefix)
        result = validate_gstin(gstin)
        assert result.is_valid is False
        assert result.error_code == "INVALID_STATE_CODE"

    def test_wrong_checksum_rejected(self):
        result = validate_gstin("27AAPFU0939F1ZA")
        assert result.is_valid is False
        assert result.error_code == "INVALID_GSTIN"

    def test_empty_gstin_rejected(self):
        result = validate_gstin(None)
        assert result.is_valid is False
        assert result.error_code == "INVALID_GSTIN"

    def test_lowercase_gstin_normalized_and_accepted(self):
        assert validate_gstin("27aapfu0939f1zv").is_valid is True


class TestGSTPlaceOfSupplyService:
    def test_same_state_is_intra_state(self):
        assert (
            GSTPlaceOfSupplyService.determine_supply_type("27", "27") == SupplyType.INTRA_STATE
        )

    def test_different_state_is_inter_state(self):
        assert (
            GSTPlaceOfSupplyService.determine_supply_type("27", "29") == SupplyType.INTER_STATE
        )

    def test_missing_state_code_raises(self):
        import pytest

        from app.core.exceptions import ValidationAppError

        with pytest.raises(ValidationAppError):
            GSTPlaceOfSupplyService.determine_supply_type("27", "")


class TestGSTCalculationService:
    def test_intra_state_18_percent_splits_evenly(self):
        breakdown = GSTCalculationService.calculate_tax_breakdown(
            taxable_value=Decimal("10000"), rate=Decimal("18"), supply_type=SupplyType.INTRA_STATE
        )
        assert breakdown.cgst_amount == Decimal("900.00")
        assert breakdown.sgst_amount == Decimal("900.00")
        assert breakdown.igst_amount == Decimal("0")
        assert breakdown.total_tax == Decimal("1800.00")
        assert breakdown.total_value == Decimal("11800.00")

    def test_inter_state_18_percent_is_all_igst(self):
        breakdown = GSTCalculationService.calculate_tax_breakdown(
            taxable_value=Decimal("10000"), rate=Decimal("18"), supply_type=SupplyType.INTER_STATE
        )
        assert breakdown.igst_amount == Decimal("1800.00")
        assert breakdown.cgst_amount == Decimal("0")
        assert breakdown.sgst_amount == Decimal("0")

    def test_rates_5_12_28_percent(self):
        for rate, expected_total_tax in (
            (Decimal("5"), Decimal("500.00")),
            (Decimal("12"), Decimal("1200.00")),
            (Decimal("28"), Decimal("2800.00")),
        ):
            breakdown = GSTCalculationService.calculate_tax_breakdown(
                taxable_value=Decimal("10000"), rate=rate, supply_type=SupplyType.INTER_STATE
            )
            assert breakdown.total_tax == expected_total_tax

    def test_cess_applied_on_top_of_gst(self):
        breakdown = GSTCalculationService.calculate_tax_breakdown(
            taxable_value=Decimal("10000"),
            rate=Decimal("28"),
            supply_type=SupplyType.INTER_STATE,
            cess_rate=Decimal("12"),
        )
        assert breakdown.cess_amount == Decimal("1200.00")
        assert breakdown.total_tax == Decimal("4000.00")

    def test_negative_taxable_value_rejected(self):
        import pytest

        from app.core.exceptions import ValidationAppError

        with pytest.raises(ValidationAppError):
            GSTCalculationService.calculate_tax_breakdown(
                taxable_value=Decimal("-1"), rate=Decimal("18"), supply_type=SupplyType.INTRA_STATE
            )


class TestGSTTransactionClassificationService:
    def test_valid_gstin_classified_b2b(self):
        result = GSTTransactionClassificationService.classify_sales_transaction(
            customer_gstin="27AAPFU0939F1ZV",
            customer_state_code="27",
            place_of_supply_state_code="27",
        )
        assert result.category == GSTTransactionCategory.B2B

    def test_no_gstin_with_state_classified_b2c(self):
        result = GSTTransactionClassificationService.classify_sales_transaction(
            customer_gstin=None, customer_state_code="27", place_of_supply_state_code="27"
        )
        assert result.category == GSTTransactionCategory.B2C

    def test_missing_place_of_supply_needs_review(self):
        result = GSTTransactionClassificationService.classify_sales_transaction(
            customer_gstin=None, customer_state_code="27", place_of_supply_state_code=None
        )
        assert result.category == GSTTransactionCategory.REVIEW_REQUIRED

    def test_malformed_gstin_needs_review(self):
        result = GSTTransactionClassificationService.classify_sales_transaction(
            customer_gstin="NOT-A-GSTIN", customer_state_code="27", place_of_supply_state_code="27"
        )
        assert result.category == GSTTransactionCategory.REVIEW_REQUIRED

    def test_no_gstin_and_no_state_needs_review(self):
        result = GSTTransactionClassificationService.classify_sales_transaction(
            customer_gstin=None, customer_state_code=None, place_of_supply_state_code="27"
        )
        assert result.category == GSTTransactionCategory.REVIEW_REQUIRED


class TestSeedGSTDefaultTaxRates:
    async def test_seeds_five_standard_slabs_idempotently(self, db_session):
        await seed_gst_default_tax_rates(db_session)
        await seed_gst_default_tax_rates(db_session)  # must not duplicate

        from sqlalchemy import select

        from app.models.gst_tax_rate import GSTTaxRate

        result = await db_session.execute(
            select(GSTTaxRate).where(GSTTaxRate.company_id.is_(None))
        )
        rates = {r.rate for r in result.scalars().all()}
        assert rates == {Decimal("0.00"), Decimal("5.00"), Decimal("12.00"), Decimal("18.00"), Decimal("28.00")}


class TestGSTProfileAPI:
    async def test_create_and_get_gst_profile(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/gst/profile?company_id={company.id}",
            json={"gstin": "27AAPFU0939F1ZV", "legal_name": company.legal_name},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()["data"]
        assert body["state_code"] == "27"
        assert body["state_name"] == "Maharashtra"

        get_response = await client.get(f"/api/v1/gst/profile?company_id={company.id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["data"]["gstin"] == "27AAPFU0939F1ZV"

    async def test_invalid_gstin_rejected(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/gst/profile?company_id={company.id}",
            json={"gstin": "INVALID_GSTIN_1", "legal_name": "Bad Co"},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_GSTIN_FORMAT"

    async def test_duplicate_profile_rejected(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        payload = {"gstin": "27AAPFU0939F1ZV", "legal_name": company.legal_name}

        first = await client.post(
            f"/api/v1/gst/profile?company_id={company.id}", json=payload, headers=headers
        )
        assert first.status_code == 201

        second = await client.post(
            f"/api/v1/gst/profile?company_id={company.id}", json=payload, headers=headers
        )
        assert second.status_code == 422
        assert second.json()["error"]["code"] == "GST_PROFILE_ALREADY_EXISTS"

    async def test_company_b_cannot_see_company_a_profile(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin

        data_a = await login(client, admin_a.email, "TestPass1!")
        await client.post(
            f"/api/v1/gst/profile?company_id={company_a.id}",
            json={"gstin": "27AAPFU0939F1ZV", "legal_name": company_a.legal_name},
            headers=auth_headers(data_a["access_token"]),
        )

        data_b = await login(client, admin_b.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/gst/profile?company_id={company_b.id}",
            headers=auth_headers(data_b["access_token"]),
        )
        assert response.status_code == 404


class TestGSTReturnPeriodAPI:
    async def test_create_return_period(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/gst/return-periods?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "year": 2025, "month": 4},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()["data"]
        assert body["period_start"] == "2025-04-01"
        assert body["period_end"] == "2025-04-30"
        assert body["status"] == "OPEN"

    async def test_duplicate_period_rejected(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        payload = {"financial_year_id": str(financial_year_a.id), "year": 2025, "month": 5}

        first = await client.post(
            f"/api/v1/gst/return-periods?company_id={company.id}", json=payload, headers=headers
        )
        assert first.status_code == 201

        second = await client.post(
            f"/api/v1/gst/return-periods?company_id={company.id}", json=payload, headers=headers
        )
        assert second.status_code == 422
        assert second.json()["error"]["code"] == "GST_RETURN_PERIOD_ALREADY_EXISTS"

    async def test_auditor_cannot_create_return_period(
        self, client, db_session, company_a_with_admin, financial_year_a, seeded_rbac
    ):
        company, admin = company_a_with_admin
        auditor = await _add_auditor(db_session, seeded_rbac, company.id)
        data = await login(client, auditor.email, "TestPass1!")

        response = await client.post(
            f"/api/v1/gst/return-periods?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "year": 2025, "month": 6},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 403


async def _add_auditor(db_session, roles, company_id):
    from tests.conftest import add_membership

    return await add_membership(
        db_session, roles, company_id=company_id, email="auditor@example.com", role_code="AUDITOR"
    )

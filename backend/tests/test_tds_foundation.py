from datetime import date
from decimal import Decimal

from app.seed import seed_default_tds_sections_and_rules
from app.utils.pan import validate_pan
from app.utils.tan import validate_tan
from tests.conftest import auth_headers, login


class TestPANValidation:
    def test_valid_pan_accepted(self):
        assert validate_pan("AAAPA1234A").is_valid is True

    def test_wrong_length_rejected(self):
        result = validate_pan("AAAPA1234")
        assert result.is_valid is False
        assert result.error_code == "INVALID_PAN_FORMAT"

    def test_bad_format_rejected(self):
        result = validate_pan("1234567890")
        assert result.is_valid is False
        assert result.error_code == "INVALID_PAN_FORMAT"

    def test_missing_pan_rejected(self):
        result = validate_pan(None)
        assert result.is_valid is False
        assert result.error_code == "INVALID_PAN"

    def test_lowercase_pan_normalized_and_accepted(self):
        assert validate_pan("aaapa1234a").is_valid is True


class TestTANValidation:
    def test_valid_tan_accepted(self):
        assert validate_tan("MUMA12345B").is_valid is True

    def test_wrong_length_rejected(self):
        result = validate_tan("MUMA1234")
        assert result.is_valid is False
        assert result.error_code == "INVALID_TAN_FORMAT"

    def test_bad_format_rejected(self):
        result = validate_tan("1234567890")
        assert result.is_valid is False
        assert result.error_code == "INVALID_TAN_FORMAT"

    def test_missing_tan_rejected(self):
        result = validate_tan(None)
        assert result.is_valid is False
        assert result.error_code == "INVALID_TAN"

    def test_lowercase_tan_normalized_and_accepted(self):
        assert validate_tan("muma12345b").is_valid is True


class TestSeedDefaultTDSSectionsAndRules:
    async def test_seeds_sample_sections_and_rules_idempotently(self, db_session):
        await seed_default_tds_sections_and_rules(db_session)
        await seed_default_tds_sections_and_rules(db_session)  # must not duplicate

        from sqlalchemy import select

        from app.models.tds_rule import TDSRule
        from app.models.tds_section import TDSSection

        sections = (await db_session.execute(select(TDSSection))).scalars().all()
        codes = {s.section_code for s in sections}
        assert codes == {"194C", "194H", "194I", "194J", "194Q"}

        rules = (
            (await db_session.execute(select(TDSRule).where(TDSRule.company_id.is_(None))))
            .scalars()
            .all()
        )
        assert len(rules) == 5


class TestTDSProfileAPI:
    async def test_create_and_get_tds_profile(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/tds/profile?company_id={company.id}",
            json={"tan": "MUMA12345B", "pan": "AAAPA1234A", "legal_name": company.legal_name},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()["data"]
        assert body["tan"] == "MUMA12345B"
        assert body["status"] == "ACTIVE"

        get_response = await client.get(f"/api/v1/tds/profile?company_id={company.id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["data"]["pan"] == "AAAPA1234A"

    async def test_invalid_tan_rejected(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/tds/profile?company_id={company.id}",
            json={"tan": "NOTATAN123", "pan": "AAAPA1234A", "legal_name": "Bad Co"},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_TAN_FORMAT"

    async def test_duplicate_profile_rejected(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        payload = {"tan": "MUMA12345B", "pan": "AAAPA1234A", "legal_name": company.legal_name}

        first = await client.post(
            f"/api/v1/tds/profile?company_id={company.id}", json=payload, headers=headers
        )
        assert first.status_code == 201

        second = await client.post(
            f"/api/v1/tds/profile?company_id={company.id}", json=payload, headers=headers
        )
        assert second.status_code == 422
        assert second.json()["error"]["code"] == "TDS_PROFILE_ALREADY_EXISTS"

    async def test_company_b_cannot_see_company_a_profile(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin

        data_a = await login(client, admin_a.email, "TestPass1!")
        await client.post(
            f"/api/v1/tds/profile?company_id={company_a.id}",
            json={"tan": "MUMA12345B", "pan": "AAAPA1234A", "legal_name": company_a.legal_name},
            headers=auth_headers(data_a["access_token"]),
        )

        data_b = await login(client, admin_b.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/tds/profile?company_id={company_b.id}",
            headers=auth_headers(data_b["access_token"]),
        )
        assert response.status_code == 404


class TestDeducteeAPI:
    async def test_create_deductee_with_valid_pan(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/tds/deductees?company_id={company.id}",
            json={"name": "Acme Contractors", "pan": "AAAPA1234A", "deductee_type": "FIRM"},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()["data"]
        assert body["pan_status"] == "AVAILABLE"

    async def test_create_deductee_without_pan_marks_not_available(
        self, client, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/tds/deductees?company_id={company.id}",
            json={"name": "No PAN Deductee"},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 201
        assert response.json()["data"]["pan_status"] == "NOT_AVAILABLE"

    async def test_invalid_pan_rejected(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/tds/deductees?company_id={company.id}",
            json={"name": "Bad PAN Deductee", "pan": "NOTAPAN"},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_PAN_FORMAT"

    async def test_accountant_can_create_deductee_auditor_cannot(
        self, client, db_session, company_a_with_admin, seeded_rbac
    ):
        from tests.conftest import add_membership

        company, _admin = company_a_with_admin
        accountant = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="acct@example.com", role_code="ACCOUNTANT"
        )
        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="aud@example.com", role_code="AUDITOR"
        )

        acct_data = await login(client, accountant.email, "TestPass1!")
        ok = await client.post(
            f"/api/v1/tds/deductees?company_id={company.id}",
            json={"name": "Accountant Made This"},
            headers=auth_headers(acct_data["access_token"]),
        )
        assert ok.status_code == 201

        aud_data = await login(client, auditor.email, "TestPass1!")
        forbidden = await client.post(
            f"/api/v1/tds/deductees?company_id={company.id}",
            json={"name": "Auditor Should Not"},
            headers=auth_headers(aud_data["access_token"]),
        )
        assert forbidden.status_code == 403

    async def test_company_b_cannot_see_company_a_deductees(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin

        data_a = await login(client, admin_a.email, "TestPass1!")
        create = await client.post(
            f"/api/v1/tds/deductees?company_id={company_a.id}",
            json={"name": "Company A Deductee"},
            headers=auth_headers(data_a["access_token"]),
        )
        deductee_id = create.json()["data"]["id"]

        data_b = await login(client, admin_b.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/tds/deductees/{deductee_id}?company_id={company_b.id}",
            headers=auth_headers(data_b["access_token"]),
        )
        assert response.status_code == 404


class TestTDSSectionAndRuleAPI:
    async def test_list_sections_returns_seeded_defaults(self, client, db_session, company_a_with_admin):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.get(
            f"/api/v1/tds/sections?company_id={company.id}",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 200
        codes = {s["section_code"] for s in response.json()["data"]}
        assert "194J" in codes

    async def test_list_rules_includes_platform_defaults(
        self, client, db_session, company_a_with_admin
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.get(
            f"/api/v1/tds/rules?company_id={company.id}",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 200
        assert len(response.json()["data"]) == 5

    async def test_create_company_specific_rule_override(
        self, client, db_session, company_a_with_admin
    ):
        await seed_default_tds_sections_and_rules(db_session)
        from sqlalchemy import select

        from app.models.tds_section import TDSSection

        section = (
            await db_session.execute(select(TDSSection).where(TDSSection.section_code == "194J"))
        ).scalar_one()

        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/tds/rules?company_id={company.id}",
            json={
                "tds_section_id": str(section.id),
                "rate": "7.5",
                "threshold_amount": "30000",
                "effective_from": "2025-04-01",
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 201, response.text
        assert Decimal(response.json()["data"]["rate"]) == Decimal("7.5")

    async def test_platform_default_rule_cannot_be_updated(
        self, client, db_session, company_a_with_admin
    ):
        await seed_default_tds_sections_and_rules(db_session)
        from sqlalchemy import select

        from app.models.tds_rule import TDSRule

        rule = (
            await db_session.execute(select(TDSRule).where(TDSRule.company_id.is_(None)))
        ).scalars().first()

        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        response = await client.patch(
            f"/api/v1/tds/rules/{rule.id}?company_id={company.id}",
            json={"rate": "99"},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "TDS_RULE_READ_ONLY"

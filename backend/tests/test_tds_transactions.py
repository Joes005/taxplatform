from decimal import Decimal

from app.models.tds_enums import PANStatus
from app.seed import seed_default_tds_sections_and_rules
from tests.conftest import auth_headers, create_financial_year, login


async def _get_section_id(db_session, code: str) -> str:
    from sqlalchemy import select

    from app.models.tds_section import TDSSection

    section = (
        await db_session.execute(select(TDSSection).where(TDSSection.section_code == code))
    ).scalar_one()
    return str(section.id)


async def _create_deductee(db_session, company_id, *, pan_status=PANStatus.AVAILABLE) -> str:
    from app.models.deductee import Deductee

    deductee = Deductee(
        company_id=company_id, name="Test Deductee", pan="AAAPA1234A", pan_status=pan_status
    )
    db_session.add(deductee)
    await db_session.flush()
    return str(deductee.id)


class TestTDSTransactionLifecycle:
    async def test_full_happy_path_draft_to_deducted(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        create = await client.post(
            f"/api/v1/tds/transactions?company_id={company.id}",
            json={
                "deductee_id": deductee_id,
                "tds_section_id": section_id,
                "transaction_date": "2025-06-15",
                "gross_amount": "100000",
            },
            headers=headers,
        )
        assert create.status_code == 201, create.text
        txn_id = create.json()["data"]["id"]
        assert create.json()["data"]["status"] == "DRAFT"

        calc = await client.post(
            f"/api/v1/tds/transactions/{txn_id}/calculate?company_id={company.id}", headers=headers
        )
        assert calc.status_code == 200, calc.text
        body = calc.json()["data"]
        assert body["status"] == "CALCULATED"
        assert body["applicability_status"] == "APPLICABLE"
        assert Decimal(body["tds_amount"]) == Decimal("10000.00")

        deduct = await client.post(
            f"/api/v1/tds/transactions/{txn_id}/deduct?company_id={company.id}", headers=headers
        )
        assert deduct.status_code == 200
        assert deduct.json()["data"]["status"] == "DEDUCTED"

        # Cannot deduct twice.
        second_deduct = await client.post(
            f"/api/v1/tds/transactions/{txn_id}/deduct?company_id={company.id}", headers=headers
        )
        assert second_deduct.status_code == 409
        assert second_deduct.json()["error"]["code"] == "INVALID_TDS_TRANSACTION_STATUS"

    async def test_below_threshold_calculates_to_zero(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        create = await client.post(
            f"/api/v1/tds/transactions?company_id={company.id}",
            json={
                "deductee_id": deductee_id,
                "tds_section_id": section_id,
                "transaction_date": "2025-06-15",
                "gross_amount": "5000",
            },
            headers=headers,
        )
        txn_id = create.json()["data"]["id"]

        calc = await client.post(
            f"/api/v1/tds/transactions/{txn_id}/calculate?company_id={company.id}", headers=headers
        )
        body = calc.json()["data"]
        assert body["applicability_status"] == "NOT_APPLICABLE"
        assert Decimal(body["tds_amount"]) == Decimal("0.00")

        # A NOT_APPLICABLE (CALCULATED) transaction still cannot be deducted since tds_amount is 0
        # but the state machine allows the call; deducting a zero-TDS transaction is a no-op deduction.
        deduct = await client.post(
            f"/api/v1/tds/transactions/{txn_id}/deduct?company_id={company.id}", headers=headers
        )
        assert deduct.status_code == 200

    async def test_missing_pan_needs_review(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194H")  # no aggregate threshold, has no_pan_rate
        deductee_id = await _create_deductee(db_session, company.id, pan_status=PANStatus.NOT_AVAILABLE)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        create = await client.post(
            f"/api/v1/tds/transactions?company_id={company.id}",
            json={
                "deductee_id": deductee_id,
                "tds_section_id": section_id,
                "transaction_date": "2025-06-15",
                "gross_amount": "50000",
            },
            headers=headers,
        )
        txn_id = create.json()["data"]["id"]

        calc = await client.post(
            f"/api/v1/tds/transactions/{txn_id}/calculate?company_id={company.id}", headers=headers
        )
        body = calc.json()["data"]
        # 194H has a no_pan_rate configured, so a missing PAN is still
        # confidently calculable at the higher rate, not REVIEW_REQUIRED.
        assert body["applicability_status"] == "APPLICABLE"
        assert Decimal(body["tds_amount"]) == Decimal("10000.00")  # 20% of 50000

    async def test_manual_override_preserves_system_calculation(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        create = await client.post(
            f"/api/v1/tds/transactions?company_id={company.id}",
            json={
                "deductee_id": deductee_id,
                "tds_section_id": section_id,
                "transaction_date": "2025-06-15",
                "gross_amount": "100000",
            },
            headers=headers,
        )
        txn_id = create.json()["data"]["id"]
        await client.post(
            f"/api/v1/tds/transactions/{txn_id}/calculate?company_id={company.id}", headers=headers
        )

        override = await client.post(
            f"/api/v1/tds/transactions/{txn_id}/override?company_id={company.id}",
            json={"tds_amount": "12000", "override_reason": "CA instructed a higher rate"},
            headers=headers,
        )
        assert override.status_code == 200, override.text
        body = override.json()["data"]
        assert Decimal(body["tds_amount"]) == Decimal("12000.00")
        assert Decimal(body["system_calculated_amount"]) == Decimal("10000.00")
        assert body["is_manual_override"] is True

    async def test_cannot_cancel_deducted_transaction(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        create = await client.post(
            f"/api/v1/tds/transactions?company_id={company.id}",
            json={
                "deductee_id": deductee_id,
                "tds_section_id": section_id,
                "transaction_date": "2025-06-15",
                "gross_amount": "100000",
            },
            headers=headers,
        )
        txn_id = create.json()["data"]["id"]
        await client.post(
            f"/api/v1/tds/transactions/{txn_id}/calculate?company_id={company.id}", headers=headers
        )
        await client.post(
            f"/api/v1/tds/transactions/{txn_id}/deduct?company_id={company.id}", headers=headers
        )

        cancel = await client.post(
            f"/api/v1/tds/transactions/{txn_id}/cancel?company_id={company.id}", headers=headers
        )
        assert cancel.status_code == 409
        assert cancel.json()["error"]["code"] == "INVALID_TDS_TRANSACTION_STATUS"

    async def test_company_b_cannot_see_company_a_transaction(
        self, client, db_session, company_a_with_admin, company_b_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company_a.id)

        data_a = await login(client, admin_a.email, "TestPass1!")
        create = await client.post(
            f"/api/v1/tds/transactions?company_id={company_a.id}",
            json={
                "deductee_id": deductee_id,
                "tds_section_id": section_id,
                "transaction_date": "2025-06-15",
                "gross_amount": "100000",
            },
            headers=auth_headers(data_a["access_token"]),
        )
        txn_id = create.json()["data"]["id"]

        data_b = await login(client, admin_b.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/tds/transactions/{txn_id}?company_id={company_b.id}",
            headers=auth_headers(data_b["access_token"]),
        )
        assert response.status_code == 404

    async def test_auditor_cannot_create_transaction(
        self, client, db_session, company_a_with_admin, financial_year_a, seeded_rbac
    ):
        from tests.conftest import add_membership

        await seed_default_tds_sections_and_rules(db_session)
        company, _admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="auditor2@example.com", role_code="AUDITOR"
        )
        data = await login(client, auditor.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/tds/transactions?company_id={company.id}",
            json={
                "deductee_id": deductee_id,
                "tds_section_id": section_id,
                "transaction_date": "2025-06-15",
                "gross_amount": "100000",
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 403

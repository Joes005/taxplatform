from app.models.tds_enums import PANStatus
from app.seed import seed_default_tds_sections_and_rules
from tests.conftest import auth_headers, login


async def _get_section_id(db_session, code: str) -> str:
    from sqlalchemy import select

    from app.models.tds_section import TDSSection

    section = (
        await db_session.execute(select(TDSSection).where(TDSSection.section_code == code))
    ).scalar_one()
    return str(section.id)


async def _create_deductee(db_session, company_id) -> str:
    from app.models.deductee import Deductee

    deductee = Deductee(company_id=company_id, name="Test Deductee", pan="AAAPA1234A", pan_status=PANStatus.AVAILABLE)
    db_session.add(deductee)
    await db_session.flush()
    return str(deductee.id)


async def _create_deducted_transaction(client, headers, company_id, section_id, deductee_id, amount="100000"):
    create = await client.post(
        f"/api/v1/tds/transactions?company_id={company_id}",
        json={
            "deductee_id": deductee_id,
            "tds_section_id": section_id,
            "transaction_date": "2025-06-15",
            "gross_amount": amount,
        },
        headers=headers,
    )
    txn_id = create.json()["data"]["id"]
    await client.post(f"/api/v1/tds/transactions/{txn_id}/calculate?company_id={company_id}", headers=headers)
    await client.post(f"/api/v1/tds/transactions/{txn_id}/deduct?company_id={company_id}", headers=headers)
    return txn_id


class TestTDSReturnPeriod:
    async def test_create_return_period_computes_quarter_dates(
        self, client, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/tds/return-periods?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "quarter": "Q1"},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()["data"]
        assert body["period_start"] == "2025-04-01"
        assert body["period_end"] == "2025-06-30"
        assert body["status"] == "OPEN"

    async def test_duplicate_quarter_rejected(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        payload = {"financial_year_id": str(financial_year_a.id), "quarter": "Q2"}

        first = await client.post(f"/api/v1/tds/return-periods?company_id={company.id}", json=payload, headers=headers)
        assert first.status_code == 201

        second = await client.post(f"/api/v1/tds/return-periods?company_id={company.id}", json=payload, headers=headers)
        assert second.status_code == 422
        assert second.json()["error"]["code"] == "TDS_RETURN_PERIOD_ALREADY_EXISTS"


class TestTDSReturnSnapshotWorkflow:
    async def test_generate_submit_approve_finalize(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_deducted_transaction(client, headers, company.id, section_id, deductee_id)

        period = await client.post(
            f"/api/v1/tds/return-periods?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "quarter": "Q1"},
            headers=headers,
        )
        period_id = period.json()["data"]["id"]

        generate = await client.post(
            f"/api/v1/tds/return-periods/{period_id}/generate?company_id={company.id}",
            json={"return_type": "FORM_26Q"},
            headers=headers,
        )
        assert generate.status_code == 201, generate.text
        body = generate.json()["data"]
        assert body["version"] == 1
        assert body["status"] == "DRAFT"
        assert body["summary_data"]["quarterly"]["tds_deducted"] == "10000.00"

        submit = await client.post(
            f"/api/v1/tds/return-periods/{period_id}/submit-for-review?company_id={company.id}",
            json={"return_type": "FORM_26Q"},
            headers=headers,
        )
        assert submit.json()["data"]["status"] == "UNDER_REVIEW"

        period_after_submit = await client.get(
            f"/api/v1/tds/return-periods/{period_id}?company_id={company.id}", headers=headers
        )
        assert period_after_submit.json()["data"]["status"] == "UNDER_REVIEW"

        approve = await client.post(
            f"/api/v1/tds/return-periods/{period_id}/approve?company_id={company.id}",
            json={"return_type": "FORM_26Q"},
            headers=headers,
        )
        assert approve.json()["data"]["status"] == "APPROVED"

        finalize = await client.post(
            f"/api/v1/tds/return-periods/{period_id}/finalize?company_id={company.id}",
            json={"return_type": "FORM_26Q"},
            headers=headers,
        )
        assert finalize.json()["data"]["status"] == "FINALIZED"

        period_after_finalize = await client.get(
            f"/api/v1/tds/return-periods/{period_id}?company_id={company.id}", headers=headers
        )
        assert period_after_finalize.json()["data"]["status"] == "FINALIZED"

        # Finalized snapshot cannot transition further.
        re_submit = await client.post(
            f"/api/v1/tds/return-periods/{period_id}/submit-for-review?company_id={company.id}",
            json={"return_type": "FORM_26Q"},
            headers=headers,
        )
        assert re_submit.status_code == 400
        assert re_submit.json()["error"]["code"] == "INVALID_TDS_SNAPSHOT_TRANSITION"

    async def test_regenerate_creates_new_version(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        period = await client.post(
            f"/api/v1/tds/return-periods?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "quarter": "Q1"},
            headers=headers,
        )
        period_id = period.json()["data"]["id"]

        first = await client.post(
            f"/api/v1/tds/return-periods/{period_id}/generate?company_id={company.id}",
            json={"return_type": "FORM_26Q"},
            headers=headers,
        )
        assert first.json()["data"]["version"] == 1

        await _create_deducted_transaction(client, headers, company.id, section_id, deductee_id)

        second = await client.post(
            f"/api/v1/tds/return-periods/{period_id}/generate?company_id={company.id}",
            json={"return_type": "FORM_26Q"},
            headers=headers,
        )
        assert second.json()["data"]["version"] == 2
        assert second.json()["data"]["summary_data"]["quarterly"]["tds_deducted"] == "10000.00"


class TestTDSReviewNotes:
    async def test_create_and_resolve_review_note(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        period = await client.post(
            f"/api/v1/tds/return-periods?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "quarter": "Q1"},
            headers=headers,
        )
        period_id = period.json()["data"]["id"]

        create = await client.post(
            f"/api/v1/tds/review-notes?company_id={company.id}",
            json={
                "return_period_id": period_id,
                "entity_type": "TDS_RETURN_PERIOD",
                "entity_id": period_id,
                "note": "Please verify deductee PAN before filing.",
            },
            headers=headers,
        )
        assert create.status_code == 201, create.text
        note_id = create.json()["data"]["id"]
        assert create.json()["data"]["status"] == "OPEN"

        listing = await client.get(
            f"/api/v1/tds/review-notes?company_id={company.id}&return_period_id={period_id}",
            headers=headers,
        )
        assert len(listing.json()["data"]) == 1

        resolve = await client.post(
            f"/api/v1/tds/review-notes/{note_id}/resolve?company_id={company.id}", headers=headers
        )
        assert resolve.json()["data"]["status"] == "RESOLVED"

        resolve_again = await client.post(
            f"/api/v1/tds/review-notes/{note_id}/resolve?company_id={company.id}", headers=headers
        )
        assert resolve_again.status_code == 409


class TestTDSReports:
    async def test_quarterly_summary_report(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await _create_deducted_transaction(client, headers, company.id, section_id, deductee_id)

        period = await client.post(
            f"/api/v1/tds/return-periods?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "quarter": "Q1"},
            headers=headers,
        )
        period_id = period.json()["data"]["id"]

        summary = await client.get(
            f"/api/v1/tds/return-periods/{period_id}/reports/summary?company_id={company.id}",
            headers=headers,
        )
        assert summary.status_code == 200, summary.text
        assert summary.json()["data"]["tds_deducted"] == "10000.00"

        sections = await client.get(
            f"/api/v1/tds/return-periods/{period_id}/reports/sections?company_id={company.id}",
            headers=headers,
        )
        assert sections.json()["data"][0]["section_code"] == "194J"

    async def test_export_quarterly_requires_tds_profile(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        period = await client.post(
            f"/api/v1/tds/return-periods?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "quarter": "Q1"},
            headers=headers,
        )
        period_id = period.json()["data"]["id"]

        export = await client.get(
            f"/api/v1/tds/return-periods/{period_id}/reports/export/quarterly?company_id={company.id}",
            headers=headers,
        )
        assert export.status_code == 422
        assert export.json()["error"]["code"] == "TDS_PROFILE_REQUIRED"

    async def test_export_quarterly_csv_succeeds_with_profile(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await _create_deducted_transaction(client, headers, company.id, section_id, deductee_id)

        await client.post(
            f"/api/v1/tds/profile?company_id={company.id}",
            json={"tan": "MUMA12345B", "pan": "AAAPA1234A", "legal_name": company.legal_name},
            headers=headers,
        )

        period = await client.post(
            f"/api/v1/tds/return-periods?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "quarter": "Q1"},
            headers=headers,
        )
        period_id = period.json()["data"]["id"]

        export = await client.get(
            f"/api/v1/tds/return-periods/{period_id}/reports/export/quarterly?company_id={company.id}&format=csv",
            headers=headers,
        )
        assert export.status_code == 200
        assert b"TDS Quarterly Preparation Report" in export.content

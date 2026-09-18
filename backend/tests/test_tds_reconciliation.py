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


class TestTDSReconciliation:
    async def test_fully_allocated_transaction_is_matched(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        txn_id = await _create_deducted_transaction(client, headers, company.id, section_id, deductee_id)

        challan = await client.post(
            f"/api/v1/tds/challans?company_id={company.id}",
            json={
                "challan_number": "CH-R1",
                "challan_date": "2025-07-07",
                "amount": "10000",
                "financial_year_id": str(financial_year_a.id),
            },
            headers=headers,
        )
        challan_id = challan.json()["data"]["id"]
        await client.post(
            f"/api/v1/tds/challans/{challan_id}/allocate?company_id={company.id}",
            json={"tds_transaction_id": txn_id, "allocated_amount": "10000"},
            headers=headers,
        )

        run = await client.post(
            f"/api/v1/tds/reconciliation/run?company_id={company.id}&financial_year_id={financial_year_a.id}",
            headers=headers,
        )
        assert run.status_code == 200, run.text
        findings = run.json()["data"]
        txn_finding = next(f for f in findings if f["tds_transaction_id"] == txn_id)
        assert txn_finding["status"] == "MATCHED"

    async def test_deducted_transaction_without_challan_is_missing_challan(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        txn_id = await _create_deducted_transaction(client, headers, company.id, section_id, deductee_id)

        run = await client.post(
            f"/api/v1/tds/reconciliation/run?company_id={company.id}&financial_year_id={financial_year_a.id}",
            headers=headers,
        )
        findings = run.json()["data"]
        txn_finding = next(f for f in findings if f["tds_transaction_id"] == txn_id)
        assert txn_finding["status"] == "MISSING_CHALLAN"

    async def test_partial_allocation_is_partially_matched(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        txn_id = await _create_deducted_transaction(client, headers, company.id, section_id, deductee_id)

        challan = await client.post(
            f"/api/v1/tds/challans?company_id={company.id}",
            json={
                "challan_number": "CH-R2",
                "challan_date": "2025-07-07",
                "amount": "10000",
                "financial_year_id": str(financial_year_a.id),
            },
            headers=headers,
        )
        challan_id = challan.json()["data"]["id"]
        await client.patch(
            f"/api/v1/tds/challans/{challan_id}?company_id={company.id}",
            json={"status": "GENERATED"},
            headers=headers,
        )
        await client.post(
            f"/api/v1/tds/challans/{challan_id}/allocate?company_id={company.id}",
            json={"tds_transaction_id": txn_id, "allocated_amount": "4000"},
            headers=headers,
        )

        run = await client.post(
            f"/api/v1/tds/reconciliation/run?company_id={company.id}&financial_year_id={financial_year_a.id}",
            headers=headers,
        )
        findings = run.json()["data"]
        txn_finding = next(f for f in findings if f["tds_transaction_id"] == txn_id)
        assert txn_finding["status"] == "PARTIALLY_MATCHED"

        # Also flags the challan itself as having an unallocated remainder.
        challan_finding = next(
            (f for f in findings if f.get("tds_challan_id") == challan_id), None
        )
        assert challan_finding is not None
        assert challan_finding["status"] == "UNALLOCATED_PAYMENT"

    async def test_rerun_clears_previous_findings(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        txn_id = await _create_deducted_transaction(client, headers, company.id, section_id, deductee_id)

        first_run = await client.post(
            f"/api/v1/tds/reconciliation/run?company_id={company.id}&financial_year_id={financial_year_a.id}",
            headers=headers,
        )
        assert len(first_run.json()["data"]) == 1

        second_run = await client.post(
            f"/api/v1/tds/reconciliation/run?company_id={company.id}&financial_year_id={financial_year_a.id}",
            headers=headers,
        )
        # Not duplicated — still exactly one finding for the one transaction.
        assert len(second_run.json()["data"]) == 1

        listing = await client.get(
            f"/api/v1/tds/reconciliation?company_id={company.id}&financial_year_id={financial_year_a.id}",
            headers=headers,
        )
        assert listing.json()["data"]["pagination"]["total"] == 1

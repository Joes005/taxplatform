from decimal import Decimal

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


class TestTDSChallanLifecycle:
    async def test_create_challan_and_allocate(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        txn_id = await _create_deducted_transaction(client, headers, company.id, section_id, deductee_id)

        create = await client.post(
            f"/api/v1/tds/challans?company_id={company.id}",
            json={
                "challan_number": "CH-001",
                "challan_date": "2025-07-07",
                "amount": "10000",
                "financial_year_id": str(financial_year_a.id),
            },
            headers=headers,
        )
        assert create.status_code == 201, create.text
        challan_id = create.json()["data"]["id"]
        assert create.json()["data"]["status"] == "DRAFT"
        assert Decimal(create.json()["data"]["unallocated_amount"]) == Decimal("10000.00")

        allocate = await client.post(
            f"/api/v1/tds/challans/{challan_id}/allocate?company_id={company.id}",
            json={"tds_transaction_id": txn_id, "allocated_amount": "10000"},
            headers=headers,
        )
        assert allocate.status_code == 200, allocate.text

        get_challan = await client.get(
            f"/api/v1/tds/challans/{challan_id}?company_id={company.id}", headers=headers
        )
        body = get_challan.json()["data"]
        assert Decimal(body["allocated_amount"]) == Decimal("10000.00")
        assert Decimal(body["unallocated_amount"]) == Decimal("0.00")

    async def test_over_allocation_beyond_challan_amount_rejected(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        txn_id = await _create_deducted_transaction(client, headers, company.id, section_id, deductee_id)

        create = await client.post(
            f"/api/v1/tds/challans?company_id={company.id}",
            json={
                "challan_number": "CH-002",
                "challan_date": "2025-07-07",
                "amount": "5000",
                "financial_year_id": str(financial_year_a.id),
            },
            headers=headers,
        )
        challan_id = create.json()["data"]["id"]

        allocate = await client.post(
            f"/api/v1/tds/challans/{challan_id}/allocate?company_id={company.id}",
            json={"tds_transaction_id": txn_id, "allocated_amount": "10000"},
            headers=headers,
        )
        assert allocate.status_code == 422
        assert allocate.json()["error"]["code"] == "CHALLAN_OVER_ALLOCATION"

    async def test_over_allocation_beyond_transaction_tds_rejected(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        txn_id = await _create_deducted_transaction(client, headers, company.id, section_id, deductee_id)

        create = await client.post(
            f"/api/v1/tds/challans?company_id={company.id}",
            json={
                "challan_number": "CH-003",
                "challan_date": "2025-07-07",
                "amount": "50000",
                "financial_year_id": str(financial_year_a.id),
            },
            headers=headers,
        )
        challan_id = create.json()["data"]["id"]

        allocate = await client.post(
            f"/api/v1/tds/challans/{challan_id}/allocate?company_id={company.id}",
            json={"tds_transaction_id": txn_id, "allocated_amount": "20000"},
            headers=headers,
        )
        assert allocate.status_code == 422
        assert allocate.json()["error"]["code"] == "TRANSACTION_OVER_ALLOCATION"

    async def test_allocation_against_paid_challan_marks_transaction_paid(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        section_id = await _get_section_id(db_session, "194J")
        deductee_id = await _create_deductee(db_session, company.id)

        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        txn_id = await _create_deducted_transaction(client, headers, company.id, section_id, deductee_id)

        create = await client.post(
            f"/api/v1/tds/challans?company_id={company.id}",
            json={
                "challan_number": "CH-004",
                "challan_date": "2025-07-07",
                "amount": "10000",
                "financial_year_id": str(financial_year_a.id),
            },
            headers=headers,
        )
        challan_id = create.json()["data"]["id"]

        await client.patch(
            f"/api/v1/tds/challans/{challan_id}?company_id={company.id}",
            json={"status": "GENERATED"},
            headers=headers,
        )
        await client.patch(
            f"/api/v1/tds/challans/{challan_id}?company_id={company.id}",
            json={"status": "PAID"},
            headers=headers,
        )

        await client.post(
            f"/api/v1/tds/challans/{challan_id}/allocate?company_id={company.id}",
            json={"tds_transaction_id": txn_id, "allocated_amount": "10000"},
            headers=headers,
        )

        txn = await client.get(
            f"/api/v1/tds/transactions/{txn_id}?company_id={company.id}", headers=headers
        )
        assert txn.json()["data"]["status"] == "PAID"

    async def test_invalid_status_transition_rejected(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        create = await client.post(
            f"/api/v1/tds/challans?company_id={company.id}",
            json={
                "challan_number": "CH-005",
                "challan_date": "2025-07-07",
                "amount": "10000",
                "financial_year_id": str(financial_year_a.id),
            },
            headers=headers,
        )
        challan_id = create.json()["data"]["id"]

        response = await client.patch(
            f"/api/v1/tds/challans/{challan_id}?company_id={company.id}",
            json={"status": "PAID"},  # DRAFT -> PAID is not allowed, must pass through GENERATED
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVALID_TDS_CHALLAN_STATUS_TRANSITION"

    async def test_company_b_cannot_see_company_a_challan(
        self, client, db_session, company_a_with_admin, company_b_with_admin, financial_year_a
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin

        data_a = await login(client, admin_a.email, "TestPass1!")
        create = await client.post(
            f"/api/v1/tds/challans?company_id={company_a.id}",
            json={
                "challan_number": "CH-006",
                "challan_date": "2025-07-07",
                "amount": "10000",
                "financial_year_id": str(financial_year_a.id),
            },
            headers=auth_headers(data_a["access_token"]),
        )
        challan_id = create.json()["data"]["id"]

        data_b = await login(client, admin_b.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/tds/challans/{challan_id}?company_id={company_b.id}",
            headers=auth_headers(data_b["access_token"]),
        )
        assert response.status_code == 404

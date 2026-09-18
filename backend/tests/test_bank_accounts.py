from tests.conftest import auth_headers, login


class TestBankAccountAPI:
    async def test_create_and_get_bank_account(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/bank/accounts?company_id={company.id}",
            json={
                "bank_name": "HDFC Bank",
                "account_name": "HDFC Current Account",
                "account_number_masked": "XXXXXX1234",
                "account_type": "CURRENT",
                "opening_balance": "100000",
                "opening_balance_date": "2025-04-01",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()["data"]
        assert body["account_number_masked"] == "XXXXXX1234"
        assert body["is_active"] is True

        get_response = await client.get(
            f"/api/v1/bank/accounts/{body['id']}?company_id={company.id}", headers=headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["data"]["bank_name"] == "HDFC Bank"

    async def test_duplicate_masked_number_rejected(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        payload = {
            "bank_name": "HDFC Bank",
            "account_name": "HDFC Current Account",
            "account_number_masked": "XXXXXX5678",
            "opening_balance": "0",
            "opening_balance_date": "2025-04-01",
        }

        first = await client.post(
            f"/api/v1/bank/accounts?company_id={company.id}", json=payload, headers=headers
        )
        assert first.status_code == 201

        second = await client.post(
            f"/api/v1/bank/accounts?company_id={company.id}", json=payload, headers=headers
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "DUPLICATE_RESOURCE"

    async def test_invalid_ledger_rejected(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/bank/accounts?company_id={company.id}",
            json={
                "bank_name": "HDFC Bank",
                "account_name": "HDFC Current Account",
                "account_number_masked": "XXXXXX9999",
                "opening_balance": "0",
                "opening_balance_date": "2025-04-01",
                "ledger_id": "00000000-0000-0000-0000-000000000000",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_LEDGER"

    async def test_company_b_cannot_see_company_a_account(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin

        data_a = await login(client, admin_a.email, "TestPass1!")
        create = await client.post(
            f"/api/v1/bank/accounts?company_id={company_a.id}",
            json={
                "bank_name": "HDFC Bank",
                "account_name": "HDFC Current Account",
                "account_number_masked": "XXXXXX1111",
                "opening_balance": "0",
                "opening_balance_date": "2025-04-01",
            },
            headers=auth_headers(data_a["access_token"]),
        )
        account_id = create.json()["data"]["id"]

        data_b = await login(client, admin_b.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/bank/accounts/{account_id}?company_id={company_b.id}",
            headers=auth_headers(data_b["access_token"]),
        )
        assert response.status_code == 404

    async def test_auditor_cannot_create_account(
        self, client, db_session, company_a_with_admin, seeded_rbac
    ):
        from tests.conftest import add_membership

        company, _admin = company_a_with_admin
        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="bank-auditor@example.com", role_code="AUDITOR"
        )
        data = await login(client, auditor.email, "TestPass1!")

        response = await client.post(
            f"/api/v1/bank/accounts?company_id={company.id}",
            json={
                "bank_name": "HDFC Bank",
                "account_name": "HDFC Current Account",
                "account_number_masked": "XXXXXX2222",
                "opening_balance": "0",
                "opening_balance_date": "2025-04-01",
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 403

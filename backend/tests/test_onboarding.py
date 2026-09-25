import uuid
import pytest
from tests.conftest import auth_headers, login


class TestOnboardingFlow:
    async def test_fresh_user_can_onboard_first_company(self, client, db_session, seeded_rbac):
        # 1. Register a brand new user
        reg_payload = {
            "first_name": "Rajesh",
            "last_name": "Kumar",
            "email": "rajesh.kumar@example.com",
            "password": "Password123!",
        }
        reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert reg_res.status_code == 201, reg_res.text

        # 2. Login as the fresh user
        auth_data = await login(client, "rajesh.kumar@example.com", "Password123!")
        access_token = auth_data["access_token"]
        assert auth_data["companies"] == []
        assert auth_data["active_company"] is None

        # 3. Call self-service onboarding: POST /api/v1/companies/onboard
        onboard_payload = {
            "legal_name": "Kumar Enterprises Pvt Ltd",
            "trade_name": "Kumar Tech",
            "business_type": "PRIVATE_LIMITED",
            "pan": "ABCDE1234F",
            "gstin": "27ABCDE1234F1Z5",
            "state": "Maharashtra",
            "city": "Mumbai",
        }
        res = await client.post(
            "/api/v1/companies/onboard",
            json=onboard_payload,
            headers=auth_headers(access_token),
        )
        assert res.status_code == 201, res.text
        company = res.json()["data"]
        company_id = company["id"]
        assert company["legal_name"] == "Kumar Enterprises Pvt Ltd"
        assert company["is_active"] is True

        # 4. Verify membership was created and creator can select newly created company
        select_res = await client.post(
            "/api/v1/auth/select-company",
            json={"company_id": company_id},
            headers=auth_headers(access_token),
        )
        assert select_res.status_code == 200, select_res.text
        selected_data = select_res.json()["data"]
        assert selected_data["company_id"] == company_id
        assert selected_data["role_code"] == "COMPANY_ADMIN"
        assert len(selected_data["permissions"]) > 0

        # 5. Verify default Financial Year was automatically initialized
        fy_res = await client.get(
            f"/api/v1/accounting/financial-years?company_id={company_id}",
            headers=auth_headers(access_token),
        )
        assert fy_res.status_code == 200, fy_res.text
        fy_items = fy_res.json()["data"]["items"]
        assert len(fy_items) >= 1
        assert fy_items[0]["is_current"] is True

        # 6. Verify default Core Ledgers (Chart of Accounts) were seeded
        ledgers_res = await client.get(
            f"/api/v1/accounting/ledgers?company_id={company_id}",
            headers=auth_headers(access_token),
        )
        assert ledgers_res.status_code == 200, ledgers_res.text
        ledger_items = ledgers_res.json()["data"]["items"]
        ledger_names = {l["name"] for l in ledger_items}
        expected_core = {
            "Cash",
            "Bank Account",
            "Accounts Receivable",
            "Accounts Payable",
            "Sales Account",
            "Purchase Account",
            "Round Off",
            "Input CGST",
            "Input SGST",
            "Input IGST",
            "Output CGST",
            "Output SGST",
            "Output IGST",
        }
        for name in expected_core:
            assert name in ledger_names, f"Missing default core ledger: {name}"

    async def test_super_admin_can_select_any_active_company(self, client, super_admin, company_a_with_admin):
        company, _admin = company_a_with_admin
        sa_data = await login(client, super_admin.email, "SuperSecret1!")
        sa_token = sa_data["access_token"]

        # Super admin selects company A even without an explicit membership row
        select_res = await client.post(
            "/api/v1/auth/select-company",
            json={"company_id": str(company.id)},
            headers=auth_headers(sa_token),
        )
        assert select_res.status_code == 200, select_res.text
        selected = select_res.json()["data"]
        assert selected["company_id"] == str(company.id)
        assert selected["role_code"] == "SUPER_ADMIN"

    async def test_tenant_isolation_unauthorized_company_selection(self, client, company_a_with_admin, company_b_with_admin):
        _comp_a, admin_a = company_a_with_admin
        comp_b, _admin_b = company_b_with_admin

        user_a_data = await login(client, admin_a.email, "TestPass1!")
        token_a = user_a_data["access_token"]

        # User A attempts to select Company B
        res = await client.post(
            "/api/v1/auth/select-company",
            json={"company_id": str(comp_b.id)},
            headers=auth_headers(token_a),
        )
        assert res.status_code == 403, res.text

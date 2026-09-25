import uuid
import pytest
from datetime import date, timedelta
from tests.conftest import auth_headers, login


class TestPhase10WorkflowIntelligence:
    async def test_dashboard_apis_and_setup_progress(self, client, db_session, seeded_rbac):
        # 1. Register and login
        reg_payload = {
            "first_name": "Siddharth",
            "last_name": "Mehta",
            "email": "siddharth@example.com",
            "password": "Password123!",
        }
        res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code == 201

        auth = await login(client, "siddharth@example.com", "Password123!")
        token = auth["access_token"]

        # 2. Onboard company
        onboard_payload = {
            "legal_name": "Mehta Infotech Solutions Pvt Ltd",
            "trade_name": "Mehta Info",
            "business_type": "PRIVATE_LIMITED",
            "pan": "ABCDE1234F",
            "gstin": "27ABCDE1234F1Z5",
            "state": "Maharashtra",
            "city": "Pune",
        }
        res = await client.post("/api/v1/companies/onboard", json=onboard_payload, headers=auth_headers(token))
        assert res.status_code == 201
        company_id = res.json()["data"]["id"]

        # Select company
        await client.post("/api/v1/auth/select-company", json={"company_id": company_id}, headers=auth_headers(token))

        # 3. GET /api/v1/dashboard/summary
        res = await client.get(f"/api/v1/dashboard/summary?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        summary = res.json()["data"]
        assert summary["company_id"] == company_id
        assert summary["company_name"] == "Mehta Infotech Solutions Pvt Ltd"
        assert summary["financial_year"] is not None
        assert "attention" in summary
        assert "critical_count" in summary["attention"]
        assert "high_priority_count" in summary["attention"]
        assert "due_soon_count" in summary["attention"]
        assert "pending_review_count" in summary["attention"]
        assert "overdue_count" in summary["attention"]
        assert "completed_count" in summary["attention"]

        # 4. GET /api/v1/dashboard/setup-progress
        res = await client.get(f"/api/v1/dashboard/setup-progress?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        setup = res.json()["data"]
        assert setup["total_count"] == 8
        assert setup["completed_count"] >= 3  # Company profile, FY, and 13 CoA ledgers are auto-seeded
        step_keys = [s["key"] for s in setup["steps"]]
        assert "COMPANY_PROFILE" in step_keys
        assert "FINANCIAL_YEAR" in step_keys
        assert "CHART_OF_ACCOUNTS" in step_keys
        assert "GST_PROFILE" in step_keys
        assert "TDS_PROFILE" in step_keys
        assert "BANK_ACCOUNT" in step_keys

        # 5. GET /api/v1/dashboard/workflow
        res = await client.get(f"/api/v1/dashboard/workflow?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        stages = res.json()["data"]
        assert len(stages) == 8
        stage_keys = [s["stage_key"] for s in stages]
        assert stage_keys == [
            "DATA_INPUT",
            "ACCOUNTING",
            "GST_TDS",
            "BANK",
            "INCOME_TAX",
            "AUDIT",
            "COMPLIANCE",
            "REPORTING",
        ]
        for s in stages:
            assert s["status"] in ("COMPLETE", "IN_PROGRESS", "BLOCKED", "NOT_STARTED")
            assert s["next_action_url"] is not None

        # 6. GET /api/v1/dashboard/health
        res = await client.get(f"/api/v1/dashboard/health?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        health = res.json()["data"]
        assert health["overall_status"] in ("READY", "NEEDS_ATTENTION", "BLOCKED", "NOT_CONFIGURED")
        assert len(health["areas"]) == 7
        area_names = [a["area"] for a in health["areas"]]
        assert "Accounting" in area_names
        assert "GST" in area_names
        assert "TDS" in area_names
        assert "Bank" in area_names
        assert "IncomeTax" in area_names
        assert "Audit" in area_names
        assert "Compliance" in area_names

        # 7. GET /api/v1/dashboard/actions
        res = await client.get(f"/api/v1/dashboard/actions?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        actions = res.json()["data"]
        assert isinstance(actions, list)

    async def test_action_center_filtering_and_pagination(self, client, db_session, seeded_rbac):
        # Register user and company
        reg = await client.post("/api/v1/auth/register", json={
            "first_name": "Arun", "last_name": "Verma", "email": "arun.verma@example.com", "password": "Password123!"
        })
        auth = await login(client, "arun.verma@example.com", "Password123!")
        token = auth["access_token"]

        res = await client.post("/api/v1/companies/onboard", json={
            "legal_name": "Verma Logistics Ltd", "pan": "ABCDE5678G", "state": "Delhi", "city": "Delhi"
        }, headers=auth_headers(token))
        company_id = res.json()["data"]["id"]

        # Create a compliance obligation and task to populate Action Center
        ob_res = await client.post(f"/api/v1/compliance/obligations?company_id={company_id}", json={
            "code": "GSTR1-DELHI",
            "name": "Delhi GSTR-1 Monthly Return",
            "category": "GST",
            "module": "GST",
            "frequency": "MONTHLY",
            "start_date": "2026-04-01",
            "due_date": str(date.today() - timedelta(days=2)),  # Overdue!
            "priority": "HIGH",
        }, headers=auth_headers(token))
        assert ob_res.status_code == 201
        ob_id = ob_res.json()["data"]["id"]

        task_res = await client.post(f"/api/v1/compliance/tasks?company_id={company_id}", json={
            "obligation_id": ob_id,
            "title": "File Overdue GSTR-1 Return",
            "category": "GST",
            "module": "GST",
            "due_date": str(date.today() - timedelta(days=2)),
        }, headers=auth_headers(token))
        assert task_res.status_code == 201

        # Test Action Center list
        res = await client.get(f"/api/v1/action-center?company_id={company_id}&page=1&page_size=10", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        data = res.json()["data"]
        assert data["pagination"]["total"] >= 1
        items = data["items"]
        assert any("GSTR-1" in item["title"] for item in items)

        # Test filtering by module
        res = await client.get(f"/api/v1/action-center?company_id={company_id}&module=COMPLIANCE", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        for item in res.json()["data"]["items"]:
            assert item["module"] == "COMPLIANCE"

        # Test filtering by severity
        res = await client.get(f"/api/v1/action-center?company_id={company_id}&severity=CRITICAL", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        for item in res.json()["data"]["items"]:
            assert item["severity"] == "CRITICAL"

    async def test_global_search_across_entities(self, client, db_session, seeded_rbac):
        # Register user and company
        await client.post("/api/v1/auth/register", json={
            "first_name": "Kavita", "last_name": "Rao", "email": "kavita.rao@example.com", "password": "Password123!"
        })
        auth = await login(client, "kavita.rao@example.com", "Password123!")
        token = auth["access_token"]

        res = await client.post("/api/v1/companies/onboard", json={
            "legal_name": "Kavita Technologies Pvt Ltd", "pan": "ABCDE9999K", "state": "Karnataka", "city": "Bengaluru"
        }, headers=auth_headers(token))
        company_id = res.json()["data"]["id"]

        # Create a customer and vendor with distinctive names
        cust_res = await client.post(f"/api/v1/accounting/customers?company_id={company_id}", json={
            "name": "Acme Aerospace Corp",
            "gstin": "29AABCA1234A1Z5",
            "pan": "AABCA1234A",
            "state": "Karnataka",
        }, headers=auth_headers(token))
        assert cust_res.status_code == 201

        vend_res = await client.post(f"/api/v1/accounting/vendors?company_id={company_id}", json={
            "name": "Apex Cloud Systems",
            "gstin": "29AABCV5678B1Z9",
            "pan": "AABCV5678B",
            "state": "Karnataka",
        }, headers=auth_headers(token))
        assert vend_res.status_code == 201

        # Search for "Aerospace"
        res = await client.get(f"/api/v1/search?company_id={company_id}&q=Aerospace", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        results = res.json()["data"]
        assert results["total"] >= 1
        assert any(r["type"] == "CUSTOMER" and "Acme Aerospace" in r["title"] for r in results["items"])

        # Search for "Apex"
        res = await client.get(f"/api/v1/search?company_id={company_id}&q=Apex", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        results = res.json()["data"]
        assert results["total"] >= 1
        assert any(r["type"] == "VENDOR" and "Apex Cloud" in r["title"] for r in results["items"])

        # Search with type filter
        res = await client.get(f"/api/v1/search?company_id={company_id}&q=A&type=CUSTOMER", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        for item in res.json()["data"]["items"]:
            assert item["type"] == "CUSTOMER"

    async def test_dashboard_and_search_tenant_isolation(self, client, db_session, seeded_rbac):
        # Register User A and Company A
        await client.post("/api/v1/auth/register", json={
            "first_name": "User", "last_name": "A", "email": "user.a@example.com", "password": "Password123!"
        })
        auth_a = await login(client, "user.a@example.com", "Password123!")
        token_a = auth_a["access_token"]
        res_a = await client.post("/api/v1/companies/onboard", json={
            "legal_name": "Company Alpha", "pan": "AAAAA1111A", "state": "Goa"
        }, headers=auth_headers(token_a))
        comp_a_id = res_a.json()["data"]["id"]

        # Register User B and Company B
        await client.post("/api/v1/auth/register", json={
            "first_name": "User", "last_name": "B", "email": "user.b@example.com", "password": "Password123!"
        })
        auth_b = await login(client, "user.b@example.com", "Password123!")
        token_b = auth_b["access_token"]
        res_b = await client.post("/api/v1/companies/onboard", json={
            "legal_name": "Company Beta", "pan": "BBBBB2222B", "state": "Gujarat"
        }, headers=auth_headers(token_b))
        comp_b_id = res_b.json()["data"]["id"]

        # User A attempts to access Company B's Dashboard Summary -> 403 Forbidden!
        res = await client.get(f"/api/v1/dashboard/summary?company_id={comp_b_id}", headers=auth_headers(token_a))
        assert res.status_code == 403, res.text

        # User A attempts to access Company B's Action Center -> 403 Forbidden!
        res = await client.get(f"/api/v1/action-center?company_id={comp_b_id}", headers=auth_headers(token_a))
        assert res.status_code == 403, res.text

        # User A attempts to search Company B -> 403 Forbidden!
        res = await client.get(f"/api/v1/search?company_id={comp_b_id}&q=Alpha", headers=auth_headers(token_a))
        assert res.status_code == 403, res.text

        # User B cannot access Company A -> 403 Forbidden!
        res = await client.get(f"/api/v1/dashboard/workflow?company_id={comp_a_id}", headers=auth_headers(token_b))
        assert res.status_code == 403, res.text

    async def test_setup_progress_advances_dynamically(self, client, db_session, seeded_rbac):
        # Register user and company
        await client.post("/api/v1/auth/register", json={
            "first_name": "Deepak", "last_name": "Shah", "email": "deepak.shah@example.com", "password": "Password123!"
        })
        auth = await login(client, "deepak.shah@example.com", "Password123!")
        token = auth["access_token"]

        res = await client.post("/api/v1/companies/onboard", json={
            "legal_name": "Shah Exports Pvt Ltd", "pan": "ABCDE7777S", "state": "Gujarat", "city": "Surat"
        }, headers=auth_headers(token))
        company_id = res.json()["data"]["id"]

        # Initial setup progress
        res = await client.get(f"/api/v1/dashboard/setup-progress?company_id={company_id}", headers=auth_headers(token))
        initial_completed = res.json()["data"]["completed_count"]

        # Configure GST Profile
        gst_res = await client.post(f"/api/v1/gst/profile?company_id={company_id}", json={
            "gstin": "27AAPFU0939F1ZV",
            "legal_name": "Shah Exports Pvt Ltd",
            "registration_type": "REGULAR",
        }, headers=auth_headers(token))
        assert gst_res.status_code == 201, gst_res.text

        # Check progress incremented!
        res = await client.get(f"/api/v1/dashboard/setup-progress?company_id={company_id}", headers=auth_headers(token))
        updated_completed = res.json()["data"]["completed_count"]
        assert updated_completed == initial_completed + 1
        gst_step = next(s for s in res.json()["data"]["steps"] if s["key"] == "GST_PROFILE")
        assert gst_step["completed"] is True


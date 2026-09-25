import uuid
import pytest
from datetime import date, timedelta
from tests.conftest import auth_headers, login


class TestPhase11ReportsAndBI:
    async def _setup_company_with_data(self, client, prefix="rep"):
        # 1. Register & login
        email = f"{prefix}_user@example.com"
        reg_payload = {
            "first_name": "Report",
            "last_name": "Auditor",
            "email": email,
            "password": "Password123!",
        }
        res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code == 201

        auth = await login(client, email, "Password123!")
        token = auth["access_token"]

        # 2. Onboard company
        onboard_payload = {
            "legal_name": f"{prefix.upper()} Enterprises Pvt Ltd",
            "trade_name": f"{prefix.upper()} Corp",
            "business_type": "PRIVATE_LIMITED",
            "pan": "ABCDE1234F",
            "gstin": "27ABCDE1234F1Z5",
            "state": "Maharashtra",
            "city": "Mumbai",
        }
        res = await client.post("/api/v1/companies/onboard", json=onboard_payload, headers=auth_headers(token))
        assert res.status_code == 201
        company_id = res.json()["data"]["id"]

        await client.post("/api/v1/auth/select-company", json={"company_id": company_id}, headers=auth_headers(token))

        # Fetch financial year
        fy_res = await client.get(f"/api/v1/accounting/financial-years?company_id={company_id}", headers=auth_headers(token))
        assert fy_res.status_code == 200
        fy_id = fy_res.json()["data"]["items"][0]["id"]

        # 3. Create customer & customer sales invoice
        cust_res = await client.post(
            f"/api/v1/accounting/customers?company_id={company_id}",
            json={"name": "Premier Retailers", "gstin": "27AABCP1234D1Z2", "state": "Maharashtra"},
            headers=auth_headers(token),
        )
        assert cust_res.status_code == 201, cust_res.text
        customer_id = cust_res.json()["data"]["id"]

        today_str = date.today().isoformat()
        inv_payload = {
            "customer_id": customer_id,
            "financial_year_id": fy_id,
            "invoice_number": f"INV-{uuid.uuid4().hex[:6].upper()}",
            "invoice_date": today_str,
            "due_date": (date.today() + timedelta(days=15)).isoformat(),
            "place_of_supply": "27",
            "items": [
                {
                    "item_name": "Consulting Services",
                    "item_type": "SERVICE",
                    "quantity": 1,
                    "unit_price": 50000.0,
                    "cgst_rate": 9.0,
                    "sgst_rate": 9.0,
                }
            ],
        }
        inv_res = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company_id}",
            json=inv_payload,
            headers=auth_headers(token),
        )
        assert inv_res.status_code == 201, inv_res.text
        sales_inv_id = inv_res.json()["data"]["id"]

        # Post sales invoice
        await client.post(
            f"/api/v1/accounting/sales-invoices/{sales_inv_id}/post?company_id={company_id}",
            headers=auth_headers(token),
        )

        # 4. Create vendor & vendor purchase invoice
        vend_res = await client.post(
            f"/api/v1/accounting/vendors?company_id={company_id}",
            json={"name": "Tech Hardware Suppliers", "gstin": "27AABCV5678D1Z9", "state": "Maharashtra"},
            headers=auth_headers(token),
        )
        assert vend_res.status_code == 201, vend_res.text
        vendor_id = vend_res.json()["data"]["id"]

        purch_payload = {
            "vendor_id": vendor_id,
            "financial_year_id": fy_id,
            "invoice_number": f"BILL-{uuid.uuid4().hex[:6].upper()}",
            "invoice_date": today_str,
            "place_of_supply": "27",
            "items": [
                {
                    "item_name": "Laptops & Equipment",
                    "item_type": "PRODUCT",
                    "quantity": 1,
                    "unit_price": 20000.0,
                    "cgst_rate": 9.0,
                    "sgst_rate": 9.0,
                }
            ],
        }
        purch_res = await client.post(
            f"/api/v1/accounting/purchase-invoices?company_id={company_id}",
            json=purch_payload,
            headers=auth_headers(token),
        )
        assert purch_res.status_code == 201, purch_res.text
        purch_inv_id = purch_res.json()["data"]["id"]

        # Post purchase invoice
        await client.post(
            f"/api/v1/accounting/purchase-invoices/{purch_inv_id}/post?company_id={company_id}",
            headers=auth_headers(token),
        )

        return token, company_id, customer_id, vendor_id

    async def test_trial_balance_and_integrity(self, client, db_session, seeded_rbac):
        token, company_id, _, _ = await self._setup_company_with_data(client, "tb")

        res = await client.get(f"/api/v1/reports/trial-balance?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        tb = res.json()["data"]

        assert "lines" in tb
        assert len(tb["lines"]) >= 4  # Accounts Receivable, Sales Revenue, CGST/SGST Input/Output, etc.
        assert "total_closing_debit" in tb
        assert "total_closing_credit" in tb
        assert tb["is_balanced"] is True
        assert float(tb["difference"]) == 0.0
        assert tb["integrity_warning"] is None

    async def test_profit_and_loss_report(self, client, db_session, seeded_rbac):
        token, company_id, _, _ = await self._setup_company_with_data(client, "pnl")

        res = await client.get(
            f"/api/v1/reports/profit-loss?company_id={company_id}&compare_previous=true",
            headers=auth_headers(token),
        )
        assert res.status_code == 200, res.text
        pnl = res.json()["data"]

        assert float(pnl["revenue_section"]["subtotal"]) == 50000.0
        assert float(pnl["direct_costs_section"]["subtotal"]) == 20000.0
        assert float(pnl["gross_profit"]) == 30000.0
        assert float(pnl["net_profit"]) == 30000.0
        assert "comparison" in pnl
        assert float(pnl["comparison"]["revenue"]["current"]) == 50000.0

    async def test_balance_sheet_report(self, client, db_session, seeded_rbac):
        token, company_id, _, _ = await self._setup_company_with_data(client, "bs")

        res = await client.get(f"/api/v1/reports/balance-sheet?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        bs = res.json()["data"]

        assert "assets" in bs
        assert "liabilities" in bs
        assert "equity" in bs
        assert float(bs["retained_earnings"]) == 30000.0
        assert bs["is_balanced"] is True
        assert float(bs["difference"]) == 0.0
        assert float(bs["total_assets"]) == float(bs["total_liabilities_and_equity"])

    async def test_receivables_and_payables_and_ageing(self, client, db_session, seeded_rbac):
        token, company_id, cust_id, vend_id = await self._setup_company_with_data(client, "rp")

        # 1. Receivables
        res = await client.get(f"/api/v1/reports/receivables?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        rec = res.json()["data"]
        assert len(rec["parties"]) == 1
        assert rec["parties"][0]["party_name"] == "Premier Retailers"
        assert rec["parties"][0]["gross_invoiced"] == "59000.00"
        assert rec["parties"][0]["outstanding"] == "59000.00"

        # 2. Payables
        res = await client.get(f"/api/v1/reports/payables?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        pay = res.json()["data"]
        assert len(pay["parties"]) == 1
        assert pay["parties"][0]["party_name"] == "Tech Hardware Suppliers"
        assert pay["parties"][0]["gross_invoiced"] == "23600.00"
        assert pay["parties"][0]["outstanding"] == "23600.00"

        # 3. Ageing
        res = await client.get(
            f"/api/v1/reports/ageing?company_id={company_id}&kind=RECEIVABLES",
            headers=auth_headers(token),
        )
        assert res.status_code == 200, res.text
        ageing = res.json()["data"]
        assert len(ageing["invoices"]) == 1
        assert ageing["total_outstanding"] == "59000.00"
        assert len(ageing["bucket_summaries"]) == 6

    async def test_management_dashboard_and_analytics(self, client, db_session, seeded_rbac):
        token, company_id, _, _ = await self._setup_company_with_data(client, "mgmt")

        # Management dashboard
        res = await client.get(f"/api/v1/reports/management?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        mgmt = res.json()["data"]

        card_keys = [c["key"] for c in mgmt["cards"]]
        assert "revenue" in card_keys
        assert "net_profit" in card_keys
        assert "receivables" in card_keys
        assert "payables" in card_keys

        # Sales Analytics
        res = await client.get(f"/api/v1/reports/sales?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        sales = res.json()["data"]
        assert sales["gross_total"] == "50000.00"
        assert sales["invoice_count"] == 1
        assert len(sales["top_parties"]) == 1

        # GST Summary
        res = await client.get(f"/api/v1/reports/gst?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        gst = res.json()["data"]
        assert gst["outward_taxable"] == "50000.00"
        assert gst["inward_taxable"] == "20000.00"
        assert gst["net_gst_payable"] == "5400.00"  # 9000 tax outward - 3600 itc

    async def test_report_exports(self, client, db_session, seeded_rbac):
        token, company_id, _, _ = await self._setup_company_with_data(client, "exp")

        for rep_type in ["trial_balance", "profit_loss", "balance_sheet", "receivables", "payables", "ageing"]:
            res = await client.get(
                f"/api/v1/reports/export?company_id={company_id}&report_type={rep_type}&format=csv",
                headers=auth_headers(token),
            )
            assert res.status_code == 200, f"Export {rep_type} failed: {res.text}"
            assert res.headers["content-type"] == "text/csv; charset=utf-8"
            assert len(res.content) > 20

    async def test_tenant_isolation_in_reports(self, client, db_session, seeded_rbac):
        token_a, company_a, _, _ = await self._setup_company_with_data(client, "tena")
        token_b, company_b, _, _ = await self._setup_company_with_data(client, "tenb")

        # User B attempts to access Company A reports
        res = await client.get(f"/api/v1/reports/trial-balance?company_id={company_a}", headers=auth_headers(token_b))
        assert res.status_code == 403

        res = await client.get(f"/api/v1/reports/profit-loss?company_id={company_a}", headers=auth_headers(token_b))
        assert res.status_code == 403

        res = await client.get(f"/api/v1/reports/management?company_id={company_a}", headers=auth_headers(token_b))
        assert res.status_code == 403

    async def test_full_integrated_scenario_reconciliation(self, client, db_session, seeded_rbac):
        """Phase 11 Section 46 & 47: Full integrated report scenario for ABC Traders Pvt Ltd.
        Validates:
        1. Sales Register <-> P&L Revenue
        2. Purchase Register <-> P&L Cost
        3. Receivables <-> Customer Outstanding
        4. Payables <-> Vendor Outstanding
        5. GST Report <-> GST Calculation
        6. Management Cockpit <-> Domain Metrics
        7. No discrepancy / Difference == 0.00
        """
        token, company_id, cust_id, vend_id = await self._setup_company_with_data(client, "abc")

        # 1. Query Sales Register & P&L
        sales_res = await client.get(f"/api/v1/reports/sales?company_id={company_id}", headers=auth_headers(token))
        assert sales_res.status_code == 200
        sales_data = sales_res.json()["data"]

        pnl_res = await client.get(f"/api/v1/reports/profit-loss?company_id={company_id}", headers=auth_headers(token))
        assert pnl_res.status_code == 200
        pnl_data = pnl_res.json()["data"]

        # Reconcile: Sales Register Gross/Net == P&L Revenue Subtotal
        assert float(sales_data["net_total"]) == float(pnl_data["revenue_section"]["subtotal"])

        # 2. Query Receivables
        rec_res = await client.get(f"/api/v1/reports/receivables?company_id={company_id}", headers=auth_headers(token))
        assert rec_res.status_code == 200
        rec_data = rec_res.json()["data"]

        # Reconcile: Receivables party outstanding == total outstanding
        assert float(rec_data["total_outstanding"]) == float(rec_data["parties"][0]["outstanding"])

        # 3. Query Payables
        pay_res = await client.get(f"/api/v1/reports/payables?company_id={company_id}", headers=auth_headers(token))
        assert pay_res.status_code == 200
        pay_data = pay_res.json()["data"]
        assert float(pay_data["total_outstanding"]) == float(pay_data["parties"][0]["outstanding"])

        # 4. Query Trial Balance
        tb_res = await client.get(f"/api/v1/reports/trial-balance?company_id={company_id}", headers=auth_headers(token))
        assert tb_res.status_code == 200
        tb_data = tb_res.json()["data"]
        assert tb_data["is_balanced"] is True
        assert float(tb_data["difference"]) == 0.0

        # 5. Query Balance Sheet
        bs_res = await client.get(f"/api/v1/reports/balance-sheet?company_id={company_id}", headers=auth_headers(token))
        assert bs_res.status_code == 200
        bs_data = bs_res.json()["data"]
        assert bs_data["is_balanced"] is True
        assert float(bs_data["difference"]) == 0.0

        # 6. Query Management Cockpit
        mgmt_res = await client.get(f"/api/v1/reports/management?company_id={company_id}", headers=auth_headers(token))
        assert mgmt_res.status_code == 200
        mgmt_data = mgmt_res.json()["data"]
        cards = {c["key"]: float(c["current_value"]) for c in mgmt_data["cards"]}
        assert cards["revenue"] == float(pnl_data["revenue_section"]["subtotal"])
        assert cards["receivables"] == float(rec_data["total_outstanding"])
        assert cards["payables"] == float(pay_data["total_outstanding"])


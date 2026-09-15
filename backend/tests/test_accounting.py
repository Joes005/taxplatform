from app.core.permissions import RoleCode
from tests.conftest import (
    add_membership,
    auth_headers,
    create_customer,
    create_financial_year,
    create_ledger,
    create_vendor,
    login,
)


class TestMasterData:
    async def test_create_and_list_ledger_with_hierarchy(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        parent = await client.post(
            f"/api/v1/accounting/ledgers?company_id={company.id}",
            json={"name": "Expenses", "ledger_type": "EXPENSE"},
            headers=headers,
        )
        assert parent.status_code == 201
        parent_id = parent.json()["data"]["id"]

        child = await client.post(
            f"/api/v1/accounting/ledgers?company_id={company.id}",
            json={"name": "Rent", "ledger_type": "EXPENSE", "parent_ledger_id": parent_id},
            headers=headers,
        )
        assert child.status_code == 201
        assert child.json()["data"]["parent_ledger_id"] == parent_id

    async def test_ledger_self_parent_rejected(self, client, company_a_with_admin, ledger_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        response = await client.patch(
            f"/api/v1/accounting/ledgers/{ledger_a.id}?company_id={company.id}",
            json={"parent_ledger_id": str(ledger_a.id)},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_LEDGER_PARENT"

    async def test_customer_invalid_gstin_rejected(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/accounting/customers?company_id={company.id}",
            json={"name": "Bad Corp", "gstin": "INVALID"},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 422

    async def test_only_one_current_financial_year(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        fy1 = await client.post(
            f"/api/v1/accounting/financial-years?company_id={company.id}",
            json={"name": "2025-26", "start_date": "2025-04-01", "end_date": "2026-03-31", "is_current": True},
            headers=headers,
        )
        fy1_id = fy1.json()["data"]["id"]

        fy2 = await client.post(
            f"/api/v1/accounting/financial-years?company_id={company.id}",
            json={"name": "2026-27", "start_date": "2026-04-01", "end_date": "2027-03-31", "is_current": True},
            headers=headers,
        )
        assert fy2.json()["data"]["is_current"] is True

        fy1_reread = await client.get(
            f"/api/v1/accounting/financial-years/{fy1_id}?company_id={company.id}", headers=headers
        )
        assert fy1_reread.json()["data"]["is_current"] is False


class TestSalesInvoiceCalculation:
    async def test_taxable_plus_tax_equals_total(
        self, client, company_a_with_admin, financial_year_a, customer_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "customer_id": str(customer_a.id),
                "invoice_number": "INV-100",
                "invoice_date": "2025-06-01",
                "items": [
                    {"quantity": 2, "unit_price": 500, "cgst_rate": 9, "sgst_rate": 9},
                    {"quantity": 1, "unit_price": 1000, "igst_rate": 18},
                ],
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 201, response.text
        body = response.json()["data"]
        taxable = float(body["taxable_amount"])
        total_tax = float(body["total_tax"])
        grand_total = float(body["grand_total"])
        assert taxable == 2000.0
        assert total_tax == 360.0
        assert abs(taxable + total_tax - grand_total) < 0.01

    async def test_mixed_igst_and_cgst_on_one_line_rejected(
        self, client, company_a_with_admin, financial_year_a, customer_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "customer_id": str(customer_a.id),
                "invoice_number": "INV-101",
                "invoice_date": "2025-06-01",
                "items": [{"quantity": 1, "unit_price": 100, "cgst_rate": 9, "igst_rate": 18}],
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_TAX_SPLIT"

    async def test_invalid_financial_year_date_rejected(
        self, client, company_a_with_admin, financial_year_a, customer_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "customer_id": str(customer_a.id),
                "invoice_number": "INV-102",
                "invoice_date": "2020-01-01",
                "items": [{"quantity": 1, "unit_price": 100}],
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_FINANCIAL_YEAR_DATE"

    async def test_duplicate_invoice_rejected(
        self, client, company_a_with_admin, financial_year_a, customer_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        payload = {
            "financial_year_id": str(financial_year_a.id),
            "customer_id": str(customer_a.id),
            "invoice_number": "INV-DUP",
            "invoice_date": "2025-06-01",
            "items": [{"quantity": 1, "unit_price": 100}],
        }

        first = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}", json=payload, headers=headers
        )
        assert first.status_code == 201

        second = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}", json=payload, headers=headers
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "DUPLICATE_INVOICE"


class TestPostingLifecycle:
    async def _create_draft(self, client, headers, company, financial_year_a, customer_a, number="INV-200"):
        response = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "customer_id": str(customer_a.id),
                "invoice_number": number,
                "invoice_date": "2025-06-01",
                "items": [{"quantity": 1, "unit_price": 100, "cgst_rate": 9, "sgst_rate": 9}],
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        return response.json()["data"]["id"]

    async def test_draft_to_posted(self, client, company_a_with_admin, financial_year_a, customer_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        invoice_id = await self._create_draft(client, headers, company, financial_year_a, customer_a)

        response = await client.post(
            f"/api/v1/accounting/sales-invoices/{invoice_id}/post?company_id={company.id}", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "POSTED"

    async def test_posted_invoice_is_immutable(
        self, client, company_a_with_admin, financial_year_a, customer_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        invoice_id = await self._create_draft(
            client, headers, company, financial_year_a, customer_a, number="INV-201"
        )
        await client.post(
            f"/api/v1/accounting/sales-invoices/{invoice_id}/post?company_id={company.id}", headers=headers
        )

        response = await client.patch(
            f"/api/v1/accounting/sales-invoices/{invoice_id}?company_id={company.id}",
            json={"invoice_number": "CHANGED"},
            headers=headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "POSTED_TRANSACTION_IMMUTABLE"

    async def test_cannot_post_twice(self, client, company_a_with_admin, financial_year_a, customer_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        invoice_id = await self._create_draft(
            client, headers, company, financial_year_a, customer_a, number="INV-202"
        )
        await client.post(
            f"/api/v1/accounting/sales-invoices/{invoice_id}/post?company_id={company.id}", headers=headers
        )
        response = await client.post(
            f"/api/v1/accounting/sales-invoices/{invoice_id}/post?company_id={company.id}", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


class TestJournalEntry:
    async def test_balanced_journal_accepted(self, client, company_a_with_admin, financial_year_a, db_session):
        company, admin = company_a_with_admin
        cash_ledger = await create_ledger(db_session, company.id, name="Cash", ledger_type="CASH")
        capital_ledger = await create_ledger(db_session, company.id, name="Capital", ledger_type="EQUITY")

        data = await login(client, admin.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/accounting/journal-entries?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "journal_number": "JV-001",
                "journal_date": "2025-06-01",
                "lines": [
                    {"ledger_id": str(cash_ledger.id), "debit_amount": 1000},
                    {"ledger_id": str(capital_ledger.id), "credit_amount": 1000},
                ],
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 201, response.text

    async def test_unbalanced_journal_rejected(
        self, client, company_a_with_admin, financial_year_a, db_session
    ):
        company, admin = company_a_with_admin
        cash_ledger = await create_ledger(db_session, company.id, name="Cash2", ledger_type="CASH")
        capital_ledger = await create_ledger(db_session, company.id, name="Capital2", ledger_type="EQUITY")

        data = await login(client, admin.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/accounting/journal-entries?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "journal_number": "JV-002",
                "journal_date": "2025-06-01",
                "lines": [
                    {"ledger_id": str(cash_ledger.id), "debit_amount": 1000},
                    {"ledger_id": str(capital_ledger.id), "credit_amount": 900},
                ],
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "UNBALANCED_JOURNAL"

    async def test_line_with_both_debit_and_credit_rejected(self, client, company_a_with_admin, ledger_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/accounting/journal-entries?company_id={company.id}",
            json={
                "financial_year_id": "00000000-0000-0000-0000-000000000000",
                "journal_number": "JV-003",
                "journal_date": "2025-06-01",
                "lines": [
                    {"ledger_id": str(ledger_a.id), "debit_amount": 100, "credit_amount": 100},
                    {"ledger_id": str(ledger_a.id), "debit_amount": 100},
                ],
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 422


class TestTenantIsolation:
    async def test_company_a_cannot_read_company_b_customer(
        self, client, company_a_with_admin, company_b_with_admin, db_session
    ):
        company_a, admin_a = company_a_with_admin
        company_b, _admin_b = company_b_with_admin
        customer_b = await create_customer(db_session, company_b.id, name="B-only Customer")

        data = await login(client, admin_a.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/accounting/customers/{customer_b.id}?company_id={company_a.id}",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 404

    async def test_company_a_cannot_access_company_b_directly(
        self, client, company_a_with_admin, company_b_with_admin, db_session
    ):
        company_a, admin_a = company_a_with_admin
        company_b, _admin_b = company_b_with_admin
        customer_b = await create_customer(db_session, company_b.id, name="B-only Customer 2")

        data = await login(client, admin_a.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/accounting/customers/{customer_b.id}?company_id={company_b.id}",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 403

    async def test_company_a_cannot_list_company_b_sales_invoices(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, _admin_b = company_b_with_admin
        data = await login(client, admin_a.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/accounting/sales-invoices?company_id={company_b.id}",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 403

    async def test_company_a_cannot_post_company_b_invoice(
        self, client, company_a_with_admin, company_b_with_admin, financial_year_b, db_session
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin
        customer_b = await create_customer(db_session, company_b.id)

        data_b = await login(client, admin_b.email, "TestPass1!")
        create_response = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company_b.id}",
            json={
                "financial_year_id": str(financial_year_b.id),
                "customer_id": str(customer_b.id),
                "invoice_number": "B-INV-1",
                "invoice_date": "2025-06-01",
                "items": [{"quantity": 1, "unit_price": 100}],
            },
            headers=auth_headers(data_b["access_token"]),
        )
        invoice_id = create_response.json()["data"]["id"]

        data_a = await login(client, admin_a.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/accounting/sales-invoices/{invoice_id}/post?company_id={company_a.id}",
            headers=auth_headers(data_a["access_token"]),
        )
        assert response.status_code == 404


class TestRBAC:
    async def test_accountant_can_create_sales_invoice(
        self, client, db_session, seeded_rbac, company_a_with_admin, financial_year_a, customer_a
    ):
        company, _admin = company_a_with_admin
        accountant = await add_membership(
            db_session, seeded_rbac, company_id=company.id,
            email="accountant-acc@example.com", role_code=RoleCode.ACCOUNTANT.value,
        )
        data = await login(client, accountant.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "customer_id": str(customer_a.id),
                "invoice_number": "INV-RBAC-1",
                "invoice_date": "2025-06-01",
                "items": [{"quantity": 1, "unit_price": 100}],
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 201

    async def test_auditor_cannot_post_invoice(
        self, client, db_session, seeded_rbac, company_a_with_admin, financial_year_a, customer_a
    ):
        company, admin = company_a_with_admin
        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id,
            email="auditor-acc@example.com", role_code=RoleCode.AUDITOR.value,
        )
        admin_data = await login(client, admin.email, "TestPass1!")
        create_response = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "customer_id": str(customer_a.id),
                "invoice_number": "INV-RBAC-2",
                "invoice_date": "2025-06-01",
                "items": [{"quantity": 1, "unit_price": 100}],
            },
            headers=auth_headers(admin_data["access_token"]),
        )
        invoice_id = create_response.json()["data"]["id"]

        auditor_data = await login(client, auditor.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/accounting/sales-invoices/{invoice_id}/post?company_id={company.id}",
            headers=auth_headers(auditor_data["access_token"]),
        )
        assert response.status_code == 403

    async def test_auditor_can_view_but_not_create(
        self, client, db_session, seeded_rbac, company_a_with_admin
    ):
        company, _admin = company_a_with_admin
        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id,
            email="auditor-acc2@example.com", role_code=RoleCode.AUDITOR.value,
        )
        data = await login(client, auditor.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        view_response = await client.get(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}", headers=headers
        )
        assert view_response.status_code == 200

        create_response = await client.post(
            f"/api/v1/accounting/ledgers?company_id={company.id}",
            json={"name": "Should Fail", "ledger_type": "EXPENSE"},
            headers=headers,
        )
        assert create_response.status_code == 403


class TestAuditLogging:
    async def test_sales_invoice_creation_is_logged(
        self, client, company_a_with_admin, financial_year_a, customer_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "customer_id": str(customer_a.id),
                "invoice_number": "INV-AUDIT-1",
                "invoice_date": "2025-06-01",
                "items": [{"quantity": 1, "unit_price": 100}],
            },
            headers=headers,
        )
        response = await client.get(
            f"/api/v1/audit-logs?company_id={company.id}&resource_type=sales_invoice", headers=headers
        )
        assert response.json()["data"]["pagination"]["total"] >= 1

from app.core.permissions import RoleCode
from app.seed import seed_default_income_tax_rule_sets
from tests.conftest import add_membership, auth_headers, create_ledger, login


async def _create_profile(client, headers, company_id, *, pan="AAAPA1234A", taxpayer_type="INDIVIDUAL"):
    response = await client.post(
        f"/api/v1/income-tax/profile?company_id={company_id}",
        json={"pan": pan, "legal_name": "Test Taxpayer", "taxpayer_type": taxpayer_type},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _create_and_post_sales_invoice(client, headers, company_id, financial_year_id, customer_id, *, amount):
    create = await client.post(
        f"/api/v1/accounting/sales-invoices?company_id={company_id}",
        json={
            "financial_year_id": str(financial_year_id),
            "customer_id": str(customer_id),
            "invoice_number": "INV-IT-001",
            "invoice_date": "2025-06-01",
            "place_of_supply_state_code": "27",
            "items": [{"quantity": 1, "unit_price": amount}],
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    invoice_id = create.json()["data"]["id"]
    post = await client.post(
        f"/api/v1/accounting/sales-invoices/{invoice_id}/post?company_id={company_id}", headers=headers
    )
    assert post.status_code == 200, post.text
    return post.json()["data"]


async def _create_and_post_purchase_invoice(client, headers, company_id, financial_year_id, vendor_id, *, amount):
    create = await client.post(
        f"/api/v1/accounting/purchase-invoices?company_id={company_id}",
        json={
            "financial_year_id": str(financial_year_id),
            "vendor_id": str(vendor_id),
            "invoice_number": "PINV-IT-001",
            "invoice_date": "2025-06-01",
            "supplier_invoice_number": "SUP-001",
            "supplier_invoice_date": "2025-05-28",
            "items": [{"quantity": 1, "unit_price": amount}],
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    invoice_id = create.json()["data"]["id"]
    post = await client.post(
        f"/api/v1/accounting/purchase-invoices/{invoice_id}/post?company_id={company_id}", headers=headers
    )
    assert post.status_code == 200, post.text
    return post.json()["data"]


class TestIncomeTaxProfile:
    async def test_create_profile_validates_pan_format(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        bad = await client.post(
            f"/api/v1/income-tax/profile?company_id={company.id}",
            json={"pan": "1234567890", "legal_name": "Test Co"},
            headers=headers,
        )
        assert bad.status_code == 422
        assert bad.json()["error"]["code"] == "INVALID_PAN_FORMAT"

        good = await _create_profile(client, headers, company.id)
        assert good["pan"] == "AAAPA1234A"

    async def test_duplicate_profile_rejected(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_profile(client, headers, company.id)
        second = await client.post(
            f"/api/v1/income-tax/profile?company_id={company.id}",
            json={"pan": "BBBPB1234B", "legal_name": "Another"},
            headers=headers,
        )
        assert second.status_code == 422
        assert second.json()["error"]["code"] == "INCOME_TAX_PROFILE_ALREADY_EXISTS"


class TestIncomeEntries:
    async def test_salary_income_computes_taxable_amount(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/income-tax/salary-income?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "employer_name": "Acme Corp",
                "gross_salary": "1000000",
                "standard_deduction": "50000",
                "professional_tax": "2400",
                "tds": "80000",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()["data"]
        assert body["taxable_amount"] == "947600.00"

    async def test_house_property_income_let_out_standard_deduction(
        self, client, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/income-tax/house-property-income?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "property_type": "LET_OUT",
                "gross_rent": "300000",
                "municipal_tax": "10000",
                "interest_on_home_loan": "50000",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()["data"]
        # NAV = 300000 - 10000 = 290000; standard deduction = 30% of NAV = 87000
        assert body["net_annual_value"] == "290000.00"
        assert body["standard_deduction"] == "87000.00"
        assert body["income_or_loss"] == "153000.00"


class TestCapitalGains:
    async def test_gain_amount_computed(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/income-tax/capital-gains?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "asset_type": "EQUITY_SHARES",
                "asset_description": "100 shares of XYZ Ltd",
                "purchase_date": "2024-01-10",
                "sale_date": "2025-08-01",
                "purchase_cost": "50000",
                "sale_consideration": "80000",
                "transfer_expenses": "500",
                "gain_type": "LONG_TERM",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        assert response.json()["data"]["gain_amount"] == "29500.00"

    async def test_sale_before_purchase_rejected(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/income-tax/capital-gains?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "asset_type": "OTHER",
                "asset_description": "Bad dates",
                "purchase_date": "2025-08-01",
                "sale_date": "2024-01-10",
                "sale_consideration": "1000",
                "gain_type": "SHORT_TERM",
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_CAPITAL_GAIN_DATES"


class TestBusinessIncomeAndComputation:
    async def test_new_regime_computation_end_to_end(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_income_tax_rule_sets(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_profile(client, headers, company.id)

        customer = await client.post(
            f"/api/v1/accounting/customers?company_id={company.id}", json={"name": "Big Client"}, headers=headers
        )
        vendor = await client.post(
            f"/api/v1/accounting/vendors?company_id={company.id}", json={"name": "Supplier Co"}, headers=headers
        )
        await _create_and_post_sales_invoice(
            client, headers, company.id, financial_year_a.id, customer.json()["data"]["id"], amount=2000000
        )
        await _create_and_post_purchase_invoice(
            client, headers, company.id, financial_year_a.id, vendor.json()["data"]["id"], amount=500000
        )

        create = await client.post(
            f"/api/v1/income-tax/computations?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "tax_regime": "NEW_REGIME"},
            headers=headers,
        )
        assert create.status_code == 201, create.text
        computation_id = create.json()["data"]["id"]
        assert create.json()["data"]["assessment_year"] == "2026-27"

        calc = await client.post(
            f"/api/v1/income-tax/computations/{computation_id}/calculate?company_id={company.id}", headers=headers
        )
        assert calc.status_code == 200, calc.text
        body = calc.json()["data"]
        assert body["business_income"] == "1500000.00"
        assert body["gross_total_income"] == "1500000.00"
        assert body["taxable_income"] == "1500000.00"
        assert body["tax_before_rebate"] == "105000.00"
        assert body["rebate"] == "0.00"
        assert body["cess"] == "4200.00"
        assert body["gross_tax_liability"] == "109200.00"
        assert body["balance_payable_or_refund"] == "109200.00"
        assert body["status"] == "CALCULATED"

        snapshots = await client.get(
            f"/api/v1/income-tax/computations/{computation_id}/snapshots?company_id={company.id}", headers=headers
        )
        assert len(snapshots.json()["data"]) == 1

    async def test_old_regime_deduction_capped_at_max_amount(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_income_tax_rule_sets(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await _create_profile(client, headers, company.id)

        customer = await client.post(
            f"/api/v1/accounting/customers?company_id={company.id}", json={"name": "Client"}, headers=headers
        )
        await _create_and_post_sales_invoice(
            client, headers, company.id, financial_year_a.id, customer.json()["data"]["id"], amount=900000
        )

        await client.post(
            f"/api/v1/income-tax/deductions?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "section_code": "80C", "claimed_amount": "200000"},
            headers=headers,
        )

        create = await client.post(
            f"/api/v1/income-tax/computations?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "tax_regime": "OLD_REGIME"},
            headers=headers,
        )
        computation_id = create.json()["data"]["id"]

        calc = await client.post(
            f"/api/v1/income-tax/computations/{computation_id}/calculate?company_id={company.id}", headers=headers
        )
        body = calc.json()["data"]
        # 80C claimed 200000 but capped at the rule set's max_amount of 150000
        assert body["total_deductions"] == "150000.00"
        assert body["taxable_income"] == "750000.00"
        assert body["gross_tax_liability"] == "65000.00"

    async def test_new_regime_disallows_80c_entirely(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_income_tax_rule_sets(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await _create_profile(client, headers, company.id)

        customer = await client.post(
            f"/api/v1/accounting/customers?company_id={company.id}", json={"name": "Client"}, headers=headers
        )
        await _create_and_post_sales_invoice(
            client, headers, company.id, financial_year_a.id, customer.json()["data"]["id"], amount=900000
        )
        await client.post(
            f"/api/v1/income-tax/deductions?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "section_code": "80C", "claimed_amount": "100000"},
            headers=headers,
        )

        create = await client.post(
            f"/api/v1/income-tax/computations?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "tax_regime": "NEW_REGIME"},
            headers=headers,
        )
        computation_id = create.json()["data"]["id"]
        calc = await client.post(
            f"/api/v1/income-tax/computations/{computation_id}/calculate?company_id={company.id}", headers=headers
        )
        assert calc.json()["data"]["total_deductions"] == "0.00"

    async def test_disallowed_ledger_expense_added_back(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_income_tax_rule_sets(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await _create_profile(client, headers, company.id)

        cash_ledger = await create_ledger(db_session, company.id, name="Cash IT", ledger_type="CASH")
        fine_ledger = await create_ledger(db_session, company.id, name="Fines & Penalties", ledger_type="EXPENSE")

        je = await client.post(
            f"/api/v1/accounting/journal-entries?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "journal_number": "JV-IT-001",
                "journal_date": "2025-06-01",
                "lines": [
                    {"ledger_id": str(fine_ledger.id), "debit_amount": 20000},
                    {"ledger_id": str(cash_ledger.id), "credit_amount": 20000},
                ],
            },
            headers=headers,
        )
        entry_id = je.json()["data"]["id"]
        await client.post(
            f"/api/v1/accounting/journal-entries/{entry_id}/post?company_id={company.id}", headers=headers
        )

        await client.post(
            f"/api/v1/income-tax/ledger-classifications?company_id={company.id}",
            json={"ledger_id": str(fine_ledger.id), "classification": "DISALLOWABLE"},
            headers=headers,
        )

        preview = await client.get(
            f"/api/v1/income-tax/business-income-preview?company_id={company.id}"
            f"&financial_year_id={financial_year_a.id}",
            headers=headers,
        )
        assert preview.status_code == 200, preview.text
        body = preview.json()["data"]
        assert body["disallowances"] == "20000.00"
        # Book profit is -20000 (an expense with no revenue); adding back the
        # disallowed fine brings taxable business income to 0.
        assert body["taxable_business_income"] == "0.00"


class TestComputationLifecycle:
    async def test_full_lifecycle_and_rbac(self, client, db_session, seeded_rbac, company_a_with_admin, financial_year_a):
        await seed_default_income_tax_rule_sets(db_session)
        company, admin = company_a_with_admin
        admin_data = await login(client, admin.email, "TestPass1!")
        admin_headers = auth_headers(admin_data["access_token"])
        await _create_profile(client, admin_headers, company.id)

        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="auditor-it@example.com",
            role_code=RoleCode.AUDITOR.value,
        )
        auditor_data = await login(client, auditor.email, "TestPass1!")
        auditor_headers = auth_headers(auditor_data["access_token"])

        customer = await client.post(
            f"/api/v1/accounting/customers?company_id={company.id}", json={"name": "Client"}, headers=admin_headers
        )
        await _create_and_post_sales_invoice(
            client, admin_headers, company.id, financial_year_a.id, customer.json()["data"]["id"], amount=900000
        )

        create = await client.post(
            f"/api/v1/income-tax/computations?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "tax_regime": "NEW_REGIME"},
            headers=admin_headers,
        )
        computation_id = create.json()["data"]["id"]

        forbidden = await client.post(
            f"/api/v1/income-tax/computations/{computation_id}/approve?company_id={company.id}",
            headers=admin_headers,
        )
        assert forbidden.status_code == 403

        await client.post(
            f"/api/v1/income-tax/computations/{computation_id}/calculate?company_id={company.id}",
            headers=admin_headers,
        )
        submit = await client.post(
            f"/api/v1/income-tax/computations/{computation_id}/submit-review?company_id={company.id}",
            headers=admin_headers,
        )
        assert submit.json()["data"]["status"] == "READY_FOR_REVIEW"

        approve = await client.post(
            f"/api/v1/income-tax/computations/{computation_id}/approve?company_id={company.id}",
            headers=auditor_headers,
        )
        assert approve.status_code == 200, approve.text
        assert approve.json()["data"]["status"] == "APPROVED"

        lock = await client.post(
            f"/api/v1/income-tax/computations/{computation_id}/lock?company_id={company.id}", headers=auditor_headers
        )
        assert lock.json()["data"]["status"] == "LOCKED"

        recalc_blocked = await client.post(
            f"/api/v1/income-tax/computations/{computation_id}/calculate?company_id={company.id}",
            headers=admin_headers,
        )
        assert recalc_blocked.status_code == 409
        assert recalc_blocked.json()["error"]["code"] == "INVALID_TAX_COMPUTATION_TRANSITION"


class TestITRPreparation:
    async def test_validate_blocks_approval_until_bank_account_added(
        self, client, db_session, seeded_rbac, company_a_with_admin, financial_year_a
    ):
        await seed_default_income_tax_rule_sets(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await _create_profile(client, headers, company.id)

        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="auditor-itr@example.com",
            role_code=RoleCode.AUDITOR.value,
        )
        auditor_data = await login(client, auditor.email, "TestPass1!")
        auditor_headers = auth_headers(auditor_data["access_token"])

        customer = await client.post(
            f"/api/v1/accounting/customers?company_id={company.id}", json={"name": "Client"}, headers=headers
        )
        await _create_and_post_sales_invoice(
            client, headers, company.id, financial_year_a.id, customer.json()["data"]["id"], amount=900000
        )
        create = await client.post(
            f"/api/v1/income-tax/computations?company_id={company.id}",
            json={"financial_year_id": str(financial_year_a.id), "tax_regime": "NEW_REGIME"},
            headers=headers,
        )
        computation_id = create.json()["data"]["id"]
        await client.post(
            f"/api/v1/income-tax/computations/{computation_id}/calculate?company_id={company.id}", headers=headers
        )

        prep = await client.post(
            f"/api/v1/income-tax/itr?company_id={company.id}",
            json={"tax_computation_id": computation_id},
            headers=headers,
        )
        assert prep.status_code == 201, prep.text
        assert prep.json()["data"]["itr_form_type"] == "ITR_3"
        preparation_id = prep.json()["data"]["id"]

        validation = await client.post(
            f"/api/v1/income-tax/itr/{preparation_id}/validate?company_id={company.id}", headers=headers
        )
        assert validation.status_code == 200
        assert validation.json()["data"]["has_errors"] is True
        codes = {issue["code"] for issue in validation.json()["data"]["issues"]}
        assert "BANK_ACCOUNT_MISSING" in codes

        await client.post(
            f"/api/v1/income-tax/itr/{preparation_id}/submit-review?company_id={company.id}", headers=headers
        )
        blocked_approve = await client.post(
            f"/api/v1/income-tax/itr/{preparation_id}/approve?company_id={company.id}", headers=auditor_headers
        )
        assert blocked_approve.status_code == 409
        assert blocked_approve.json()["error"]["code"] == "ITR_VALIDATION_ERRORS_BLOCK_APPROVAL"

        await client.post(
            f"/api/v1/bank/accounts?company_id={company.id}",
            json={
                "bank_name": "HDFC Bank",
                "account_name": "Primary Account",
                "account_number_masked": "XXXXXX1234",
                "account_type": "SAVINGS",
                "opening_balance": "0",
                "opening_balance_date": "2025-04-01",
            },
            headers=headers,
        )

        approve = await client.post(
            f"/api/v1/income-tax/itr/{preparation_id}/approve?company_id={company.id}", headers=auditor_headers
        )
        assert approve.status_code == 200, approve.text
        assert approve.json()["data"]["status"] == "APPROVED"

        lock = await client.post(
            f"/api/v1/income-tax/itr/{preparation_id}/lock?company_id={company.id}", headers=auditor_headers
        )
        assert lock.json()["data"]["status"] == "LOCKED"


class TestTenantIsolation:
    async def test_company_b_cannot_access_company_a_profile(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        _company_b, admin_b = company_b_with_admin
        data_a = await login(client, admin_a.email, "TestPass1!")
        await _create_profile(client, auth_headers(data_a["access_token"]), company_a.id)

        data_b = await login(client, admin_b.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/income-tax/profile?company_id={company_a.id}", headers=auth_headers(data_b["access_token"])
        )
        assert response.status_code == 403

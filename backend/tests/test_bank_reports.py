from tests.conftest import auth_headers, create_customer, create_ledger, login


async def _setup_matched_scenario(client, db_session, company, admin, financial_year_a):
    data = await login(client, admin.email, "TestPass1!")
    headers = auth_headers(data["access_token"])

    bank_ledger = await create_ledger(db_session, company.id, name="HDFC Bank Ledger", ledger_type="BANK")
    account = await client.post(
        f"/api/v1/bank/accounts?company_id={company.id}",
        json={
            "bank_name": "HDFC Bank",
            "account_name": "HDFC Current Account",
            "account_number_masked": "XXXXXX1234",
            "opening_balance": "100000",
            "opening_balance_date": "2025-04-01",
            "ledger_id": str(bank_ledger.id),
        },
        headers=headers,
    )
    bank_account_id = account.json()["data"]["id"]

    statement = await client.post(
        f"/api/v1/bank/statements?company_id={company.id}",
        json={
            "bank_account_id": bank_account_id,
            "statement_name": "September 2025",
            "period_start": "2025-09-01",
            "period_end": "2025-09-30",
            "opening_balance": "100000",
            "closing_balance": "150000",
        },
        headers=headers,
    )
    statement_id = statement.json()["data"]["id"]

    customer = await create_customer(db_session, company.id, name="ABC Traders")
    await client.post(
        f"/api/v1/accounting/receipts?company_id={company.id}",
        json={
            "financial_year_id": str(financial_year_a.id),
            "receipt_date": "2025-09-01",
            "receipt_number": "REC-001",
            "customer_id": str(customer.id),
            "ledger_id": str(bank_ledger.id),
            "amount": "50000",
            "payment_mode": "UPI",
            "reference_number": "UPI12345",
        },
        headers=headers,
    )

    upload = await client.post(
        f"/api/v1/documents?company_id={company.id}",
        headers=headers,
        data={"document_type": "OTHER"},
        files={
            "file": (
                "stmt.csv",
                b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n"
                b"2025-09-01,UPI RECEIVED ABC TRADERS,UPI12345,,50000,150000\n"
                b"2025-09-02,BANK CHARGES,,500,,149500\n",
                "text/csv",
            )
        },
    )
    document_id = upload.json()["data"]["id"]
    mapping = {
        "Date": "transaction_date", "Narration": "description", "Ref": "reference_number",
        "Withdrawal": "debit_amount", "Deposit": "credit_amount", "Balance": "balance_after_transaction",
    }
    job = await client.post(
        f"/api/v1/accounting/imports?company_id={company.id}",
        json={"document_id": document_id, "import_type": "BANK_STATEMENT", "bank_statement_id": statement_id, "column_mapping": mapping},
        headers=headers,
    )
    await client.post(f"/api/v1/accounting/imports/{job.json()['data']['id']}/commit?company_id={company.id}", headers=headers)

    recon = await client.post(
        f"/api/v1/bank/reconciliations?company_id={company.id}",
        json={
            "bank_account_id": bank_account_id, "period_start": "2025-09-01", "period_end": "2025-09-30",
            "opening_balance": "100000", "closing_balance": "150000",
        },
        headers=headers,
    )
    recon_id = recon.json()["data"]["id"]
    await client.post(f"/api/v1/bank/reconciliations/{recon_id}/run-matching?company_id={company.id}", headers=headers)

    return headers, bank_account_id, bank_ledger.id, recon_id


class TestBankReports:
    async def test_unmatched_bank_transactions_report(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        headers, bank_account_id, _ledger_id, _recon_id = await _setup_matched_scenario(
            client, db_session, company, admin, financial_year_a
        )

        response = await client.get(
            f"/api/v1/bank/reports/unmatched-bank-transactions?company_id={company.id}"
            f"&bank_account_id={bank_account_id}&period_start=2025-09-01&period_end=2025-09-30",
            headers=headers,
        )
        assert response.status_code == 200
        rows = response.json()["data"]
        assert len(rows) == 1
        assert rows[0]["amount"] == "500.00"

    async def test_matching_report(self, client, db_session, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        headers, bank_account_id, _ledger_id, _recon_id = await _setup_matched_scenario(
            client, db_session, company, admin, financial_year_a
        )

        response = await client.get(
            f"/api/v1/bank/reports/matches?company_id={company.id}&bank_account_id={bank_account_id}"
            f"&period_start=2025-09-01&period_end=2025-09-30",
            headers=headers,
        )
        assert response.status_code == 200
        rows = response.json()["data"]
        assert len(rows) == 1
        assert rows[0]["match_type"] == "AUTO"

    async def test_export_reconciliation_csv(self, client, db_session, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        headers, _bank_account_id, _ledger_id, recon_id = await _setup_matched_scenario(
            client, db_session, company, admin, financial_year_a
        )

        response = await client.get(
            f"/api/v1/bank/reports/reconciliations/{recon_id}/export?company_id={company.id}&format=csv",
            headers=headers,
        )
        assert response.status_code == 200
        assert b"Bank Reconciliation Report" in response.content

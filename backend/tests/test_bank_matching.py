from decimal import Decimal

from tests.conftest import auth_headers, create_customer, create_ledger, create_vendor, login


async def _create_bank_account(client, headers, company_id, *, ledger_id=None) -> str:
    payload = {
        "bank_name": "HDFC Bank",
        "account_name": "HDFC Current Account",
        "account_number_masked": "XXXXXX1234",
        "opening_balance": "100000",
        "opening_balance_date": "2026-04-01",
    }
    if ledger_id:
        payload["ledger_id"] = ledger_id
    response = await client.post(f"/api/v1/bank/accounts?company_id={company_id}", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


async def _create_statement(client, headers, company_id, bank_account_id, *, closing="150000") -> str:
    response = await client.post(
        f"/api/v1/bank/statements?company_id={company_id}",
        json={
            "bank_account_id": bank_account_id,
            "statement_name": "September 2026",
            "period_start": "2025-09-01",
            "period_end": "2025-09-30",
            "opening_balance": "100000",
            "closing_balance": closing,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


async def _import_bank_transactions(client, headers, company_id, statement_id, csv_content: bytes):
    upload = await client.post(
        f"/api/v1/documents?company_id={company_id}",
        headers=headers,
        data={"document_type": "OTHER"},
        files={"file": ("stmt.csv", csv_content, "text/csv")},
    )
    document_id = upload.json()["data"]["id"]
    mapping = {
        "Date": "transaction_date",
        "Narration": "description",
        "Ref": "reference_number",
        "Withdrawal": "debit_amount",
        "Deposit": "credit_amount",
        "Balance": "balance_after_transaction",
    }
    job = await client.post(
        f"/api/v1/accounting/imports?company_id={company_id}",
        json={
            "document_id": document_id,
            "import_type": "BANK_STATEMENT",
            "bank_statement_id": statement_id,
            "column_mapping": mapping,
        },
        headers=headers,
    )
    job_id = job.json()["data"]["id"]
    await client.post(f"/api/v1/accounting/imports/{job_id}/commit?company_id={company_id}", headers=headers)
    transactions = await client.get(
        f"/api/v1/bank/statements/{statement_id}/transactions?company_id={company_id}&page_size=200", headers=headers
    )
    return transactions.json()["data"]["items"]


class TestBankAutoMatching:
    async def test_unambiguous_strong_match_auto_matches(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        bank_ledger = await create_ledger(db_session, company.id, name="HDFC Bank Ledger", ledger_type="BANK")
        bank_account_id = await _create_bank_account(client, headers, company.id, ledger_id=str(bank_ledger.id))
        statement_id = await _create_statement(client, headers, company.id, bank_account_id)

        customer = await create_customer(db_session, company.id, name="ABC Traders")
        receipt = await client.post(
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
        assert receipt.status_code == 201, receipt.text

        csv_content = b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n2025-09-01,UPI RECEIVED ABC TRADERS,UPI12345,,50000,150000\n"
        await _import_bank_transactions(client, headers, company.id, statement_id, csv_content)

        recon = await client.post(
            f"/api/v1/bank/reconciliations?company_id={company.id}",
            json={
                "bank_account_id": bank_account_id,
                "period_start": "2025-09-01",
                "period_end": "2025-09-30",
                "opening_balance": "100000",
                "closing_balance": "150000",
            },
            headers=headers,
        )
        recon_id = recon.json()["data"]["id"]

        run = await client.post(
            f"/api/v1/bank/reconciliations/{recon_id}/run-matching?company_id={company.id}", headers=headers
        )
        assert run.status_code == 200, run.text

        transactions = await client.get(
            f"/api/v1/bank/statements/{statement_id}/transactions?company_id={company.id}", headers=headers
        )
        txn = transactions.json()["data"]["items"][0]
        assert txn["reconciliation_status"] == "MATCHED"

        matches = await client.get(
            f"/api/v1/bank/transactions/{txn['id']}/matches?company_id={company.id}", headers=headers
        )
        match_list = matches.json()["data"]
        assert len(match_list) == 1
        assert match_list[0]["match_type"] == "AUTO"
        assert match_list[0]["source_type"] == "RECEIPT"

    async def test_ambiguous_same_amount_needs_review(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        bank_ledger = await create_ledger(db_session, company.id, name="HDFC Bank Ledger", ledger_type="BANK")
        bank_account_id = await _create_bank_account(client, headers, company.id, ledger_id=str(bank_ledger.id))
        statement_id = await _create_statement(client, headers, company.id, bank_account_id)

        customer = await create_customer(db_session, company.id, name="Generic Customer")
        for i in range(2):
            r = await client.post(
                f"/api/v1/accounting/receipts?company_id={company.id}",
                json={
                    "financial_year_id": str(financial_year_a.id),
                    "receipt_date": "2025-09-01",
                    "receipt_number": f"REC-10{i}",
                    "customer_id": str(customer.id),
                    "ledger_id": str(bank_ledger.id),
                    "amount": "50000",
                    "payment_mode": "UPI",
                },
                headers=headers,
            )
            assert r.status_code == 201

        csv_content = b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n2025-09-01,SOME DEPOSIT,,,50000,150000\n"
        await _import_bank_transactions(client, headers, company.id, statement_id, csv_content)

        recon = await client.post(
            f"/api/v1/bank/reconciliations?company_id={company.id}",
            json={
                "bank_account_id": bank_account_id,
                "period_start": "2025-09-01",
                "period_end": "2025-09-30",
                "opening_balance": "100000",
                "closing_balance": "150000",
            },
            headers=headers,
        )
        recon_id = recon.json()["data"]["id"]
        await client.post(
            f"/api/v1/bank/reconciliations/{recon_id}/run-matching?company_id={company.id}", headers=headers
        )

        transactions = await client.get(
            f"/api/v1/bank/statements/{statement_id}/transactions?company_id={company.id}", headers=headers
        )
        txn = transactions.json()["data"]["items"][0]
        assert txn["reconciliation_status"] in ("REVIEW_REQUIRED", "MATCH_SUGGESTED")

        candidates = await client.get(
            f"/api/v1/bank/transactions/{txn['id']}/candidates?company_id={company.id}", headers=headers
        )
        assert len(candidates.json()["data"]) == 2


class TestBankManualMatching:
    async def test_partial_matching_two_receipts(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        bank_ledger = await create_ledger(db_session, company.id, name="HDFC Bank Ledger", ledger_type="BANK")
        bank_account_id = await _create_bank_account(client, headers, company.id, ledger_id=str(bank_ledger.id))
        statement_id = await _create_statement(client, headers, company.id, bank_account_id, closing="110000")

        customer = await create_customer(db_session, company.id, name="Split Payer")
        receipt_ids = []
        for i, amt in enumerate(["6000", "4000"]):
            r = await client.post(
                f"/api/v1/accounting/receipts?company_id={company.id}",
                json={
                    "financial_year_id": str(financial_year_a.id),
                    "receipt_date": "2025-09-01",
                    "receipt_number": f"REC-P{i}",
                    "customer_id": str(customer.id),
                    "ledger_id": str(bank_ledger.id),
                    "amount": amt,
                    "payment_mode": "CASH",
                },
                headers=headers,
            )
            receipt_ids.append(r.json()["data"]["id"])

        csv_content = b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n2025-09-01,COMBINED DEPOSIT,,,10000,110000\n"
        txns = await _import_bank_transactions(client, headers, company.id, statement_id, csv_content)
        txn_id = txns[0]["id"]

        first = await client.post(
            f"/api/v1/bank/transactions/{txn_id}/match?company_id={company.id}",
            json={"source_type": "RECEIPT", "source_id": receipt_ids[0], "matched_amount": "6000"},
            headers=headers,
        )
        assert first.status_code == 201, first.text

        after_first = await client.get(
            f"/api/v1/bank/transactions/{txn_id}?company_id={company.id}", headers=headers
        )
        assert after_first.json()["data"]["reconciliation_status"] == "PARTIALLY_MATCHED"

        second = await client.post(
            f"/api/v1/bank/transactions/{txn_id}/match?company_id={company.id}",
            json={"source_type": "RECEIPT", "source_id": receipt_ids[1], "matched_amount": "4000"},
            headers=headers,
        )
        assert second.status_code == 201

        after_second = await client.get(
            f"/api/v1/bank/transactions/{txn_id}?company_id={company.id}", headers=headers
        )
        assert after_second.json()["data"]["reconciliation_status"] == "MANUALLY_MATCHED"

    async def test_over_allocation_beyond_bank_amount_rejected(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        bank_ledger = await create_ledger(db_session, company.id, name="HDFC Bank Ledger", ledger_type="BANK")
        bank_account_id = await _create_bank_account(client, headers, company.id, ledger_id=str(bank_ledger.id))
        statement_id = await _create_statement(client, headers, company.id, bank_account_id, closing="105000")

        customer = await create_customer(db_session, company.id, name="Over Payer")
        receipt = await client.post(
            f"/api/v1/accounting/receipts?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "receipt_date": "2025-09-01",
                "receipt_number": "REC-OVER",
                "customer_id": str(customer.id),
                "ledger_id": str(bank_ledger.id),
                "amount": "20000",
                "payment_mode": "CASH",
            },
            headers=headers,
        )
        receipt_id = receipt.json()["data"]["id"]

        csv_content = b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n2025-09-01,DEPOSIT,,,5000,105000\n"
        txns = await _import_bank_transactions(client, headers, company.id, statement_id, csv_content)
        txn_id = txns[0]["id"]

        response = await client.post(
            f"/api/v1/bank/transactions/{txn_id}/match?company_id={company.id}",
            json={"source_type": "RECEIPT", "source_id": receipt_id, "matched_amount": "20000"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "MATCH_AMOUNT_EXCEEDS_BANK_TRANSACTION"

    async def test_reverse_match(self, client, db_session, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        bank_ledger = await create_ledger(db_session, company.id, name="HDFC Bank Ledger", ledger_type="BANK")
        bank_account_id = await _create_bank_account(client, headers, company.id, ledger_id=str(bank_ledger.id))
        statement_id = await _create_statement(client, headers, company.id, bank_account_id, closing="108000")

        vendor = await create_vendor(db_session, company.id, name="Some Vendor")
        payment = await client.post(
            f"/api/v1/accounting/payments?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "payment_date": "2025-09-02",
                "payment_number": "PAY-001",
                "party_type": "VENDOR",
                "party_id": str(vendor.id),
                "ledger_id": str(bank_ledger.id),
                "amount": "8000",
                "payment_mode": "BANK",
            },
            headers=headers,
        )
        payment_id = payment.json()["data"]["id"]

        csv_content = b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n2025-09-02,NEFT PAYMENT,,8000,,108000\n"
        txns = await _import_bank_transactions(client, headers, company.id, statement_id, csv_content)
        txn_id = txns[0]["id"]

        match = await client.post(
            f"/api/v1/bank/transactions/{txn_id}/match?company_id={company.id}",
            json={"source_type": "PAYMENT", "source_id": payment_id, "matched_amount": "8000"},
            headers=headers,
        )
        match_id = match.json()["data"]["id"]

        reverse = await client.post(
            f"/api/v1/bank/matches/{match_id}/reverse?company_id={company.id}", headers=headers
        )
        assert reverse.json()["data"]["status"] == "REVERSED"

        after = await client.get(f"/api/v1/bank/transactions/{txn_id}?company_id={company.id}", headers=headers)
        assert after.json()["data"]["reconciliation_status"] == "UNMATCHED"


class TestBankReconciliationWorkflow:
    async def test_full_workflow_and_lock(self, client, db_session, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        bank_account_id = await _create_bank_account(client, headers, company.id)

        recon = await client.post(
            f"/api/v1/bank/reconciliations?company_id={company.id}",
            json={
                "bank_account_id": bank_account_id,
                "period_start": "2025-09-01",
                "period_end": "2025-09-30",
                "opening_balance": "100000",
                "closing_balance": "100000",
            },
            headers=headers,
        )
        assert recon.status_code == 201
        recon_id = recon.json()["data"]["id"]

        run = await client.post(
            f"/api/v1/bank/reconciliations/{recon_id}/run-matching?company_id={company.id}", headers=headers
        )
        assert run.json()["data"]["status"] == "IN_PROGRESS"

        submit = await client.post(
            f"/api/v1/bank/reconciliations/{recon_id}/submit?company_id={company.id}", headers=headers, json={}
        )
        assert submit.json()["data"]["status"] == "PENDING_REVIEW"

        approve = await client.post(
            f"/api/v1/bank/reconciliations/{recon_id}/approve?company_id={company.id}", headers=headers, json={}
        )
        assert approve.json()["data"]["status"] == "RECONCILED"

        lock = await client.post(
            f"/api/v1/bank/reconciliations/{recon_id}/lock?company_id={company.id}", headers=headers
        )
        assert lock.json()["data"]["status"] == "LOCKED"

        re_submit = await client.post(
            f"/api/v1/bank/reconciliations/{recon_id}/submit?company_id={company.id}", headers=headers, json={}
        )
        assert re_submit.status_code == 409

    async def test_duplicate_session_for_same_period_rejected(
        self, client, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        bank_account_id = await _create_bank_account(client, headers, company.id)
        payload = {
            "bank_account_id": bank_account_id,
            "period_start": "2025-09-01",
            "period_end": "2025-09-30",
            "opening_balance": "100000",
            "closing_balance": "100000",
        }

        first = await client.post(
            f"/api/v1/bank/reconciliations?company_id={company.id}", json=payload, headers=headers
        )
        assert first.status_code == 201

        second = await client.post(
            f"/api/v1/bank/reconciliations?company_id={company.id}", json=payload, headers=headers
        )
        assert second.status_code == 422
        assert second.json()["error"]["code"] == "BANK_RECONCILIATION_ALREADY_EXISTS"

    async def test_auditor_cannot_run_matching_but_can_approve(
        self, client, db_session, company_a_with_admin, seeded_rbac
    ):
        from tests.conftest import add_membership

        company, admin = company_a_with_admin
        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="bank-recon-auditor@example.com", role_code="AUDITOR"
        )
        admin_data = await login(client, admin.email, "TestPass1!")
        admin_headers = auth_headers(admin_data["access_token"])
        bank_account_id = await _create_bank_account(client, admin_headers, company.id)

        recon = await client.post(
            f"/api/v1/bank/reconciliations?company_id={company.id}",
            json={
                "bank_account_id": bank_account_id,
                "period_start": "2025-09-01",
                "period_end": "2025-09-30",
                "opening_balance": "100000",
                "closing_balance": "100000",
            },
            headers=admin_headers,
        )
        recon_id = recon.json()["data"]["id"]

        auditor_data = await login(client, auditor.email, "TestPass1!")
        auditor_headers = auth_headers(auditor_data["access_token"])

        forbidden = await client.post(
            f"/api/v1/bank/reconciliations/{recon_id}/run-matching?company_id={company.id}", headers=auditor_headers
        )
        assert forbidden.status_code == 403


class TestBankAdjustment:
    async def test_create_adjustment_for_bank_charges(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        bank_ledger = await create_ledger(db_session, company.id, name="HDFC Bank Ledger", ledger_type="BANK")
        expense_ledger = await create_ledger(db_session, company.id, name="Bank Charges", ledger_type="EXPENSE")
        bank_account_id = await _create_bank_account(client, headers, company.id, ledger_id=str(bank_ledger.id))
        statement_id = await _create_statement(client, headers, company.id, bank_account_id, closing="99500")

        csv_content = b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n2025-09-03,BANK CHARGES,,500,,99500\n"
        txns = await _import_bank_transactions(client, headers, company.id, statement_id, csv_content)
        txn_id = txns[0]["id"]

        response = await client.post(
            f"/api/v1/bank/transactions/{txn_id}/adjust?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "journal_number": "BANKADJ-001",
                "offset_ledger_id": str(expense_ledger.id),
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        assert response.json()["data"]["status"] == "POSTED"

        after = await client.get(f"/api/v1/bank/transactions/{txn_id}?company_id={company.id}", headers=headers)
        assert after.json()["data"]["reconciliation_status"] == "MANUALLY_MATCHED"

    async def test_adjustment_requires_linked_ledger(
        self, client, db_session, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        expense_ledger = await create_ledger(db_session, company.id, name="Bank Charges", ledger_type="EXPENSE")
        bank_account_id = await _create_bank_account(client, headers, company.id)  # no ledger_id
        statement_id = await _create_statement(client, headers, company.id, bank_account_id, closing="99500")

        csv_content = b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n2025-09-03,BANK CHARGES,,500,,99500\n"
        txns = await _import_bank_transactions(client, headers, company.id, statement_id, csv_content)
        txn_id = txns[0]["id"]

        response = await client.post(
            f"/api/v1/bank/transactions/{txn_id}/adjust?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "journal_number": "BANKADJ-002",
                "offset_ledger_id": str(expense_ledger.id),
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "BANK_ACCOUNT_LEDGER_REQUIRED"

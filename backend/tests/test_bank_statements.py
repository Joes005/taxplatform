from decimal import Decimal

from tests.conftest import auth_headers, login


async def upload_csv(client, access_token, company_id, *, filename: str, content: bytes):
    return await client.post(
        f"/api/v1/documents?company_id={company_id}",
        headers=auth_headers(access_token),
        data={"document_type": "OTHER"},
        files={"file": (filename, content, "text/csv")},
    )


BANK_MAPPING = {
    "Date": "transaction_date",
    "Narration": "description",
    "Ref": "reference_number",
    "Withdrawal": "debit_amount",
    "Deposit": "credit_amount",
    "Balance": "balance_after_transaction",
}


async def _create_bank_account(client, headers, company_id) -> str:
    response = await client.post(
        f"/api/v1/bank/accounts?company_id={company_id}",
        json={
            "bank_name": "HDFC Bank",
            "account_name": "HDFC Current Account",
            "account_number_masked": "XXXXXX1234",
            "opening_balance": "100000",
            "opening_balance_date": "2026-04-01",
        },
        headers=headers,
    )
    return response.json()["data"]["id"]


async def _create_statement(client, headers, company_id, bank_account_id, *, closing_balance="163500") -> str:
    response = await client.post(
        f"/api/v1/bank/statements?company_id={company_id}",
        json={
            "bank_account_id": bank_account_id,
            "statement_name": "September 2026",
            "period_start": "2026-09-01",
            "period_end": "2026-09-30",
            "opening_balance": "100000",
            "closing_balance": closing_balance,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


class TestBankStatementImport:
    async def test_valid_csv_imports_and_commits(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        bank_account_id = await _create_bank_account(client, headers, company.id)
        statement_id = await _create_statement(client, headers, company.id, bank_account_id)

        csv_content = (
            b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n"
            b"2026-09-01,UPI RECEIVED ABC TRADERS,UPI12345,,50000,150000\n"
            b"2026-09-02,NEFT PAYMENT XYZ SUPPLIERS,NEFT999,12000,,138000\n"
            b"2026-09-03,BANK CHARGES,,500,,137500\n"
            b"2026-09-04,UPI RECEIVED DEF TRADERS,UPI777,,26000,163500\n"
        )
        upload = await upload_csv(
            client, data["access_token"], company.id, filename="stmt.csv", content=csv_content
        )
        document_id = upload.json()["data"]["id"]

        job = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={
                "document_id": document_id,
                "import_type": "BANK_STATEMENT",
                "bank_statement_id": statement_id,
                "column_mapping": BANK_MAPPING,
            },
            headers=headers,
        )
        assert job.status_code == 201, job.text
        body = job.json()["data"]
        assert body["successful_rows"] == 4
        job_id = body["id"]

        commit = await client.post(
            f"/api/v1/accounting/imports/{job_id}/commit?company_id={company.id}", headers=headers
        )
        assert commit.status_code == 200, commit.text
        assert commit.json()["data"]["status"] == "COMPLETED"

        statement = await client.get(
            f"/api/v1/bank/statements/{statement_id}?company_id={company.id}", headers=headers
        )
        assert statement.json()["data"]["status"] == "READY"

        transactions = await client.get(
            f"/api/v1/bank/statements/{statement_id}/transactions?company_id={company.id}", headers=headers
        )
        items = transactions.json()["data"]["items"]
        assert len(items) == 4
        assert all(t["reconciliation_status"] == "UNMATCHED" for t in items)
        credit_row = next(t for t in items if t["reference_number"] == "UPI12345")
        assert credit_row["transaction_type"] == "CREDIT"
        assert credit_row["amount"] == "50000.00"
        assert credit_row["normalized_description"] == "upi received abc traders"

        balance_check = await client.get(
            f"/api/v1/bank/statements/{statement_id}/balance-check?company_id={company.id}", headers=headers
        )
        assert balance_check.json()["data"]["balanced"] is True

    async def test_both_debit_and_credit_rejected(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        bank_account_id = await _create_bank_account(client, headers, company.id)
        statement_id = await _create_statement(client, headers, company.id, bank_account_id)

        csv_content = b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n2026-09-01,BAD ROW,REF1,500,500,100000\n"
        upload = await upload_csv(
            client, data["access_token"], company.id, filename="stmt2.csv", content=csv_content
        )
        document_id = upload.json()["data"]["id"]

        job = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={
                "document_id": document_id,
                "import_type": "BANK_STATEMENT",
                "bank_statement_id": statement_id,
                "column_mapping": BANK_MAPPING,
            },
            headers=headers,
        )
        assert job.json()["data"]["failed_rows"] == 1

        errors = await client.get(
            f"/api/v1/accounting/imports/{job.json()['data']['id']}/errors?company_id={company.id}",
            headers=headers,
        )
        assert errors.json()["data"]["items"][0]["error_code"] == "BOTH_DEBIT_AND_CREDIT"

    async def test_duplicate_row_detected(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        bank_account_id = await _create_bank_account(client, headers, company.id)
        statement_id = await _create_statement(client, headers, company.id, bank_account_id, closing_balance="150000")

        csv_content = (
            b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n"
            b"2026-09-01,UPI RECEIVED ABC TRADERS,UPI12345,,50000,150000\n"
            b"2026-09-01,UPI RECEIVED ABC TRADERS,UPI12345,,50000,150000\n"
        )
        upload = await upload_csv(
            client, data["access_token"], company.id, filename="stmt3.csv", content=csv_content
        )
        document_id = upload.json()["data"]["id"]

        job = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={
                "document_id": document_id,
                "import_type": "BANK_STATEMENT",
                "bank_statement_id": statement_id,
                "column_mapping": BANK_MAPPING,
            },
            headers=headers,
        )
        body = job.json()["data"]
        assert body["successful_rows"] == 1
        assert body["duplicate_rows"] == 1

    async def test_statement_balance_mismatch_detected(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        bank_account_id = await _create_bank_account(client, headers, company.id)
        # Deliberately wrong closing balance.
        statement_id = await _create_statement(client, headers, company.id, bank_account_id, closing_balance="999999")

        csv_content = b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n2026-09-01,DEPOSIT,REF1,,50000,150000\n"
        upload = await upload_csv(
            client, data["access_token"], company.id, filename="stmt4.csv", content=csv_content
        )
        document_id = upload.json()["data"]["id"]
        job = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={
                "document_id": document_id,
                "import_type": "BANK_STATEMENT",
                "bank_statement_id": statement_id,
                "column_mapping": BANK_MAPPING,
            },
            headers=headers,
        )
        await client.post(
            f"/api/v1/accounting/imports/{job.json()['data']['id']}/commit?company_id={company.id}",
            headers=headers,
        )

        balance_check = await client.get(
            f"/api/v1/bank/statements/{statement_id}/balance-check?company_id={company.id}", headers=headers
        )
        result = balance_check.json()["data"]
        assert result["balanced"] is False
        assert Decimal(result["difference"]) == Decimal("849999.00")

    async def test_exclude_and_review_transaction(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        bank_account_id = await _create_bank_account(client, headers, company.id)
        statement_id = await _create_statement(client, headers, company.id, bank_account_id, closing_balance="150000")

        csv_content = b"Date,Narration,Ref,Withdrawal,Deposit,Balance\n2026-09-01,DEPOSIT,REF1,,50000,150000\n"
        upload = await upload_csv(
            client, data["access_token"], company.id, filename="stmt5.csv", content=csv_content
        )
        document_id = upload.json()["data"]["id"]
        job = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={
                "document_id": document_id,
                "import_type": "BANK_STATEMENT",
                "bank_statement_id": statement_id,
                "column_mapping": BANK_MAPPING,
            },
            headers=headers,
        )
        await client.post(
            f"/api/v1/accounting/imports/{job.json()['data']['id']}/commit?company_id={company.id}",
            headers=headers,
        )
        transactions = await client.get(
            f"/api/v1/bank/statements/{statement_id}/transactions?company_id={company.id}", headers=headers
        )
        txn_id = transactions.json()["data"]["items"][0]["id"]

        exclude = await client.post(
            f"/api/v1/bank/transactions/{txn_id}/exclude?company_id={company.id}", headers=headers
        )
        assert exclude.json()["data"]["reconciliation_status"] == "EXCLUDED"

        # Cannot exclude twice.
        exclude_again = await client.post(
            f"/api/v1/bank/transactions/{txn_id}/exclude?company_id={company.id}", headers=headers
        )
        assert exclude_again.status_code == 409

    async def test_company_b_cannot_see_company_a_statement(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin

        data_a = await login(client, admin_a.email, "TestPass1!")
        headers_a = auth_headers(data_a["access_token"])
        bank_account_id = await _create_bank_account(client, headers_a, company_a.id)
        statement_id = await _create_statement(client, headers_a, company_a.id, bank_account_id)

        data_b = await login(client, admin_b.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/bank/statements/{statement_id}?company_id={company_b.id}",
            headers=auth_headers(data_b["access_token"]),
        )
        assert response.status_code == 404

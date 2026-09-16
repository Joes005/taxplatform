import json

from tests.conftest import add_membership, auth_headers, login

GSTR2B_MAPPING = {
    "supplier_gstin": "supplier_gstin",
    "supplier_name": "supplier_name",
    "invoice_number": "invoice_number",
    "invoice_date": "invoice_date",
    "document_type": "document_type",
    "taxable_value": "taxable_value",
    "cgst_amount": "cgst_amount",
    "sgst_amount": "sgst_amount",
    "igst_amount": "igst_amount",
    "cess_amount": "cess_amount",
}


async def _upload_json(client, access_token, company_id, *, filename: str, rows: list[dict]):
    return await client.post(
        f"/api/v1/documents?company_id={company_id}",
        headers=auth_headers(access_token),
        data={"document_type": "GST_REPORT"},
        files={"file": (filename, json.dumps(rows).encode(), "application/json")},
    )


async def _setup_profile_and_period(client, headers, company_id, financial_year_id):
    profile = await client.post(
        f"/api/v1/gst/profile?company_id={company_id}",
        json={"gstin": "27AAPFU0939F1ZV", "legal_name": "Test Co"},
        headers=headers,
    )
    assert profile.status_code == 201, profile.text

    period = await client.post(
        f"/api/v1/gst/return-periods?company_id={company_id}",
        json={"financial_year_id": str(financial_year_id), "year": 2025, "month": 4},
        headers=headers,
    )
    assert period.status_code == 201, period.text
    return period.json()["data"]


VALID_ROWS = [
    {
        "supplier_gstin": "29AABCU9603R1ZJ",
        "supplier_name": "Good Supplier",
        "invoice_number": "SUP-1",
        "invoice_date": "2025-04-05",
        "document_type": "INVOICE",
        "taxable_value": "10000",
        "cgst_amount": "0",
        "sgst_amount": "0",
        "igst_amount": "1800",
        "cess_amount": "0",
    },
    {
        "supplier_gstin": "NOT-A-GSTIN",
        "supplier_name": "Bad Supplier",
        "invoice_number": "SUP-2",
        "invoice_date": "2025-04-06",
        "document_type": "INVOICE",
        "taxable_value": "5000",
        "cgst_amount": "450",
        "sgst_amount": "450",
        "igst_amount": "0",
        "cess_amount": "0",
    },
    {
        "supplier_gstin": "29AABCU9603R1ZJ",
        "supplier_name": "Good Supplier",
        "invoice_number": "SUP-1",
        "invoice_date": "2025-04-05",
        "document_type": "INVOICE",
        "taxable_value": "10000",
        "cgst_amount": "0",
        "sgst_amount": "0",
        "igst_amount": "1800",
        "cess_amount": "0",
    },
]


class TestGSTR2BImport:
    async def test_json_import_parses_validates_and_commits(
        self, client, document_storage, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        period = await _setup_profile_and_period(client, headers, company.id, financial_year_a.id)

        upload = await _upload_json(
            client, data["access_token"], company.id, filename="gstr2b.json", rows=VALID_ROWS
        )
        assert upload.status_code == 201, upload.text
        document_id = upload.json()["data"]["id"]

        job_response = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={
                "document_id": document_id,
                "import_type": "GSTR2B",
                "return_period_id": period["id"],
                "column_mapping": GSTR2B_MAPPING,
            },
            headers=headers,
        )
        assert job_response.status_code == 201, job_response.text
        job = job_response.json()["data"]
        assert job["total_rows"] == 3
        assert job["successful_rows"] == 1
        assert job["failed_rows"] == 1
        assert job["duplicate_rows"] == 1

        commit = await client.post(
            f"/api/v1/accounting/imports/{job['id']}/commit?company_id={company.id}", headers=headers
        )
        assert commit.status_code == 200, commit.text
        assert commit.json()["data"]["status"] == "COMPLETED_WITH_ERRORS"

        records = await client.get(
            f"/api/v1/gst/gstr2b?company_id={company.id}&return_period_id={period['id']}",
            headers=headers,
        )
        assert records.status_code == 200, records.text
        items = records.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["supplier_gstin"] == "29AABCU9603R1ZJ"
        assert items[0]["igst_amount"] == "1800.00"
        assert items[0]["return_period_id"] == period["id"]

    async def test_missing_return_period_rejected(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        upload = await _upload_json(
            client, data["access_token"], company.id, filename="gstr2b.json", rows=VALID_ROWS[:1]
        )
        document_id = upload.json()["data"]["id"]

        response = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={
                "document_id": document_id,
                "import_type": "GSTR2B",
                "column_mapping": GSTR2B_MAPPING,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "RETURN_PERIOD_REQUIRED"

    async def test_auditor_cannot_import_gstr2b(
        self, client, document_storage, db_session, company_a_with_admin, financial_year_a, seeded_rbac
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        period = await _setup_profile_and_period(client, headers, company.id, financial_year_a.id)

        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="auditor2@example.com", role_code="AUDITOR"
        )
        auditor_login = await login(client, auditor.email, "TestPass1!")
        auditor_headers = auth_headers(auditor_login["access_token"])

        upload = await _upload_json(
            client, data["access_token"], company.id, filename="gstr2b.json", rows=VALID_ROWS[:1]
        )
        assert upload.status_code == 201
        document_id = upload.json()["data"]["id"]

        response = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={
                "document_id": document_id,
                "import_type": "GSTR2B",
                "return_period_id": period["id"],
                "column_mapping": GSTR2B_MAPPING,
            },
            headers=auditor_headers,
        )
        assert response.status_code == 403

from app.core.permissions import RoleCode
from tests.conftest import add_membership, auth_headers, create_customer, login


async def upload_csv(client, access_token, company_id, *, filename: str, content: bytes):
    return await client.post(
        f"/api/v1/documents?company_id={company_id}",
        headers=auth_headers(access_token),
        data={"document_type": "OTHER"},
        files={"file": (filename, content, "text/csv")},
    )


CUSTOMERS_CSV = (
    b"Party Name,GSTIN,Email\n"
    b"Alpha Corp,27AAPFU0939F1ZV,alpha@example.com\n"
    b"Beta Traders,,beta@example.com\n"
    b",noowner@example.com,\n"
    b"Alpha Corp,27AAPFU0939F1ZV,dup@example.com\n"
)

CUSTOMER_MAPPING = {"Party Name": "name", "GSTIN": "gstin", "Email": "email"}


class TestImportUploadAndParse:
    async def test_valid_customers_csv_parses_correctly(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        upload_response = await upload_csv(
            client, data["access_token"], company.id, filename="customers.csv", content=CUSTOMERS_CSV
        )
        assert upload_response.status_code == 201
        document_id = upload_response.json()["data"]["id"]

        job_response = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={
                "document_id": document_id,
                "import_type": "CUSTOMERS",
                "column_mapping": CUSTOMER_MAPPING,
            },
            headers=headers,
        )
        assert job_response.status_code == 201, job_response.text
        body = job_response.json()["data"]
        assert body["total_rows"] == 4
        assert body["successful_rows"] == 2
        assert body["failed_rows"] == 1
        assert body["duplicate_rows"] == 1
        assert body["status"] == "READY"

    async def test_missing_required_field_produces_error(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        upload_response = await upload_csv(
            client, data["access_token"], company.id, filename="customers2.csv", content=CUSTOMERS_CSV
        )
        document_id = upload_response.json()["data"]["id"]
        job_response = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={"document_id": document_id, "import_type": "CUSTOMERS", "column_mapping": CUSTOMER_MAPPING},
            headers=headers,
        )
        job_id = job_response.json()["data"]["id"]

        errors_response = await client.get(
            f"/api/v1/accounting/imports/{job_id}/errors?company_id={company.id}", headers=headers
        )
        errors = errors_response.json()["data"]["items"]
        assert len(errors) == 1
        assert errors[0]["error_code"] == "MISSING_REQUIRED_FIELD"
        assert errors[0]["row_number"] == 3

    async def test_incomplete_mapping_rejected(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        upload_response = await upload_csv(
            client, data["access_token"], company.id, filename="customers3.csv", content=CUSTOMERS_CSV
        )
        document_id = upload_response.json()["data"]["id"]

        response = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={"document_id": document_id, "import_type": "CUSTOMERS", "column_mapping": {"GSTIN": "gstin"}},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INCOMPLETE_COLUMN_MAPPING"

    async def test_invalid_date_row_produces_specific_error(
        self, client, document_storage, company_a_with_admin, financial_year_a, customer_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        csv_content = (
            f"Invoice No,Date,Party Name,Taxable Value\n"
            f"SI-1,15/06/2025,{customer_a.name},1000\n"
            f"SI-2,not-a-real-date,{customer_a.name},2000\n"
        ).encode()
        upload_response = await upload_csv(
            client, data["access_token"], company.id, filename="sales.csv", content=csv_content
        )
        document_id = upload_response.json()["data"]["id"]

        job_response = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={
                "document_id": document_id,
                "import_type": "SALES",
                "financial_year_id": str(financial_year_a.id),
                "column_mapping": {
                    "Invoice No": "invoice_number",
                    "Date": "invoice_date",
                    "Party Name": "customer_name",
                    "Taxable Value": "taxable_amount",
                },
            },
            headers=headers,
        )
        body = job_response.json()["data"]
        assert body["successful_rows"] == 1
        assert body["failed_rows"] == 1

        errors_response = await client.get(
            f"/api/v1/accounting/imports/{body['id']}/errors?company_id={company.id}", headers=headers
        )
        errors = errors_response.json()["data"]["items"]
        assert any(e["error_code"] == "INVALID_DATE" for e in errors)

    async def test_missing_customer_produces_error(
        self, client, document_storage, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        csv_content = b"Invoice No,Date,Party Name,Taxable Value\nSI-1,15/06/2025,Nobody Ltd,1000\n"
        upload_response = await upload_csv(
            client, data["access_token"], company.id, filename="sales2.csv", content=csv_content
        )
        document_id = upload_response.json()["data"]["id"]

        job_response = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={
                "document_id": document_id,
                "import_type": "SALES",
                "financial_year_id": str(financial_year_a.id),
                "column_mapping": {
                    "Invoice No": "invoice_number",
                    "Date": "invoice_date",
                    "Party Name": "customer_name",
                    "Taxable Value": "taxable_amount",
                },
            },
            headers=headers,
        )
        body = job_response.json()["data"]
        assert body["failed_rows"] == 1

        errors_response = await client.get(
            f"/api/v1/accounting/imports/{body['id']}/errors?company_id={company.id}", headers=headers
        )
        errors = errors_response.json()["data"]["items"]
        assert any(e["error_code"] == "MISSING_CUSTOMER" for e in errors)


class TestImportCommit:
    async def _create_ready_job(self, client, headers, company):
        upload_response = await upload_csv(
            client, headers["Authorization"].split(" ")[1], company.id,
            filename="commit_customers.csv", content=CUSTOMERS_CSV,
        )
        document_id = upload_response.json()["data"]["id"]
        job_response = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={"document_id": document_id, "import_type": "CUSTOMERS", "column_mapping": CUSTOMER_MAPPING},
            headers=headers,
        )
        return job_response.json()["data"]

    async def test_commit_creates_only_valid_records(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        job = await self._create_ready_job(client, headers, company)

        commit_response = await client.post(
            f"/api/v1/accounting/imports/{job['id']}/commit?company_id={company.id}", headers=headers
        )
        assert commit_response.status_code == 200
        body = commit_response.json()["data"]
        assert body["status"] == "COMPLETED_WITH_ERRORS"
        assert body["successful_rows"] == 2

        customers_response = await client.get(
            f"/api/v1/accounting/customers?company_id={company.id}", headers=headers
        )
        names = {c["name"] for c in customers_response.json()["data"]["items"]}
        assert "Alpha Corp" in names
        assert "Beta Traders" in names

    async def test_cannot_commit_twice(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        job = await self._create_ready_job(client, headers, company)

        await client.post(
            f"/api/v1/accounting/imports/{job['id']}/commit?company_id={company.id}", headers=headers
        )
        second = await client.post(
            f"/api/v1/accounting/imports/{job['id']}/commit?company_id={company.id}", headers=headers
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "INVALID_IMPORT_STATUS"

    async def test_cancel_prevents_commit(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        job = await self._create_ready_job(client, headers, company)

        cancel_response = await client.post(
            f"/api/v1/accounting/imports/{job['id']}/cancel?company_id={company.id}", headers=headers
        )
        assert cancel_response.json()["data"]["status"] == "CANCELLED"

        commit_response = await client.post(
            f"/api/v1/accounting/imports/{job['id']}/commit?company_id={company.id}", headers=headers
        )
        assert commit_response.status_code == 409


class TestImportTenantIsolationAndRBAC:
    async def test_company_a_cannot_import_into_company_b(
        self, client, document_storage, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, _admin_b = company_b_with_admin
        data_a = await login(client, admin_a.email, "TestPass1!")

        upload_response = await upload_csv(
            client, data_a["access_token"], company_a.id, filename="cross.csv", content=CUSTOMERS_CSV
        )
        document_id = upload_response.json()["data"]["id"]

        # Attempting to use company A's own document to import into
        # company B must fail — both because the caller isn't a member of
        # B, and because the document itself doesn't belong to B.
        response = await client.post(
            f"/api/v1/accounting/imports?company_id={company_b.id}",
            json={"document_id": document_id, "import_type": "CUSTOMERS", "column_mapping": CUSTOMER_MAPPING},
            headers=auth_headers(data_a["access_token"]),
        )
        assert response.status_code == 403

    async def test_accountant_cannot_commit_without_permission(
        self, client, document_storage, db_session, seeded_rbac, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        admin_data = await login(client, admin.email, "TestPass1!")
        admin_headers = auth_headers(admin_data["access_token"])

        upload_response = await upload_csv(
            client, admin_data["access_token"], company.id, filename="rbac.csv", content=CUSTOMERS_CSV
        )
        document_id = upload_response.json()["data"]["id"]
        job_response = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={"document_id": document_id, "import_type": "CUSTOMERS", "column_mapping": CUSTOMER_MAPPING},
            headers=admin_headers,
        )
        job_id = job_response.json()["data"]["id"]

        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id,
            email="auditor-import@example.com", role_code=RoleCode.AUDITOR.value,
        )
        auditor_data = await login(client, auditor.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/accounting/imports/{job_id}/commit?company_id={company.id}",
            headers=auth_headers(auditor_data["access_token"]),
        )
        assert response.status_code == 403

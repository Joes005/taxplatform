from app.seed import seed_default_tds_sections_and_rules
from tests.conftest import auth_headers, login


async def upload_csv(client, access_token, company_id, *, filename: str, content: bytes):
    return await client.post(
        f"/api/v1/documents?company_id={company_id}",
        headers=auth_headers(access_token),
        data={"document_type": "OTHER"},
        files={"file": (filename, content, "text/csv")},
    )


TDS_MAPPING = {
    "Deductee": "deductee_name",
    "PAN": "pan",
    "Section": "section_code",
    "Date": "transaction_date",
    "Gross": "gross_amount",
    "TDS": "tds_amount",
}


async def _create_deductee(client, headers, company_id, name="Acme Contractors"):
    response = await client.post(
        f"/api/v1/tds/deductees?company_id={company_id}",
        json={"name": name, "pan": "AAAPA1234A"},
        headers=headers,
    )
    return response.json()["data"]["id"]


class TestTDSImport:
    async def test_valid_tds_csv_parses_and_commits(
        self, client, document_storage, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await _create_deductee(client, headers, company.id)

        csv_content = (
            b"Deductee,PAN,Section,Date,Gross,TDS\n"
            b"Acme Contractors,AAAPA1234A,194J,2025-06-15,100000,10000\n"
        )
        upload = await upload_csv(
            client, data["access_token"], company.id, filename="tds.csv", content=csv_content
        )
        document_id = upload.json()["data"]["id"]

        job = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={"document_id": document_id, "import_type": "TDS", "column_mapping": TDS_MAPPING},
            headers=headers,
        )
        assert job.status_code == 201, job.text
        body = job.json()["data"]
        assert body["successful_rows"] == 1
        job_id = body["id"]

        commit = await client.post(
            f"/api/v1/accounting/imports/{job_id}/commit?company_id={company.id}", headers=headers
        )
        assert commit.status_code == 200, commit.text
        assert commit.json()["data"]["status"] == "COMPLETED"

        transactions = await client.get(
            f"/api/v1/tds/transactions?company_id={company.id}", headers=headers
        )
        items = transactions.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["status"] == "DEDUCTED"
        assert items[0]["tds_amount"] == "10000.00"

    async def test_missing_deductee_produces_error(
        self, client, document_storage, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        csv_content = (
            b"Deductee,PAN,Section,Date,Gross,TDS\n"
            b"Nobody Ltd,AAAPA1234A,194J,2025-06-15,100000,10000\n"
        )
        upload = await upload_csv(
            client, data["access_token"], company.id, filename="tds2.csv", content=csv_content
        )
        document_id = upload.json()["data"]["id"]

        job = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={"document_id": document_id, "import_type": "TDS", "column_mapping": TDS_MAPPING},
            headers=headers,
        )
        body = job.json()["data"]
        assert body["failed_rows"] == 1

        errors = await client.get(
            f"/api/v1/accounting/imports/{body['id']}/errors?company_id={company.id}", headers=headers
        )
        assert errors.json()["data"]["items"][0]["error_code"] == "MISSING_DEDUCTEE"

    async def test_unknown_section_produces_error(
        self, client, document_storage, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await _create_deductee(client, headers, company.id)

        csv_content = (
            b"Deductee,PAN,Section,Date,Gross,TDS\n"
            b"Acme Contractors,AAAPA1234A,999X,2025-06-15,100000,10000\n"
        )
        upload = await upload_csv(
            client, data["access_token"], company.id, filename="tds3.csv", content=csv_content
        )
        document_id = upload.json()["data"]["id"]

        job = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={"document_id": document_id, "import_type": "TDS", "column_mapping": TDS_MAPPING},
            headers=headers,
        )
        body = job.json()["data"]
        assert body["failed_rows"] == 1

        errors = await client.get(
            f"/api/v1/accounting/imports/{body['id']}/errors?company_id={company.id}", headers=headers
        )
        assert errors.json()["data"]["items"][0]["error_code"] == "MISSING_SECTION"

    async def test_duplicate_row_detected(
        self, client, document_storage, db_session, company_a_with_admin, financial_year_a
    ):
        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await _create_deductee(client, headers, company.id)

        csv_content = (
            b"Deductee,PAN,Section,Date,Gross,TDS\n"
            b"Acme Contractors,AAAPA1234A,194J,2025-06-15,100000,10000\n"
            b"Acme Contractors,AAAPA1234A,194J,2025-06-15,100000,10000\n"
        )
        upload = await upload_csv(
            client, data["access_token"], company.id, filename="tds4.csv", content=csv_content
        )
        document_id = upload.json()["data"]["id"]

        job = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={"document_id": document_id, "import_type": "TDS", "column_mapping": TDS_MAPPING},
            headers=headers,
        )
        body = job.json()["data"]
        assert body["successful_rows"] == 1
        assert body["duplicate_rows"] == 1

    async def test_tds_import_requires_tds_import_permission(
        self, client, document_storage, db_session, company_a_with_admin, financial_year_a, seeded_rbac
    ):
        from tests.conftest import add_membership

        await seed_default_tds_sections_and_rules(db_session)
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await _create_deductee(client, headers, company.id)

        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="tds-import-auditor@example.com", role_code="AUDITOR"
        )
        auditor_data = await login(client, auditor.email, "TestPass1!")
        auditor_headers = auth_headers(auditor_data["access_token"])

        csv_content = (
            b"Deductee,PAN,Section,Date,Gross,TDS\n"
            b"Acme Contractors,AAAPA1234A,194J,2025-06-15,100000,10000\n"
        )
        upload = await upload_csv(
            client, data["access_token"], company.id, filename="tds5.csv", content=csv_content
        )
        document_id = upload.json()["data"]["id"]

        response = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={"document_id": document_id, "import_type": "TDS", "column_mapping": TDS_MAPPING},
            headers=auditor_headers,
        )
        assert response.status_code == 403

import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.core.exceptions import AppException
from app.core.permissions import RoleCode
from app.models.document import DocumentType
from app.services.auth_service import RequestMeta
from app.services.document_service import DocumentService
from app.storage.local import LocalStorageProvider
from tests.conftest import add_membership, auth_headers, login
from tests.sample_files import EXE_CONTENT, MIN_CSV, MIN_JPEG, MIN_PDF, MIN_PNG, MIN_XLS, MIN_XLSX


async def upload(
    client: AsyncClient,
    access_token: str,
    company_id,
    *,
    filename: str,
    content: bytes,
    mime_type: str,
    document_type: str = "OTHER",
    description: str | None = None,
):
    data = {"document_type": document_type}
    if description is not None:
        data["description"] = description
    return await client.post(
        f"/api/v1/documents?company_id={company_id}",
        headers=auth_headers(access_token),
        data=data,
        files={"file": (filename, content, mime_type)},
    )


class TestUpload:
    async def test_valid_pdf_upload(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await upload(
            client,
            data["access_token"],
            company.id,
            filename="invoice.pdf",
            content=MIN_PDF,
            mime_type="application/pdf",
            document_type="SALES_INVOICE",
            description="Q1 sales invoice",
        )
        assert response.status_code == 201, response.text
        body = response.json()["data"]
        assert body["original_filename"] == "invoice.pdf"
        assert body["document_type"] == "SALES_INVOICE"
        assert body["status"] == "READY"
        assert body["file_extension"] == "pdf"
        assert len(body["checksum"]) == 64
        assert "storage_path" not in body

    async def test_valid_image_upload(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await upload(
            client,
            data["access_token"],
            company.id,
            filename="receipt.png",
            content=MIN_PNG,
            mime_type="image/png",
            document_type="EXPENSE_BILL",
        )
        assert response.status_code == 201, response.text
        assert response.json()["data"]["file_extension"] == "png"

    async def test_valid_jpeg_upload(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await upload(
            client,
            data["access_token"],
            company.id,
            filename="receipt.jpg",
            content=MIN_JPEG,
            mime_type="image/jpeg",
            document_type="EXPENSE_BILL",
        )
        assert response.status_code == 201, response.text

    async def test_valid_xlsx_upload(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await upload(
            client,
            data["access_token"],
            company.id,
            filename="ledger.xlsx",
            content=MIN_XLSX,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            document_type="FINANCIAL_STATEMENT",
        )
        assert response.status_code == 201, response.text

    async def test_valid_xls_upload(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await upload(
            client,
            data["access_token"],
            company.id,
            filename="ledger.xls",
            content=MIN_XLS,
            mime_type="application/vnd.ms-excel",
            document_type="FINANCIAL_STATEMENT",
        )
        assert response.status_code == 201, response.text

    async def test_valid_csv_upload(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await upload(
            client,
            data["access_token"],
            company.id,
            filename="transactions.csv",
            content=MIN_CSV,
            mime_type="text/csv",
            document_type="BANK_STATEMENT",
        )
        assert response.status_code == 201, response.text

    async def test_unsupported_extension_rejected(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await upload(
            client,
            data["access_token"],
            company.id,
            filename="malware.exe",
            content=EXE_CONTENT,
            mime_type="application/octet-stream",
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "DOCUMENT_TYPE_NOT_SUPPORTED"

    async def test_unsupported_mime_rejected(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await upload(
            client,
            data["access_token"],
            company.id,
            filename="invoice.pdf",
            content=MIN_PDF,
            mime_type="application/zip",  # doesn't match a .pdf
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_FILE"

    async def test_content_signature_mismatch_rejected(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await upload(
            client,
            data["access_token"],
            company.id,
            filename="fake.pdf",
            content=MIN_PNG,  # PNG bytes wearing a .pdf extension + matching mime lie
            mime_type="application/pdf",
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_FILE"

    async def test_oversized_file_rejected(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        oversized = MIN_PDF[:9] + b"0" * (11 * 1024 * 1024)
        response = await upload(
            client,
            data["access_token"],
            company.id,
            filename="huge.pdf",
            content=oversized,
            mime_type="application/pdf",
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "DOCUMENT_TOO_LARGE"

    async def test_missing_document_type_rejected(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.post(
            f"/api/v1/documents?company_id={company.id}",
            headers=auth_headers(data["access_token"]),
            files={"file": ("invoice.pdf", MIN_PDF, "application/pdf")},
        )
        assert response.status_code == 422

    async def test_duplicate_document_rejected(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        first = await upload(
            client,
            data["access_token"],
            company.id,
            filename="invoice.pdf",
            content=MIN_PDF,
            mime_type="application/pdf",
        )
        assert first.status_code == 201

        second = await upload(
            client,
            data["access_token"],
            company.id,
            filename="invoice-copy.pdf",
            content=MIN_PDF,
            mime_type="application/pdf",
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "DOCUMENT_DUPLICATE"


class TestSecurity:
    async def test_company_a_cannot_view_company_b_document(
        self, client, document_storage, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin
        data_b = await login(client, admin_b.email, "TestPass1!")

        upload_response = await upload(
            client,
            data_b["access_token"],
            company_b.id,
            filename="secret.pdf",
            content=MIN_PDF,
            mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]

        data_a = await login(client, admin_a.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/documents/{doc_id}?company_id={company_a.id}",
            headers=auth_headers(data_a["access_token"]),
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

    async def test_company_a_cannot_download_company_b_document(
        self, client, document_storage, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin
        data_b = await login(client, admin_b.email, "TestPass1!")

        upload_response = await upload(
            client,
            data_b["access_token"],
            company_b.id,
            filename="secret.pdf",
            content=MIN_PDF,
            mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]

        data_a = await login(client, admin_a.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/documents/{doc_id}/download?company_id={company_a.id}",
            headers=auth_headers(data_a["access_token"]),
        )
        assert response.status_code == 404

    async def test_company_a_cannot_archive_company_b_document(
        self, client, document_storage, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin
        data_b = await login(client, admin_b.email, "TestPass1!")

        upload_response = await upload(
            client,
            data_b["access_token"],
            company_b.id,
            filename="secret.pdf",
            content=MIN_PDF,
            mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]

        data_a = await login(client, admin_a.email, "TestPass1!")
        response = await client.patch(
            f"/api/v1/documents/{doc_id}/archive?company_id={company_a.id}",
            headers=auth_headers(data_a["access_token"]),
        )
        assert response.status_code == 404

    async def test_company_a_cannot_restore_company_b_document(
        self, client, document_storage, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin
        data_b = await login(client, admin_b.email, "TestPass1!")

        upload_response = await upload(
            client,
            data_b["access_token"],
            company_b.id,
            filename="secret.pdf",
            content=MIN_PDF,
            mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]
        await client.patch(
            f"/api/v1/documents/{doc_id}/archive?company_id={company_b.id}",
            headers=auth_headers(data_b["access_token"]),
        )

        data_a = await login(client, admin_a.email, "TestPass1!")
        response = await client.patch(
            f"/api/v1/documents/{doc_id}/restore?company_id={company_a.id}",
            headers=auth_headers(data_a["access_token"]),
        )
        assert response.status_code == 404

    async def test_company_a_cannot_list_company_b_documents(
        self, client, document_storage, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin
        data_a = await login(client, admin_a.email, "TestPass1!")

        response = await client.get(
            f"/api/v1/documents?company_id={company_b.id}",
            headers=auth_headers(data_a["access_token"]),
        )
        assert response.status_code == 403

    async def test_document_ids_never_collide_across_companies(
        self, client, document_storage, company_a_with_admin, company_b_with_admin
    ):
        """Uploading the identical bytes to two different companies must
        succeed for both — duplicate detection is company-scoped only.
        """
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin
        data_a = await login(client, admin_a.email, "TestPass1!")
        data_b = await login(client, admin_b.email, "TestPass1!")

        response_a = await upload(
            client, data_a["access_token"], company_a.id,
            filename="shared.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        response_b = await upload(
            client, data_b["access_token"], company_b.id,
            filename="shared.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        assert response_a.status_code == 201
        assert response_b.status_code == 201


class TestPermissions:
    async def test_authorized_accountant_can_upload(
        self, client, document_storage, db_session, seeded_rbac, company_a_with_admin
    ):
        company, _admin = company_a_with_admin
        accountant = await add_membership(
            db_session, seeded_rbac, company_id=company.id,
            email="accountant@example.com", role_code=RoleCode.ACCOUNTANT.value,
        )
        data = await login(client, accountant.email, "TestPass1!")

        response = await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        assert response.status_code == 201

    async def test_auditor_cannot_upload(
        self, client, document_storage, db_session, seeded_rbac, company_a_with_admin
    ):
        company, _admin = company_a_with_admin
        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id,
            email="auditor@example.com", role_code=RoleCode.AUDITOR.value,
        )
        data = await login(client, auditor.email, "TestPass1!")

        response = await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"

    async def test_auditor_cannot_archive(
        self, client, document_storage, db_session, seeded_rbac, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id,
            email="auditor2@example.com", role_code=RoleCode.AUDITOR.value,
        )
        admin_data = await login(client, admin.email, "TestPass1!")
        upload_response = await upload(
            client, admin_data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]

        auditor_data = await login(client, auditor.email, "TestPass1!")
        response = await client.patch(
            f"/api/v1/documents/{doc_id}/archive?company_id={company.id}",
            headers=auth_headers(auditor_data["access_token"]),
        )
        assert response.status_code == 403

    async def test_accountant_cannot_permanently_delete(
        self, client, document_storage, db_session, seeded_rbac, company_a_with_admin
    ):
        # Phase 2 exposes no delete endpoint at all (archive-only by design);
        # this documents that expectation at the routing level.
        company, _admin = company_a_with_admin
        accountant = await add_membership(
            db_session, seeded_rbac, company_id=company.id,
            email="accountant2@example.com", role_code=RoleCode.ACCOUNTANT.value,
        )
        data = await login(client, accountant.email, "TestPass1!")
        response = await client.delete(
            f"/api/v1/documents/{uuid.uuid4()}?company_id={company.id}",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 405  # method not allowed - no DELETE route exists

    async def test_authorized_user_can_download(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        upload_response = await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]

        response = await client.get(
            f"/api/v1/documents/{doc_id}/download?company_id={company.id}",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 200
        assert response.content == MIN_PDF

    async def test_unauthenticated_upload_rejected(self, client, document_storage, company_a_with_admin):
        company, _admin = company_a_with_admin
        response = await client.post(
            f"/api/v1/documents?company_id={company.id}",
            data={"document_type": "OTHER"},
            files={"file": ("bill.pdf", MIN_PDF, "application/pdf")},
        )
        assert response.status_code == 401


class TestArchiveRestore:
    async def test_archive_works(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        upload_response = await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]

        response = await client.patch(
            f"/api/v1/documents/{doc_id}/archive?company_id={company.id}",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "ARCHIVED"
        assert response.json()["data"]["is_archived"] is True

    async def test_archiving_twice_rejected(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        upload_response = await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]
        headers = auth_headers(data["access_token"])

        await client.patch(f"/api/v1/documents/{doc_id}/archive?company_id={company.id}", headers=headers)
        response = await client.patch(
            f"/api/v1/documents/{doc_id}/archive?company_id={company.id}", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DOCUMENT_ARCHIVED"

    async def test_archived_document_remains_downloadable(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        upload_response = await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]

        await client.patch(f"/api/v1/documents/{doc_id}/archive?company_id={company.id}", headers=headers)
        response = await client.get(
            f"/api/v1/documents/{doc_id}/download?company_id={company.id}", headers=headers
        )
        assert response.status_code == 200
        assert response.content == MIN_PDF

    async def test_restore_works(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        upload_response = await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]

        await client.patch(f"/api/v1/documents/{doc_id}/archive?company_id={company.id}", headers=headers)
        response = await client.patch(
            f"/api/v1/documents/{doc_id}/restore?company_id={company.id}", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "READY"

    async def test_restore_without_archive_rejected(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        upload_response = await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]

        response = await client.patch(
            f"/api/v1/documents/{doc_id}/restore?company_id={company.id}",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_ARCHIVED"


class TestSearchFilterSort:
    async def _upload_set(self, client, access_token, company_id):
        await upload(
            client, access_token, company_id,
            filename="sales-invoice.pdf", content=MIN_PDF, mime_type="application/pdf",
            document_type="SALES_INVOICE", description="Big client invoice",
        )
        await upload(
            client, access_token, company_id,
            filename="expense.png", content=MIN_PNG, mime_type="image/png",
            document_type="EXPENSE_BILL", description="Office supplies",
        )
        await upload(
            client, access_token, company_id,
            filename="bank-statement.csv", content=MIN_CSV, mime_type="text/csv",
            document_type="BANK_STATEMENT",
        )

    async def test_search_works(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        await self._upload_set(client, data["access_token"], company.id)

        response = await client.get(
            f"/api/v1/documents?company_id={company.id}&search=invoice",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["original_filename"] == "sales-invoice.pdf"

    async def test_type_filter_works(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        await self._upload_set(client, data["access_token"], company.id)

        response = await client.get(
            f"/api/v1/documents?company_id={company.id}&document_type=EXPENSE_BILL",
            headers=auth_headers(data["access_token"]),
        )
        items = response.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["document_type"] == "EXPENSE_BILL"

    async def test_status_filter_works(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await self._upload_set(client, data["access_token"], company.id)

        list_response = await client.get(f"/api/v1/documents?company_id={company.id}", headers=headers)
        doc_id = list_response.json()["data"]["items"][0]["id"]
        await client.patch(f"/api/v1/documents/{doc_id}/archive?company_id={company.id}", headers=headers)

        response = await client.get(
            f"/api/v1/documents?company_id={company.id}&status=ARCHIVED", headers=headers
        )
        items = response.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["id"] == doc_id

    async def test_date_filter_works(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        await self._upload_set(client, data["access_token"], company.id)

        response = await client.get(
            f"/api/v1/documents?company_id={company.id}&date_from=2099-01-01T00:00:00",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 200
        assert response.json()["data"]["items"] == []

    async def test_pagination_works(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        await self._upload_set(client, data["access_token"], company.id)

        response = await client.get(
            f"/api/v1/documents?company_id={company.id}&page=1&page_size=2",
            headers=auth_headers(data["access_token"]),
        )
        body = response.json()["data"]
        assert len(body["items"]) == 2
        assert body["pagination"]["total"] == 3
        assert body["pagination"]["total_pages"] == 2

    async def test_sorting_works(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        await self._upload_set(client, data["access_token"], company.id)

        response = await client.get(
            f"/api/v1/documents?company_id={company.id}&sort_by=file_name&sort_dir=asc",
            headers=auth_headers(data["access_token"]),
        )
        names = [item["original_filename"] for item in response.json()["data"]["items"]]
        assert names == sorted(names)

    async def test_invalid_sort_field_rejected(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.get(
            f"/api/v1/documents?company_id={company.id}&sort_by=storage_path",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 422


class TestStorage:
    async def test_file_and_db_record_created_together(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        response = await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        doc_id = response.json()["data"]["id"]

        stored_files = list(document_storage.root.rglob("*"))
        stored_file_names = [f.name for f in stored_files if f.is_file()]
        assert any(doc_id.replace("-", "") in name for name in stored_file_names)

    async def test_oversized_filename_rejected_before_storage(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        too_long_name = ("a" * 300) + ".pdf"
        response = await upload(
            client, data["access_token"], company.id,
            filename=too_long_name, content=MIN_PDF, mime_type="application/pdf",
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_FILE"
        assert [f for f in document_storage.root.rglob("*") if f.is_file()] == []

    async def test_failed_db_insert_cleans_up_stored_file(
        self, db_session, seeded_rbac, company_a_with_admin
    ):
        """Exercises DocumentService directly with a repository whose
        create() is forced to fail after the file is already on disk — the
        service must delete the orphaned file and convert the raw DB error
        into a clean AppException rather than leaking it or the file.
        """
        company, admin = company_a_with_admin
        temp_dir = tempfile.mkdtemp(prefix="taxplatform-unit-test-storage-")
        storage = LocalStorageProvider(temp_dir)
        service = DocumentService(db_session, storage)

        class FakeUploadFile:
            filename = "bill.pdf"
            content_type = "application/pdf"

            async def read(self) -> bytes:
                return MIN_PDF

        with patch.object(
            service.documents, "create", AsyncMock(side_effect=RuntimeError("simulated DB failure"))
        ):
            try:
                await service.upload_document(
                    company_id=company.id,
                    current_user=admin,
                    file=FakeUploadFile(),
                    document_type=DocumentType.OTHER,
                    description=None,
                    meta=RequestMeta(),
                )
                assert False, "expected an AppException"
            except AppException as exc:
                assert exc.code == "DOCUMENT_STORAGE_ERROR"

        stored_files = [f for f in Path(temp_dir).rglob("*") if f.is_file()]
        assert stored_files == []

    async def test_missing_stored_file_returns_safe_error(
        self, client, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        upload_response = await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]

        # Simulate the file having disappeared from disk (e.g. manual
        # tampering or a storage-backend hiccup) without touching the DB.
        for f in document_storage.root.rglob("*"):
            if f.is_file():
                f.unlink()

        response = await client.get(
            f"/api/v1/documents/{doc_id}/download?company_id={company.id}", headers=headers
        )
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "DOCUMENT_STORAGE_ERROR"
        # No raw filesystem path or OS error message should ever leak.
        assert str(document_storage.root) not in response.text


class TestAuditLogging:
    async def test_upload_is_logged(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )

        response = await client.get(
            f"/api/v1/audit-logs?company_id={company.id}&action=DOCUMENT_UPLOAD",
            headers=auth_headers(data["access_token"]),
        )
        assert response.json()["data"]["pagination"]["total"] == 1

    async def test_download_is_logged(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        upload_response = await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]
        await client.get(f"/api/v1/documents/{doc_id}/download?company_id={company.id}", headers=headers)

        response = await client.get(
            f"/api/v1/audit-logs?company_id={company.id}&action=DOCUMENT_DOWNLOAD", headers=headers
        )
        assert response.json()["data"]["pagination"]["total"] == 1

    async def test_archive_and_restore_are_logged(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        upload_response = await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        doc_id = upload_response.json()["data"]["id"]

        await client.patch(f"/api/v1/documents/{doc_id}/archive?company_id={company.id}", headers=headers)
        await client.patch(f"/api/v1/documents/{doc_id}/restore?company_id={company.id}", headers=headers)

        archive_logs = await client.get(
            f"/api/v1/audit-logs?company_id={company.id}&action=DOCUMENT_ARCHIVE", headers=headers
        )
        restore_logs = await client.get(
            f"/api/v1/audit-logs?company_id={company.id}&action=DOCUMENT_RESTORE", headers=headers
        )
        assert archive_logs.json()["data"]["pagination"]["total"] == 1
        assert restore_logs.json()["data"]["pagination"]["total"] == 1

    async def test_duplicate_attempt_is_logged(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await upload(
            client, data["access_token"], company.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )
        await upload(
            client, data["access_token"], company.id,
            filename="bill-copy.pdf", content=MIN_PDF, mime_type="application/pdf",
        )

        response = await client.get(
            f"/api/v1/audit-logs?company_id={company.id}&action=DOCUMENT_DUPLICATE_ATTEMPT",
            headers=headers,
        )
        assert response.json()["data"]["pagination"]["total"] == 1

    async def test_audit_logs_are_tenant_isolated_for_documents(
        self, client, document_storage, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin
        data_a = await login(client, admin_a.email, "TestPass1!")
        data_b = await login(client, admin_b.email, "TestPass1!")

        await upload(
            client, data_b["access_token"], company_b.id,
            filename="bill.pdf", content=MIN_PDF, mime_type="application/pdf",
        )

        response = await client.get(
            f"/api/v1/audit-logs?company_id={company_a.id}&action=DOCUMENT_UPLOAD",
            headers=auth_headers(data_a["access_token"]),
        )
        assert response.json()["data"]["pagination"]["total"] == 0

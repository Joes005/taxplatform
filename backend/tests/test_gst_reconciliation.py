import json

from tests.conftest import auth_headers, login

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


async def _setup(client, headers, company_id, financial_year_id):
    await client.post(
        f"/api/v1/gst/profile?company_id={company_id}",
        json={"gstin": "27AAPFU0939F1ZV", "legal_name": "Test Co"},
        headers=headers,
    )
    period = await client.post(
        f"/api/v1/gst/return-periods?company_id={company_id}",
        json={"financial_year_id": str(financial_year_id), "year": 2025, "month": 4},
        headers=headers,
    )
    return period.json()["data"]


async def _create_vendor(client, headers, company_id, *, name, gstin):
    response = await client.post(
        f"/api/v1/accounting/vendors?company_id={company_id}",
        json={"name": name, "gstin": gstin},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _create_and_post_purchase(
    client, headers, company_id, financial_year_id, vendor_id, *, invoice_number, supplier_invoice_number, taxable, igst_rate
):
    create = await client.post(
        f"/api/v1/accounting/purchase-invoices?company_id={company_id}",
        json={
            "financial_year_id": str(financial_year_id),
            "vendor_id": vendor_id,
            "invoice_number": invoice_number,
            "invoice_date": "2025-04-10",
            "supplier_invoice_number": supplier_invoice_number,
            "supplier_invoice_date": "2025-04-05",
            "items": [{"quantity": 1, "unit_price": taxable, "igst_rate": igst_rate}],
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


async def _import_gstr2b(client, headers, access_token, company_id, period_id, rows):
    upload = await client.post(
        f"/api/v1/documents?company_id={company_id}",
        headers=auth_headers(access_token),
        data={"document_type": "GST_REPORT"},
        files={"file": ("gstr2b.json", json.dumps(rows).encode(), "application/json")},
    )
    assert upload.status_code == 201, upload.text
    document_id = upload.json()["data"]["id"]

    job = await client.post(
        f"/api/v1/accounting/imports?company_id={company_id}",
        json={
            "document_id": document_id,
            "import_type": "GSTR2B",
            "return_period_id": period_id,
            "column_mapping": GSTR2B_MAPPING,
        },
        headers=headers,
    )
    assert job.status_code == 201, job.text
    job_id = job.json()["data"]["id"]

    commit = await client.post(
        f"/api/v1/accounting/imports/{job_id}/commit?company_id={company_id}", headers=headers
    )
    assert commit.status_code == 200, commit.text


class TestGSTReconciliation:
    async def test_matched_mismatch_books_only_and_2b_only(
        self, client, document_storage, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        period = await _setup(client, headers, company.id, financial_year_a.id)

        vendor_matched = await _create_vendor(
            client, headers, company.id, name="Matched Vendor", gstin="29AABCU9603R1ZJ"
        )
        vendor_mismatch = await _create_vendor(
            client, headers, company.id, name="Mismatch Vendor", gstin="27AAPFU0939F1ZV"
        )
        vendor_books_only = await _create_vendor(
            client, headers, company.id, name="Books Only Vendor", gstin="29AABCU9603R1ZJ"
        )

        await _create_and_post_purchase(
            client, headers, company.id, financial_year_a.id, vendor_matched["id"],
            invoice_number="PINV-1", supplier_invoice_number="SUP-1", taxable=10000, igst_rate=18,
        )
        await _create_and_post_purchase(
            client, headers, company.id, financial_year_a.id, vendor_mismatch["id"],
            invoice_number="PINV-2", supplier_invoice_number="SUP-2", taxable=5000, igst_rate=18,
        )
        await _create_and_post_purchase(
            client, headers, company.id, financial_year_a.id, vendor_books_only["id"],
            invoice_number="PINV-3", supplier_invoice_number="SUP-3", taxable=2000, igst_rate=18,
        )

        await _import_gstr2b(
            client, headers, data["access_token"], company.id, period["id"],
            [
                {
                    "supplier_gstin": "29AABCU9603R1ZJ", "supplier_name": "Matched Vendor",
                    "invoice_number": "SUP-1", "invoice_date": "2025-04-05", "document_type": "INVOICE",
                    "taxable_value": "10000", "cgst_amount": "0", "sgst_amount": "0",
                    "igst_amount": "1800", "cess_amount": "0",
                },
                {
                    "supplier_gstin": "27AAPFU0939F1ZV", "supplier_name": "Mismatch Vendor",
                    "invoice_number": "SUP-2", "invoice_date": "2025-04-05", "document_type": "INVOICE",
                    "taxable_value": "5000", "cgst_amount": "0", "sgst_amount": "0",
                    "igst_amount": "630", "cess_amount": "0",
                },
                {
                    "supplier_gstin": "36AABCU9603R1ZO", "supplier_name": "2B Only Vendor",
                    "invoice_number": "SUP-99", "invoice_date": "2025-04-08", "document_type": "INVOICE",
                    "taxable_value": "3000", "cgst_amount": "0", "sgst_amount": "0",
                    "igst_amount": "540", "cess_amount": "0",
                },
            ],
        )

        run_response = await client.post(
            f"/api/v1/gst/return-periods/{period['id']}/reconciliation?company_id={company.id}",
            headers=headers,
        )
        assert run_response.status_code == 201, run_response.text
        run = run_response.json()["data"]
        assert run["total_purchase_invoices"] == 3
        assert run["matched_count"] == 1
        assert run["mismatch_count"] == 1
        assert run["books_only_count"] == 1
        assert run["gstr2b_only_count"] == 1

        results_response = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/reconciliation/results?company_id={company.id}",
            headers=headers,
        )
        statuses = {r["status"] for r in results_response.json()["data"]["items"]}
        assert statuses == {"MATCHED", "AMOUNT_MISMATCH", "BOOKS_ONLY", "GSTR2B_ONLY"}

    async def test_rerun_replaces_previous_results(
        self, client, document_storage, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        period = await _setup(client, headers, company.id, financial_year_a.id)

        vendor = await _create_vendor(client, headers, company.id, name="V1", gstin="29AABCU9603R1ZJ")
        await _create_and_post_purchase(
            client, headers, company.id, financial_year_a.id, vendor["id"],
            invoice_number="PINV-R1", supplier_invoice_number="SUP-R1", taxable=1000, igst_rate=18,
        )

        first = await client.post(
            f"/api/v1/gst/return-periods/{period['id']}/reconciliation?company_id={company.id}",
            headers=headers,
        )
        assert first.json()["data"]["books_only_count"] == 1

        second = await client.post(
            f"/api/v1/gst/return-periods/{period['id']}/reconciliation?company_id={company.id}",
            headers=headers,
        )
        assert second.status_code == 201
        assert second.json()["data"]["books_only_count"] == 1
        assert second.json()["data"]["id"] != first.json()["data"]["id"]


class TestITCReview:
    async def test_review_and_approve_flow(
        self, client, document_storage, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        period = await _setup(client, headers, company.id, financial_year_a.id)

        vendor = await _create_vendor(client, headers, company.id, name="V2", gstin="29AABCU9603R1ZJ")
        await _create_and_post_purchase(
            client, headers, company.id, financial_year_a.id, vendor["id"],
            invoice_number="PINV-ITC1", supplier_invoice_number="SUP-ITC1", taxable=10000, igst_rate=18,
        )
        await _import_gstr2b(
            client, headers, data["access_token"], company.id, period["id"],
            [{
                "supplier_gstin": "29AABCU9603R1ZJ", "supplier_name": "V2",
                "invoice_number": "SUP-ITC1", "invoice_date": "2025-04-05", "document_type": "INVOICE",
                "taxable_value": "10000", "cgst_amount": "0", "sgst_amount": "0",
                "igst_amount": "1800", "cess_amount": "0",
            }],
        )
        await client.post(
            f"/api/v1/gst/return-periods/{period['id']}/reconciliation?company_id={company.id}",
            headers=headers,
        )

        summary = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/itc/summary?company_id={company.id}",
            headers=headers,
        )
        assert summary.status_code == 200, summary.text
        matched_entry = summary.json()["data"]["MATCHED_ITC"]
        assert matched_entry["count"] == 1
        assert matched_entry["total_itc"] == "1800.00"

        listing = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/itc?company_id={company.id}&category=MATCHED_ITC",
            headers=headers,
        )
        result_id = listing.json()["data"]["items"][0]["id"]

        review = await client.post(
            f"/api/v1/gst/return-periods/{period['id']}/itc/{result_id}/review?company_id={company.id}",
            json={"comment": "Looks good"},
            headers=headers,
        )
        assert review.status_code == 200, review.text
        assert review.json()["data"]["itc_review_status"] == "REVIEWED"

        approve = await client.post(
            f"/api/v1/gst/return-periods/{period['id']}/itc/{result_id}/approve?company_id={company.id}",
            json={"approved": True, "comment": "Approved"},
            headers=headers,
        )
        assert approve.status_code == 200, approve.text
        assert approve.json()["data"]["itc_review_status"] == "ACCEPTED"

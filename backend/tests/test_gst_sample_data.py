"""Exercises the shipped samples/sample_gst_*.csv / sample_gstr2b.* files
through the real import + GST pipeline, so the sample data in the repo can
never silently drift from what the importers/validators actually accept.
"""

import json
from pathlib import Path

import pytest

from tests.conftest import auth_headers, login

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"

CUSTOMER_MAPPING = {
    "Customer Name": "name", "Customer Code": "code", "GSTIN": "gstin",
    "State": "state", "State Code": "state_code", "Email": "email",
}
VENDOR_MAPPING = {
    "Vendor Name": "name", "Vendor Code": "code", "GSTIN": "gstin",
    "State": "state", "State Code": "state_code",
}
SALES_MAPPING = {
    "Invoice Number": "invoice_number", "Invoice Date": "invoice_date", "Customer Name": "customer_name",
    "Taxable Amount": "taxable_amount", "CGST Amount": "cgst_amount", "SGST Amount": "sgst_amount",
    "IGST Amount": "igst_amount", "Cess Amount": "cess_amount", "Place of Supply": "place_of_supply",
    "Place of Supply State Code": "place_of_supply_state_code",
}
PURCHASE_MAPPING = {
    "Invoice Number": "invoice_number", "Invoice Date": "invoice_date", "Vendor Name": "vendor_name",
    "Taxable Amount": "taxable_amount", "CGST Amount": "cgst_amount", "SGST Amount": "sgst_amount",
    "IGST Amount": "igst_amount", "Cess Amount": "cess_amount",
    "Supplier Invoice Number": "supplier_invoice_number", "Supplier Invoice Date": "supplier_invoice_date",
}
GSTR2B_MAPPING = {
    "Supplier GSTIN": "supplier_gstin", "Supplier Name": "supplier_name", "Invoice No": "invoice_number",
    "Invoice Date": "invoice_date", "Doc Type": "document_type", "Taxable Value": "taxable_value",
    "CGST": "cgst_amount", "SGST": "sgst_amount", "IGST": "igst_amount", "Cess": "cess_amount",
}


async def _upload_and_commit(client, headers, access_token, company_id, *, filename, content, mime, import_type, mapping, extra=None):
    upload = await client.post(
        f"/api/v1/documents?company_id={company_id}",
        headers=auth_headers(access_token),
        data={"document_type": "OTHER"},
        files={"file": (filename, content, mime)},
    )
    assert upload.status_code == 201, upload.text
    document_id = upload.json()["data"]["id"]

    payload = {"document_id": document_id, "import_type": import_type, "column_mapping": mapping}
    if extra:
        payload.update(extra)

    job = await client.post(
        f"/api/v1/accounting/imports?company_id={company_id}", json=payload, headers=headers
    )
    assert job.status_code == 201, job.text
    job_id = job.json()["data"]["id"]

    commit = await client.post(
        f"/api/v1/accounting/imports/{job_id}/commit?company_id={company_id}", headers=headers
    )
    assert commit.status_code == 200, commit.text
    return job.json()["data"], commit.json()["data"]


@pytest.mark.skipif(not SAMPLES_DIR.exists(), reason="samples/ directory not present")
class TestGSTSampleData:
    async def test_full_sample_walkthrough(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        access_token = data["access_token"]

        await client.post(
            f"/api/v1/gst/profile?company_id={company.id}",
            json={"gstin": "27AAPFT8890K1Z3", "legal_name": company.legal_name},
            headers=headers,
        )
        # financial_year_a fixture covers 2025-04-01..2026-03-31; our sample dates are all
        # April 2026, so create a matching financial year for this test rather than relying
        # on the fixture's range.
        fy2 = await client.post(
            f"/api/v1/accounting/financial-years?company_id={company.id}",
            json={"name": "2026-27", "start_date": "2026-04-01", "end_date": "2027-03-31", "is_current": True},
            headers=headers,
        )
        fy2_id = fy2.json()["data"]["id"]
        period = await client.post(
            f"/api/v1/gst/return-periods?company_id={company.id}",
            json={"financial_year_id": fy2_id, "year": 2026, "month": 4},
            headers=headers,
        )
        assert period.status_code == 201, period.text
        period_id = period.json()["data"]["id"]

        job, commit = await _upload_and_commit(
            client, headers, access_token, company.id,
            filename="sample_gst_customers.csv",
            content=(SAMPLES_DIR / "sample_gst_customers.csv").read_bytes(),
            mime="text/csv", import_type="CUSTOMERS", mapping=CUSTOMER_MAPPING,
        )
        assert commit["failed_rows"] == 1  # the blank-name row

        job, commit = await _upload_and_commit(
            client, headers, access_token, company.id,
            filename="sample_gst_vendors.csv",
            content=(SAMPLES_DIR / "sample_gst_vendors.csv").read_bytes(),
            mime="text/csv", import_type="VENDORS", mapping=VENDOR_MAPPING,
        )
        assert commit["failed_rows"] == 1  # the invalid-GSTIN row

        job, commit = await _upload_and_commit(
            client, headers, access_token, company.id,
            filename="sample_gst_sales.csv",
            content=(SAMPLES_DIR / "sample_gst_sales.csv").read_bytes(),
            mime="text/csv", import_type="SALES", mapping=SALES_MAPPING,
            extra={"financial_year_id": fy2_id},
        )
        assert commit["successful_rows"] == 5
        assert commit["failed_rows"] == 0

        job, commit = await _upload_and_commit(
            client, headers, access_token, company.id,
            filename="sample_gst_purchases.csv",
            content=(SAMPLES_DIR / "sample_gst_purchases.csv").read_bytes(),
            mime="text/csv", import_type="PURCHASES", mapping=PURCHASE_MAPPING,
            extra={"financial_year_id": fy2_id},
        )
        assert commit["successful_rows"] == 3
        assert commit["failed_rows"] == 1  # not-a-date row

        job, commit = await _upload_and_commit(
            client, headers, access_token, company.id,
            filename="sample_gstr2b.csv",
            content=(SAMPLES_DIR / "sample_gstr2b.csv").read_bytes(),
            mime="text/csv", import_type="GSTR2B", mapping=GSTR2B_MAPPING,
            extra={"return_period_id": period_id},
        )
        assert commit["successful_rows"] == 3
        assert commit["failed_rows"] == 1  # invalid GSTIN row

        # --- GSTR-1 classification ---
        b2b = await client.get(
            f"/api/v1/gst/return-periods/{period_id}/gstr1/b2b?company_id={company.id}", headers=headers
        )
        assert len(b2b.json()["data"]) == 2  # Bangalore Buyers + Mumbai Retail Traders (GINV-002)

        b2c_large = await client.get(
            f"/api/v1/gst/return-periods/{period_id}/gstr1/b2c-large?company_id={company.id}", headers=headers
        )
        assert len(b2c_large.json()["data"]) == 1  # GINV-004

        validation = await client.get(
            f"/api/v1/gst/return-periods/{period_id}/gstr1/validation?company_id={company.id}", headers=headers
        )
        codes = {f["code"] for f in validation.json()["data"]["findings"]}
        assert "MISSING_PLACE_OF_SUPPLY" in codes  # GINV-005

        # --- Reconciliation ---
        run = await client.post(
            f"/api/v1/gst/return-periods/{period_id}/reconciliation?company_id={company.id}", headers=headers
        )
        assert run.status_code == 201, run.text
        result = run.json()["data"]
        assert result["total_purchase_invoices"] == 3
        assert result["matched_count"] == 1  # Steelcore
        assert result["mismatch_count"] == 1  # Northern Paper (amount mismatch)
        assert result["books_only_count"] == 1  # Bangalore Electricals BLR-771
        assert result["gstr2b_only_count"] == 1  # Bangalore Electricals BLR-999

    async def test_xlsx_and_json_variants_match_csv_row_count(
        self, client, company_a_with_admin
    ):
        """The three sample_gstr2b.* files must describe the same four rows —
        this catches the formats silently drifting apart."""
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        access_token = data["access_token"]

        fy = await client.post(
            f"/api/v1/accounting/financial-years?company_id={company.id}",
            json={"name": "2026-27", "start_date": "2026-04-01", "end_date": "2027-03-31", "is_current": True},
            headers=headers,
        )
        period = await client.post(
            f"/api/v1/gst/return-periods?company_id={company.id}",
            json={"financial_year_id": fy.json()["data"]["id"], "year": 2026, "month": 4},
            headers=headers,
        )
        period_id = period.json()["data"]["id"]

        for filename, mime, import_type in [
            ("sample_gstr2b.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "GSTR2B"),
            ("sample_gstr2b.json", "application/json", "GSTR2B"),
        ]:
            _, commit = await _upload_and_commit(
                client, headers, access_token, company.id,
                filename=filename,
                content=(SAMPLES_DIR / filename).read_bytes(),
                mime=mime, import_type=import_type, mapping=GSTR2B_MAPPING,
                extra={"return_period_id": period_id},
            )
            assert commit["total_rows"] == 4, f"{filename}: {commit}"
            assert commit["successful_rows"] == 3, f"{filename}: {commit}"
            assert commit["failed_rows"] == 1, f"{filename}: {commit}"

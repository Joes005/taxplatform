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


class TestGSTR3B:
    async def test_outward_supplies_only_before_any_reconciliation(
        self, client, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        period = await _setup(client, headers, company.id, financial_year_a.id)

        customer = await client.post(
            f"/api/v1/accounting/customers?company_id={company.id}",
            json={"name": "Buyer", "gstin": "29AABCU9603R1ZJ", "state_code": "29"},
            headers=headers,
        )
        customer_id = customer.json()["data"]["id"]

        create = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "customer_id": customer_id,
                "invoice_number": "INV-3B-1",
                "invoice_date": "2025-04-10",
                "place_of_supply_state_code": "29",
                "items": [{"quantity": 1, "unit_price": 10000, "igst_rate": 18}],
            },
            headers=headers,
        )
        invoice_id = create.json()["data"]["id"]
        await client.post(
            f"/api/v1/accounting/sales-invoices/{invoice_id}/post?company_id={company.id}", headers=headers
        )

        response = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr3b?company_id={company.id}", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()["data"]
        assert body["outward_supplies"]["taxable_value"] == "10000.00"
        assert body["outward_supplies"]["igst_amount"] == "1800.00"
        assert body["input_tax_credit"]["itc_approved"] == "0.00"
        assert body["net_liability"]["net_liability"] == "1800.00"

    async def test_approved_itc_reduces_net_liability(
        self, client, document_storage, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        period = await _setup(client, headers, company.id, financial_year_a.id)

        customer = await client.post(
            f"/api/v1/accounting/customers?company_id={company.id}",
            json={"name": "Buyer", "gstin": "29AABCU9603R1ZJ", "state_code": "29"},
            headers=headers,
        )
        customer_id = customer.json()["data"]["id"]
        sale = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "customer_id": customer_id,
                "invoice_number": "INV-3B-2",
                "invoice_date": "2025-04-10",
                "place_of_supply_state_code": "29",
                "items": [{"quantity": 1, "unit_price": 10000, "igst_rate": 18}],
            },
            headers=headers,
        )
        sale_id = sale.json()["data"]["id"]
        await client.post(
            f"/api/v1/accounting/sales-invoices/{sale_id}/post?company_id={company.id}", headers=headers
        )

        vendor = await client.post(
            f"/api/v1/accounting/vendors?company_id={company.id}",
            json={"name": "Supplier", "gstin": "29AABCU9603R1ZJ"},
            headers=headers,
        )
        vendor_id = vendor.json()["data"]["id"]
        purchase = await client.post(
            f"/api/v1/accounting/purchase-invoices?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "vendor_id": vendor_id,
                "invoice_number": "PINV-3B-1",
                "invoice_date": "2025-04-10",
                "supplier_invoice_number": "SUP-3B-1",
                "supplier_invoice_date": "2025-04-05",
                "items": [{"quantity": 1, "unit_price": 4000, "igst_rate": 18}],
            },
            headers=headers,
        )
        purchase_id = purchase.json()["data"]["id"]
        await client.post(
            f"/api/v1/accounting/purchase-invoices/{purchase_id}/post?company_id={company.id}", headers=headers
        )

        upload = await client.post(
            f"/api/v1/documents?company_id={company.id}",
            headers=auth_headers(data["access_token"]),
            data={"document_type": "GST_REPORT"},
            files={
                "file": (
                    "gstr2b.json",
                    json.dumps([
                        {
                            "supplier_gstin": "29AABCU9603R1ZJ", "supplier_name": "Supplier",
                            "invoice_number": "SUP-3B-1", "invoice_date": "2025-04-05",
                            "document_type": "INVOICE", "taxable_value": "4000",
                            "cgst_amount": "0", "sgst_amount": "0", "igst_amount": "720", "cess_amount": "0",
                        }
                    ]).encode(),
                    "application/json",
                )
            },
        )
        document_id = upload.json()["data"]["id"]
        job = await client.post(
            f"/api/v1/accounting/imports?company_id={company.id}",
            json={
                "document_id": document_id,
                "import_type": "GSTR2B",
                "return_period_id": period["id"],
                "column_mapping": GSTR2B_MAPPING,
            },
            headers=headers,
        )
        job_id = job.json()["data"]["id"]
        await client.post(
            f"/api/v1/accounting/imports/{job_id}/commit?company_id={company.id}", headers=headers
        )
        await client.post(
            f"/api/v1/gst/return-periods/{period['id']}/reconciliation?company_id={company.id}", headers=headers
        )

        before = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr3b?company_id={company.id}", headers=headers
        )
        assert before.json()["data"]["input_tax_credit"]["itc_approved"] == "0.00"
        assert before.json()["data"]["net_liability"]["net_liability"] == "1800.00"

        results = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/itc?company_id={company.id}&category=MATCHED_ITC",
            headers=headers,
        )
        result_id = results.json()["data"]["items"][0]["id"]
        await client.post(
            f"/api/v1/gst/return-periods/{period['id']}/itc/{result_id}/approve?company_id={company.id}",
            json={"approved": True},
            headers=headers,
        )

        after = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr3b?company_id={company.id}", headers=headers
        )
        body = after.json()["data"]
        assert body["input_tax_credit"]["itc_approved"] == "720.00"
        assert body["net_liability"]["net_liability"] == "1080.00"

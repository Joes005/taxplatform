from tests.conftest import auth_headers, login


async def _create_gst_profile(client, headers, company_id, *, gstin="27AAPFU0939F1ZV"):
    response = await client.post(
        f"/api/v1/gst/profile?company_id={company_id}",
        json={"gstin": gstin, "legal_name": "Test Co"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _create_return_period(client, headers, company_id, financial_year_id, *, year=2025, month=4):
    response = await client.post(
        f"/api/v1/gst/return-periods?company_id={company_id}",
        json={"financial_year_id": str(financial_year_id), "year": year, "month": month},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _create_customer(
    client, headers, company_id, *, name, gstin=None, state_code=None, is_sez=False, is_export=False
):
    payload = {"name": name, "is_sez": is_sez, "is_export": is_export}
    if gstin:
        payload["gstin"] = gstin
    if state_code:
        payload["state_code"] = state_code
    response = await client.post(
        f"/api/v1/accounting/customers?company_id={company_id}", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _create_and_post_invoice(
    client,
    headers,
    company_id,
    financial_year_id,
    customer_id,
    *,
    invoice_number,
    place_of_supply_state_code,
    items,
    export_type=None,
    shipping_bill_number=None,
    shipping_bill_date=None,
    port_code=None,
):
    body = {
        "financial_year_id": str(financial_year_id),
        "customer_id": str(customer_id),
        "invoice_number": invoice_number,
        "invoice_date": "2025-04-10",
        "place_of_supply_state_code": place_of_supply_state_code,
        "items": items,
    }
    if export_type:
        body["export_type"] = export_type
    if shipping_bill_number:
        body["shipping_bill_number"] = shipping_bill_number
    if shipping_bill_date:
        body["shipping_bill_date"] = shipping_bill_date
    if port_code:
        body["port_code"] = port_code

    create = await client.post(
        f"/api/v1/accounting/sales-invoices?company_id={company_id}",
        json=body,
        headers=headers,
    )
    assert create.status_code == 201, create.text
    invoice_id = create.json()["data"]["id"]

    post = await client.post(
        f"/api/v1/accounting/sales-invoices/{invoice_id}/post?company_id={company_id}", headers=headers
    )
    assert post.status_code == 200, post.text
    return post.json()["data"]


class TestGSTR1:
    async def test_b2b_invoice_appears_in_b2b_section(
        self, client, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_gst_profile(client, headers, company.id)
        period = await _create_return_period(client, headers, company.id, financial_year_a.id)
        customer = await _create_customer(
            client, headers, company.id, name="B2B Buyer", gstin="29AABCU9603R1ZJ", state_code="29"
        )
        await _create_and_post_invoice(
            client,
            headers,
            company.id,
            financial_year_a.id,
            customer["id"],
            invoice_number="INV-B2B-1",
            place_of_supply_state_code="29",
            items=[{"quantity": 1, "unit_price": 10000, "igst_rate": 18}],
        )

        response = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/b2b?company_id={company.id}",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        rows = response.json()["data"]
        assert len(rows) == 1
        assert rows[0]["recipient_gstin"] == "29AABCU9603R1ZJ"
        assert rows[0]["igst_amount"] == "1800.00"

    async def test_b2c_small_invoice_aggregated_by_state_and_rate(
        self, client, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_gst_profile(client, headers, company.id)
        period = await _create_return_period(client, headers, company.id, financial_year_a.id)
        customer = await _create_customer(
            client, headers, company.id, name="B2C Buyer", state_code="27"
        )
        await _create_and_post_invoice(
            client,
            headers,
            company.id,
            financial_year_a.id,
            customer["id"],
            invoice_number="INV-B2C-1",
            place_of_supply_state_code="27",
            items=[{"quantity": 1, "unit_price": 5000, "cgst_rate": 9, "sgst_rate": 9}],
        )

        response = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/b2c-others?company_id={company.id}",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        rows = response.json()["data"]
        assert len(rows) == 1
        assert rows[0]["place_of_supply_state_code"] == "27"
        assert rows[0]["invoice_count"] == 1
        assert rows[0]["taxable_value"] == "5000.00"

    async def test_b2c_large_interstate_invoice_listed_individually(
        self, client, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_gst_profile(client, headers, company.id)
        period = await _create_return_period(client, headers, company.id, financial_year_a.id)
        customer = await _create_customer(
            client, headers, company.id, name="Big B2C Buyer", state_code="29"
        )
        await _create_and_post_invoice(
            client,
            headers,
            company.id,
            financial_year_a.id,
            customer["id"],
            invoice_number="INV-B2C-LARGE-1",
            place_of_supply_state_code="29",
            items=[{"quantity": 1, "unit_price": 300000, "igst_rate": 18}],
        )

        large_response = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/b2c-large?company_id={company.id}",
            headers=headers,
        )
        assert len(large_response.json()["data"]) == 1

        others_response = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/b2c-others?company_id={company.id}",
            headers=headers,
        )
        assert others_response.json()["data"] == []

    async def test_missing_place_of_supply_flagged_review_required_and_validation_error(
        self, client, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_gst_profile(client, headers, company.id)
        period = await _create_return_period(client, headers, company.id, financial_year_a.id)
        customer = await _create_customer(client, headers, company.id, name="No POS Buyer")

        create = await client.post(
            f"/api/v1/accounting/sales-invoices?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "customer_id": customer["id"],
                "invoice_number": "INV-NOPOS-1",
                "invoice_date": "2025-04-10",
                "items": [{"quantity": 1, "unit_price": 1000, "cgst_rate": 9, "sgst_rate": 9}],
            },
            headers=headers,
        )
        assert create.status_code == 201, create.text
        invoice_id = create.json()["data"]["id"]
        await client.post(
            f"/api/v1/accounting/sales-invoices/{invoice_id}/post?company_id={company.id}",
            headers=headers,
        )

        b2b = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/b2b?company_id={company.id}",
            headers=headers,
        )
        assert b2b.json()["data"] == []
        others = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/b2c-others?company_id={company.id}",
            headers=headers,
        )
        assert others.json()["data"] == []

        validation = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/validation?company_id={company.id}",
            headers=headers,
        )
        assert validation.status_code == 200, validation.text
        body = validation.json()["data"]
        codes = {f["code"] for f in body["findings"]}
        assert "MISSING_PLACE_OF_SUPPLY" in codes
        assert body["error_count"] >= 1

    async def test_cancelled_invoice_excluded_but_counted_in_document_summary(
        self, client, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_gst_profile(client, headers, company.id)
        period = await _create_return_period(client, headers, company.id, financial_year_a.id)
        customer = await _create_customer(
            client, headers, company.id, name="Cancel Buyer", state_code="27"
        )
        posted = await _create_and_post_invoice(
            client,
            headers,
            company.id,
            financial_year_a.id,
            customer["id"],
            invoice_number="INV-CANCEL-1",
            place_of_supply_state_code="27",
            items=[{"quantity": 1, "unit_price": 1000, "cgst_rate": 9, "sgst_rate": 9}],
        )
        cancel = await client.post(
            f"/api/v1/accounting/sales-invoices/{posted['id']}/cancel?company_id={company.id}",
            headers=headers,
        )
        assert cancel.status_code == 200, cancel.text

        others = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/b2c-others?company_id={company.id}",
            headers=headers,
        )
        assert others.json()["data"] == []

        docs = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/documents?company_id={company.id}",
            headers=headers,
        )
        rows = {r["document_type"]: r for r in docs.json()["data"]}
        assert rows["Sales Invoice"]["total_count"] == 1
        assert rows["Sales Invoice"]["cancelled_count"] == 1
        assert rows["Sales Invoice"]["net_count"] == 0

    async def test_hsn_summary_flags_missing_hsn_and_aggregates_known_hsn(
        self, client, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_gst_profile(client, headers, company.id)
        period = await _create_return_period(client, headers, company.id, financial_year_a.id)
        customer = await _create_customer(
            client, headers, company.id, name="HSN Buyer", state_code="27"
        )

        product = await client.post(
            f"/api/v1/accounting/products?company_id={company.id}",
            json={"name": "Widget", "item_type": "PRODUCT", "hsn_sac": "8481", "tax_rate": 18},
            headers=headers,
        )
        assert product.status_code == 201, product.text
        product_id = product.json()["data"]["id"]

        await _create_and_post_invoice(
            client,
            headers,
            company.id,
            financial_year_a.id,
            customer["id"],
            invoice_number="INV-HSN-1",
            place_of_supply_state_code="27",
            items=[
                {
                    "product_service_id": product_id,
                    "quantity": 2,
                    "unit_price": 1000,
                    "cgst_rate": 9,
                    "sgst_rate": 9,
                },
                {"quantity": 1, "unit_price": 500, "cgst_rate": 9, "sgst_rate": 9},
            ],
        )

        response = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/hsn?company_id={company.id}",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        rows = response.json()["data"]
        hsn_codes = {r["hsn_sac"] for r in rows}
        assert "8481" in hsn_codes
        assert None in hsn_codes

    async def test_gstr1_requires_gst_profile(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        period = await _create_return_period(client, headers, company.id, financial_year_a.id)
        response = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1?company_id={company.id}", headers=headers
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "GST_PROFILE_REQUIRED"

    async def test_company_b_cannot_view_company_a_gstr1(
        self, client, company_a_with_admin, company_b_with_admin, financial_year_a
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin
        data_a = await login(client, admin_a.email, "TestPass1!")
        headers_a = auth_headers(data_a["access_token"])

        await _create_gst_profile(client, headers_a, company_a.id)
        period = await _create_return_period(client, headers_a, company_a.id, financial_year_a.id)

        data_b = await login(client, admin_b.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1?company_id={company_b.id}",
            headers=auth_headers(data_b["access_token"]),
        )
        assert response.status_code == 404

    async def test_export_with_payment(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_gst_profile(client, headers, company.id)
        period = await _create_return_period(client, headers, company.id, financial_year_a.id)
        customer = await _create_customer(
            client, headers, company.id, name="Overseas Client Inc", is_export=True
        )
        await _create_and_post_invoice(
            client,
            headers,
            company.id,
            financial_year_a.id,
            customer["id"],
            invoice_number="INV-EXP-WP-1",
            place_of_supply_state_code="96",
            export_type="WITH_PAYMENT",
            shipping_bill_number="SB-998877",
            shipping_bill_date="2025-04-12",
            port_code="INBOM1",
            items=[{"quantity": 1, "unit_price": 50000, "igst_rate": 18}],
        )

        resp = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/exports?company_id={company.id}",
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        rows = resp.json()["data"]
        assert len(rows) == 1
        assert rows[0]["invoice_number"] == "INV-EXP-WP-1"
        assert rows[0]["export_type"] == "WITH_PAYMENT"
        assert rows[0]["shipping_bill_number"] == "SB-998877"
        assert rows[0]["port_code"] == "INBOM1"
        assert rows[0]["taxable_value"] == "50000.00"
        assert rows[0]["igst_amount"] == "9000.00"

        b2b_resp = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/b2b?company_id={company.id}",
            headers=headers,
        )
        assert len(b2b_resp.json()["data"]) == 0

    async def test_export_without_payment_under_lut(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_gst_profile(client, headers, company.id)
        period = await _create_return_period(client, headers, company.id, financial_year_a.id)
        customer = await _create_customer(
            client, headers, company.id, name="Foreign Buyer Ltd", is_export=True
        )
        await _create_and_post_invoice(
            client,
            headers,
            company.id,
            financial_year_a.id,
            customer["id"],
            invoice_number="INV-EXP-WOP-1",
            place_of_supply_state_code="96",
            export_type="WITHOUT_PAYMENT",
            items=[{"quantity": 2, "unit_price": 25000, "igst_rate": 0}],
        )

        resp = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/exports?company_id={company.id}",
            headers=headers,
        )
        assert resp.status_code == 200
        rows = resp.json()["data"]
        assert len(rows) == 1
        assert rows[0]["export_type"] == "WITHOUT_PAYMENT"
        assert rows[0]["igst_amount"] == "0.00"

    async def test_sez_supplies(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_gst_profile(client, headers, company.id)
        period = await _create_return_period(client, headers, company.id, financial_year_a.id)
        customer = await _create_customer(
            client,
            headers,
            company.id,
            name="SEZ Developer TechPark",
            gstin="27AAACS1234A1Z1",
            state_code="27",
            is_sez=True,
        )
        await _create_and_post_invoice(
            client,
            headers,
            company.id,
            financial_year_a.id,
            customer["id"],
            invoice_number="INV-SEZ-1",
            place_of_supply_state_code="27",
            export_type="SEZ_WITH_PAYMENT",
            items=[{"quantity": 1, "unit_price": 100000, "igst_rate": 18}],
        )

        resp = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1/exports?company_id={company.id}",
            headers=headers,
        )
        assert resp.status_code == 200
        rows = resp.json()["data"]
        assert len(rows) == 1
        assert rows[0]["export_type"] == "SEZ_WITH_PAYMENT"
        assert rows[0]["recipient_gstin"] == "27AAACS1234A1Z1"

        overview = await client.get(
            f"/api/v1/gst/return-periods/{period['id']}/gstr1?company_id={company.id}",
            headers=headers,
        )
        assert overview.status_code == 200
        data = overview.json()["data"]
        assert data["export_count"] == 1
        assert data["b2b_invoice_count"] == 0


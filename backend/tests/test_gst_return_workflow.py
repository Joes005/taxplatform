from tests.conftest import auth_headers, login


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


class TestGSTReturnWorkflow:
    async def test_full_draft_to_finalized_flow(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        period = await _setup(client, headers, company.id, financial_year_a.id)
        period_id = period["id"]

        generate = await client.post(
            f"/api/v1/gst/return-periods/{period_id}/generate?company_id={company.id}",
            json={"return_type": "GSTR1"},
            headers=headers,
        )
        assert generate.status_code == 201, generate.text
        snapshot = generate.json()["data"]
        assert snapshot["version"] == 1
        assert snapshot["status"] == "DRAFT"
        assert snapshot["summary_data"]["b2b_invoice_count"] == 0

        submit = await client.post(
            f"/api/v1/gst/return-periods/{period_id}/submit-for-review?company_id={company.id}",
            json={"return_type": "GSTR1"},
            headers=headers,
        )
        assert submit.status_code == 200, submit.text
        assert submit.json()["data"]["status"] == "UNDER_REVIEW"

        period_after_submit = await client.get(
            f"/api/v1/gst/return-periods/{period_id}?company_id={company.id}", headers=headers
        )
        assert period_after_submit.json()["data"]["status"] == "UNDER_REVIEW"

        approve = await client.post(
            f"/api/v1/gst/return-periods/{period_id}/approve?company_id={company.id}",
            json={"return_type": "GSTR1", "comment": "Looks correct"},
            headers=headers,
        )
        assert approve.status_code == 200, approve.text
        assert approve.json()["data"]["status"] == "APPROVED"

        finalize = await client.post(
            f"/api/v1/gst/return-periods/{period_id}/finalize?company_id={company.id}",
            json={"return_type": "GSTR1"},
            headers=headers,
        )
        assert finalize.status_code == 200, finalize.text
        assert finalize.json()["data"]["status"] == "FINALIZED"

        # GSTR1 alone finalized -> period stays UNDER_REVIEW until GSTR3B is finalized too.
        period_after_gstr1 = await client.get(
            f"/api/v1/gst/return-periods/{period_id}?company_id={company.id}", headers=headers
        )
        assert period_after_gstr1.json()["data"]["status"] == "UNDER_REVIEW"

        for action, expected_status in [
            ("generate", None),
            ("submit-for-review", "UNDER_REVIEW"),
            ("approve", "APPROVED"),
            ("finalize", "FINALIZED"),
        ]:
            body = {"return_type": "GSTR3B"}
            resp = await client.post(
                f"/api/v1/gst/return-periods/{period_id}/{action}?company_id={company.id}",
                json=body,
                headers=headers,
            )
            assert resp.status_code in (200, 201), resp.text
            if expected_status:
                assert resp.json()["data"]["status"] == expected_status

        period_final = await client.get(
            f"/api/v1/gst/return-periods/{period_id}?company_id={company.id}", headers=headers
        )
        assert period_final.json()["data"]["status"] == "FINALIZED"

    async def test_finalized_snapshot_cannot_be_transitioned_again(
        self, client, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        period = await _setup(client, headers, company.id, financial_year_a.id)
        period_id = period["id"]

        for action in ("generate", "submit-for-review", "approve", "finalize"):
            await client.post(
                f"/api/v1/gst/return-periods/{period_id}/{action}?company_id={company.id}",
                json={"return_type": "GSTR1"},
                headers=headers,
            )

        response = await client.post(
            f"/api/v1/gst/return-periods/{period_id}/submit-for-review?company_id={company.id}",
            json={"return_type": "GSTR1"},
            headers=headers,
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_SNAPSHOT_TRANSITION"

    async def test_regenerate_after_finalize_creates_new_version(
        self, client, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        period = await _setup(client, headers, company.id, financial_year_a.id)
        period_id = period["id"]

        for action in ("generate", "submit-for-review", "approve", "finalize"):
            await client.post(
                f"/api/v1/gst/return-periods/{period_id}/{action}?company_id={company.id}",
                json={"return_type": "GSTR1"},
                headers=headers,
            )

        regenerate = await client.post(
            f"/api/v1/gst/return-periods/{period_id}/generate?company_id={company.id}",
            json={"return_type": "GSTR1"},
            headers=headers,
        )
        assert regenerate.status_code == 201
        assert regenerate.json()["data"]["version"] == 2
        assert regenerate.json()["data"]["status"] == "DRAFT"

        versions = await client.get(
            f"/api/v1/gst/return-periods/{period_id}/snapshots?company_id={company.id}&return_type=GSTR1",
            headers=headers,
        )
        assert len(versions.json()["data"]) == 2

    async def test_accountant_cannot_finalize(
        self, client, db_session, company_a_with_admin, financial_year_a, seeded_rbac
    ):
        from tests.conftest import add_membership

        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        period = await _setup(client, headers, company.id, financial_year_a.id)
        period_id = period["id"]

        accountant = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="accountant@example.com", role_code="ACCOUNTANT"
        )
        accountant_login = await login(client, accountant.email, "TestPass1!")
        accountant_headers = auth_headers(accountant_login["access_token"])

        for action in ("generate", "submit-for-review"):
            resp = await client.post(
                f"/api/v1/gst/return-periods/{period_id}/{action}?company_id={company.id}",
                json={"return_type": "GSTR1"},
                headers=accountant_headers,
            )
            assert resp.status_code in (200, 201), f"{action}: {resp.text}"

        approve = await client.post(
            f"/api/v1/gst/return-periods/{period_id}/approve?company_id={company.id}",
            json={"return_type": "GSTR1"},
            headers=accountant_headers,
        )
        assert approve.status_code == 403

        finalize = await client.post(
            f"/api/v1/gst/return-periods/{period_id}/finalize?company_id={company.id}",
            json={"return_type": "GSTR1"},
            headers=accountant_headers,
        )
        assert finalize.status_code == 403

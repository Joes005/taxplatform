from tests.conftest import auth_headers, login


class TestCrossTenantIsolation:
    async def test_user_cannot_access_other_companys_details(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        _company_a, admin_a = company_a_with_admin
        company_b, _admin_b = company_b_with_admin

        data = await login(client, admin_a.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/companies/{company_b.id}", headers=auth_headers(data["access_token"])
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"

    async def test_user_cannot_list_other_companys_users(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        _company_a, admin_a = company_a_with_admin
        company_b, _admin_b = company_b_with_admin

        data = await login(client, admin_a.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/companies/{company_b.id}/users", headers=auth_headers(data["access_token"])
        )
        assert response.status_code == 403

    async def test_user_cannot_modify_other_companys_details(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        _company_a, admin_a = company_a_with_admin
        company_b, _admin_b = company_b_with_admin

        data = await login(client, admin_a.email, "TestPass1!")
        response = await client.patch(
            f"/api/v1/companies/{company_b.id}",
            json={"legal_name": "Hacked Name"},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 403

    async def test_user_cannot_add_users_to_other_company(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        _company_a, admin_a = company_a_with_admin
        company_b, _admin_b = company_b_with_admin

        data = await login(client, admin_a.email, "TestPass1!")
        response = await client.post(
            f"/api/v1/companies/{company_b.id}/users",
            json={
                "email": "intruder@example.com",
                "first_name": "In",
                "last_name": "Truder",
                "password": "IntruderPass1!",
                "role_code": "ACCOUNTANT",
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 403

    async def test_company_list_only_shows_own_companies(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        _company_a, admin_a = company_a_with_admin
        company_b, _admin_b = company_b_with_admin

        data = await login(client, admin_a.email, "TestPass1!")
        response = await client.get("/api/v1/companies", headers=auth_headers(data["access_token"]))
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        ids = {item["id"] for item in items}
        assert str(company_b.id) not in ids
        assert len(items) == 1

    async def test_company_switch_validates_membership(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        _company_a, admin_a = company_a_with_admin
        company_b, _admin_b = company_b_with_admin

        data = await login(client, admin_a.email, "TestPass1!")
        response = await client.post(
            "/api/v1/auth/select-company",
            json={"company_id": str(company_b.id)},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"

    async def test_company_switch_succeeds_for_valid_membership(self, client, company_a_with_admin):
        company_a, admin_a = company_a_with_admin

        data = await login(client, admin_a.email, "TestPass1!")
        response = await client.post(
            "/api/v1/auth/select-company",
            json={"company_id": str(company_a.id)},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 200
        assert response.json()["data"]["company_id"] == str(company_a.id)

    async def test_audit_logs_are_tenant_isolated(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin

        data_a = await login(client, admin_a.email, "TestPass1!")
        data_b = await login(client, admin_b.email, "TestPass1!")

        # Attempting to read Company B's audit logs as Company A's admin must fail.
        response = await client.get(
            f"/api/v1/audit-logs?company_id={company_b.id}",
            headers=auth_headers(data_a["access_token"]),
        )
        assert response.status_code == 403

        # Company B's own admin can read their own logs, and every entry
        # returned belongs to Company B only.
        own_logs = await client.get(
            f"/api/v1/audit-logs?company_id={company_b.id}",
            headers=auth_headers(data_b["access_token"]),
        )
        assert own_logs.status_code == 200
        for item in own_logs.json()["data"]["items"]:
            assert item["company_id"] == str(company_b.id)

    async def test_inactive_company_blocks_member_access(
        self, client, db_session, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        company.is_active = False
        await db_session.flush()

        data = await login(client, admin.email, "TestPass1!")
        response = await client.get(
            f"/api/v1/companies/{company.id}", headers=auth_headers(data["access_token"])
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"

    async def test_super_admin_can_access_any_company(
        self, client, super_admin, company_a_with_admin, company_b_with_admin
    ):
        company_a, _ = company_a_with_admin
        company_b, _ = company_b_with_admin

        data = await login(client, super_admin.email, "SuperSecret1!")

        for company in (company_a, company_b):
            response = await client.get(
                f"/api/v1/companies/{company.id}", headers=auth_headers(data["access_token"])
            )
            assert response.status_code == 200

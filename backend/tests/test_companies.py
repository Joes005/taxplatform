from tests.conftest import auth_headers, login


class TestCompanyCRUD:
    async def test_super_admin_can_create_company(self, client, super_admin):
        data = await login(client, super_admin.email, "SuperSecret1!")
        response = await client.post(
            "/api/v1/companies",
            json={
                "legal_name": "New Ventures Pvt Ltd",
                "state": "Delhi",
                "city": "New Delhi",
                "pan": "ABCDE1234F",
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 201, response.text
        body = response.json()["data"]
        assert body["legal_name"] == "New Ventures Pvt Ltd"
        assert body["is_active"] is True

    async def test_company_admin_can_read_own_company(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.get(
            f"/api/v1/companies/{company.id}", headers=auth_headers(data["access_token"])
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == str(company.id)

    async def test_company_admin_can_update_own_company(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.patch(
            f"/api/v1/companies/{company.id}",
            json={"trade_name": "Updated Trade Name", "city": "Pune"},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 200, response.text
        body = response.json()["data"]
        assert body["trade_name"] == "Updated Trade Name"
        assert body["city"] == "Pune"

    async def test_unauthorized_access_to_nonexistent_membership(self, client, db_session, seeded_rbac):
        from app.core.security import hash_password
        from app.models.user import User

        user = User(
            email="orphan@example.com",
            password_hash=hash_password("OrphanPass1!"),
            first_name="Orphan",
            last_name="User",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.flush()

        data = await login(client, user.email, "OrphanPass1!")
        import uuid

        response = await client.get(
            f"/api/v1/companies/{uuid.uuid4()}", headers=auth_headers(data["access_token"])
        )
        assert response.status_code == 403

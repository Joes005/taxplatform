import pytest

from tests.conftest import auth_headers, login


class TestRegistration:
    async def test_register_success(self, client, seeded_rbac):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "John",
                "last_name": "Doe",
                "email": "John.Doe@Example.com",
                "password": "StrongPass1!",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["success"] is True
        assert body["data"]["email"] == "john.doe@example.com"
        assert "password" not in body["data"]
        assert "password_hash" not in body["data"]

    async def test_register_duplicate_email_rejected(self, client, seeded_rbac):
        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "dup@example.com",
            "password": "StrongPass1!",
        }
        first = await client.post("/api/v1/auth/register", json=payload)
        assert first.status_code == 201

        second = await client.post("/api/v1/auth/register", json=payload)
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "DUPLICATE_RESOURCE"

    @pytest.mark.parametrize(
        "password",
        ["short1!", "alllowercase1!", "ALLUPPERCASE1!", "NoDigitsHere!", "NoSpecialChar1"],
    )
    async def test_register_weak_password_rejected(self, client, seeded_rbac, password):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Weak",
                "last_name": "Pass",
                "email": "weak@example.com",
                "password": password,
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


class TestLogin:
    async def test_login_success(self, client, seeded_rbac):
        await client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane@example.com",
                "password": "StrongPass1!",
            },
        )
        response = await client.post(
            "/api/v1/auth/login", json={"email": "jane@example.com", "password": "StrongPass1!"}
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["user"]["email"] == "jane@example.com"

    async def test_login_invalid_credentials_rejected(self, client, seeded_rbac):
        await client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane2@example.com",
                "password": "StrongPass1!",
            },
        )
        response = await client.post(
            "/api/v1/auth/login", json={"email": "jane2@example.com", "password": "WrongPass1!"}
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    async def test_login_unknown_email_rejected(self, client, seeded_rbac):
        response = await client.post(
            "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "WrongPass1!"}
        )
        assert response.status_code == 401

    async def test_inactive_user_cannot_login(self, client, db_session, seeded_rbac):
        from app.core.security import hash_password
        from app.models.user import User

        user = User(
            email="inactive@example.com",
            password_hash=hash_password("StrongPass1!"),
            first_name="In",
            last_name="Active",
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.com", "password": "StrongPass1!"},
        )
        assert response.status_code == 401


class TestTokenLifecycle:
    async def _register_and_login(self, client, email="tok@example.com"):
        await client.post(
            "/api/v1/auth/register",
            json={"first_name": "Tok", "last_name": "En", "email": email, "password": "StrongPass1!"},
        )
        return await login(client, email, "StrongPass1!")

    async def test_refresh_token_works(self, client, seeded_rbac):
        data = await self._register_and_login(client)
        response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]}
        )
        assert response.status_code == 200, response.text
        new_data = response.json()["data"]
        assert new_data["access_token"] != data["access_token"]
        assert new_data["refresh_token"] != data["refresh_token"]

    async def test_revoked_refresh_token_rejected(self, client, seeded_rbac):
        data = await self._register_and_login(client, email="revoke@example.com")

        first_refresh = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]}
        )
        assert first_refresh.status_code == 200

        reuse = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]}
        )
        assert reuse.status_code == 401
        assert reuse.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    async def test_logout_revokes_session(self, client, seeded_rbac):
        data = await self._register_and_login(client, email="logout@example.com")

        logout_response = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": data["refresh_token"]},
            headers=auth_headers(data["access_token"]),
        )
        assert logout_response.status_code == 200

        refresh_after_logout = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]}
        )
        assert refresh_after_logout.status_code == 401

    async def test_protected_route_requires_token(self, client, seeded_rbac):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_protected_route_with_token_works(self, client, seeded_rbac):
        data = await self._register_and_login(client, email="me@example.com")
        response = await client.get("/api/v1/auth/me", headers=auth_headers(data["access_token"]))
        assert response.status_code == 200
        assert response.json()["data"]["email"] == "me@example.com"

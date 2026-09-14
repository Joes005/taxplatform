from app.core.permissions import RoleCode
from app.models import CompanyMembership, MembershipStatus, User
from app.core.security import hash_password
from tests.conftest import auth_headers, login


async def _add_membership(db_session, roles, *, company_id, email, role_code, password="TestPass1!"):
    user = User(
        email=email,
        password_hash=hash_password(password),
        first_name="RBAC",
        last_name="Test",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    membership = CompanyMembership(
        user_id=user.id,
        company_id=company_id,
        role_id=roles[role_code].id,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(membership)
    await db_session.flush()
    return user


class TestCompanyAdminPermissions:
    async def test_company_admin_can_manage_users(self, client, db_session, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.post(
            f"/api/v1/companies/{company.id}/users",
            json={
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "password": "NewUserPass1!",
                "role_code": "ACCOUNTANT",
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 201, response.text
        assert response.json()["data"]["role_code"] == "ACCOUNTANT"

    async def test_accountant_cannot_manage_users(
        self, client, db_session, seeded_rbac, company_a_with_admin
    ):
        company, _admin = company_a_with_admin
        accountant = await _add_membership(
            db_session,
            seeded_rbac,
            company_id=company.id,
            email="accountant@example.com",
            role_code=RoleCode.ACCOUNTANT.value,
        )
        data = await login(client, accountant.email, "TestPass1!")

        response = await client.post(
            f"/api/v1/companies/{company.id}/users",
            json={
                "email": "blocked@example.com",
                "first_name": "Should",
                "last_name": "Fail",
                "password": "BlockedPass1!",
                "role_code": "ACCOUNTANT",
            },
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"

    async def test_auditor_cannot_modify_users(
        self, client, db_session, seeded_rbac, company_a_with_admin
    ):
        company, _admin = company_a_with_admin
        auditor = await _add_membership(
            db_session,
            seeded_rbac,
            company_id=company.id,
            email="auditor@example.com",
            role_code=RoleCode.AUDITOR.value,
        )
        data = await login(client, auditor.email, "TestPass1!")

        response = await client.patch(
            f"/api/v1/companies/{company.id}/users/{auditor.id}",
            json={"first_name": "Changed"},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 403

    async def test_auditor_can_view_audit_logs(
        self, client, db_session, seeded_rbac, company_a_with_admin
    ):
        company, _admin = company_a_with_admin
        auditor = await _add_membership(
            db_session,
            seeded_rbac,
            company_id=company.id,
            email="auditor2@example.com",
            role_code=RoleCode.AUDITOR.value,
        )
        data = await login(client, auditor.email, "TestPass1!")

        response = await client.get(
            f"/api/v1/audit-logs?company_id={company.id}", headers=auth_headers(data["access_token"])
        )
        assert response.status_code == 200

    async def test_accountant_cannot_view_audit_logs(
        self, client, db_session, seeded_rbac, company_a_with_admin
    ):
        company, _admin = company_a_with_admin
        accountant = await _add_membership(
            db_session,
            seeded_rbac,
            company_id=company.id,
            email="accountant2@example.com",
            role_code=RoleCode.ACCOUNTANT.value,
        )
        data = await login(client, accountant.email, "TestPass1!")

        response = await client.get(
            f"/api/v1/audit-logs?company_id={company.id}", headers=auth_headers(data["access_token"])
        )
        assert response.status_code == 403


class TestUnauthenticatedAccess:
    async def test_unauthenticated_request_returns_401(self, client, company_a_with_admin):
        company, _admin = company_a_with_admin
        response = await client.get(f"/api/v1/companies/{company.id}/users")
        assert response.status_code == 401

    async def test_only_super_admin_can_create_company(self, client, db_session, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.post(
            "/api/v1/companies",
            json={"legal_name": "Unauthorized Co"},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 403


class TestLastAdminSafeguard:
    async def test_cannot_deactivate_last_company_admin(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.delete(
            f"/api/v1/companies/{company.id}/users/{admin.id}",
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_STATE"

    async def test_cannot_demote_last_company_admin(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")

        response = await client.patch(
            f"/api/v1/companies/{company.id}/users/{admin.id}",
            json={"role_code": "ACCOUNTANT"},
            headers=auth_headers(data["access_token"]),
        )
        assert response.status_code == 400

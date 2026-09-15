import shutil
import tempfile
import uuid
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.permissions import RoleCode
from app.core.security import hash_password
from app.main import app
from app.models import Company, CompanyMembership, MembershipStatus, Role, User
from app.seed import seed_permissions, seed_role_permissions, seed_roles
from app.storage import get_storage_provider
from app.storage.local import LocalStorageProvider

TEST_DATABASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/taxplatform_test"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_database():
    """Creates the schema once per test session using a short-lived engine
    that is disposed immediately after, so it never outlives the event loop
    it was created on (pytest-asyncio gives fixtures and test functions
    independent, function-scoped event loops by default).
    """
    setup_engine = create_async_engine(TEST_DATABASE_URL, future=True)
    async with setup_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await setup_engine.dispose()
    yield
    teardown_engine = create_async_engine(TEST_DATABASE_URL, future=True)
    async with teardown_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await teardown_engine.dispose()


@pytest_asyncio.fixture
async def db_session(_setup_database):
    """Each test gets its own engine (bound to that test's own event loop)
    and runs inside a transaction that is rolled back afterwards, so tests
    never leak state into one another even though they share the same
    Postgres test database.
    """
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    connection = await engine.connect()
    outer_transaction = await connection.begin()
    session_factory = async_sessionmaker(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    session = session_factory()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    yield session

    await session.close()
    await outer_transaction.rollback()
    await connection.close()
    await engine.dispose()
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def client(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seeded_rbac(db_session):
    """Seed roles + permissions (but not the super admin user) into the
    per-test transaction so role/permission lookups behave like production.
    """
    permissions = await seed_permissions(db_session)
    roles = await seed_roles(db_session)
    await seed_role_permissions(db_session, roles, permissions)
    await db_session.flush()
    return roles


@pytest_asyncio.fixture
async def super_admin(db_session, seeded_rbac):
    user = User(
        email="superadmin@example.com",
        password_hash=hash_password("SuperSecret1!"),
        first_name="Super",
        last_name="Admin",
        is_active=True,
        is_verified=True,
        is_platform_super_admin=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _create_user(db_session, *, email: str, password: str = "TestPass1!") -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        first_name="Test",
        last_name="User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _create_company_with_admin(
    db_session, roles, *, legal_name: str, admin_email: str, admin_password: str = "TestPass1!"
) -> tuple[Company, User]:
    company = Company(legal_name=legal_name, state="Maharashtra", city="Mumbai")
    db_session.add(company)
    await db_session.flush()

    user = await _create_user(db_session, email=admin_email, password=admin_password)

    membership = CompanyMembership(
        user_id=user.id,
        company_id=company.id,
        role_id=roles[RoleCode.COMPANY_ADMIN.value].id,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(membership)
    await db_session.flush()

    return company, user


@pytest_asyncio.fixture
async def company_a_with_admin(db_session, seeded_rbac):
    return await _create_company_with_admin(
        db_session,
        seeded_rbac,
        legal_name="Company A Pvt Ltd",
        admin_email="admin-a@example.com",
    )


@pytest_asyncio.fixture
async def company_b_with_admin(db_session, seeded_rbac):
    return await _create_company_with_admin(
        db_session,
        seeded_rbac,
        legal_name="Company B Traders",
        admin_email="admin-b@example.com",
    )


async def create_financial_year(
    db_session, company_id: uuid.UUID, *, name: str = "2025-26", is_current: bool = True
):
    from datetime import date as _date

    from app.models.financial_year import FinancialYear

    fy = FinancialYear(
        company_id=company_id,
        name=name,
        start_date=_date(2025, 4, 1),
        end_date=_date(2026, 3, 31),
        is_current=is_current,
    )
    db_session.add(fy)
    await db_session.flush()
    return fy


@pytest_asyncio.fixture
async def financial_year_a(db_session, company_a_with_admin):
    company, _admin = company_a_with_admin
    return await create_financial_year(db_session, company.id)


@pytest_asyncio.fixture
async def financial_year_b(db_session, company_b_with_admin):
    company, _admin = company_b_with_admin
    return await create_financial_year(db_session, company.id)


async def create_customer(db_session, company_id: uuid.UUID, *, name: str = "Test Customer"):
    from app.models.customer import Customer

    customer = Customer(company_id=company_id, name=name)
    db_session.add(customer)
    await db_session.flush()
    return customer


async def create_vendor(db_session, company_id: uuid.UUID, *, name: str = "Test Vendor"):
    from app.models.vendor import Vendor

    vendor = Vendor(company_id=company_id, name=name)
    db_session.add(vendor)
    await db_session.flush()
    return vendor


async def create_ledger(
    db_session, company_id: uuid.UUID, *, name: str = "Test Ledger", ledger_type: str = "EXPENSE"
):
    from app.models.ledger import Ledger

    ledger = Ledger(company_id=company_id, name=name, ledger_type=ledger_type)
    db_session.add(ledger)
    await db_session.flush()
    return ledger


@pytest_asyncio.fixture
async def customer_a(db_session, company_a_with_admin):
    company, _admin = company_a_with_admin
    return await create_customer(db_session, company.id)


@pytest_asyncio.fixture
async def vendor_a(db_session, company_a_with_admin):
    company, _admin = company_a_with_admin
    return await create_vendor(db_session, company.id)


@pytest_asyncio.fixture
async def ledger_a(db_session, company_a_with_admin):
    company, _admin = company_a_with_admin
    return await create_ledger(db_session, company.id)


@pytest_asyncio.fixture
async def document_storage():
    """Each test gets an isolated temp directory as its document store, so
    upload tests never touch (or depend on) the real ./storage directory.
    """
    temp_dir = tempfile.mkdtemp(prefix="taxplatform-test-storage-")
    provider = LocalStorageProvider(temp_dir)

    def override_get_storage_provider():
        return provider

    app.dependency_overrides[get_storage_provider] = override_get_storage_provider

    yield provider

    app.dependency_overrides.pop(get_storage_provider, None)
    shutil.rmtree(temp_dir, ignore_errors=True)


async def add_membership(
    db_session,
    roles: dict[str, Role],
    *,
    company_id: uuid.UUID,
    email: str,
    role_code: str,
    password: str = "TestPass1!",
) -> User:
    """Creates a user and an ACTIVE membership for `company_id` under the
    given role code — shared by any test that needs a non-admin user with a
    specific role (accountant, auditor, ...) inside an existing company.
    """
    user = await _create_user(db_session, email=email, password=password)
    membership = CompanyMembership(
        user_id=user.id,
        company_id=company_id,
        role_id=roles[role_code].id,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(membership)
    await db_session.flush()
    return user


async def login(client: AsyncClient, email: str, password: str) -> dict:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}

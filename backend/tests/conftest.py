import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.permissions import RoleCode
from app.core.security import hash_password
from app.main import app
from app.models import Company, CompanyMembership, MembershipStatus, User
from app.seed import seed_permissions, seed_role_permissions, seed_roles

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


async def login(client: AsyncClient, email: str, password: str) -> dict:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}

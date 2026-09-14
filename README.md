# Tax Compliance & Audit Support Platform

**Phase 1 — Foundation, Authentication, RBAC & Multi-Tenant Architecture**

A production-oriented, multi-tenant SaaS foundation for a Tax Compliance & Audit Support
Platform for Indian businesses. Phase 1 delivers authentication, role-based access control,
company (tenant) management, user management, and audit logging — the base that future
GST, TDS, Income Tax, reconciliation, and document modules will build on.

> **Scope note:** GST, TDS, Income Tax preparation, Tally integration, OCR, and government
> filing are intentionally **not implemented** in Phase 1. Where the platform anticipates
> them (e.g. `companies.gstin`, `companies.tan`, the `/gst`, `/tds` route namespaces), they
> are marked as future modules, not stubbed-in fakes.

---

## 1. Project Overview

The platform is a **Modular Monolith**: a single FastAPI service organized into clear
layers (API → Service → Repository → ORM), and a single React SPA that talks to it over a
versioned REST API. Every business table carries a `company_id` so tenant isolation is
enforced at the data layer, not just in the UI.

Core Phase 1 capabilities:

- Email/password registration and login with Argon2id password hashing
- JWT access tokens + rotating, hashed, revocable refresh tokens
- Database-backed RBAC (roles, permissions, role-permission mappings) — no hardcoded
  `if role == "admin"` checks scattered through the codebase
- Multi-tenant company membership model (`User` → `CompanyMembership` → `Company` + `Role`)
- Company management, company switching, and company-scoped user management
- A full audit trail for security- and state-changing actions
- A React dashboard, company UI, user management UI, and audit log UI

---

## 2. Architecture

```
React (SPA)
   |
   |  REST (JSON, versioned /api/v1)
   v
FastAPI routers  (app/api/*.py)          — HTTP concerns, dependency injection only
   |
   v
Service layer    (app/services/*.py)     — business rules, orchestration, audit logging
   |
   v
Repository layer (app/repositories/*.py) — all SQL/ORM access, tenant-scoped queries
   |
   v
SQLAlchemy 2.x ORM  →  PostgreSQL
```

Route handlers never talk to the database directly and never contain business logic.
Every company-scoped endpoint re-validates the caller's membership **on the server**, on
every request — the frontend hiding a button is a UX nicety, never a security boundary.

### RBAC model

```
User → CompanyMembership → Role → RolePermission → Permission
```

A `require_permission("PERMISSION_CODE")` FastAPI dependency resolves the caller's
membership for the `{company_id}` in the URL, loads that membership's role, and checks
its permissions — all in one reusable place (`app/core/dependencies.py`), never
duplicated route-by-route.

**Platform Super Admin** is a separate concept from company roles: it's a boolean flag
(`User.is_platform_super_admin`), not a membership. This models the real-world split
between "administers the whole platform" (creates companies, exists outside any one
tenant) and "administers one company" (`COMPANY_ADMIN`, held via membership like every
other role). A super admin bypasses per-company membership checks entirely and is granted
every permission that exists, including ones added by future modules.

### Multi-tenancy

A user's access to a company is never taken from a client-supplied `company_id` alone. Every
company-scoped request re-derives access from `(current_user, company_id_in_url)` against
the `company_memberships` table — see `MembershipRepository.get_active_membership` and the
`get_current_membership` / `require_permission` dependencies. `POST /auth/select-company`
is a UX and audit-trail convenience (it validates membership and returns permissions for
the frontend to render around) — it is not itself the security boundary.

---

## 3. Tech Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x (async, `asyncpg`), Pydantic v2, Alembic,
PostgreSQL 16, Argon2id (`argon2-cffi`), `python-jose` for JWT, pytest / pytest-asyncio / httpx.

**Frontend:** React 18, TypeScript, Vite, React Router, Tailwind CSS, shadcn/ui-style
components (Radix primitives + `class-variance-authority`), TanStack Query, React Hook
Form, Zod.

**Infra:** Docker, Docker Compose, PostgreSQL container. Redis/Celery/AWS are intentionally
out of scope for Phase 1.

---

## 4. Folder Structure

```
tax-compliance-platform/
├── backend/
│   ├── app/
│   │   ├── main.py                 FastAPI app, middleware, exception handlers
│   │   ├── core/                   config, database, security, dependencies, exceptions,
│   │   │                           permissions catalogue
│   │   ├── models/                 SQLAlchemy ORM models
│   │   ├── schemas/                Pydantic request/response schemas
│   │   ├── api/                    route handlers (thin — validation + service calls)
│   │   ├── services/                business logic + audit logging
│   │   ├── repositories/           all DB queries, tenant-scoped
│   │   ├── utils/                  GUID type, password validators
│   │   └── seed.py                 idempotent roles/permissions/super-admin seed
│   ├── alembic/                    migrations
│   ├── tests/                      pytest suite (auth, RBAC, multi-tenancy, companies)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/             shared UI (shadcn-style primitives in components/ui)
│   │   ├── layouts/                AppLayout (sidebar+topbar), AuthLayout
│   │   ├── pages/                  auth, dashboard, companies, users, audit-logs, settings, errors
│   │   ├── services/                thin fetch wrappers per resource
│   │   ├── hooks/                   useAuth, useToast, TanStack Query hooks
│   │   ├── types/                   API response types
│   │   ├── lib/                     api-client (fetch + refresh), token/session storage, utils
│   │   └── router/                  route table + ProtectedRoute
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 5. Local Setup (Docker — recommended)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit backend/.env: set a real JWT_SECRET_KEY and a strong SEED_SUPER_ADMIN_PASSWORD

docker compose up
```

This starts PostgreSQL, runs Alembic migrations, seeds roles/permissions/super-admin, and
starts both the backend (http://localhost:8000) and frontend (http://localhost:5173).

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

## 6. Local Setup (without Docker)

**Backend**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # point DATABASE_URL / DATABASE_URL_SYNC at your local Postgres

alembic upgrade head
python -m app.seed

uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

---

## 7. Environment Variables

**`backend/.env`**

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Async SQLAlchemy URL (`asyncpg`) used by the running app |
| `DATABASE_URL_SYNC` | Sync URL (`psycopg2`) used by Alembic |
| `JWT_SECRET_KEY` | Signing key for access tokens — **must** be a long random secret in production |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (default 15) |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime (default 7) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `SEED_SUPER_ADMIN_EMAIL` / `_PASSWORD` / `_FIRST_NAME` / `_LAST_NAME` | Bootstrap super admin, development only |

**`frontend/.env`**

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Base URL of the backend API, e.g. `http://localhost:8000/api/v1` |

No secrets are committed — `.env` is git-ignored; only `.env.example` files are tracked.

---

## 8. Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1     # roll back one revision
```

The initial migration creates `users`, `companies`, `roles`, `permissions`,
`role_permissions`, `company_memberships`, `refresh_tokens`, and `audit_logs`, with indexes
on `users.email`, `company_memberships.user_id` / `company_id` (including a **partial
unique index** enforcing one *active* membership per user/company pair),
`audit_logs.company_id`, and `audit_logs.created_at`.

## 9. Seed Data

```bash
python -m app.seed
```

Idempotent — safe to run repeatedly. Seeds:

- Roles: `SUPER_ADMIN`, `COMPANY_ADMIN`, `ACCOUNTANT`, `AUDITOR`
- The full Phase 1 permission catalogue (`app/core/permissions.py`) and role→permission
  mappings
- One bootstrap platform super admin, from `SEED_SUPER_ADMIN_*` env vars — never
  hardcoded, and the password must be changed before any real deployment

## 10. Running the Backend

```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload
```

## 11. Running the Frontend

```bash
cd frontend
npm run dev
```

## 12. Testing

```bash
cd backend && source .venv/bin/activate
pytest -q
```

The suite runs against a real PostgreSQL database (`taxplatform_test` by default — see
`tests/conftest.py`), not SQLite, so tenant-isolation and RBAC behavior is verified
against the same engine Phase 1 runs on in production. Each test runs inside a rolled-back
transaction (via a `SAVEPOINT`), so tests never leak state into one another.

Coverage includes:

- **Auth:** registration, duplicate email rejection, password strength rejection, login,
  invalid credentials, inactive-user login rejection, refresh rotation, revoked-token
  rejection, logout revocation
- **RBAC:** Company Admin can manage users; Accountant and Auditor cannot; unauthenticated
  requests return 401; non-super-admins cannot create companies
- **Multi-tenancy:** cross-company read/list/update/user-add all return 403; company list
  only shows the caller's own companies; company switching validates membership; audit
  logs are tenant-isolated; a super admin can reach any company
- **Companies:** create, read, update; the "cannot remove/demote the last Company Admin"
  safeguard

## 13. API Documentation

Interactive OpenAPI docs are served at `/docs` (Swagger UI) and `/redoc` while the backend
is running. All routes are versioned under `/api/v1`.

---

## 14. Authentication Flow

1. `POST /api/v1/auth/register` — creates a user (`is_verified=false`; Phase 1 has no
   email provider, so verification is a flag future phases can act on).
2. `POST /api/v1/auth/login` — verifies the Argon2id hash, issues a short-lived JWT
   **access token** and an opaque **refresh token**. Only a SHA-256 hash of the refresh
   token is stored server-side (`refresh_tokens.token_hash`); the raw token is returned to
   the client exactly once.
3. Every authenticated request sends `Authorization: Bearer <access_token>`.
4. `POST /api/v1/auth/refresh` — **rotates** the refresh token: the presented token is
   revoked and a new one issued in the same call. Presenting an already-used or revoked
   refresh token is rejected with 401, which detects token replay/theft.
5. `POST /api/v1/auth/logout` — revokes the refresh token, ending that session.
6. `POST /api/v1/auth/select-company` — validates the caller's membership in the requested
   company and returns that company's role + permission list for the frontend to use.

The frontend's `apiClient` (`frontend/src/lib/api-client.ts`) automatically retries a
401 once after a silent token refresh, and redirects to `/login` if the refresh itself
fails.

## 15. RBAC Explanation

Permissions are **data**, not code branches. `app/core/permissions.py` is the single
source of truth for the permission catalogue and role→permission mapping (seeded into
`roles`, `permissions`, `role_permissions`). A route declares what it needs —
`Depends(require_permission(PermissionCode.USER_CREATE.value))` — and the dependency in
`app/core/dependencies.py` resolves membership → role → permissions and allows or denies
(403) accordingly. `401` is reserved for "who are you" failures (missing/invalid/expired
token); `403` is reserved for "I know who you are, but no."

Adding a new permission for a future module means adding one line to
`app/core/permissions.py` and one seed row — never touching route handlers that already
exist.

## 16. Multi-Tenancy Explanation

See [Architecture](#2-architecture) above. In one sentence: **every company-scoped read or
write re-checks `(user, company_id)` against `company_memberships` on the server, every
time** — the `company_id` in a URL or request body is treated as untrusted input, never as
authorization.

## 17. Future Module Roadmap

Phase 1 deliberately leaves these as route-namespace placeholders only
(`/gst`, `/tds`, `/income-tax`, `/documents`, `/reconciliation`, `/bank`, `/audit`,
`/compliance`, `/reports`, `/tally`, `/integrations`):

| Phase | Module |
|---|---|
| 2 | GST Compliance (GSTR-1, GSTR-3B, GSTR-2B reconciliation) |
| 3 | TDS Compliance |
| 4 | Bank Reconciliation |
| — | Income Tax preparation support, Document management, CA/Auditor review workflows, Compliance calendar, Tax/audit reports, Tally import, government portal integrations |

Each future module is expected to live in its own `models/ schemas/ services/
repositories/ api/` subtree (per `app/core/permissions.py`'s module grouping), reusing —
never re-implementing — the authentication, RBAC, tenant-isolation, and audit-logging
foundation built in Phase 1.

---

## 18. Key Architectural Decisions

- **Modular monolith, not microservices.** One deployable backend, cleanly layered, so
  future modules are new packages inside `app/`, not new services to operate.
- **Platform Super Admin is a user flag, not a role held via membership**, because it
  models platform-wide authority (creating companies before any membership can exist)
  that a company-scoped role cannot represent.
- **Refresh tokens are opaque, hashed, and rotated**, not JWTs — this lets a token be
  revoked server-side (a signed JWT refresh token can't be un-issued before it expires)
  and makes reuse-after-rotation a detectable signal of token theft.
- **Cross-dialect `GUID` column type** (`app/utils/types.py`): native `UUID` on
  PostgreSQL, a 32-char hex `CHAR` elsewhere. This lets the test suite run the exact same
  models against a real Postgres test database without any SQLite special-casing.
- **A partial unique index**, not just a uniqueness check in code, enforces "one active
  membership per user per company" at the database layer — the constraint holds even
  under concurrent requests.
- **Tokens are stored in `localStorage` on the frontend** for Phase 1 simplicity — a
  known XSS-exposure tradeoff versus httpOnly cookies, isolated entirely behind
  `frontend/src/lib/token-storage.ts` so a future phase can switch strategies without
  touching the rest of the auth flow.

---

## 19. Security Notes

- Passwords are hashed with **Argon2id** (`argon2-cffi`), never stored or logged in
  plaintext.
- Refresh tokens are stored as **SHA-256 hashes only**; the raw token is returned to the
  client exactly once, at issuance/rotation.
- No password, access token, or refresh token is ever written to application logs.
- All ORM queries go through SQLAlchemy's parameterized query builder — no raw SQL string
  interpolation.
- CORS origins are explicit and environment-configured, not wildcarded.
- Error responses never leak stack traces; unhandled exceptions are logged server-side
  and returned to the client as a generic `INTERNAL_ERROR`.
- Every response follows one of two envelopes:
  `{"success": true, "data": ..., "message": ...}` or
  `{"success": false, "error": {"code", "message", "fields"}}`.

# Tax Compliance & Audit Support Platform

**Phase 1 — Foundation, Authentication, RBAC & Multi-Tenant Architecture**
**Phase 2 — Document Management & Data Ingestion**

A production-oriented, multi-tenant SaaS foundation for a Tax Compliance & Audit Support
Platform for Indian businesses. Phase 1 delivers authentication, role-based access control,
company (tenant) management, user management, and audit logging. Phase 2 builds a complete
local document management module on top of it — upload, validation, storage, search, secure
download, and archival — the base that future GST, TDS, Income Tax, and reconciliation
modules will build on.

> **Scope note:** GST, TDS, Income Tax preparation, Tally integration, OCR/AI extraction,
> and government filing are intentionally **not implemented**. Where the platform
> anticipates them (e.g. `companies.gstin`, the `document_links` table, the `/gst`, `/tds`
> route namespaces), they are marked as future modules, not stubbed-in fakes. **Phase 2 has
> no paid or cloud dependency** — documents are validated and stored entirely on the local
> filesystem; everything runs offline via `docker compose up`.

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

Core Phase 2 capabilities:

- Secure document upload (`multipart/form-data`) with extension + declared-MIME +
  magic-byte signature validation, a configurable size cap, and SHA-256 checksums
- Per-company duplicate detection (identical file content is rejected, not silently
  re-stored)
- Local filesystem storage behind a `StorageProvider` abstraction (swappable for a cloud
  backend later without touching the service, API, model, or frontend)
- Tenant-isolated search, filter (type/status/uploader/date range), sort, and pagination
- Secure, streamed download; archive/restore lifecycle (no destructive delete for normal
  users — documents are compliance evidence)
- A `document_links` table laying the foundation for linking documents to future business
  records (invoices, bank transactions, GST returns) without those tables existing yet
- A React documents page with drag-and-drop upload, native PDF/image preview, and full
  audit-activity visibility per document

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

Phase 2 adds one more layer beneath the service layer for documents specifically:

```
Service layer (DocumentService)
   |
   v
StorageProvider abstraction (app/storage/)  →  LocalStorageProvider  →  ./storage/
```

`DocumentService` never touches the filesystem directly — it calls `storage.save()` /
`.get()` / `.delete()` / `.exists()`. Swapping `LocalStorageProvider` for a future
`S3StorageProvider` is a one-line change in `app/storage/__init__.py::get_storage_provider`;
nothing above that layer changes.

### Document routes and tenant scoping

Documents deliberately use **flat** routes (`/api/v1/documents`, not
`/api/v1/companies/{company_id}/documents`) to match the spec's API shape, while still
reusing Phase 1's `require_permission` dependency completely unchanged: FastAPI resolves a
dependency's `company_id` parameter as a **path** parameter when the route path contains
`{company_id}`, and automatically falls back to a **required query parameter**
(`?company_id=...`) when it doesn't. So `GET /api/v1/documents?company_id=...` runs through
the exact same membership-and-permission check as `GET /api/v1/companies/{company_id}`,
with zero changes to `app/core/dependencies.py`. Every document lookup is additionally
scoped by `company_id` at the repository layer (`WHERE company_id = :company_id AND id =
:document_id`), so a valid membership in *your* company can never resolve a document that
belongs to another one — confirmed by the cross-tenant tests in
`tests/test_documents.py::TestSecurity`.

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
│   │   ├── storage/                 StorageProvider abstraction (base.py) + LocalStorageProvider
│   │   ├── utils/                  GUID type, password validators, file-signature validation
│   │   └── seed.py                 idempotent roles/permissions/super-admin seed
│   ├── alembic/                    migrations
│   ├── storage/                    local document storage root (git-ignored, created at runtime)
│   ├── tests/                      pytest suite (auth, RBAC, multi-tenancy, companies, documents)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/             shared UI (shadcn-style primitives in components/ui)
│   │   ├── layouts/                AppLayout (sidebar+topbar), AuthLayout
│   │   ├── pages/                  auth, dashboard, companies, users, documents, audit-logs, settings, errors
│   │   ├── services/                thin fetch wrappers per resource
│   │   ├── hooks/                   useAuth, useToast, TanStack Query hooks
│   │   ├── types/                   API response types
│   │   ├── lib/                     api-client (fetch + refresh + upload/downloadBlob), token/session storage, utils
│   │   └── router/                  route table + ProtectedRoute
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

`app/models/document.py`, `app/schemas/document.py`, `app/api/documents.py`,
`app/services/document_service.py`, and `app/repositories/document_repository.py` follow
the same flat-per-layer convention as every Phase 1 resource — no separate nested
`documents/` package was introduced, to stay consistent with the existing codebase rather
than restructure it.

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
| `DOCUMENT_STORAGE_PATH` | Root directory for local document storage (default `./storage`) |
| `MAX_UPLOAD_SIZE_MB` | Per-file upload size cap (default 10) |
| `ALLOWED_DOCUMENT_EXTENSIONS` | Comma-separated whitelist (default `pdf,jpg,jpeg,png,xlsx,xls,csv`) — this can only *narrow* the set of types the backend knows how to signature-check (`app/utils/file_validation.py`), never expand beyond it |

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

A second migration (Phase 2) adds `documents` — indexed on `company_id`, `document_type`,
`status`, a composite `(company_id, uploaded_at)` for the default sort, and a composite
`(company_id, checksum)` for duplicate detection — and `document_links`, the generic
future-linking table (indexed on `document_id` and on `(company_id, resource_type,
resource_id)` for reverse lookups once a future module needs them). Neither migration
alters a Phase 1 table.

## 9. Seed Data

```bash
python -m app.seed
```

Idempotent — safe to run repeatedly. Seeds:

- Roles: `SUPER_ADMIN`, `COMPANY_ADMIN`, `ACCOUNTANT`, `AUDITOR`
- The full permission catalogue (`app/core/permissions.py`, now including 8 `DOCUMENT_*`
  permissions from Phase 2) and role→permission mappings
- One bootstrap platform super admin, from `SEED_SUPER_ADMIN_*` env vars — never
  hardcoded, and the password must be changed before any real deployment

`DOCUMENT_DELETE` and `DOCUMENT_MANAGE` are deliberately not granted to any seeded
company-level role — only a platform super admin (via the `is_platform_super_admin`
bypass) has them, per the spec's requirement that permanent deletion stay restricted.

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
- **Documents (Phase 2):** valid upload for every supported type (PDF, JPG, JPEG, PNG,
  XLSX, XLS, CSV); rejection of unsupported extensions, MIME/content mismatches, oversized
  files, missing document type, and duplicates; cross-tenant view/download/archive/restore
  all return 404 (not 403 — see the Security Notes below on why); role-based upload/archive
  permission checks; the archive→restore lifecycle and its invalid-state guards; search,
  type/status/date filters, sorting (with an explicit whitelist rejection test), and
  pagination; a file-plus-DB-record creation test; and a unit test that forces a DB failure
  after the file is already on disk to prove the orphaned file gets cleaned up and the raw
  DB error never leaks to the client
- **Audit logging (Phase 2):** upload, download, archive, restore, and duplicate-attempt
  are all logged and tenant-isolated

## 13. API Documentation

Interactive OpenAPI docs are served at `/docs` (Swagger UI) and `/redoc` while the backend
is running. All routes are versioned under `/api/v1`, including the Phase 2 document
endpoints:

```
POST   /api/v1/documents?company_id=...                       multipart upload
GET    /api/v1/documents?company_id=...&search=...&...        list/search/filter/sort/paginate
GET    /api/v1/documents/{document_id}?company_id=...          metadata
GET    /api/v1/documents/{document_id}/download?company_id=... streamed file
PATCH  /api/v1/documents/{document_id}?company_id=...           update type/description
PATCH  /api/v1/documents/{document_id}/archive?company_id=...
PATCH  /api/v1/documents/{document_id}/restore?company_id=...
```

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

## 17. Document Management Explanation (Phase 2)

The upload pipeline follows the spec's process exactly, in `DocumentService.upload_document`
(`app/services/document_service.py`):

```
Permission check (require_permission, at the route)
   → File validation (extension + declared MIME + magic-byte signature)
   → SHA-256 checksum
   → Duplicate check (same checksum, same company, non-archived)
   → storage.save()
   → Document row created
   → Audit log
   → Response (metadata only — never the internal storage path)
```

**Validation never trusts the filename extension alone.** `app/utils/file_validation.py`
holds a small registry mapping each allowed extension to its accepted declared MIME
types and, where the format has one, a real magic-byte signature (`%PDF-` for PDF, the PNG
8-byte signature, `\xff\xd8\xff` for JPEG, the ZIP signature for XLSX, the OLE2 signature
for XLS). A file must match on extension, declared MIME type, *and* content signature — a
`.pdf` that is actually PNG bytes wearing a matching `Content-Type: application/pdf` lie is
still rejected, because the signature check inspects the real leading bytes. CSV has no
fixed signature, so it's instead checked for being plausible, non-binary text.

**Storage failure handling is transactional in spirit, if not in a literal DB transaction**
(the file lives outside Postgres): if `storage.save()` fails, no DB row is ever created; if
the DB insert fails after the file was already written, the file is deleted and the session
is rolled back before a clean `AppException` (never the raw DB/driver error) is raised —
see `tests/test_documents.py::TestStorage::test_failed_db_insert_cleans_up_stored_file`,
which forces this exact failure with a mocked repository and asserts no file is left behind.

**Duplicate detection** is scoped to `(company_id, checksum)` and excludes already-archived
documents (an archived original no longer blocks re-upload of the same content) — see
`DocumentRepository.get_by_checksum_for_company`.

**Archive, not delete.** Phase 2 exposes no delete endpoint at all for normal roles;
`PATCH .../archive` and `.../restore` are logical status transitions
(`READY ⇄ ARCHIVED`), and an archived document's file and metadata are untouched and
remain downloadable to authorized users — documents are compliance evidence, and Phase 2
never destroys them.

## 18. Future Module Roadmap

These remain route-namespace placeholders only, ready for a future module to fill in
without touching Phase 1 or Phase 2 (`/gst`, `/tds`, `/income-tax`, `/reconciliation`,
`/bank`, `/audit`, `/compliance`, `/reports`, `/tally`, `/integrations`):

| Phase | Module |
|---|---|
| 1 | Foundation, auth, RBAC, multi-tenancy, audit logging *(done)* |
| 2 | Document management & local data ingestion *(done)* |
| 3 | GST Compliance (GSTR-1, GSTR-3B, GSTR-2B reconciliation) |
| 4 | TDS Compliance |
| 5 | Bank Reconciliation |
| — | Income Tax preparation support, OCR/data extraction (`DocumentProcessor` extension point), CA/Auditor review workflows, Compliance calendar, Tax/audit reports, Tally import, government portal integrations |

Each future module is expected to live in its own `models/ schemas/ services/
repositories/ api/` subtree (per `app/core/permissions.py`'s module grouping), reusing —
never re-implementing — the authentication, RBAC, tenant-isolation, audit-logging, and
(from Phase 2 on) document-storage foundation already built. A future extraction pipeline
plugs into the document lifecycle at the states Phase 2 already reserved for it:
`UPLOADED → PROCESSING → READY → REVIEW_REQUIRED → VERIFIED`.

---

## 19. Key Architectural Decisions

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
- **Document routes are flat, scoped by a `company_id` query parameter, not a path
  segment** (Phase 2) — this matches the spec's literal API shape while still running
  through Phase 1's `require_permission` dependency completely unchanged, because FastAPI
  resolves a dependency's plain `company_id` parameter as a query parameter whenever the
  calling route's path doesn't contain `{company_id}`.
- **A `StorageProvider` abstraction, not direct filesystem calls, throughout
  `DocumentService`** (Phase 2) — the entire module can move to S3 or another cloud
  backend later by adding one provider class and one line in
  `get_storage_provider()`, with no change to business logic, routes, the DB model, or the
  frontend.
- **Uploaded files are never trusted by extension alone** (Phase 2) — extension, declared
  MIME type, and (where the format supports it) the actual magic-byte signature must all
  agree, so a renamed/mislabeled file is rejected even when two of the three checks lie.
- **Downloads always go through an authenticated fetch, never a bare `<a href>` or
  `<iframe src>`** (Phase 2 frontend) — auth here is a bearer token, not a cookie, which a
  plain URL has no way to carry; the blob is fetched via `apiClient.downloadBlob()` and
  either saved (`triggerBlobDownload`) or turned into an object URL for the native
  PDF/image preview.

---

## 20. Security Notes

- Passwords are hashed with **Argon2id** (`argon2-cffi`), never stored or logged in
  plaintext.
- Refresh tokens are stored as **SHA-256 hashes only**; the raw token is returned to the
  client exactly once, at issuance/rotation.
- No password, access token, or refresh token is ever written to application logs.
- All ORM queries go through SQLAlchemy's parameterized query builder — no raw SQL string
  interpolation, including for document search (`ILIKE` with bound parameters) and sorting
  (the sort column comes from a server-side whitelist — `SORTABLE_FIELDS` in
  `document_repository.py` — never a client-supplied column name).
- CORS origins are explicit and environment-configured, not wildcarded.
- Error responses never leak stack traces; unhandled exceptions are logged server-side
  and returned to the client as a generic `INTERNAL_ERROR`. This extends to storage and
  database errors during document upload — a raw filesystem or DB driver error is always
  converted to a clean `AppException` (e.g. `DOCUMENT_STORAGE_ERROR`) before it can reach
  the client or an unhandled-exception path.
- Every response follows one of two envelopes:
  `{"success": true, "data": ..., "message": ...}` or
  `{"success": false, "error": {"code", "message", "fields"}}`.
- **Path traversal is blocked structurally, not by pattern-matching filenames.**
  `LocalStorageProvider._resolve()` resolves every storage key against the storage root and
  rejects (`StorageKeyError`) anything that would land outside it — and since the uploaded
  file's *original* filename is never used to build a storage path (a UUID-based
  `stored_filename` is generated server-side instead), there is no path for a crafted
  filename to influence disk layout at all.
- **`Content-Disposition` filenames are safely encoded**, not raw-interpolated — a
  filename containing a `"` or a control character can't corrupt or inject into the
  download response header (`app/utils/file_validation.py::safe_content_disposition`,
  mirroring the encoding Starlette's `FileResponse` already applies on the local-storage
  path).
- Document access errors return an identical `404 DOCUMENT_NOT_FOUND` whether the
  document truly doesn't exist or simply belongs to another company — deliberately, so a
  valid session can never distinguish "wrong ID" from "someone else's document" and
  enumerate other tenants' data.

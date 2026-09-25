# Tax Compliance & Audit Support Platform

**Phase 1 — Foundation, Authentication, RBAC & Multi-Tenant Architecture**
**Phase 2 — Document Management & Data Ingestion**
**Phase 3 — Accounting Data Layer & Tally/Excel/CSV Import**
**Phase 4 — GST Compliance Engine (GSTR-1, GSTR-2B Reconciliation, ITC, GSTR-3B)**
**Phase 5 — TDS Compliance Engine (Deductees, Rule Engine, Challans, Reconciliation, Returns)**
**Phase 6 — Bank Reconciliation Engine (Statement Import, Matching, Review Workflow)**
**Phase 7 — CA/Auditor Workflow (Engagements, Findings, Evidence, Review, Sign-off)**
**Phase 8 — Income Tax Compliance Engine (Computation, Tax Credits, ITR Preparation, Validation)**
**Phase 9 — Compliance Calendar & Task Management (Obligations, Tasks, Notifications)**
**Phase 10 — Business Workflow & UX Intelligence (Dashboard, Action Center, Pipeline, Global Search)**
**Phase 11 — Reports & Business Intelligence (Report Center, Financial, Tax, Banking, Audit, Management BI)**

A production-oriented, multi-tenant SaaS foundation for a Tax Compliance & Audit Support
Platform for Indian businesses. Phase 1 delivers authentication, role-based access control,
company (tenant) management, user management, and audit logging. Phase 2 builds a complete
local document management module on top of it — upload, validation, storage, search, secure
download, and archival. Phase 3 builds a full double-entry accounting data layer on top of
both — financial years, ledgers, customers/vendors/products, sales & purchase invoices,
credit/debit notes, payments, receipts, journal entries, opening balances, basic reports,
and a guided CSV/Excel/Tally-export import wizard. Phase 4 builds a GST **preparation and
review** engine on top of that accounting data — GSTR-1 preparation, local GSTR-2B import
and reconciliation, an ITC review workflow, and GSTR-3B preparation. Phase 5 builds a TDS
**preparation and review** engine alongside it — deductee management, a configurable/
effective-dated rule engine that decides applicability and calculates deductions (never
silently), the deduction lifecycle through to challan tracking and payment reconciliation,
and quarterly TDS return preparation. Phase 6 builds a bank reconciliation engine on top of
the same accounting layer — bank statement import with checksum-based duplicate detection,
a deterministic (no-AI) point-scored matching engine against existing Payments/Receipts/
Journal Entries, manual and partial matching with over-allocation guards, adjustment journal
entries for bank charges/interest, and a full reconciliation session review workflow — all
for a CA/auditor to review before anything is filed or acted on elsewhere. Phase 7 builds a
CA/Auditor workflow layer on top of every prior phase — review engagements with a controlled
lifecycle, an assignable team, a standard (editable) checklist, findings that reference any
prior-phase record without duplicating it, an evidence trail that reuses Phase 2's document
store, a formal response/review cycle, and an internal review + sign-off trail — so a review
of this company's data has one shared, auditable home instead of being tracked in someone's
inbox or spreadsheet. Phase 8 builds an Income Tax **preparation and computation** engine on
top of every prior phase — a taxpayer profile, versioned/configurable tax rules (slabs,
rebate, surcharge, cess, deduction eligibility) per assessment year and regime, salary/house-
property/capital-gains/other-source income entry, business income derived straight from the
Phase 3 accounting data, TDS/TCS credit and advance/self-assessment tax tracking, a
transparent slab-to-final-liability computation with versioned snapshots, and an ITR
preparation record with its own validation engine — all reviewable through Phase 7's existing
engagement/finding/sign-off workflow rather than a parallel one. Phase 9 ties every prior
compliance-producing module (GST, TDS, Income Tax, Audit, Bank Reconciliation) together
through one central coordination layer — a versioned, configurable compliance rule engine
that generates obligations with reproducible due dates, a task lifecycle (assign → start →
review → verify → lock) any module can create work items against without duplicating its own
logic, deterministic overdue detection with no Celery/Redis, an in-app notification system,
and a lightweight month/week calendar and dashboard — so "what's due, who owns it, what's
overdue" has one shared answer instead of living separately inside each module.

> **Scope note:** GST/TDS/Income Tax *filing*, live Tally API integration, OCR/AI
> extraction, and government portal integration are intentionally **not implemented**.
> Phase 4 specifically does **not**: log into the GST portal, fetch GSTR-2B live, file
> GSTR-1/GSTR-3B, submit any return, or process a GST payment/challan. Phase 5 specifically
> does **not**: log into the TRACES/Income Tax e-filing portal, verify a PAN/TAN against any
> government service, file 24Q/26Q/27Q/27EQ, or pay a TDS challan. Phase 6 specifically does
> **not**: connect to any bank (no Open Banking, OAuth, or bank API), fetch live transactions,
> or use AI/ML for matching — it is entirely file-import-based and every match is either a
> deterministic point-score result or an explicit human choice. Phase 7 specifically does
> **not**: use AI/LLM classification for anything, auto-label a finding "fraud" or "illegal"
> (severity is an internal workflow classification only — `LOW`/`MEDIUM`/`HIGH`/`CRITICAL` —
> never a legal determination), or let a sign-off claim to be a DSC, ICAI, or statutory
> certification — every sign-off statement is a fixed, neutral, internal-acknowledgement
> sentence the service layer controls, never freely authored text. Phase 8 specifically does
> **not**: log into the Income Tax e-filing portal, fetch Form 26AS/AIS live, verify a PAN
> against any government service beyond structural format, file any ITR form, or compute
> surcharge marginal relief (a `WARNING` is raised near a threshold instead) — every tax rule
> (slabs/rebate/surcharge/cess/deduction caps) comes from an explicitly configured, versioned
> `IncomeTaxRuleSet`, never a value invented in code, and the seeded sample rule sets are
> documented as illustrative, non-authoritative development data. Phase 9 specifically does
> **not**: send email or SMS (`InAppNotificationProvider` is the only notification provider
> that exists), integrate a government compliance-deadline feed, or hard-code a statutory
> due date — every `ComplianceRule.due_date_rule` is a configurable JSON document, and the
> seeded sample rules are illustrative demo data, not an authoritative compliance calendar.
> No Celery, no Redis, no background worker — overdue detection is a plain, synchronous sweep
> run from the dashboard/calendar endpoints. All six only prepare,
> calculate, validate, reconcile, and export data locally so a human files or acts on it
> elsewhere. Where the platform anticipates a not-yet-built integration (e.g. structural-only
> PAN/TAN validation, or bank statement import — CSV/XLSX only today through the same
> adapter interface Phase 3's import pipeline already defines, deliberately not duplicated
> for a future live bank-feed provider), it is marked as a future module, not a stubbed-in
> fake. **No phase has
> a paid or cloud dependency** — documents are validated and stored entirely on the local
> filesystem, accounting data is imported from files the user already has (a Tally *export*,
> not a live Tally connection), and GSTR-2B/TDS/bank-statement reconciliation data are all
> imported from local CSV/XLSX/JSON files, never fetched live from any government portal or
> bank; everything runs offline via `docker compose up`.

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

Core Phase 3 capabilities:

- A full double-entry accounting foundation: financial years, accounting periods,
  a hierarchical ledger (chart of accounts), customers, vendors, products/services, sales
  invoices, purchase invoices, credit notes, debit notes, payments, receipts, journal
  entries, and opening balances — money always stored as `Decimal`/`NUMERIC(18,2)`, never
  `float`
- Centralized GST-aware tax/total calculation (`AccountingCalculationService`) shared by
  every transaction type, so the rounding rule and CGST/SGST/IGST split logic exist in
  exactly one place
- A `DRAFT → POSTED → CANCELLED` posting lifecycle with server-enforced immutability once
  an invoice is posted
- A CSV/Excel/Tally-export import pipeline (`AccountingImportAdapter`) with column mapping,
  normalization, duplicate detection, a preview-before-commit step, and per-row error
  reporting — plus full source traceability (`source`, `source_reference`, `import_job_id`)
  on every imported record
- Basic reports: sales/purchase summary, customer/vendor outstanding, ledger trial balance
- A React accounting dashboard, master-data pages, invoice forms with live tax preview, and
  a guided multi-step import wizard

Core Phase 4 capabilities:

- A GST profile per company with **local, structural GSTIN validation** — full 15-character
  format, state-code lookup, and a real mod-36 checksum recomputation, never a call to any
  government service
- Configurable GST tax rates (platform-wide defaults plus company-specific ones) and a
  centralized `GSTCalculationService` (CGST/SGST vs IGST split, cess) so GSTR-1, GSTR-3B,
  and reconciliation all read the same arithmetic instead of each computing tax independently
- Monthly **GST return periods**, a versioned generate → submit-for-review → approve →
  finalize workflow (`GSTReturnSnapshot`), and full tenant isolation on every entity
- **GSTR-1 preparation**: B2B, B2C (large inter-state invoices listed individually, the rest
  aggregated by state + rate), credit/debit notes, HSN/SAC summary, document summary, and
  structured validation findings — every row traceable back to its source `SalesInvoice`
- **GSTR-2B import** reusing Phase 3's import pipeline unchanged (new `GSTR2B` import type,
  plus a new JSON adapter) — from a locally uploaded CSV/XLSX/JSON file only
- **Reconciliation** of purchase books against imported GSTR-2B in stages — exact match,
  normalized-invoice-number match, then a cross-GSTIN check purely to explain a mismatch —
  producing one of ten specific statuses (`MATCHED`, `AMOUNT_MISMATCH`, `BOOKS_ONLY`,
  `GSTR2B_ONLY`, `DUPLICATE`, ...), never a single generic "mismatch"
- **ITC review**: matched/unmatched/potential/review-required categorization with an
  explicit reviewed → accepted/rejected workflow — only an *approved* ITC figure ever
  reduces GSTR-3B's net liability
- **GSTR-3B preparation**: outward supplies (netted against credit/debit notes), approved
  vs. review-required ITC, and net tax liability by CGST/SGST/IGST/cess
- Local CSV/XLSX export of every report, always labeled "Preparation" or "Reconciliation
  Report," never "Filed Return"
- A full GST React UI: dashboard, return-period detail page with GSTR-1/GSTR-2B/
  Reconciliation/ITC/GSTR-3B tabs, all wired through the same RBAC/permission-gating
  conventions as Phases 1–3

Core Phase 5 capabilities:

- A TDS profile per company with **local, structural TAN/PAN validation** (format only — TAN
  has no publicly documented checksum, so none is invented) and a deductee register
  optionally linked to an existing Phase 3 Vendor/Customer rather than duplicating it
- A **rule engine** (`TDSRuleEngine` = `TDSApplicabilityService` + `TDSCalculationService`)
  over effective-dated, company-overridable `TDSRule`s (mirroring `GSTTaxRate`): every
  evaluation resolves to `APPLICABLE`, `NOT_APPLICABLE`, `REVIEW_REQUIRED`, or
  `MISSING_DATA` with a stated reason — a missing rule, missing PAN with no configured
  no-PAN rate, or an unresolvable aggregate threshold is **never guessed**, only flagged
- **TDS transactions** with a server-enforced `DRAFT → CALCULATED → DEDUCTED → PAID` (and
  `→ CANCELLED`) lifecycle; a manual override preserves the original `system_calculated_amount`
  alongside the overridden `tds_amount` so an auditor can always see what changed and why
- **TDS challans** with allocation against transactions, guarded against over-allocation on
  both the challan side and the transaction side — tracking/preparation only, this platform
  never pays a challan
- **Reconciliation** comparing deducted amounts against challan allocations, producing
  `MATCHED` / `PARTIALLY_MATCHED` / `MISSING_CHALLAN` / `UNALLOCATED_PAYMENT` findings,
  fully recomputed on every run rather than accumulating stale state
- A CSV/Excel **reconciliation import** (new `TDS` import type on Phase 3's existing import
  pipeline) for bringing in already-known TDS data — deductees must already exist by name,
  never auto-created, and every row lands as a traceable `DEDUCTED` transaction
- **Quarterly TDS return periods**, a versioned generate → submit-for-review → approve →
  finalize workflow (`TDSReturnSnapshot`), quarterly/section/deductee/challan reports, and
  local CSV/XLSX export always labeled "Preparation" or "Reconciliation Report"
- A full TDS React UI: dashboard, deductees/transactions/challans pages, and a return-period
  detail page with Overview/Sections/Deductees/Challans/Reconciliation/Review Notes tabs,
  wired through the same RBAC/permission-gating conventions as Phases 1–4

Core Phase 6 capabilities:

- **Bank accounts** that only ever store a masked account number (`account_number_masked`,
  e.g. `XXXXXX1234`) — the full number is never collected — optionally linked to a Phase 3
  `Ledger` so "book balance" can be computed from the real chart of accounts instead of a
  second, parallel balance this module would have to keep in sync itself
- **Bank statement import** reusing Phase 3's import pipeline unchanged (new
  `BANK_STATEMENT` import type): flexible column mapping, light-touch normalization that
  never overwrites the bank's own original description, and a deterministic SHA-256
  **checksum** (`company + account + date + amount + reference + description`) enforced by
  both application-level duplicate detection and a DB unique index — never description
  matching alone
- **Opening/closing balance validation** on every imported statement
  (`opening + credits − debits = closing`), surfaced as a non-blocking `balanced: bool` +
  `difference` finding rather than rejecting an otherwise-valid partial statement
- A **deterministic, no-AI matching engine** (`BankMatchingService`) — a fixed point system
  (exact amount as the base filter, +30 exact reference, +15 exact date, +10 counterparty,
  +5 description overlap) against Payments, Receipts, and Journal Entry lines touching the
  account's linked ledger; auto-matching only fires when exactly one candidate clears the
  strong-match threshold — any tie or weak signal is left as `MATCH_SUGGESTED` /
  `REVIEW_REQUIRED` for a human, never force-picked (mirroring GST/TDS's "flag, don't guess"
  principle)
- **Manual and partial matching** — one bank transaction can be split across several
  accounting records (or vice versa), with over-allocation blocked on both the bank-transaction
  side and the accounting-record side, and every match reversible (soft `REVERSED` status,
  never deleted, so match history is permanent)
- **Adjustments reuse Phase 3's `JournalEntryService` directly** — a bank charge or interest
  line becomes a real, POSTED journal entry (subject to the existing period-lock check) plus
  an `ADJUSTMENT`-type match, never a parallel adjustment ledger
- **Reconciliation sessions** with a full `OPEN → IN_PROGRESS → PENDING_REVIEW → RECONCILED →
  LOCKED` review workflow (Accountant runs/submits, Auditor approves/rejects/locks), bank vs.
  book balance/difference calculation, and unmatched-bank/unmatched-book/matching reports with
  local CSV/XLSX export
- A full Banking React UI: dashboard, accounts, statements (feeding the same generic import
  wizard Phases 3–5 already use), transactions, and a reconciliation session detail page with
  live match-candidate selection, wired through the same RBAC/permission-gating conventions
  as Phases 1–5

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
│   │   │   └── imports/            CSV/Excel/Tally/JSON import adapters, normalizers, validators
│   │   ├── repositories/           all DB queries, tenant-scoped
│   │   ├── storage/                 StorageProvider abstraction (base.py) + LocalStorageProvider
│   │   ├── utils/                  GUID type, password validators, file-signature validation,
│   │   │                           GSTIN structural + checksum validation (`utils/gstin.py`),
│   │   │                           PAN/TAN structural validation (`utils/pan.py`, `utils/tan.py`),
│   │   │                           invoice-number normalization
│   │   └── seed.py                 idempotent roles/permissions/super-admin/GST-rates/
│   │                               TDS-sections-and-rates seed
│   ├── alembic/                    migrations
│   ├── storage/                    local document storage root (git-ignored, created at runtime)
│   ├── tests/                      pytest suite (auth, RBAC, multi-tenancy, companies,
│   │                               documents, accounting, imports, GST foundation, GSTR-1,
│   │                               GSTR-2B import, reconciliation, ITC, GSTR-3B, return
│   │                               workflow, exports, sample data, TDS foundation, TDS
│   │                               engine, TDS transactions, TDS challans, TDS
│   │                               reconciliation, TDS import, TDS return workflow, bank
│   │                               accounts/statements/matching/reconciliation/reports,
│   │                               audit workflow, income tax, compliance calendar/tasks/
│   │                               notifications)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/             shared UI (shadcn-style primitives in components/ui)
│   │   ├── layouts/                AppLayout (sidebar+topbar), AuthLayout
│   │   ├── pages/                  auth, dashboard, companies, users, documents, audit-logs,
│   │   │                           settings, errors, accounting (ledgers, invoices, imports,
│   │   │                           reports, accounting dashboard), gst (dashboard, return
│   │   │                           period detail with GSTR-1/GSTR-2B/Reconciliation/ITC/
│   │   │                           GSTR-3B tabs), tds (dashboard, deductees, transactions,
│   │   │                           challans, return period detail with Overview/Sections/
│   │   │                           Deductees/Challans/Reconciliation/Review Notes tabs),
│   │   │                           bank (dashboard, accounts, statements, transactions,
│   │   │                           reconciliations, reconciliation detail), audit (dashboard,
│   │   │                           engagements list, engagement detail with Overview/
│   │   │                           Checklist/Findings/Review & Sign-off tabs, finding detail),
│   │   │                           income-tax (dashboard, profile, income, capital gains,
│   │   │                           deductions, tax payments, computations list/detail with
│   │   │                           breakdown tree and embedded ITR preparation), compliance
│   │   │                           (dashboard, month calendar, task list/detail, notifications)
│   │   ├── components/              ...NotificationBell (unread-count bell + dropdown in the
│   │   │                           app header)
│   │   ├── services/                thin fetch wrappers per resource
│   │   ├── hooks/                   useAuth, useToast, TanStack Query hooks (hierarchical
│   │   │                           query keys — see §24)
│   │   ├── types/                   API response types (api.ts + accounting.ts + gst.ts +
│   │   │                           tds.ts + bank.ts + audit.ts + incomeTax.ts + compliance.ts)
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
| `ALLOWED_DOCUMENT_EXTENSIONS` | Comma-separated whitelist (default `pdf,jpg,jpeg,png,xlsx,xls,csv,json` — `json` added in Phase 4 for GSTR-2B uploads) — this can only *narrow* the set of types the backend knows how to signature-check (`app/utils/file_validation.py`), never expand beyond it |

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

Phase 4 adds two migrations: one creating `gst_profiles`, `gst_tax_rates`,
`gst_return_periods`, `gst_return_snapshots`, `gstr2b_records`, `gst_reconciliations`,
`gst_reconciliation_results`, and `gst_review_notes` (all `company_id`-indexed, plus
composite indexes for the lookups reconciliation and GSTR-1 actually run — e.g.
`(company_id, return_period_id, supplier_gstin, invoice_number)` on `gstr2b_records`); a
second adds a nullable `return_period_id` to the existing Phase 3 `import_jobs` table (the
same generalization `financial_year_id` already represents for accounting imports — "the
period this import belongs to"). No Phase 1–3 table is altered beyond that one additive
column.

Phase 5 adds four migrations, none altering a prior table beyond the `TDS` import-type
addition (a non-native enum stored as plain `VARCHAR`, so it needed no schema change at
all): `tds_profiles`, `tds_sections`, `tds_rules`, and `deductees` (foundation);
`tds_transactions`; `tds_challans` and `tds_challan_allocations`; and
`tds_payment_reconciliations`, `tds_return_periods`, `tds_return_snapshots`, and
`tds_review_notes` together. Composite indexes match the lookups the engine actually
runs — e.g. `(company_id, status)` and `(company_id, transaction_date)` on
`tds_transactions` for the payable summary and quarterly reports.

Phase 6 adds two migrations: one creating `bank_accounts`, `bank_statements`,
`bank_transactions`, `bank_transaction_matches`, and `bank_reconciliations` (a unique index
on `(company_id, bank_account_id, checksum)` on `bank_transactions` enforces duplicate
detection at the database layer, not just in the import pipeline); a second adds a nullable
`bank_statement_id` to the existing `import_jobs` table, the same generalization
`return_period_id`/`bank_statement_id` already represent for GST/TDS/bank imports. The
`BANK_STATEMENT` import type itself needed no migration — like `TDS` before it, `ImportType`
is a non-native enum stored as plain `VARCHAR`. No Phase 1–5 table is altered beyond that one
additive column.

Phase 7 adds one migration creating `audit_engagements`, `audit_assignments`,
`audit_checklists`, `audit_checklist_items`, `audit_findings`, `audit_finding_comments`,
`audit_finding_evidence`, `audit_finding_responses`, `audit_reviews`, and `audit_signoffs` —
all `company_id`-indexed, plus a unique `(company_id, engagement_code)` index on
`audit_engagements`, a unique `(engagement_id, finding_code)` index on `audit_findings`, a
`(source_type, source_id)` index on `audit_findings` for reverse lookups, and a **partial
unique index** on `audit_assignments` enforcing one active `(engagement_id, user_id, role)`
assignment at a time (`WHERE is_active = true`, the same pattern Phase 1 already uses for
active company memberships). No Phase 1–6 table is altered.

Phase 8 adds one migration creating 20 tables: `income_tax_profiles`; the versioned rule-set
family `income_tax_rule_sets`, `income_tax_slabs`, `income_tax_rebate_rules`,
`income_tax_surcharge_rules`, `income_tax_deduction_rules`; the income tables
`income_tax_salary_incomes`, `income_tax_house_property_incomes`, `income_tax_other_incomes`,
`income_tax_exempt_incomes`, `income_tax_capital_gains`; `income_tax_deductions`,
`income_tax_adjustments`, `income_tax_ledger_classifications`, `income_tax_losses`,
`income_tax_advance_tax_payments`, `income_tax_self_assessment_tax_payments`,
`income_tax_credit_entries`; and the computation/preparation core `tax_computations`,
`tax_computation_snapshots`, `itr_preparations`. A unique index on
`(assessment_year, taxpayer_type, tax_regime, version)` on `income_tax_rule_sets` prevents
two active versions of the same rule set from ever coexisting; every other table is indexed
on `(company_id, financial_year_id)` (or `company_id` alone for the computation/preparation
tables), matching the same scoping convention Phase 3/5's own transactional tables use. No
Phase 1–7 table is altered.

Phase 9 adds one migration creating 6 tables: `compliance_rules` (a unique
`(code, company_id, version)` index prevents two active versions of the same rule from
coexisting), `compliance_obligations` (a unique
`(company_id, code, financial_year_id, tax_period)` index is the deterministic duplicate
guard recurring generation relies on), `compliance_tasks` (indexed on
`(company_id, status)`, `(company_id, due_date)`, and `(source_type, source_id)` for the
calendar/dashboard/traceability queries), `compliance_task_comments`,
`compliance_task_evidence`, and `notifications` (indexed on `(user_id, is_read)` for the
unread-count query). No Phase 1–8 table is altered.

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
- The five standard platform-wide GST tax rate slabs (0/5/12/18/28%, `company_id=NULL`) —
  Phase 4's `seed_gst_default_tax_rates`; a company can still add its own rates on top
- Five sample platform-wide TDS sections (194C, 194H, 194I, 194J, 194Q) and their standard
  rates — Phase 5's `seed_default_tds_sections_and_rules`, explicitly documented as
  development/testing configuration, not an authoritative statutory rate table; a company
  can add its own section-specific override rules on top
- One illustrative Income Tax rule set per regime (OLD_REGIME, NEW_REGIME) for AY 2026-27,
  INDIVIDUAL taxpayers only, with sample slabs/rebate/surcharge/cess and a handful of
  Chapter VI-A deduction rules (80C/80D/80TTA/80TTB/80G/80CCD(2)) — Phase 8's
  `seed_default_income_tax_rule_sets`, explicitly documented as illustrative sample data,
  not verified current tax law; a real deployment must configure its own rule sets
  (including for COMPANY/LLP/PARTNERSHIP/TRUST/HUF, none of which are seeded)
- Five sample platform-wide compliance rules (monthly GSTR-1/GSTR-3B, quarterly TDS return,
  monthly TDS challan review, monthly bank reconciliation) — Phase 9's
  `seed_default_compliance_rules`, explicitly documented as illustrative demo data, not an
  authoritative compliance calendar; a company can layer its own override rule on top of
  any of them under the same `code`

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
- **Accounting (Phase 3):** master data CRUD; tax/total calculation against hand-computed
  expected values; the `INVALID_TAX_SPLIT` and `UNBALANCED_JOURNAL` rejections; the
  `DRAFT → POSTED → CANCELLED` posting lifecycle and its immutability guard; duplicate
  invoice detection scoped to `(company, number, date, party)`; financial-year/period date
  guards; cross-tenant isolation; RBAC on every accounting permission; audit logging
- **Imports (Phase 3):** upload/parse producing correct row counts; missing-field,
  incomplete-mapping, invalid-date, and missing-customer row errors; commit creating only
  the rows still valid at commit time; rejection of a second commit on an already-committed
  job; cancel preventing a later commit; cross-tenant import isolation; RBAC on commit
- **GST foundation (Phase 4):** GSTIN structural + checksum validation (valid/invalid
  format, unknown state code, wrong checksum) against known real GSTIN examples; tax
  calculation at 5/12/18/28% for both intra- and inter-state, plus cess; place-of-supply
  intra/inter-state determination; transaction classification (B2B/B2C/review-required);
  tenant isolation and RBAC on the profile/tax-rate/return-period endpoints
- **GSTR-1:** B2B classification, B2C aggregation by state+rate, B2C-large vs. B2C-others
  split at the ₹2.5L inter-state threshold, missing-place-of-supply → `REVIEW_REQUIRED`
  and a `MISSING_PLACE_OF_SUPPLY` validation finding, cancelled invoices excluded from
  totals but counted in the document summary, HSN summary aggregation and missing-HSN
  flagging, the `GST_PROFILE_REQUIRED` guard, cross-tenant isolation
- **GSTR-2B import:** JSON/CSV/XLSX parsing through the extended Phase 3 pipeline,
  invalid-GSTIN and duplicate-row handling, the `RETURN_PERIOD_REQUIRED` guard, RBAC
- **Reconciliation & ITC:** exact match, amount mismatch, books-only, GSTR-2B-only,
  re-running replacing prior results, the full review → accept/reject workflow and its
  effect on the ITC summary
- **GSTR-3B:** outward supplies before any reconciliation has run, and net liability
  correctly dropping only after an ITC result is explicitly approved
- **Return workflow:** the full `generate → submit-for-review → approve → finalize`
  transition sequence, per-return-type snapshot versioning, the "finalized is immutable"
  guard, the return period's own status only reaching `FINALIZED` once *both* GSTR-1 and
  GSTR-3B are finalized, and RBAC (an Accountant can generate/submit but not
  approve/finalize)
- **Exports:** CSV and XLSX generation for GSTR-1/GSTR-3B/reconciliation/ITC, with the
  reconciliation/ITC exports correctly requiring a reconciliation run first
- **Sample data (Phase 4):** the shipped `samples/sample_gst_*` and `samples/sample_gstr2b.*`
  files are imported through the real pipeline and asserted to produce the exact matched/
  mismatch/books-only/GSTR-2B-only/review-required outcomes documented in
  `samples/README.md`, so the sample data can never silently drift from the code
- **TDS foundation (Phase 5):** PAN/TAN structural validation (valid/invalid format, missing
  value); idempotent seeding of the five sample sections/rules; TDS profile create/get/
  update and its `TDS_PROFILE_ALREADY_EXISTS` guard; deductee create/update with automatic
  `pan_status` derivation; company-specific rule override creation and the
  `TDS_RULE_READ_ONLY` guard on platform defaults; tenant isolation and RBAC throughout
- **TDS engine:** calculation at a configured percentage rate against hand-computed expected
  values; the missing-PAN → no-PAN-rate substitution and its `MISSING_NO_PAN_RATE` failure
  when unconfigured; FIXED-rate clamping to the gross amount; applicability resolving to
  `MISSING_DATA`/`NOT_APPLICABLE`/`APPLICABLE`/`REVIEW_REQUIRED` for missing deductee, below-
  threshold, above-threshold, unresolvable aggregate threshold, invalid PAN, and no-effective-
  rule cases respectively; the rule engine's end-to-end trace including/excluding a
  calculation depending on applicability
- **TDS transactions:** the full `DRAFT → CALCULATED → DEDUCTED` happy path via the API; a
  below-threshold transaction calculating to zero TDS; a missing-PAN section with a
  configured no-PAN rate still resolving to `APPLICABLE`; a manual override preserving
  `system_calculated_amount` while changing `tds_amount`; the "cannot cancel a DEDUCTED
  transaction" and "cannot deduct twice" state-machine guards; tenant isolation; RBAC (an
  Auditor cannot create a transaction)
- **TDS challans:** creation and allocation; over-allocation rejected on both the challan
  side (`CHALLAN_OVER_ALLOCATION`) and the transaction side (`TRANSACTION_OVER_ALLOCATION`);
  an allocation against a `PAID` challan marking its transaction `PAID`; the forward-only
  status-transition guard (`DRAFT` cannot jump straight to `PAID`); tenant isolation
- **TDS reconciliation:** a fully-allocated transaction resolving `MATCHED`; an unallocated
  deduction resolving `MISSING_CHALLAN`; a partial allocation resolving `PARTIALLY_MATCHED`
  on the transaction side and `UNALLOCATED_PAYMENT` on the challan side simultaneously; a
  re-run replacing (never duplicating) prior findings
- **TDS import:** valid CSV parsing and commit landing rows as `DEDUCTED` transactions
  directly (reconciliation import of known data, not a calculation request);
  `MISSING_DEDUCTEE` and `MISSING_SECTION` row errors when the referenced deductee/section
  doesn't exist; duplicate-row detection; the `TDS_IMPORT`/`TDS_IMPORT_COMMIT` permission
  gates layered onto the shared Phase 3 import endpoints (mirroring how Phase 4 gated
  GSTR-2B)
- **TDS return workflow:** quarter date-range computation from the financial year's start
  month; the duplicate-quarter guard; the full `generate → submit-for-review → approve →
  finalize` sequence with the return period's own status kept in sync at each step; the
  "finalized is immutable" guard; regeneration producing a new version reflecting data
  changed since v1; review-note creation and the "cannot resolve twice" guard; the
  quarterly/section summary report endpoints; the `TDS_PROFILE_REQUIRED` export guard and a
  successful CSV export
- **Bank accounts (Phase 6):** create/get, the masked-account-number duplicate guard
  (`DUPLICATE_RESOURCE` from the DB unique index), the invalid-linked-ledger rejection,
  tenant isolation, RBAC (an Auditor cannot create an account)
- **Bank statement import:** valid CSV import and commit creating `UNMATCHED` transactions
  with correct debit/credit/type and normalized-description derivation; the
  `BOTH_DEBIT_AND_CREDIT` row-validation rejection; duplicate-row detection via checksum; the
  statement balance-check endpoint correctly reporting both a balanced and a deliberately
  mismatched statement; exclude/flag-for-review transitions and their "already excluded"
  guard
- **Matching engine:** an unambiguous strong candidate (exact amount + reference + date)
  auto-matching and creating an `AUTO` match; two same-amount candidates correctly producing
  `REVIEW_REQUIRED`/`MATCH_SUGGESTED` with both surfaced via the candidates endpoint rather
  than one being silently picked; partial matching across two receipts summing to one bank
  transaction; the `MATCH_AMOUNT_EXCEEDS_BANK_TRANSACTION` over-allocation guard; match
  reversal restoring `UNMATCHED` status
- **Reconciliation workflow:** the full `run-matching → submit → approve → lock` sequence
  with status kept in sync at each step; the "locked cannot transition further" guard; the
  duplicate-session-for-the-same-period guard; RBAC (an Auditor cannot run matching but can
  approve/lock)
- **Adjustments:** a bank-charges transaction correctly producing a POSTED journal entry and
  moving the transaction to `MANUALLY_MATCHED`; the `BANK_ACCOUNT_LEDGER_REQUIRED` guard when
  the account has no linked ledger
- **Bank reports:** the unmatched-bank-transactions and matching-report endpoints returning
  correct rows for a known scenario; a successful CSV export
- **Audit workflow (Phase 7):** the full engagement lifecycle (`open → assign → start-review →
  submit-for-review → approve → sign-off → close → lock`), including the "approve is blocked
  while a HIGH/CRITICAL finding is still open" guard and the "sign-off requires a recorded
  lead-auditor sign-off first" guard; assignment requiring an active company membership and
  rejecting a duplicate active assignment; checklist seeding from the standard template and
  item status updates; finding creation surfacing (never blocking on) a duplicate-open-finding
  warning for the same source record; the response → review → accept/resolve cycle; evidence
  reusing an existing Phase 2 document by id; reject/reopen transitions; RBAC (an Accountant
  cannot create or approve an engagement); tenant isolation on engagement access
- **Income Tax (Phase 8):** PAN format validation on the profile; computed fields (salary
  taxable amount, house-property NAV/standard-deduction/income-or-loss, capital gain amount,
  the sale-before-purchase-date guard) verified against hand-computed `Decimal` values; a
  full computation end-to-end against the seeded sample NEW_REGIME rule set with every
  breakdown figure (business income from real posted sales/purchase invoices, slab tax,
  cess, gross tax liability, balance payable) asserted against hand-computed expected
  values; an OLD_REGIME deduction correctly capped at the rule set's `max_amount` even when
  a larger amount was claimed; the same section disallowed entirely under NEW_REGIME; a
  disallowed ledger classification correctly added back into taxable business income; the
  full computation lifecycle (`calculate → submit-review → approve → lock`) with RBAC (a
  Company Admin can calculate/submit but not approve — that's Auditor-only) and the "locked
  computation cannot be recalculated" guard; ITR form-type determination; ITR validation's
  `BANK_ACCOUNT_MISSING` error correctly blocking approval until a bank account exists, then
  succeeding once one is added; tenant isolation on the Income Tax profile
- **Compliance calendar/tasks (Phase 9):** pure due-date arithmetic (`DAYS_AFTER_PERIOD_END`,
  `DAY_OF_MONTH_AFTER_PERIOD_END` including short-month clamping, `DAYS_AFTER_START`) against
  fixtures, no DB involved; a Company Admin creating a company-specific rule vs. being
  refused a platform-wide one; updating a rule's description never changing its `version`;
  the natural-key duplicate guard on manually created obligations and the idempotent
  `generate_from_rule` re-fetch; the full task lifecycle (`start → submit-review →
  return-for-changes → submit-review → verify → lock`) proving `PENDING → VERIFIED` is
  unreachable in one step; the `complete` path for a task with no reviewer; the
  "submitting for review without a reviewer" guard; the "locked task rejects updates" guard;
  the assignment-target-must-be-a-company-member guard; the overdue sweep correctly flipping
  a past-due open task to `OVERDUE` (and never touching a completed one) when the dashboard
  is viewed; comments and evidence (reusing an existing Phase 2 document); the
  task-assignment notification firing, unread count, mark-read, and mark-all-read; tenant
  isolation on task access; a CSV export

As of Phase 9, the full suite is **315 tests**, all passing against a real PostgreSQL
database.

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

...and the Phase 4 GST endpoints:

```
POST   /api/v1/gst/profile?company_id=...                                    create GST profile
GET    /api/v1/gst/tax-rates?company_id=...
POST   /api/v1/gst/return-periods?company_id=...
GET    /api/v1/gst/return-periods/{period_id}/gstr1?company_id=...           overview
GET    /api/v1/gst/return-periods/{period_id}/gstr1/{b2b|b2c-large|b2c-others|credit-notes|debit-notes|hsn|documents|validation}
POST   /api/v1/accounting/imports?company_id=...                             import_type=GSTR2B, reused from Phase 3
GET    /api/v1/gst/gstr2b?company_id=...&return_period_id=...                imported records
POST   /api/v1/gst/return-periods/{period_id}/reconciliation?company_id=...  run reconciliation
GET    /api/v1/gst/return-periods/{period_id}/itc/summary?company_id=...
POST   /api/v1/gst/return-periods/{period_id}/itc/{result_id}/{review|approve}?company_id=...
GET    /api/v1/gst/return-periods/{period_id}/gstr3b?company_id=...
POST   /api/v1/gst/return-periods/{period_id}/{generate|submit-for-review|approve|finalize}?company_id=...
GET    /api/v1/gst/return-periods/{period_id}/reports/{gstr1|gstr3b|reconciliation|itc}?company_id=...&format=csv|xlsx
```

...and the Phase 5 TDS endpoints:

```
POST   /api/v1/tds/profile?company_id=...                                    create TDS profile
GET    /api/v1/tds/sections?company_id=...
POST   /api/v1/tds/rules?company_id=...
GET    /api/v1/tds/deductees?company_id=...&search=...
POST   /api/v1/tds/transactions?company_id=...
POST   /api/v1/tds/transactions/{id}/{calculate|override|deduct|cancel}?company_id=...
GET    /api/v1/tds/transactions/payable-summary?company_id=...
POST   /api/v1/tds/challans?company_id=...
POST   /api/v1/tds/challans/{id}/allocate?company_id=...
POST   /api/v1/tds/reconciliation/run?company_id=...&financial_year_id=...
POST   /api/v1/accounting/imports?company_id=...                             import_type=TDS, reused from Phase 3
POST   /api/v1/tds/return-periods?company_id=...
POST   /api/v1/tds/return-periods/{id}/{generate|submit-for-review|approve|finalize}?company_id=...
GET    /api/v1/tds/return-periods/{id}/reports/{summary|sections|deductees|challans}?company_id=...
GET    /api/v1/tds/return-periods/{id}/reports/export/{quarterly|reconciliation}?company_id=...&format=csv|xlsx
POST   /api/v1/tds/review-notes?company_id=...
```

...and the Phase 6 bank reconciliation endpoints:

```
POST   /api/v1/bank/accounts?company_id=...                                  create bank account
POST   /api/v1/bank/statements?company_id=...                                register a statement
GET    /api/v1/bank/statements/{id}/balance-check?company_id=...
POST   /api/v1/accounting/imports?company_id=...                             import_type=BANK_STATEMENT, reused from Phase 3
GET    /api/v1/bank/statements/{id}/transactions?company_id=...
GET    /api/v1/bank/transactions?company_id=...&reconciliation_status=...
POST   /api/v1/bank/transactions/{id}/{exclude|review}?company_id=...
GET    /api/v1/bank/transactions/{id}/candidates?company_id=...              scored match candidates
POST   /api/v1/bank/transactions/{id}/match?company_id=...                   manual/partial match
POST   /api/v1/bank/matches/{id}/reverse?company_id=...
POST   /api/v1/bank/transactions/{id}/adjust?company_id=...                  posts a real JournalEntry
POST   /api/v1/bank/reconciliations?company_id=...                           start a session
POST   /api/v1/bank/reconciliations/{id}/run-matching?company_id=...
POST   /api/v1/bank/reconciliations/{id}/{submit|approve|reject|lock|cancel}?company_id=...
GET    /api/v1/bank/reports/{unmatched-bank-transactions|unmatched-book-transactions|matches}?company_id=...
GET    /api/v1/bank/reports/reconciliations/{id}/export?company_id=...&format=csv|xlsx
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

## 18. Accounting & Import Explanation (Phase 3)

Phase 3 adds a full double-entry accounting data layer — financial years, a hierarchical
chart of accounts (ledgers), customers/vendors/products, sales & purchase invoices, credit
& debit notes, payments, receipts, journal entries, opening balances — plus a
CSV/Excel/Tally import pipeline, all reusing Phase 1's RBAC and Phase 2's document storage
without modifying either.

**Money is `Decimal`/`NUMERIC(18,2)` everywhere, never `float`.** `app/models/mixins.py`
defines shared `MONEY`, `RATE`, and `QUANTITY` `Numeric` column types, and every tax/total
calculation runs through one shared module, `AccountingCalculationService`
(`app/services/accounting_calculation_service.py`), so the rounding rule
(`ROUND_HALF_UP`, to 2 decimal places) is applied identically for sales invoices, purchase
invoices, and credit/debit notes — there is exactly one place in the codebase that computes
tax and totals.

**GST math without GST filing.** A line item may carry CGST+SGST *or* IGST, never both
(`INVALID_TAX_SPLIT` if both are set) — this mirrors how intra-state vs inter-state supply
works in Indian GST, but Phase 3 only *computes and stores* these amounts on documents; it
never generates a GSTR return or talks to a government API. GSTIN fields are validated only
**structurally** (`app/utils/gst_validators.py`: a regex shape check plus a state-code
lookup table) — never against a live government registry.

**Posting lifecycle: `DRAFT → POSTED → CANCELLED`.** Sales and purchase invoices are
mutable while `DRAFT` and become server-enforced immutable once `POSTED`
(`POSTED_TRANSACTION_IMMUTABLE` on any edit attempt); `CANCELLED` is terminal. This
mirrors how a real accountant works — an invoice can be corrected freely up until it's
"finalized," after which correcting it means issuing a credit/debit note, not silently
editing history.

**Duplicate detection is scoped to `(company_id, invoice_number, date, party)`, not
`invoice_number` alone** — two different customers, or the same customer on two different
dates, can legitimately reuse an invoice number sequence (e.g. after a books reset), so a
bare number match would produce false positives. Cancelled invoices are excluded from the
duplicate check so a corrected re-entry isn't blocked by its own cancelled predecessor.

**The import pipeline** (`app/services/import_service.py` and `app/services/imports/`)
follows one path regardless of source format:

```
Upload file (Phase 2's document endpoint)
   → Create Import Job (choose type + column mapping)
   → Parse (CSVImportAdapter / ExcelImportAdapter / TallyExportAdapter)
   → Normalize (dates, amounts, header variants)
   → Validate each row (per-ImportType validators, using a preloaded
     ImportContext so name→id lookups aren't N+1 queries)
   → Detect duplicates (in-batch and against existing DB records)
   → Preview (row-by-row VALID / ERROR / DUPLICATE status + error detail)
   → User reviews and confirms
   → Commit (creates real records; only rows still VALID at commit time
     are created — a job can only be committed once, from READY)
   → Summary (counts recomputed from final row statuses)
```

A source file's column headers **never** need to match the system's field names — the
column-mapping step (`app/services/imports/column_mapping.py`) lets the user map
`"Cust Name"` → `name`, `"Inv#"` → `invoice_number`, etc. Every imported record carries
`source` (`"IMPORT"` vs `"MANUAL"`), `source_reference`, and `import_job_id`, so it's always
possible to trace a ledger entry back to the exact file and job that created it. A "Tally
export" is handled by `TallyExportAdapter`, which delegates to the CSV or Excel adapter by
file extension — Phase 3 reads Tally's *exported* CSV/XLSX files, never Tally's live API.

The frontend wizard (`frontend/src/pages/accounting/ImportWizardPage.tsx`) walks the same
three stages — upload & pick type, map columns (backed by a `GET
/accounting/imports/preview-columns` endpoint that parses the file and returns just its
headers and a few sample rows, without creating a job, so the user can map columns *before*
committing to anything), then preview & commit.

## 19. GST Compliance Explanation (Phase 4)

Phase 4 is a **preparation, validation, reconciliation, and export** layer on top of
Phase 3's accounting data — it never files anything and never talks to the GST portal.
Every service that reads sales/purchase data does so read-only; nothing in this phase
mutates a `SalesInvoice`, `PurchaseInvoice`, `CreditNote`, or `DebitNote`.

```
Accounting Data (Phase 3)
   → GST Classification (B2B/B2C/REVIEW_REQUIRED — never guessed)
   → GST Calculation (one shared CGST/SGST/IGST/cess engine)
   → GSTR-1 Preparation
   → GSTR-2B Import (local file only)
   → Reconciliation (staged matching)
   → ITC Review (reviewed → accepted/rejected)
   → GSTR-3B Preparation
   → Return Workflow (generate → submit-for-review → approve → finalize, versioned)
   → Export (CSV/XLSX, clearly labeled "Preparation")
```

**GSTIN validation is entirely local.** `app/utils/gstin.py` checks the 15-character
structure, looks the state-code prefix up in a static table (`app/core/gst_state_codes.py`),
and recomputes the check digit with the published mod-36, alternating-factor algorithm —
verified in tests against two publicly documented real GSTINs. A structurally valid GSTIN
is never presented as "verified" or "active"; that would require a government API this
platform does not call.

**"Don't guess" is the load-bearing rule of the whole classification layer.**
`GSTTransactionClassificationService` returns `B2B` only when the customer has a
structurally valid GSTIN, `B2C` only when the customer has neither a GSTIN nor a missing
state code, and `REVIEW_REQUIRED` for everything else — including the case Phase 3's
`Customer`/`SalesInvoice` models simply cannot answer yet (no export/SEZ indicator exists),
which is why `GSTR1Service.get_exports` always returns an empty list rather than a guess.
The same principle drives `GSTValidationService`: every finding carries a `severity`
(`INFO`/`WARNING`/`ERROR`) and points at the exact source record, so a CA reviews specific,
traceable issues instead of a vague "something's wrong."

**GSTR-1's B2C split follows the actual legal rule, not an approximation.** An inter-state
B2C invoice over ₹2,50,000 is listed individually (`GSTR1B2CLargeRow`); everything else is
aggregated by place-of-supply state code + tax rate at the *line-item* level
(`GSTR1B2COthersRow`), because a single invoice can legitimately mix tax rates across its
items.

**Reconciliation matches in stages, and only ever narrows a mismatch — it never hides
one.** `GSTReconciliationService.run()` tries an exact match (supplier GSTIN + invoice
number + date) first, then a normalized-invoice-number match (`INV-001` ≡ `INV001` ≡
`inv 001`, via `app/utils/invoice_number.py`) within the same GSTIN, and only then a
same-invoice-number-different-GSTIN check purely to produce a specific `GSTIN_MISMATCH`
finding rather than a silent `BOOKS_ONLY`. Amount comparison uses a small, explicit rupee
tolerance (`AMOUNT_TOLERANCE`), never a "looks close enough" heuristic. Re-running a
period's reconciliation deletes and replaces its prior result rows — the reconciliation
*run* history (counts, match %) is kept, but individual stale result rows never linger
mixed in with fresh ones.

**ITC only reduces GSTR-3B's liability once a human has said so.** Every reconciliation
result also carries an `itc_category` (derived mechanically from its match status) and an
`itc_review_status` that starts `PENDING` and can only move to `REVIEWED`, `ACCEPTED`, or
`REJECTED` through an explicit API call with its own permission
(`ITC_REVIEW` vs. the stronger `ITC_APPROVE`) and audit log entry.
`GSTR3BService.generate()` sums only `ACCEPTED` amounts into `eligible_itc` — a `MATCHED`
but not-yet-reviewed result contributes to `itc_matched` for visibility, never to the net
liability figure.

**Finalizing is real, and it's genuinely one-way.** A `GSTReturnSnapshot` moves
`DRAFT → UNDER_REVIEW → APPROVED → FINALIZED` (or `UNDER_REVIEW → CHANGES_REQUESTED`, a
dead end for that version); the finalized `_TRANSITIONS` state machine in
`gst_return_snapshot_service.py` has no entry starting from `FINALIZED`, so no code path can
transition it further. If the underlying accounting data changes afterward, the fix is a
new `generate()` call, which creates version 2 rather than mutating version 1 — the return
period's own `GSTReturnPeriodStatus` only reaches `FINALIZED` once *both* its GSTR-1 and
GSTR-3B snapshots are finalized, so a period stays visibly `UNDER_REVIEW` until it truly is.

**GSTR-2B import reuses Phase 3's pipeline, not a parallel one.** Adding it was: one new
`ImportType.GSTR2B` member, one new `JSONImportAdapter` (CSV/XLSX already worked via the
existing adapters), one `validate_gstr2b_row` function, and one `_commit_gstr2b` branch —
in the same files Phase 3 already dispatches every other import type from. The only schema
change was a nullable `return_period_id` on `ImportJob`, mirroring how `financial_year_id`
already works for accounting imports. No new upload/preview/commit endpoints were needed;
the existing generic `/accounting/imports/*` routes already parametrize on `import_type`.

## 20. CA/Auditor Workflow Explanation (Phase 7)

Phase 7 is a **workflow and traceability** layer on top of every prior phase — it never
files, certifies, or legally opines on anything, and it never duplicates a record another
phase already owns.

```
Engagement (DRAFT → OPEN → ASSIGNED → IN_REVIEW ⇄ PENDING_CLIENT_ACTION)
   → PENDING_AUDITOR_REVIEW → APPROVED → SIGNED_OFF → CLOSED (→ locked)
   → Checklist (seeded from a small, documented, non-authoritative template)
   → Findings (generic source_type/source_id reference into any prior phase)
        → Evidence (links an existing Phase 2 Document — never a 2nd file store)
        → Comments (append-only)
        → Response → Review (accept → resolved / reject → action required)
   → Review passes (initial/final/second/quality — free-form notes, never a status driver)
   → Sign-off (fixed, neutral, internal-acknowledgement statement only)
```

**"Audit" means two different things in this codebase, and they're kept deliberately
separate.** The platform-wide security audit trail (`AuditLog`/`AuditAction`, Phase 1) logs
*who did what, when* across every module — Phase 7 extends its `AuditAction` catalogue with
its own action constants rather than building a second logging mechanism. The new
CA/Auditor *workflow* domain — engagements, findings, evidence, sign-off — lives entirely in
its own `audit_workflow_enums.py`/`AuditEngagement`/`AuditFinding`/... models, its own
`/audits/...` route prefix (distinct from the existing `/audit-logs`), and is never
conflated with the security log it also happens to write to.

**Approval is a checkpoint, not a formality.** `AuditEngagementService._check_can_approve()`
blocks the `approve` transition while any `HIGH`/`CRITICAL` finding is still open (not
`RESOLVED`/`CLOSED`/`REJECTED`) or any checklist item is still `REQUIRES_ATTENTION` — the
same "flag and block, never silently proceed" principle GST/TDS/Bank use for reconciliation
mismatches. Marking an engagement `SIGNED_OFF` is blocked, in turn, until at least one
`LEAD_AUDITOR` sign-off has actually been recorded, so the terminal status can never be
reached by a route call alone.

**A finding's severity is an internal triage label, never a legal claim.** `AuditFinding`'s
`severity` is `LOW`/`MEDIUM`/`HIGH`/`CRITICAL` and its `category` is a neutral bucket
(`ACCOUNTING`/`GST`/`TDS`/`BANK`/`DOCUMENT`/`DATA_QUALITY`/`CONTROL`/`COMPLIANCE`/`PROCESS`/
`OTHER`) — there is no "FRAUD" or "ILLEGAL" value anywhere in the schema, and nothing in the
service layer infers one. `resolution_summary` and comments are the only free-text fields
a human ever fills in, and even the sign-off `statement` is a fixed sentence chosen by
`sign_off_type`, assembled by `AuditSignOffService`, never accepted as request input — so
the platform cannot be made to emit a "legally certified" or DSC-equivalent claim.

**Findings reference other phases; they never copy them.** `AuditFinding.source_type`/
`source_id` is the same generic-reference shape `TDSTransaction.source_type`/`source_id` and
`BankTransactionMatch.source_type`/`source_id` already use — a finding can point at a sales
invoice, a GST return period, a TDS challan, a bank transaction, or a document without a hard
FK into five different tables. Creating a second open finding against the same source record
in the same engagement doesn't fail — `AuditFindingRepository.find_potential_duplicates()`
surfaces it as a warning (`duplicate_warning`/`duplicate_finding_codes` in the create
response) so a reviewer can decide whether it's a genuine second issue or a duplicate.

**Evidence reuses Phase 2's document store outright.** `AuditFindingEvidence` is a thin join
row — `finding_id` + `document_id` + an optional description — over the existing `Document`
table; the physical file is never re-uploaded or copied, and the service layer validates the
document belongs to the same company before linking it. This was chosen over extending the
existing generic `DocumentLink` table specifically because Phase 7 needed a per-evidence
`description` field `DocumentLink` doesn't carry.

**Assignment never creates a new kind of user.** `AuditAssignmentService.assign()` requires
an active `CompanyMembership` for the engagement's company before it will create an
`AuditAssignment` row — the existing RBAC roles (Company Admin/Accountant/Auditor) and
membership system are the only source of "who can be put on this engagement," never a
parallel identity concept.

## 21. Income Tax Compliance Engine Explanation (Phase 8)

Phase 8 is a **preparation and computation** layer, not a filing system — it never talks to
the Income Tax e-filing portal and never produces a legal opinion on a return.

```
Taxpayer Profile (PAN, taxpayer type, regime)
   → Financial Year → Assessment Year (computed, never string-sliced)
   → Versioned Tax Rule Set (slabs, rebate, surcharge, cess, deduction eligibility)
   → Income collection (salary, house property, capital gains, other sources, exempt)
   → Accounting-derived business income (Phase 3 invoices + ledger movement)
   → Deductions (eligibility capped/regime-gated by the rule set, never the claim as-is)
   → Current-year loss set-off
   → Gross Total Income → Taxable Income
   → Slab tax → Rebate → Surcharge → Cess → Gross Tax Liability
   → TDS/TCS credit + Advance Tax + Self-Assessment Tax
   → Balance Payable / Refund
   → Computation Snapshot (versioned, reproducible)
   → ITR Preparation → Validation → Phase 7 review → Internal Approval → Locked
```

**Tax law is versioned configuration, never a number baked into the calculator.**
`IncomeTaxRuleSet` (one row per assessment year + taxpayer type + regime, versioned) owns
child `IncomeTaxSlab`/`IncomeTaxRebateRule`/`IncomeTaxSurchargeRule`/`IncomeTaxDeductionRule`
rows; `app/services/income_tax_calculator.py` is pure arithmetic over whatever rule set it's
handed — it contains no slab percentage, rebate ceiling, or cess rate of its own. The one
rule set seeded (`seed_default_income_tax_rule_sets`, AY 2026-27, INDIVIDUAL, both regimes)
is explicitly documented as illustrative sample data, the same "small, documented, non-
authoritative" precedent Phase 5 set for `DEFAULT_TDS_SECTIONS` — a real deployment must
configure its own verified figures, including for COMPANY/LLP/PARTNERSHIP/TRUST/HUF, none
of which are seeded here.

**TDS credit is a genuinely new concept, not a reuse of Phase 5's `TDSTransaction`.**
Phase 5 models TDS *this company deducts from its vendors* — an outgoing liability tracked
toward 24Q/26Q filing. Income Tax "TDS credit" is the opposite direction: tax *other
parties deduct on income paid to this company*, the Form 26AS-style asset that reduces this
company's own liability. Since Phase 5 never captured that data, Phase 8 adds one small,
honestly-scoped model (`IncomeTaxCreditEntry`) for it, rather than stretching
`TDSTransaction` to mean something it doesn't, or building a second full TDS subsystem.

**Business income is computed, never stored as its own ledger.** Phase 3's `SalesInvoice`/
`PurchaseInvoice` are never auto-posted to `JournalEntryLine`s in this codebase (see
`ReportService.trial_balance`'s own docstring) — so `BusinessIncomeCalculationService` sums
posted invoice/note totals *and* posted journal movement on `INCOME`/`EXPENSE` ledgers as
two genuinely separate, non-overlapping data sources, nets them into book profit, then adds
back only the ledgers a human has explicitly classified `DISALLOWABLE` via the thin
`IncomeTaxLedgerClassification` side table (never inferred from a ledger's name) plus any
itemized `IncomeTaxAdjustment` rows. An unclassified expense ledger is deducted at book
value by default and separately flagged for review — the engine never guesses a
disallowance against the taxpayer's favor either.

**A deduction's claimed amount is never what the computation uses.** `IncomeTaxDeduction`
stores `claimed_amount` and a display-default `eligible_amount`; the actual figure that
enters a computation is always recomputed fresh by `DeductionService.eligible_amount_for()`
against that computation's own rule set — checking whether the section is allowed under the
regime at all, then capping at the rule's `max_amount` — the same "system's answer is
authoritative, never the raw input" principle `TDSTransaction.system_calculated_amount`
already established.

**Surcharge is computed without marginal relief, and says so.** `IncomeTaxSurchargeRule`
gives a flat rate once an income threshold is crossed; real marginal relief (capping the
surcharge so it never exceeds the excess income over the threshold) is a materially larger
piece of tax logic this cut does not implement. Crossing a threshold instead raises a
`WARNING` validation item prompting a human to check it manually — flagged, never guessed.

**Loss carry-forward is tracked, not yet auto-consumed.** `IncomeTaxLoss` records a loss's
origin year, amount, and a human-entered `setoff_amount` for the *current* year only —
`carried_forward_amount` (`amount - setoff_amount`) is always visible, but automatically
re-applying that balance against a *future* year's computation is a deliberately deferred
next iteration; real set-off ordering rules (a capital loss can only offset a capital gain;
a business loss cannot offset salary) are intricate enough that guessing them silently
risked being wrong in a way a human wouldn't easily catch.

**Everything is reviewed through Phase 7, never a parallel review system.** A tax
computation or ITR preparation is just another company record an `AuditFinding` can point
at — `AuditFindingCategory`/`AuditFindingSourceType` gained a handful of Phase 8 values
(`TAX_COMPUTATION`, `ITR_PREPARATION`, `TAX_DEDUCTION`, `CAPITAL_GAIN`, `TAX_CREDIT_ENTRY`,
...) the same way they gained Bank values in Phase 6, kept to 20 characters or fewer so the
existing `audit_findings.source_type` column never needed an `ALTER`.

**ITR form-type is determined, not asserted, and can honestly say "I don't know."**
`determine_itr_form_type()` maps `COMPANY → ITR_6`, `PARTNERSHIP`/`LLP → ITR_5`,
`TRUST → ITR_7`, and `INDIVIDUAL`/`HUF` to `ITR_1`/`ITR_2`/`ITR_3` based on which income
heads are actually present — anything it can't confidently place resolves to
`NOT_DETERMINED`, which `ITRValidationService` surfaces as a `REVIEW_REQUIRED` item rather
than a guess. Approving an ITR preparation is the one hard validation gate in Phase 8:
`ITRPreparationService.approve()` re-runs validation and refuses if any `ERROR`-severity
issue (missing PAN, no active bank account, ...) remains — the same "flag and block, never
rubber-stamp" principle `AuditEngagementService._check_can_approve()` already applies.

## 22. Compliance Calendar & Task Management Explanation (Phase 9)

Phase 9 is a **coordination layer**, not a seventh compliance engine — it never recomputes
a GST/TDS/Income Tax/Audit number; it schedules, assigns, tracks, and reminds around work
those modules already produce.

```
ComplianceRule (versioned, configurable due-date arithmetic)
   → ComplianceObligation (one company's instance for one period, reproducible due date)
        → ComplianceTask (assign → start → submit-review → verify → lock)
             → Comments / Evidence (reuses Phase 2 Document)
             → Notification (in-app only)
   → Calendar / Dashboard (date-range queries, never "load every task")
```

**Due-date arithmetic is versioned configuration, never a number in Python.**
`app/services/compliance_deadline_service.py` is a pure function over a
`ComplianceRule.due_date_rule` JSON document (`DAYS_AFTER_PERIOD_END`,
`DAY_OF_MONTH_AFTER_PERIOD_END`, `DAYS_AFTER_START`) — the same "rules are data, the
calculator has no opinion" discipline `income_tax_calculator.py` already applies to tax
slabs. Every `ComplianceObligation` a rule generates stores that rule's `version`, so a
later rule change (a statutory deadline moving) never rewrites a historical obligation's
due date — reproducibility Phase 8's `TaxComputationSnapshot` established first.

**A company-specific rule always overrides the platform-wide default, never replaces it.**
`ComplianceRule.company_id` is nullable — `NULL` rows are platform-wide samples (only a
platform super admin can create them), and a company can layer its own override on top
under the same `code`. `ComplianceRuleRepository.get_active_version()` always prefers the
company's own version when one exists, the same override precedence `TDSRule` already uses
for company-specific TDS rates over the platform default.

**A task's status transitions are enforced by a lookup table, not scattered `if`
statements** (PHASE9 §43) — the same `(from_status, action) -> to_status` pattern already
proven for `AuditEngagementStatus`/`TaxComputationStatus`. `PENDING -> VERIFIED` is
unreachable by construction; a task without a reviewer cannot be submitted for review at
all (`COMPLIANCE_TASK_REVIEWER_REQUIRED`), and a locked task rejects every further edit.

**Overdue is an overlay, not a dead end.** `OVERDUE` is applied by a plain, synchronous
sweep (`ComplianceTaskService.sweep_overdue()`, run opportunistically from the dashboard and
calendar endpoints — no Celery, no Redis, no background worker) to any open task whose due
date has passed; every forward action the task's underlying state supported (`start`,
`submit_review`, `complete`, `cancel`) still applies from `OVERDUE` exactly as it did before,
so going overdue never traps a task in a dead status.

**Notifications are in-app only, deduplicated by construction, and built behind one
interface.** `NotificationService.notify()` is the only way any code creates a
`Notification` row, and it skips creating a duplicate unread notification for the same
`(user, type, entity)` — so re-running the overdue sweep never spams the same user twice for
the same task. `InAppNotificationProvider` is the only implementation of the small
`NotificationProvider` protocol that exists; a future `EmailNotificationProvider`/
`SMSNotificationProvider` could be added without any caller changing, but neither exists
today — there is no email or SMS provider anywhere in this codebase.

**Evidence and source references reuse existing data outright.** `ComplianceTaskEvidence`
is the same thin join-to-`Document` shape `AuditFindingEvidence` (Phase 7) and
`ComplianceTaskEvidence`'s own sibling `IncomeTaxProfile`-adjacent evidence tables already
established — never a second file store. `ComplianceTask.source_type`/`source_id` is the
same generic-reference shape used throughout the app (`TDSTransaction`, `AuditFinding`,
...), so a task can point at a GST return, a TDS period, an audit checklist item, or nothing
at all (`MANUAL`) without a hard FK into five different modules.

## 23. Future Module Roadmap

These remain route-namespace placeholders only, ready for a future module to fill in
without touching Phases 1–9 (`/tally`, `/integrations`):

| Phase | Module |
|---|---|
| 1 | Foundation, auth, RBAC, multi-tenancy, audit logging *(done)* |
| 2 | Document management & local data ingestion *(done)* |
| 3 | Accounting data layer & Tally/Excel/CSV import *(done)* |
| 4 | GST Compliance — GSTR-1, GSTR-2B reconciliation, ITC, GSTR-3B *(done — no portal filing)* |
| 5 | TDS Compliance — deductees, rule engine, transactions, challans, reconciliation, quarterly returns *(done — no TRACES/portal filing)* |
| 6 | Bank Reconciliation — statement import, deterministic matching engine, manual/partial matching, adjustments, review workflow *(done — no live bank connection, no AI)* |
| 7 | CA/Auditor Workflow — engagements, assignments, checklist, findings, evidence, response/review, sign-off *(done — no AI, no statutory certification)* |
| 8 | Income Tax Compliance Engine — tax profile, versioned tax rules, income/deductions/capital gains, business income from accounting data, tax credits, computation, ITR preparation, validation *(done — no e-filing, no AI, no marginal relief)* |
| 9 | Compliance Calendar & Task Management — versioned rule engine, obligations, task lifecycle, overdue detection, in-app notifications, calendar/dashboard *(done — no Celery/Redis, no email/SMS)* |
| — | OCR/data extraction (`DocumentProcessor` extension point), a `GSTPortalAdapter`/`TDSPortalAdapter`/`IncomeTaxPortalAdapter`/`OpenBankingProvider` for an eventual real filing/bank-feed integration, live Tally API integration, surcharge marginal relief, automatic loss carry-forward set-off, `EmailNotificationProvider`/`SMSNotificationProvider` |

Each future module is expected to live in its own `models/ schemas/ services/
repositories/ api/` subtree (per `app/core/permissions.py`'s module grouping), reusing —
never re-implementing — the authentication, RBAC, tenant-isolation, audit-logging, and
(from Phase 2 on) document-storage foundation already built. A future extraction pipeline
plugs into the document lifecycle at the states Phase 2 already reserved for it:
`UPLOADED → PROCESSING → READY → REVIEW_REQUIRED → VERIFIED`.

---

## 24. Key Architectural Decisions

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
- **One shared `AccountingCalculationService`, not per-endpoint tax math** (Phase 3) — sales
  invoices, purchase invoices, and credit/debit notes all compute taxable amounts, GST
  splits, and grand totals through the same `calculate_line_item`/`calculate_document`
  methods, so a rounding-rule change or bug fix applies everywhere at once instead of
  needing to be found and fixed in four separate services.
- **Duplicate detection keys on `(company_id, invoice_number, date, party)`, not
  `invoice_number` alone** (Phase 3) — matches how invoice numbering actually works in
  practice (numbers can legitimately repeat across customers or after a books reset), and
  cancelled invoices are excluded so a corrected re-entry isn't blocked by its own
  cancelled predecessor.
- **Imported records carry full source traceability** (Phase 3) — every row created via
  import stores `source="IMPORT"`, `source_reference`, and `import_job_id`, so any ledger
  entry can always be traced back to the exact file and job that created it, without a
  separate audit table.
- **GST-specific entities are new flat models, never duplicates of Phase 3 data** (Phase 4)
  — `GSTProfile`, `GSTTaxRate`, `GSTReturnPeriod`, `GSTReturnSnapshot`, `GSTR2BRecord`,
  `GSTReconciliation`/`Result` exist because the GST domain genuinely needs independent
  records (a GSTR-2B row has no Phase 3 equivalent at all); everything else — customers,
  vendors, sales/purchase invoices — is read directly from Phase 3's existing tables.
- **One `GSTCalculationService`, reusing Phase 3's own `round_money`** (Phase 4) — rather
  than a second, similar-but-not-identical rounding rule, the GST engine imports the exact
  same paise-rounding function `AccountingCalculationService` already uses, so a rupee
  never rounds differently depending on which module touched it last.
- **Classification defaults to `REVIEW_REQUIRED`, never a best guess** (Phase 4) — GST
  compliance carries real legal and financial consequences, so every place the engine lacks
  enough data to classify a transaction confidently (missing place of supply, an
  unrecognized customer GSTIN, an export with no indicator field to read) it says so
  explicitly instead of silently picking the most likely answer.
- **A versioned `GSTReturnSnapshot`, not live-recomputed "current" data, backs the review
  workflow** (Phase 4) — accounting data is mutable and a GST return preparation must not
  be. Generating a return snapshots the numbers at that moment; approving/finalizing acts
  on that frozen version, and a later accounting correction produces version 2 rather than
  silently changing what a reviewer already approved.
- **The applicability engine is separate from the calculation engine** (Phase 5) —
  `TDSApplicabilityService` decides *whether* TDS applies (threshold, PAN, rule-effective-
  date checks) and only ever hands `TDSCalculationService` a confirmed `APPLICABLE` case;
  the calculator itself has no fallback path for an unresolved case, so a caller literally
  cannot compute an amount for a transaction the applicability engine hasn't cleared —
  `TDSRuleEngine` composes the two rather than merging their logic.
- **A manual override never overwrites the system's answer** (Phase 5) — `TDSTransaction`
  stores `system_calculated_amount` and `tds_amount` as two separate columns; overriding
  changes only `tds_amount` (plus `override_reason`/`overridden_by`/`overridden_at`), so an
  auditor reviewing a transaction later can always see both what the engine calculated and
  what a human changed it to, and why.
- **`no_pan_rate` is an explicit, optional column on `TDSRule`, not a hardcoded 20%**
  (Phase 5) — Section 206AA's higher no-PAN rate is real but not universal across every
  section/scenario a future rule might need, so the engine reads it from configuration and
  refuses to calculate (`MISSING_NO_PAN_RATE`) rather than assume 20% when it's unset.
- **Deductee, not a duplicated Vendor/Customer row, optionally links to one** (Phase 5) —
  `Deductee.vendor_id`/`customer_id` are nullable FKs so a company's existing Phase 3 party
  data is reused where it already exists, while still allowing a deductee that isn't
  otherwise tracked as a Vendor/Customer (e.g. a one-off professional fee) to exist
  independently.
- **Reconciliation findings are fully recomputed on every run, never incrementally patched**
  (Phase 5) — `TDSReconciliationService.run()` clears prior findings for the financial year
  before regenerating them, the same "it's a report, not a ledger" principle Phase 4's GST
  reconciliation already established, so a finding can never silently go stale after a
  challan allocation changes.
- **Only a masked bank account number is ever collected, not encrypted-and-stored** (Phase
  6) — `BankAccount.account_number_masked` accepts exactly what the user types (e.g.
  `XXXXXX1234`); the platform never asks for, transmits, or stores a full account number, so
  there is nothing sensitive to protect at rest or accidentally log in the first place.
- **The matching engine is a fixed point-score system, not a similarity threshold or ML
  model** (Phase 6) — `BankMatchingService`'s weights (`SCORE_EXACT_AMOUNT`,
  `SCORE_EXACT_REFERENCE`, ...) are named module constants, so the exact same inputs always
  produce the exact same score and an auditor can read the source to know precisely why a
  match scored what it did — never a black box.
- **Auto-matching requires both a strong score and zero ties for the top score** (Phase 6) —
  two candidates at the same top score (e.g. two receipts of the same amount on the same
  day) block auto-matching even if that score would otherwise clear the threshold; ambiguity
  itself, not just a low score, is treated as a reason to ask a human (PHASE6 §20).
- **`BankTransactionMatch.source_type`/`source_id` is a generic reference, not three nullable
  FKs** (Phase 6) — mirrors `TDSTransaction.source_type`/`source_id` from Phase 5: a match
  points to exactly one of Payment/Receipt/JournalEntry, and the same shape works whichever
  it is, without a `CHECK` constraint enumerating "exactly one of three FKs is set."
- **Bank adjustments call `JournalEntryService.create()` and `.post()` directly, never
  duplicate their validation** (Phase 6) — an adjustment is a real, POSTED journal entry
  subject to the exact same financial-year and period-lock checks every other journal entry
  already goes through; `BankAdjustmentService` only builds the two offsetting lines and
  records the resulting `ADJUSTMENT` match, it owns no accounting logic of its own.
- **Reconciliation status transitions are a `(from_status, action) -> to_status` lookup
  table, not scattered `if` statements** (Phase 6) — the same pattern Phase 4/5's return
  workflows already use for `GSTReturnSnapshot`/`TDSReturnSnapshot`; an unlisted transition
  (e.g. submitting a `LOCKED` session) is refused by construction rather than by remembering
  to add a check.
- **The CA/Auditor workflow domain is named and routed to never collide with the
  pre-existing security audit trail** (Phase 7) — `audit_workflow_enums.py`,
  `AuditEngagement`/`AuditFinding`/..., and the `/audits/...` prefix are all distinct from
  the Phase 1 `AuditLog`/`AuditAction`/`/audit-logs` it extends rather than duplicates, so
  "who did what" logging and "what does this engagement's review look like" stay two
  separate concerns that happen to share an English word.
- **`AuditFindingEvidence` links an existing `Document`, it never re-stores a file** (Phase
  7) — the same "reuse, don't duplicate" instinct Phase 5 applied to `Deductee`/Vendor and
  Phase 6 applied to journal entries; the only new data is the join row plus an optional
  description, so there is exactly one place a file's bytes ever live.
- **Approval and sign-off are gated by explicit, queryable checks, not left to reviewer
  memory** (Phase 7) — `_check_can_approve()` and the lead-auditor-sign-off check both run
  inside the same transition path every other action goes through, so "did anyone check for
  open critical findings before approving" is a guarantee the code makes, not a step a busy
  reviewer might skip.
- **`IncomeTaxCreditEntry` is a new model, not a reuse of `TDSTransaction`** (Phase 8) —
  they represent tax moving in opposite directions (deducted by this company vs. deducted
  from this company); reusing one table for both would have made every downstream query
  ambiguous about which direction a row meant.
- **The Income Tax calculator is pure functions over a caller-supplied rule set, with no
  DB access of its own** (Phase 8) — `income_tax_calculator.py`'s `compute_slab_tax`/
  `compute_rebate`/`compute_surcharge`/`compute_cess` take plain `Decimal`s and rule-set
  rows in, return a result out, and are unit-tested directly against fixtures rather than
  through the full computation service — the same reason `TaxCalculationService`
  (Phase 5) and `GSTCalculationService` (Phase 4) were kept side-effect-free.
- **A deduction's stored `eligible_amount` is a display default, never the figure a
  computation trusts** (Phase 8) — `IncomeTaxComputationService.calculate()` always
  recomputes eligibility fresh against its own rule set via
  `DeductionService.eligible_amount_for()`, so a deduction entered before a regime was
  even chosen can never silently carry a stale eligibility figure into the final tax.
- **Overdue is computed by a synchronous sweep triggered from a real request, not a
  scheduled job** (Phase 9) — Phase 9's explicit "no Celery, no Redis" constraint ruled out
  a background worker, so `ComplianceTaskService.sweep_overdue()` runs inline whenever the
  dashboard or calendar is actually viewed; the tradeoff (a task might show `PENDING` for a
  few minutes after midnight until someone opens the dashboard) was accepted deliberately
  rather than adding infrastructure the rest of the project doesn't use.
- **Every notification write goes through one method, never a direct `Notification()`
  construction** (Phase 9) — `NotificationService.notify()` owns both the dedup check and
  the `NotificationProvider.send()` call, so a future email/SMS provider is one class away
  and every trigger site (assignment, review-required, overdue, comment, reassignment)
  automatically gets deduplication for free instead of each call site reimplementing it.
- **A compliance rule's `company_id` is nullable to express "platform default vs. company
  override" in one table, not two** (Phase 9) — mirrors `GSTTaxRate`/`TDSRule`'s own
  `company_id IS NULL` convention for statutory defaults; `ComplianceRuleRepository.
  get_active_version()` centralizes the "company override wins" lookup so no caller has to
  remember the precedence rule itself.

---

## 25. Security Notes

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

---

## 26. Phase 10 — Business Workflow & UX Intelligence

Phase 10 transforms the platform from a collection of isolated compliance modules into a cohesive, actionable, business-driven workflow application.

### 1. Architectural Highlights
- **Command Center Dashboard (`/dashboard`)**:
  - Unifies real-time business attention counters, active FY/quarter context, deterministic setup progress, end-to-end workflow pipeline, compliance health matrix, today's actionable tasks, and role-tailored quick action hubs.
  - Replaces generic/disconnected statistics with real backend-derived operational states.
- **Action Center (`/action-center`)**:
  - Central clearinghouse for pending tasks, reconciliation exceptions, missing balances, and compliance deadlines.
  - Multi-dimensional filtering by Category (Critical, Due Soon, Overdue, Review Required, Reconciliation, Compliance, Tax, Accounting), Severity (Critical, High, Medium, Low, Info), and Module.
  - Fully URL-synced filters for direct deep-linking from attention cards.
- **Workflow Lifecycle Pipeline**:
  - Visual 8-stage pipeline tracking progress across: Data Ingestion → Accounting → GST / TDS → Bank Reconciliation → Income Tax → Audit → Compliance → Reporting.
  - Real-time pending and blocking counters with direct action navigation.
- **Deterministic Setup Progress**:
  - Evaluates 8 essential organization prerequisites (Profile, Financial Year, Chart of Accounts, GST Profile, TDS Profile, Bank Account, Opening Balances, First Import) directly against the database state.
- **Company Health Matrix**:
  - Deterministically evaluates 7 operational domains (Accounting, GST, TDS, Bank, Income Tax, Audit, Compliance) into `READY`, `NEEDS_ATTENTION`, `BLOCKED`, or `NOT_CONFIGURED` with domain-specific metrics.
- **Global Search (`Cmd+K` / `Ctrl+K`)**:
  - Company-scoped fast query across 11 entity types: Customers, Vendors, Sales Invoices, Purchase Invoices, Receipts, Payments, Ledgers, Documents, Bank Transactions, Audit Findings, and Compliance Obligations.
  - Strict tenant isolation enforced server-side.
- **Backend Aggregation Layer**:
  - `GET /api/v1/dashboard/summary`: Aggregates active period and 6-tier attention counters.
  - `GET /api/v1/dashboard/actions`: Assembles prioritized action items across all modules.
  - `GET /api/v1/dashboard/workflow`: Evaluates the 8 lifecycle stages.
  - `GET /api/v1/dashboard/setup-progress`: Evaluates 8 setup prerequisites.
  - `GET /api/v1/dashboard/health`: Evaluates the 7 compliance domain health states.
  - `GET /api/v1/action-center`: Paginated and filtered action center tasks.
  - `GET /api/v1/search`: High-performance company-scoped global search.

### 2. Constraints & Security
- **Local & Self-Contained**: 100% free and local architecture. No cloud or paid APIs.
- **Tenant Isolation**: All aggregation and search endpoints resolve company membership server-side; cross-tenant access returns `403 Forbidden` / `404 Not Found`.
- **Zero Regressions**: 369/369 tests pass (364 baseline + 5 Phase 10 tests).
- **Migration Head**: `21f14d138a81` (no schema change required; workflow states are derived directly from existing domain models).
- **External Integrations**: Live portal integrations remain adapter-ready only.

---

## 27. Phase 11 — Reports & Business Intelligence

Phase 11 transforms raw transactional and compliance data across all modules into authoritative, auditable, drill-down business intelligence.

### 1. Architectural Highlights
- **Centralized Report Center (`/reports`)**:
  - Organizes reporting into 6 structured domains: Management, Financial, Tax & GST, Banking, Audit, and Compliance.
  - Interactive search, domain tagging, quick access, and direct deep-linking.
- **Executive BI Cockpit (`/reports/management`)**:
  - Executive KPI cards: Revenue, Costs, Net Profit, Receivables, Payables, Bank Position, Net GST, TDS Payable, Open Findings, Overdue Tasks.
  - Prior Period / Prior FY comparison with safe zero-division handling (`N/A`).
  - Top Debtors & Creditors with direct drill-down links to invoices.
- **Financial Reports (`/reports/financial`)**:
  - **Standardized Trial Balance**: Opening Dr/Cr, Period Dr/Cr, Closing Dr/Cr. Total Debit == Total Credit integrity verification with visible warning banner.
  - **Profit & Loss Statement**: Revenue, Cost of Sales, Gross Profit, Operating Expenses, Operating Profit, Other Income/Expenses, Profit Before Tax, Tax Expense, Net Profit. Explicit classification warnings when ledgers lack mapping.
  - **Balance Sheet**: Assets, Liabilities, and Equity (including retained earnings from P&L). Real-time Assets == Liabilities + Equity balance verification.
  - **General Ledger (`/reports/general-ledger`)**: Running balance, voucher type badges, date constraints, and direct link to underlying transaction.
  - **Receivables & Payables Outstanding**: Full customer and vendor registers respecting Phase 9.6 formula (`Net Invoiced = Invoice + Debit Note - Credit Note`, `Outstanding = Net Invoiced - Receipts/Payments`).
  - **Ageing Analysis**: Receivable & Payable ageing bucketed into `CURRENT`, `1_30`, `31_60`, `61_90`, `91_180`, and `181_PLUS` days. Explicit fallback to invoice date when due date is unavailable.
  - **Sales & Purchase Analytics**: Monthly trends, GST tax slabs distribution, and party contribution percentages.
- **Tax & Statutory Intelligence (`/reports/tax`)**:
  - **GST Summary**: Outward supplies, CGST/SGST/IGST/Cess liability, eligible input tax credit (ITC), and net payable position.
  - **TDS Intelligence**: Section-wise transaction counts, gross amount, TDS calculated, deducted, paid, and payable. Full challan deposit and allocation tracking.
  - **Income Tax Summary**: Breakdown by head of income, chapter VI-A deductions, rebate 87A, surcharge, cess, and final net tax liability/refund.
- **Audit & Compliance Intelligence**:
  - **Audit Engagements & Findings**: Open vs completed engagements, checklist completion percentage, critical findings, and pending auditor review items.
  - **Compliance Status**: Category-wise distribution, overdue obligations, and tasks due soon.
- **Universal Report Filter System (`ReportFilterBar`)**:
  - Reusable filter component with FY selection, quick presets (This FY, Q1, Q2, Q3, Q4, Last Month, Custom), date range pickers, As Of date, and comparison toggle.
  - URL query synchronization (`/reports/financial?tab=profit-loss&date_from=2025-04-01&date_to=2025-09-30`) allowing stateful sharing and reopening.
- **Standardized Export Engine**:
  - Dual CSV and XLSX export powered by server-side `render_export` utility.
  - Auditable export logging (`REPORT_EXPORT_GENERATED`).
  - Strict tenant and permission enforcement on all exports.

### 2. Backend Endpoints
- `GET /api/v1/reports/management`: Executive KPI summary with prior period comparisons.
- `GET /api/v1/reports/trial-balance`: Standardized double-entry trial balance.
- `GET /api/v1/reports/profit-loss`: Multi-step P&L with COGS and operating profit.
- `GET /api/v1/reports/balance-sheet`: Reconciled balance sheet statement.
- `GET /api/v1/reports/general-ledger`: Detailed ledger entry register with running balance.
- `GET /api/v1/reports/receivables`: Customer-level receivables outstanding.
- `GET /api/v1/reports/payables`: Vendor-level payables outstanding.
- `GET /api/v1/reports/ageing`: 6-bucket ageing analysis for debtors or creditors.
- `GET /api/v1/reports/sales`: Sales and purchase analytics with GST distribution.
- `GET /api/v1/reports/cash-bank`: Bank account summary and reconciliation overview.
- `GET /api/v1/reports/gst`: GST outward, ITC, and net tax position summary.
- `GET /api/v1/reports/tds`: TDS deduction and challan allocation summary.
- `GET /api/v1/reports/income-tax`: Income tax calculation breakdown summary.
- `GET /api/v1/reports/audit`: Audit engagement and checklist progress summary.
- `GET /api/v1/reports/compliance`: Compliance task health and category distribution.
- `GET /api/v1/reports/export`: Standardized CSV / XLSX report file downloads.

### 3. Verification & Quality Gates
- **Total Backend Tests**: 377 / 377 PASS (369 frozen baseline + 8 comprehensive Phase 11 integration tests).
- **Frontend Quality**: TypeScript passed with zero errors; ESLint clean; Vite production bundle built successfully.
- **Migration Head**: `21f14d138a81` (no schema change; all reports derived cleanly from existing domain models).
- **Tenant Isolation**: Cross-tenant direct API requests return `403 Forbidden`.



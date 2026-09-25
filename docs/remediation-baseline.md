# Tally Tax — Remediation Baseline Report

**Date**: 2026-09-24  
**Workspace**: `/home/joes_17/taliy`  
**Phase**: Phase 0 — Create Remediation Baseline  

---

## 1. Executive Summary

This baseline report captures the operational state of the Tally Tax codebase prior to applying remediation fixes across Phases 1 through 13. Baseline metrics cover Backend environment & tests, Frontend lint & build, Database migrations, and affected file inventories.

---

## 2. Environment & Tooling Baseline

- **Operating System**: Linux 6.6.137+
- **Host Python Version**: Python 3.12.3
- **Package Manager Available**: `uv 0.11.19` (`/home/joes_17/.local/bin/uv`)
- **Node.js Version**: v22.23.1
- **npm Version**: 10.9.8
- **PostgreSQL Database**: PostgreSQL 16.13 on `localhost:5432` (`taxplatform:taxplatform@localhost:5432/taxplatform`)

---

## 3. Frontend Baseline

### 3.1 Lint Status (`npm run lint`)
- **Status**: **FAILED** (Exit code 1)11
- **Total Problems**: 125 (121 Errors, 4 Warnings)
- **Error Summary**:
  - `react-hooks/rules-of-hooks`: 121 errors across 20 page components.
  - Root Cause: Components execute early return `if (!activeCompany) return <EmptyState />;` before declaring React hooks (`useState`, `useQuery`, `useMutation`, `useForm`, `useEffect`).
- **Warning Summary**:
  - `react-refresh/only-export-components`: 4 warnings (`badge.tsx`, `button.tsx`, `useAuth.tsx`, `useToast.tsx`).

#### Identified Affected Frontend Files (20 Files with Rule of Hooks Violations):
1. `frontend/src/pages/audit/AuditDashboardPage.tsx`
2. `frontend/src/pages/audit/AuditEngagementDetailPage.tsx`
3. `frontend/src/pages/audit/AuditFindingDetailPage.tsx`
4. `frontend/src/pages/bank/BankDashboardPage.tsx`
5. `frontend/src/pages/bank/BankReconciliationDetailPage.tsx`
6. `frontend/src/pages/compliance/ComplianceCalendarPage.tsx`
7. `frontend/src/pages/compliance/ComplianceDashboardPage.tsx`
8. `frontend/src/pages/compliance/ComplianceTaskDetailPage.tsx`
9. `frontend/src/pages/compliance/ComplianceTasksPage.tsx`
10. `frontend/src/pages/compliance/NotificationsPage.tsx`
11. `frontend/src/pages/gst/GstReturnPeriodDetailPage.tsx`
12. `frontend/src/pages/income-tax/CapitalGainsPage.tsx`
13. `frontend/src/pages/income-tax/DeductionsPage.tsx`
14. `frontend/src/pages/income-tax/IncomeTaxDashboardPage.tsx`
15. `frontend/src/pages/income-tax/IncomeTaxIncomePage.tsx`
16. `frontend/src/pages/income-tax/IncomeTaxProfilePage.tsx`
17. `frontend/src/pages/income-tax/TaxComputationDetailPage.tsx`
18. `frontend/src/pages/income-tax/TaxComputationsPage.tsx`
19. `frontend/src/pages/income-tax/TaxPaymentsPage.tsx`
20. `frontend/src/pages/tds/TdsReturnPeriodDetailPage.tsx`

### 3.2 Build Status (`npm run build`)
- **Status**: **PASSED** (Exit code 0)
- **Vite Build Time**: 3.86s
- **Output Artifacts**: `dist/index.html` (0.47 kB), `dist/assets/index-*.css` (45.39 kB), `dist/assets/index-*.js` (621.15 kB)

---

## 4. Backend Baseline

### 4.1 Dependency Check & Test Collection Status (`pytest -v`)
- **Status**: **COLLECTION FAILED** (Exit code 4)
- **Collection Error**:
  ```
  ImportError while loading conftest '/home/joes_17/taliy/backend/tests/conftest.py'.
  ModuleNotFoundError: No module named 'httpx'
  ```
- **Root Cause**: Host Python 3.12 environment is missing core dependencies specified in `backend/requirements.txt`:
  - `httpx==0.28.1`
  - `asyncpg==0.30.0`
  - `aiosqlite==0.20.0`
  - `argon2-cffi==23.1.0`
  - `psycopg2-binary==2.9.10`
- **Remediation Plan**: Create isolated virtual environment `backend/.venv` using `uv`, install exact dependencies from `backend/requirements.txt`, and execute pytest test suites.

---

## 5. Database Baseline

### 5.1 Alembic Migration Status
- **Current Version**: `9f0530640b44` (Head)
- **Total Migrations Applied**: 16 migrations
  - `001_initial_schema.py`
  - `002_gst_models.py`
  - `003_tds_models.py`
  - `004_banking_models.py`
  - `005_audit_models.py`
  - `006_income_tax_models.py`
  - `007_compliance_models.py`
  - `008_accounting_models.py`
  - `009_party_tax_profiles.py`
  - `010_e_way_bills.py`
  - `011_tds_challan_allocations.py`
  - `012_bank_reconciliations.py`
  - `013_audit_sampling_evidence.py`
  - `014_advance_tax_calculations.py`
  - `015_compliance_alerts.py`
  - `016_accounting_reports.py` (`9f0530640b44`)
- **Table Count**: 94 tables in database schema.

---

## 6. Identified Deficiencies Requiring Remediation

| Phase | Category | Description | Affected Modules |
|-------|----------|-------------|------------------|
| **Phase 1** | Frontend Hooks | React Hook order violation after early return `if (!activeCompany)` | 20 Page components across Audit, Bank, Compliance, GST, Income Tax, TDS |
| **Phase 2** | Backend Environment | Missing Python test dependencies in test environment | `backend/requirements.txt`, `backend/.venv` |
| **Phase 3** | Accounting | Invoice auto-posting omitted (invoices marked POSTED create no journal entries) | `sales_invoice_service.py`, `purchase_invoice_service.py`, `journal_entry_service.py`, `report_service.py` |
| **Phase 4** | Compliance | `ComplianceObligationService.generate_from_rule()` has no API endpoint | `compliance_obligations.py`, `compliance_obligation_service.py` |
| **Phase 5** | Exports | Accounting reports only provide JSON, lack CSV/XLSX export endpoints | `reports.py`, `backend/app/utils/export.py` |
| **Phase 6** | GST / SEZ | GSTR-1 export section empty; models lack export/SEZ flags | `Customer`, `SalesInvoice`, `gstr1_service.py`, Alembic migration |
| **Phase 7** | Compliance | Compliance overdue task sweep only runs on user page visits | `compliance_calendar_service.py`, `compliance_task_service.py`, `main.py` |
| **Phase 8** | Notifications | InAppNotificationProvider is sole hardcoded implementation | `notification_service.py` provider interface & extensibility |
| **Phase 9** | Income Tax | Surcharge marginal relief warns but is not calculated | `income_tax_calculator.py` |
| **Phase 10** | Security | Default insecure development JWT secret key permitted without check | `backend/app/core/config.py` |

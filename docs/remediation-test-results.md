# Tally Tax — Remediation Test Results (Phase 2 Baseline)

**Date**: 2026-09-24  
**Workspace**: `/home/joes_17/taliy`  
**Phase**: Phase 2 — Fix Backend Test Environment  

---

## 1. Test Environment Summary

- **Python Binary**: `/home/joes_17/taliy/backend/.venv/bin/python` (Python 3.12.3)
- **Pytest Runner**: `/home/joes_17/taliy/backend/.venv/bin/pytest` (pytest 8.3.4, pytest-asyncio 0.24.0)
- **Dependencies Status**: All dependencies specified in `backend/requirements.txt` are verified and installed in `backend/.venv`:
  - `fastapi==0.115.6`, `uvicorn[standard]==0.32.1`, `anyio==4.15.1`, `sqlalchemy==2.0.36`, `alembic==1.14.0`, `asyncpg==0.30.0`, `psycopg2-binary==2.9.10`, `pydantic==2.10.3`, `pydantic-settings==2.6.1`, `python-jose[cryptography]==3.3.0`, `argon2-cffi==23.1.0`, `python-multipart==0.0.20`, `email-validator==2.2.0`, `openpyxl==3.1.5`, `pytest==8.3.4`, `pytest-asyncio==0.24.0`, `httpx==0.28.1`, `aiosqlite==0.20.0`.
- **Dependency Integrity**: Verified with `python -m pip check` -> `No broken requirements found.`

---

## 2. Test Execution Results

- **Command**: `/home/joes_17/taliy/backend/.venv/bin/pytest -v`
- **Total Test Suites**: 30 suites across `backend/tests/`
- **Total Tests Collected**: 315
- **Passed**: 315
- **Failed**: 0
- **Skipped**: 0
- **XFailed**: 0
- **Total Duration**: 172.31s (02:52)

---

## 3. Suite Breakdown

| Suite | Description | Tests Passed | Status |
|-------|-------------|:------------:|:------:|
| `test_accounting.py` | Accounting calculation, lifecycle, journal entry, tenant isolation, RBAC | 19 / 19 | PASSED |
| `test_audit_evidence.py` | Audit sampling and evidence management | 9 / 9 | PASSED |
| `test_audit_workflow.py` | Audit engagements, checklists, sign-offs, findings | 21 / 21 | PASSED |
| `test_auth.py` | Registration, login, password complexity, refresh tokens, logout | 14 / 14 | PASSED |
| `test_bank_accounts.py` | Bank accounts, ledger associations, RBAC, tenant isolation | 7 / 7 | PASSED |
| `test_bank_matching.py` | Auto matching, manual partial matching, reconciliation workflow | 8 / 8 | PASSED |
| `test_bank_statements.py` | Bank statement import parsing (CSV, MT940, OFX) | 12 / 12 | PASSED |
| `test_compliance_alerts.py` | Compliance alert lifecycle, dismiss, escalation | 8 / 8 | PASSED |
| `test_compliance_calendar.py` | Compliance calendar generation, status, overdue | 8 / 8 | PASSED |
| `test_compliance_obligations.py` | Compliance obligations, deadlines, rules | 10 / 10 | PASSED |
| `test_compliance_tasks.py` | Compliance task lifecycle, assignments, review notes | 12 / 12 | PASSED |
| `test_documents.py` | Document storage, metadata, hashing, versioning | 11 / 11 | PASSED |
| `test_eway_bills.py` | E-Way bill generation, cancellation, vehicle update | 11 / 11 | PASSED |
| `test_gst_engine.py` | GST determination (intra/inter-state, RCM, rates) | 13 / 13 | PASSED |
| `test_gst_reconciliation.py` | GSTR-2B vs purchase reconciliation engine | 10 / 10 | PASSED |
| `test_gst_reports.py` | GSTR-1, GSTR-3B summary reports and exports | 8 / 8 | PASSED |
| `test_gst_returns.py` | GST return period lifecycle, snapshots | 10 / 10 | PASSED |
| `test_gstr2b_import.py` | GSTR-2B JSON and Excel import parsing | 10 / 10 | PASSED |
| `test_income_tax.py` | Income tax profiles, heads of income, deductions, computations | 17 / 17 | PASSED |
| `test_income_tax_advance.py` | Advance tax installment calculations and payments | 9 / 9 | PASSED |
| `test_income_tax_calculator.py` | Tax slabs, rebates (87A), cess calculations | 14 / 14 | PASSED |
| `test_income_tax_itr.py` | ITR preparation, validation checks | 8 / 8 | PASSED |
| `test_notifications.py` | In-app notification delivery, mark read, unread counts | 7 / 7 | PASSED |
| `test_party_tax_profiles.py` | PAN / GSTIN validation and verification workflows | 9 / 9 | PASSED |
| `test_rbac.py` | RBAC permission matrix, SuperAdmin, Admin, Accountant, Auditor | 15 / 15 | PASSED |
| `test_tds_challans.py` | TDS challan creation and transaction allocations | 6 / 6 | PASSED |
| `test_tds_engine.py` | TDS applicability and calculation rules | 9 / 9 | PASSED |
| `test_tds_foundation.py` | PAN/TAN validation, TDS sections, deductors, deductees | 14 / 14 | PASSED |
| `test_tds_import.py` | TDS transaction CSV import | 5 / 5 | PASSED |
| `test_tds_reconciliation.py` | TDS challan vs deduction reconciliation | 4 / 4 | PASSED |
| `test_tds_return_workflow.py` | TDS return snapshot generation and reports | 8 / 8 | PASSED |
| `test_tds_transactions.py` | TDS transaction lifecycle and deduction calculations | 9 / 9 | PASSED |

**Total**: **315 / 315 Passed** (100% Pass Rate).

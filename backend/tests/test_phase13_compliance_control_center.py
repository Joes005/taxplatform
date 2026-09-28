import uuid
import pytest
from datetime import date, datetime, timedelta, timezone

from app.core.exceptions import ValidationAppError
from app.core.permissions import RoleCode
from app.models.compliance_enums import (
    ComplianceCategory,
    ComplianceFrequency,
    ComplianceHealthStatus,
    ComplianceModule,
    ComplianceObligationStatus,
    CompliancePriority,
    ReadinessStatus,
)
from app.models.compliance_obligation import ComplianceObligation
from app.services.compliance_deadline_service import compute_due_date
from app.services.compliance_health_service import ComplianceHealthService
from app.services.compliance_readiness_service import ComplianceReadinessService
from tests.conftest import add_membership, auth_headers, login
from tests.sample_files import MIN_PDF


class TestDueDateEngine:
    """Unit tests for Phase 13 Centralized Due Date Engine."""

    def test_days_after_month_end(self):
        due = compute_due_date(
            {"type": "DAYS_AFTER_MONTH_END", "days": 11},
            period_start=date(2025, 4, 1),
            period_end=date(2025, 4, 30),
        )
        assert due == date(2025, 5, 11)

    def test_days_after_month_end_clamped(self):
        due = compute_due_date(
            {"type": "DAYS_AFTER_MONTH_END", "days": 20},
            period_start=date(2025, 5, 1),
            period_end=date(2025, 5, 31),
        )
        assert due == date(2025, 6, 20)

    def test_quarter_based_offset(self):
        # Q1 ends June 30 -> offset month 1, day 31 -> July 31
        due = compute_due_date(
            {"type": "QUARTER_BASED_OFFSET", "month_offset": 1, "day": 31},
            period_start=date(2025, 4, 1),
            period_end=date(2025, 6, 30),
        )
        assert due == date(2025, 7, 31)

    def test_fixed_date_annual(self):
        # Tax return due date: July 31
        due = compute_due_date(
            {"type": "FIXED_DATE_ANNUAL", "month": 7, "day": 31},
            period_start=date(2025, 4, 1),
            period_end=date(2026, 3, 31),
        )
        assert due == date(2026, 7, 31)


class TestReadinessAndHealthUnits:
    """Unit tests for cross-module readiness & health scoring services."""

    @pytest.mark.asyncio
    async def test_readiness_service_gst_missing_profile(self, db_session, company_a_with_admin):
        company, _admin = company_a_with_admin
        readiness_svc = ComplianceReadinessService(db_session)

        # Obligation for GSTR-1
        ob = ComplianceObligation(
            company_id=company.id,
            code="GST-GSTR1-2025-04",
            name="GSTR-1 Monthly Return",
            category=ComplianceCategory.GST,
            module=ComplianceModule.GST,
            frequency=ComplianceFrequency.MONTHLY,
            start_date=date(2025, 4, 1),
            due_date=date(2025, 5, 11),
            priority=CompliancePriority.HIGH,
            status=ComplianceObligationStatus.ACTIVE,
            created_by=_admin.id,
        )
        db_session.add(ob)
        await db_session.flush()

        res = await readiness_svc.evaluate_obligation(company.id, ob)
        assert res.overall_status in (ReadinessStatus.BLOCKED, ReadinessStatus.READY_WITH_WARNINGS)
        assert len(res.checks) > 0
        # GST profile missing check should fail
        gst_checks = [c for c in res.checks if c.check_code == "GST_PROFILE_MISSING"]
        assert len(gst_checks) == 1
        assert gst_checks[0].status == "FAIL"
        assert gst_checks[0].blocking is True

    @pytest.mark.asyncio
    async def test_compliance_health_service_deterministic(self, db_session, company_a_with_admin):
        company, _admin = company_a_with_admin
        health_svc = ComplianceHealthService(db_session)

        # Add 1 overdue obligation
        ob = ComplianceObligation(
            company_id=company.id,
            code="COMP-OVERDUE-01",
            name="Overdue Statutory Return",
            category=ComplianceCategory.GENERAL,
            module=ComplianceModule.GENERAL,
            frequency=ComplianceFrequency.ANNUAL,
            start_date=date(2025, 1, 1),
            due_date=date(2025, 2, 1),  # In the past
            priority=CompliancePriority.CRITICAL,
            status=ComplianceObligationStatus.OVERDUE,
            created_by=_admin.id,
        )
        db_session.add(ob)
        await db_session.flush()

        health = await health_svc.compute_company_health(company.id)
        assert health.health_status == ComplianceHealthStatus.OVERDUE
        assert health.score < 100
        assert len(health.reasons) > 0
        assert any("overdue" in r.lower() for r in health.reasons)


class TestObligationLifecycleAndGuards:
    """Test full state machine transitions and blocking guards."""

    @pytest.mark.asyncio
    async def test_lifecycle_and_blocking_guards(self, client, db_session, seeded_rbac, company_a_with_admin):
        company, admin = company_a_with_admin
        auth = await login(client, "admin-a@example.com", "TestPass1!")
        token = auth["access_token"]
        headers = auth_headers(token)

        # Create obligation
        create_res = await client.post(
            f"/api/v1/compliance/obligations?company_id={company.id}",
            json={
                "code": "GSTR1-MAY-2025",
                "name": "GSTR-1 May 2025 Return",
                "category": "GST",
                "module": "GST",
                "frequency": "MONTHLY",
                "start_date": "2025-05-01",
                "due_date": "2025-06-11",
                "priority": "HIGH",
            },
            headers=headers,
        )
        assert create_res.status_code == 201, create_res.text
        ob_id = create_res.json()["data"]["id"]

        # 1. Assign blocked obligation
        assign_res = await client.post(
            f"/api/v1/compliance/obligations/{ob_id}/assign?company_id={company.id}",
            json={"assigned_to": str(admin.id), "reviewer_id": str(admin.id)},
            headers=headers,
        )
        assert assign_res.status_code == 200
        assert assign_res.json()["data"]["assigned_to"] == str(admin.id)
        assert assign_res.json()["data"]["status"] == "BLOCKED"

        # 2. Check Readiness (fails because GST profile is not yet configured)
        readiness_res = await client.post(
            f"/api/v1/compliance/obligations/{ob_id}/readiness?company_id={company.id}",
            headers=headers,
        )
        assert readiness_res.status_code == 200
        assert readiness_res.json()["data"]["overall_status"] in ("BLOCKED", "READY_WITH_WARNINGS")

        # 3. Guard test: Approve should fail while BLOCKED
        approve_fail = await client.post(
            f"/api/v1/compliance/obligations/{ob_id}/approve?company_id={company.id}",
            json={"review_notes": "Trying to bypass"},
            headers=headers,
        )
        assert approve_fail.status_code in (409, 422), "Should block approval when prerequisite fails"

        # 4. Guard test: Submit review should fail while BLOCKED
        submit_fail = await client.post(
            f"/api/v1/compliance/obligations/{ob_id}/submit-review?company_id={company.id}",
            json={"review_notes": "Ready for check"},
            headers=headers,
        )
        assert submit_fail.status_code in (409, 422), "Should block review submission when prerequisite fails"

        # 5. Non-blocked obligation: test full review, reject, approve, complete lifecycle
        gen_res = await client.post(
            f"/api/v1/compliance/obligations?company_id={company.id}",
            json={
                "code": "GEN-BOARD-01",
                "name": "Annual Board Resolution Filing",
                "category": "GENERAL",
                "module": "GENERAL",
                "frequency": "ANNUAL",
                "start_date": "2025-04-01",
                "due_date": "2025-09-30",
                "priority": "MEDIUM",
            },
            headers=headers,
        )
        assert gen_res.status_code == 201
        gen_id = gen_res.json()["data"]["id"]

        # Assign
        assign_gen = await client.post(
            f"/api/v1/compliance/obligations/{gen_id}/assign?company_id={company.id}",
            json={"assigned_to": str(admin.id), "reviewer_id": str(admin.id)},
            headers=headers,
        )
        assert assign_gen.status_code == 200
        assert assign_gen.json()["data"]["status"] == "ASSIGNED"

        # Submit review
        submit_gen = await client.post(
            f"/api/v1/compliance/obligations/{gen_id}/submit-review?company_id={company.id}",
            json={"review_notes": "Board notes ready"},
            headers=headers,
        )
        assert submit_gen.status_code == 200
        assert submit_gen.json()["data"]["status"] == "READY_FOR_REVIEW"

        # Reject (return for changes)
        reject_gen = await client.post(
            f"/api/v1/compliance/obligations/{gen_id}/reject?company_id={company.id}",
            json={"review_notes": "Missing signed director sheet"},
            headers=headers,
        )
        assert reject_gen.status_code == 200
        assert reject_gen.json()["data"]["status"] == "REJECTED"

        # Re-submit review
        resubmit = await client.post(
            f"/api/v1/compliance/obligations/{gen_id}/submit-review?company_id={company.id}",
            json={"review_notes": "Signed sheet attached"},
            headers=headers,
        )
        assert resubmit.status_code == 200
        assert resubmit.json()["data"]["status"] in ("READY_FOR_REVIEW", "UNDER_REVIEW")

        # Approve
        approve_gen = await client.post(
            f"/api/v1/compliance/obligations/{gen_id}/approve?company_id={company.id}",
            json={"review_notes": "Approved by auditor"},
            headers=headers,
        )
        assert approve_gen.status_code == 200
        assert approve_gen.json()["data"]["status"] == "APPROVED"

        # Complete
        complete_gen = await client.post(
            f"/api/v1/compliance/obligations/{gen_id}/complete?company_id={company.id}",
            json={"review_notes": "Filed successfully"},
            headers=headers,
        )
        assert complete_gen.status_code == 200
        assert complete_gen.json()["data"]["status"] == "COMPLETED"

        # Reopen
        reopen_gen = await client.post(
            f"/api/v1/compliance/obligations/{gen_id}/reopen?company_id={company.id}",
            json={"reason": "Audit request to amend minutes"},
            headers=headers,
        )
        assert reopen_gen.status_code == 200
        assert reopen_gen.json()["data"]["status"] == "REOPENED"


class TestEvidenceAndDocuments:
    """Test evidence attachment, listing, and multi-tenant isolation."""

    @pytest.mark.asyncio
    async def test_evidence_workflow(
        self, client, db_session, seeded_rbac, company_a_with_admin, company_b_with_admin, document_storage
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin

        auth_a = await login(client, "admin-a@example.com", "TestPass1!")
        headers_a = auth_headers(auth_a["access_token"])

        auth_b = await login(client, "admin-b@example.com", "TestPass1!")
        headers_b = auth_headers(auth_b["access_token"])

        # Upload document in Company A
        upload_res = await client.post(
            f"/api/v1/documents?company_id={company_a.id}",
            files={"file": ("receipt.pdf", MIN_PDF, "application/pdf")},
            data={"document_type": "TDS_DOCUMENT", "description": "Payment Challan Receipt"},
            headers=headers_a,
        )
        assert upload_res.status_code == 201, upload_res.text
        doc_id = upload_res.json()["data"]["id"]

        # Create obligation in Company A
        ob_res = await client.post(
            f"/api/v1/compliance/obligations?company_id={company_a.id}",
            json={
                "code": "TDS-CHALLAN-Q1",
                "name": "TDS Challan Payment",
                "category": "TDS",
                "module": "TDS",
                "frequency": "QUARTERLY",
                "start_date": "2025-04-01",
                "due_date": "2025-07-07",
                "priority": "MEDIUM",
            },
            headers=headers_a,
        )
        ob_id = ob_res.json()["data"]["id"]

        # Attach evidence
        attach_res = await client.post(
            f"/api/v1/compliance/obligations/{ob_id}/evidence?company_id={company_a.id}",
            json={"document_id": doc_id, "description": "Bank Paid Challan"},
            headers=headers_a,
        )
        assert attach_res.status_code == 201
        evidence_id = attach_res.json()["data"]["id"]

        # List evidence
        list_res = await client.get(
            f"/api/v1/compliance/obligations/{ob_id}/evidence?company_id={company_a.id}",
            headers=headers_a,
        )
        assert list_res.status_code == 200
        assert len(list_res.json()["data"]) == 1

        # Multi-tenancy check: Company B cannot attach or see Company A evidence
        cross_attach = await client.post(
            f"/api/v1/compliance/obligations/{ob_id}/evidence?company_id={company_b.id}",
            json={"document_id": doc_id, "description": "Malicious attach"},
            headers=headers_b,
        )
        assert cross_attach.status_code in (403, 404)

        # Remove evidence
        del_res = await client.delete(
            f"/api/v1/compliance/obligations/{ob_id}/evidence/{evidence_id}?company_id={company_a.id}",
            headers=headers_a,
        )
        assert del_res.status_code == 200
        assert del_res.json()["data"]["deleted"] is True


class TestReportsAndActionCenter:
    """Test exports, calendar, and Action Center integration."""

    @pytest.mark.asyncio
    async def test_control_center_and_exports(self, client, db_session, seeded_rbac, company_a_with_admin):
        company, _admin = company_a_with_admin
        auth = await login(client, "admin-a@example.com", "TestPass1!")
        headers = auth_headers(auth["access_token"])

        # Control center summary
        res = await client.get(f"/api/v1/compliance/control-center?company_id={company.id}", headers=headers)
        assert res.status_code == 200
        summary = res.json()["data"]
        assert "total_obligations" in summary
        assert "health" in summary

        # CSV Export Obligations
        csv_res = await client.get(
            f"/api/v1/compliance/reports/obligations/export?company_id={company.id}&format=csv",
            headers=headers,
        )
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]

        # XLSX Export Obligations
        xlsx_res = await client.get(
            f"/api/v1/compliance/reports/obligations/export?company_id={company.id}&format=xlsx",
            headers=headers,
        )
        assert xlsx_res.status_code == 200
        assert "application/vnd.openxmlformats" in xlsx_res.headers["content-type"]

        # Readiness CSV Export
        readiness_csv = await client.get(
            f"/api/v1/compliance/reports/readiness/export?company_id={company.id}&format=csv",
            headers=headers,
        )
        assert readiness_csv.status_code == 200

        # Action center integration check
        action_res = await client.get(f"/api/v1/action-center?company_id={company.id}", headers=headers)
        assert action_res.status_code == 200


class TestABC_Traders_Integrated_Scenario:
    """
    Real Integrated Scenario (Section 30):
    Company: ABC Traders Pvt Ltd
    1. Register user & onboard company
    2. Configure Financial Year
    3. Generate compliance obligations
    4. Calculate due dates
    5. Run readiness checks — detect missing prerequisites
    6. Assign obligations
    7. Upload evidence
    8. Submit for review
    9. Review & approve
    10. Complete
    11. Sweep overdue & verify notifications
    12. Reopen obligation & verify audit trail
    13. Verify Action Center and final health counts
    """

    @pytest.mark.asyncio
    async def test_abc_traders_full_lifecycle(self, client, db_session, seeded_rbac, document_storage):
        # 1. Register and login
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Ramesh",
                "last_name": "Gupta",
                "email": "ramesh@abctraders.com",
                "password": "Password123!",
            },
        )
        assert reg_res.status_code == 201

        auth = await login(client, "ramesh@abctraders.com", "Password123!")
        token = auth["access_token"]
        headers = auth_headers(token)

        # 2. Onboard ABC Traders Pvt Ltd
        onboard_res = await client.post(
            "/api/v1/companies/onboard",
            json={
                "legal_name": "ABC Traders Pvt Ltd",
                "trade_name": "ABC Traders",
                "business_type": "PRIVATE_LIMITED",
                "pan": "AAACA1234A",
                "gstin": "27AAPFU0939F1ZV",
                "state": "Maharashtra",
                "city": "Mumbai",
            },
            headers=headers,
        )
        assert onboard_res.status_code == 201
        company_id = onboard_res.json()["data"]["id"]

        # Select company
        await client.post("/api/v1/auth/select-company", json={"company_id": company_id}, headers=headers)

        # 3. Create active Financial Year 2025-26
        fy_res = await client.post(
            f"/api/v1/accounting/financial-years?company_id={company_id}",
            json={
                "name": "2025-26",
                "start_date": "2025-04-01",
                "end_date": "2026-03-31",
                "is_current": True,
            },
            headers=headers,
        )
        assert fy_res.status_code == 201
        fy_id = fy_res.json()["data"]["id"]

        # 4. Generate compliance obligations for ABC Traders
        ob1_res = await client.post(
            f"/api/v1/compliance/obligations?company_id={company_id}",
            json={
                "code": "ABC-GST-3B-APR",
                "name": "GSTR-3B Monthly Return - April",
                "category": "GST",
                "module": "GST",
                "frequency": "MONTHLY",
                "financial_year_id": fy_id,
                "start_date": "2025-04-01",
                "due_date": "2025-05-20",
                "priority": "HIGH",
            },
            headers=headers,
        )
        assert ob1_res.status_code == 201
        ob1_id = ob1_res.json()["data"]["id"]

        # Obligation 2: TDS return
        ob2_res = await client.post(
            f"/api/v1/compliance/obligations?company_id={company_id}",
            json={
                "code": "ABC-TDS-26Q-Q1",
                "name": "TDS Return 26Q Q1",
                "category": "TDS",
                "module": "TDS",
                "frequency": "QUARTERLY",
                "financial_year_id": fy_id,
                "start_date": "2025-04-01",
                "due_date": "2025-07-31",
                "priority": "MEDIUM",
            },
            headers=headers,
        )
        assert ob2_res.status_code == 201
        ob2_id = ob2_res.json()["data"]["id"]

        # 5. Run readiness checks — verify missing GST profile is detected
        readiness1 = await client.post(
            f"/api/v1/compliance/obligations/{ob1_id}/readiness?company_id={company_id}",
            headers=headers,
        )
        assert readiness1.status_code == 200
        r_data = readiness1.json()["data"]
        assert r_data["overall_status"] == "BLOCKED"
        blocking_codes = [c["check_code"] for c in r_data["checks"] if c["blocking"] and c["status"] == "FAIL"]
        assert "GST_PROFILE_MISSING" in blocking_codes

        # Attempt to submit for review while blocked -> must fail
        submit_fail = await client.post(
            f"/api/v1/compliance/obligations/{ob1_id}/submit-review?company_id={company_id}",
            json={"review_notes": "Attempting early submission"},
            headers=headers,
        )
        assert submit_fail.status_code in (409, 422)

        # 6. Fix prerequisite: Configure GST Profile
        gst_prof_res = await client.post(
            f"/api/v1/gst/profile?company_id={company_id}",
            json={
                "gstin": "27AAPFU0939F1ZV",
                "legal_name": "ABC Traders Pvt Ltd",
                "trade_name": "ABC Traders",
                "registration_type": "REGULAR",
            },
            headers=headers,
        )
        assert gst_prof_res.status_code == 201

        # Re-run readiness check -> should no longer be BLOCKED
        readiness2 = await client.post(
            f"/api/v1/compliance/obligations/{ob1_id}/readiness?company_id={company_id}",
            headers=headers,
        )
        assert readiness2.status_code == 200
        r_data2 = readiness2.json()["data"]
        assert r_data2["overall_status"] != "BLOCKED"

        # Also configure TDS Profile to resolve prerequisites for TDS obligation (ob2)
        tds_prof_res = await client.post(
            f"/api/v1/tds/profile?company_id={company_id}",
            json={
                "tan": "MUMB12345A",
                "pan": "AAACA1234A",
                "legal_name": "ABC Traders Pvt Ltd",
                "trade_name": "ABC Traders",
                "deductor_type": "COMPANY",
            },
            headers=headers,
        )
        assert tds_prof_res.status_code == 201

        readiness_ob2 = await client.post(
            f"/api/v1/compliance/obligations/{ob2_id}/readiness?company_id={company_id}",
            headers=headers,
        )
        assert readiness_ob2.status_code == 200
        assert readiness_ob2.json()["data"]["overall_status"] != "BLOCKED"

        # 7. Assign obligation to user
        user_info = await client.get("/api/v1/auth/me", headers=headers)
        user_id = user_info.json()["data"]["id"]

        assign_res = await client.post(
            f"/api/v1/compliance/obligations/{ob1_id}/assign?company_id={company_id}",
            json={"assigned_to": user_id, "reviewer_id": user_id},
            headers=headers,
        )
        assert assign_res.status_code == 200

        # 8. Upload and attach evidence
        upload_res = await client.post(
            f"/api/v1/documents?company_id={company_id}",
            files={"file": ("gstr3b_challan.pdf", MIN_PDF, "application/pdf")},
            data={"document_type": "GST_REPORT", "description": "April GSTR-3B Tax Paid Challan"},
            headers=headers,
        )
        assert upload_res.status_code == 201
        doc_id = upload_res.json()["data"]["id"]

        evidence_res = await client.post(
            f"/api/v1/compliance/obligations/{ob1_id}/evidence?company_id={company_id}",
            json={"document_id": doc_id, "description": "Paid tax receipt"},
            headers=headers,
        )
        assert evidence_res.status_code == 201

        # 9. Submit for review -> succeeds now that prerequisites are resolved
        submit_res = await client.post(
            f"/api/v1/compliance/obligations/{ob1_id}/submit-review?company_id={company_id}",
            json={"review_notes": "All invoices verified and challan attached."},
            headers=headers,
        )
        assert submit_res.status_code == 200
        assert submit_res.json()["data"]["status"] == "READY_FOR_REVIEW"

        # 10. Review & Approve
        approve_res = await client.post(
            f"/api/v1/compliance/obligations/{ob1_id}/approve?company_id={company_id}",
            json={"notes": "Reviewed and approved by CA"},
            headers=headers,
        )
        assert approve_res.status_code == 200
        assert approve_res.json()["data"]["status"] == "APPROVED"

        # 11. Complete
        complete_res = await client.post(
            f"/api/v1/compliance/obligations/{ob1_id}/complete?company_id={company_id}",
            json={"review_notes": "Filed successfully on GST portal."},
            headers=headers,
        )
        assert complete_res.status_code == 200
        assert complete_res.json()["data"]["status"] == "COMPLETED"

        # 12. Obligation 2: Complete & Reopen
        c2 = await client.post(
            f"/api/v1/compliance/obligations/{ob2_id}/complete?company_id={company_id}",
            json={"review_notes": "TDS filed"},
            headers=headers,
        )
        assert c2.status_code == 200
        reopen_res = await client.post(
            f"/api/v1/compliance/obligations/{ob2_id}/reopen?company_id={company_id}",
            json={"reason": "Need to revise TDS deductee PAN"},
            headers=headers,
        )
        assert reopen_res.status_code == 200
        assert reopen_res.json()["data"]["status"] == "REOPENED"

        # 13. Sweep overdue obligations
        sweep_res = await client.post(
            f"/api/v1/compliance/obligations/sweep-overdue?company_id={company_id}",
            headers=headers,
        )
        assert sweep_res.status_code == 200
        assert "marked_overdue" in sweep_res.json()["data"]

        # 14. Verify notifications
        notif_res = await client.get(f"/api/v1/notifications?company_id={company_id}", headers=headers)
        assert notif_res.status_code == 200

        # 15. Verify Audit Trail contains compliance actions
        audit_res = await client.get(f"/api/v1/audit-logs?company_id={company_id}", headers=headers)
        assert audit_res.status_code == 200
        audit_items = audit_res.json()["data"]["items"]
        audit_actions = [a["action"] for a in audit_items]
        assert any("COMPLIANCE" in a for a in audit_actions)

        # 16. Verify Control Center Summary & Health
        cc_res = await client.get(f"/api/v1/compliance/control-center?company_id={company_id}", headers=headers)
        assert cc_res.status_code == 200
        cc_data = cc_res.json()["data"]
        assert cc_data["total_obligations"] >= 2
        assert cc_data["health"]["score"] > 0

        # 17. Verify Action Center integration
        ac_res = await client.get(f"/api/v1/action-center?company_id={company_id}", headers=headers)
        assert ac_res.status_code == 200

        # 18. Verify Compliance Reports Export
        rep_csv = await client.get(
            f"/api/v1/compliance/reports/obligations/export?company_id={company_id}&format=csv",
            headers=headers,
        )
        assert rep_csv.status_code == 200
        assert b"ABC-GST-3B-APR" in rep_csv.content

        rep_xlsx = await client.get(
            f"/api/v1/compliance/reports/obligations/export?company_id={company_id}&format=xlsx",
            headers=headers,
        )
        assert rep_xlsx.status_code == 200

        # 19. Verify Tenant Isolation (Company B user cannot view ABC Traders obligations)
        await client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Suresh",
                "last_name": "Patel",
                "email": "suresh@companyb.com",
                "password": "Password123!",
            },
        )
        auth_b = await login(client, "suresh@companyb.com", "Password123!")
        headers_b = auth_headers(auth_b["access_token"])

        onboard_b = await client.post(
            "/api/v1/companies/onboard",
            json={
                "legal_name": "Company B Enterprises",
                "trade_name": "Company B",
                "business_type": "PRIVATE_LIMITED",
                "pan": "BBBCB1234B",
                "state": "Gujarat",
                "city": "Ahmedabad",
            },
            headers=headers_b,
        )
        assert onboard_b.status_code == 201

        # Attempt to access ABC Traders obligations with Company B user
        cross_res = await client.get(
            f"/api/v1/compliance/obligations/{ob1_id}?company_id={company_id}",
            headers=headers_b,
        )
        assert cross_res.status_code in [403, 404]

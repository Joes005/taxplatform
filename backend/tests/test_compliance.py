from datetime import date, timedelta

from app.core.permissions import RoleCode
from app.services.compliance_deadline_service import compute_due_date
from tests.conftest import add_membership, auth_headers, login
from tests.sample_files import MIN_PDF


class TestComplianceDeadlineService:
    """Pure due-date arithmetic — no DB (PHASE9 §46)."""

    def test_days_after_period_end(self):
        due = compute_due_date(
            {"type": "DAYS_AFTER_PERIOD_END", "days": 20},
            period_start=date(2025, 4, 1),
            period_end=date(2025, 4, 30),
        )
        assert due == date(2025, 5, 20)

    def test_day_of_month_after_period_end(self):
        due = compute_due_date(
            {"type": "DAY_OF_MONTH_AFTER_PERIOD_END", "month_offset": 1, "day": 20},
            period_start=date(2025, 4, 1),
            period_end=date(2025, 4, 30),
        )
        assert due == date(2025, 5, 20)

    def test_day_of_month_clamped_to_short_month(self):
        due = compute_due_date(
            {"type": "DAY_OF_MONTH_AFTER_PERIOD_END", "month_offset": 1, "day": 31},
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
        )
        assert due == date(2025, 2, 28)

    def test_days_after_start(self):
        due = compute_due_date(
            {"type": "DAYS_AFTER_START", "days": 30}, period_start=date(2025, 4, 1), period_end=date(2025, 4, 1)
        )
        assert due == date(2025, 5, 1)

    def test_unsupported_type_rejected(self):
        import pytest

        from app.core.exceptions import ValidationAppError

        with pytest.raises(ValidationAppError):
            compute_due_date({"type": "NOT_A_REAL_TYPE"}, period_start=date.today(), period_end=date.today())


async def _create_rule(client, headers, company_id, *, code="GSTR3B_MONTHLY", company_specific=False):
    response = await client.post(
        f"/api/v1/compliance/rules?company_id={company_id}",
        json={
            "code": code,
            "name": "Monthly GSTR-3B",
            "category": "GST",
            "module": "GST",
            "frequency": "MONTHLY",
            "due_date_rule": {"type": "DAY_OF_MONTH_AFTER_PERIOD_END", "month_offset": 1, "day": 20},
            "effective_from": "2025-04-01",
            "company_specific": company_specific,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


class TestComplianceRule:
    async def test_company_admin_can_create_company_specific_rule(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        rule = await _create_rule(client, headers, company.id, company_specific=True)
        assert rule["version"] == 1
        assert rule["company_id"] == str(company.id)

    async def test_company_admin_cannot_create_platform_wide_rule(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/compliance/rules?company_id={company.id}",
            json={
                "code": "TDS_QUARTERLY",
                "name": "Quarterly TDS Return",
                "category": "TDS",
                "module": "TDS",
                "frequency": "QUARTERLY",
                "due_date_rule": {"type": "DAYS_AFTER_PERIOD_END", "days": 31},
                "effective_from": "2025-04-01",
                "company_specific": False,
            },
            headers=headers,
        )
        assert response.status_code == 403

    async def test_updating_rule_does_not_change_version(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        rule = await _create_rule(client, headers, company.id, company_specific=True)

        updated = await client.patch(
            f"/api/v1/compliance/rules/{rule['id']}?company_id={company.id}",
            json={"name": "Monthly GSTR-3B (renamed)"},
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["version"] == 1
        assert updated.json()["data"]["name"] == "Monthly GSTR-3B (renamed)"

    async def test_deactivate_rule(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        rule = await _create_rule(client, headers, company.id, company_specific=True)

        response = await client.post(
            f"/api/v1/compliance/rules/{rule['id']}/deactivate?company_id={company.id}", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False

    async def test_generate_obligation_from_rule_api(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        rule = await _create_rule(client, headers, company.id, code="GSTR1_API_TEST", company_specific=True)

        resp = await client.post(
            f"/api/v1/compliance/rules/{rule['id']}/generate-obligations?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "tax_period": "2025-05",
                "period_start": "2025-05-01",
                "period_end": "2025-05-31",
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["due_date"] == "2025-06-20"
        assert data["code"] == "GSTR1_API_TEST"
        assert data["rule_version"] == 1
        assert data["financial_year_id"] == str(financial_year_a.id)
        obligation_id = data["id"]

        # Test idempotency via the HTTP API
        resp_idem = await client.post(
            f"/api/v1/compliance/rules/{rule['id']}/generate-obligations?company_id={company.id}",
            json={
                "financial_year_id": str(financial_year_a.id),
                "tax_period": "2025-05",
                "period_start": "2025-05-01",
                "period_end": "2025-05-31",
            },
            headers=headers,
        )
        assert resp_idem.status_code == 201
        assert resp_idem.json()["data"]["id"] == obligation_id


class TestComplianceObligation:
    async def test_manual_obligation_duplicate_natural_key_rejected(
        self, client, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await _create_rule(client, headers, company.id, company_specific=True)

        first = await client.post(
            f"/api/v1/compliance/obligations?company_id={company.id}",
            json={
                "code": "GSTR3B_MONTHLY",
                "name": "Monthly GSTR-3B",
                "category": "GST",
                "module": "GST",
                "frequency": "MONTHLY",
                "financial_year_id": str(financial_year_a.id),
                "tax_period": "2025-04",
                "start_date": "2025-04-01",
                "due_date": "2025-05-20",
            },
            headers=headers,
        )
        assert first.status_code == 201, first.text
        assert first.json()["data"]["due_date"] == "2025-05-20"

        duplicate = await client.post(
            f"/api/v1/compliance/obligations?company_id={company.id}",
            json={
                "code": "GSTR3B_MONTHLY",
                "name": "Monthly GSTR-3B",
                "category": "GST",
                "module": "GST",
                "frequency": "MONTHLY",
                "financial_year_id": str(financial_year_a.id),
                "tax_period": "2025-04",
                "start_date": "2025-04-01",
                "due_date": "2025-05-20",
            },
            headers=headers,
        )
        assert duplicate.status_code == 422
        assert duplicate.json()["error"]["code"] == "COMPLIANCE_OBLIGATION_ALREADY_EXISTS"

    async def test_generate_from_rule_is_idempotent(self, client, db_session, company_a_with_admin, financial_year_a):
        """`generate_from_rule` itself has no dedicated HTTP endpoint (it's
        invoked internally by whichever module owns a period, e.g. a GST
        return-period service) — exercised directly against the service."""
        from app.services.auth_service import RequestMeta
        from app.services.compliance_obligation_service import ComplianceObligationService

        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        await _create_rule(client, headers, company.id, code="GSTR1_MONTHLY", company_specific=True)

        service = ComplianceObligationService(db_session)
        meta = RequestMeta(ip_address=None, user_agent=None)

        first = await service.generate_from_rule(
            company.id,
            rule_code="GSTR1_MONTHLY",
            financial_year_id=financial_year_a.id,
            tax_period="2025-05",
            period_start=date(2025, 5, 1),
            period_end=date(2025, 5, 31),
            current_user=admin,
            meta=meta,
        )
        assert first.due_date == date(2025, 6, 20)
        assert first.rule_version == 1

        second = await service.generate_from_rule(
            company.id,
            rule_code="GSTR1_MONTHLY",
            financial_year_id=financial_year_a.id,
            tax_period="2025-05",
            period_start=date(2025, 5, 1),
            period_end=date(2025, 5, 31),
            current_user=admin,
            meta=meta,
        )
        assert second.id == first.id

    async def test_generate_task_from_obligation(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        obligation = await client.post(
            f"/api/v1/compliance/obligations?company_id={company.id}",
            json={
                "code": "TDS_Q1",
                "name": "Quarterly TDS Return Review",
                "category": "TDS",
                "module": "TDS",
                "frequency": "QUARTERLY",
                "financial_year_id": str(financial_year_a.id),
                "tax_period": "Q1",
                "start_date": "2025-04-01",
                "due_date": "2025-07-31",
            },
            headers=headers,
        )
        obligation_id = obligation.json()["data"]["id"]

        task = await client.post(
            f"/api/v1/compliance/obligations/{obligation_id}/generate-task?company_id={company.id}",
            json={},
            headers=headers,
        )
        assert task.status_code == 201, task.text
        assert task.json()["data"]["title"] == "Quarterly TDS Return Review"
        assert task.json()["data"]["due_date"] == "2025-07-31"
        assert task.json()["data"]["status"] == "PENDING"


class TestComplianceTaskLifecycle:
    async def test_full_lifecycle_with_review_and_rbac(
        self, client, db_session, seeded_rbac, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        admin_data = await login(client, admin.email, "TestPass1!")
        admin_headers = auth_headers(admin_data["access_token"])

        accountant = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="accountant-compliance@example.com",
            role_code=RoleCode.ACCOUNTANT.value,
        )
        accountant_data = await login(client, accountant.email, "TestPass1!")
        accountant_headers = auth_headers(accountant_data["access_token"])

        auditor = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="auditor-compliance@example.com",
            role_code=RoleCode.AUDITOR.value,
        )
        auditor_data = await login(client, auditor.email, "TestPass1!")
        auditor_headers = auth_headers(auditor_data["access_token"])

        create = await client.post(
            f"/api/v1/compliance/tasks?company_id={company.id}",
            json={
                "title": "Prepare GSTR-1 for April",
                "category": "GST",
                "module": "GST",
                "priority": "HIGH",
                "assigned_to": str(accountant.id),
                "reviewer_id": str(auditor.id),
                "due_date": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=admin_headers,
        )
        assert create.status_code == 201, create.text
        task_id = create.json()["data"]["id"]
        assert create.json()["data"]["status"] == "PENDING"

        # Accountant starts and submits for review.
        start = await client.post(
            f"/api/v1/compliance/tasks/{task_id}/start?company_id={company.id}", headers=accountant_headers
        )
        assert start.json()["data"]["status"] == "IN_PROGRESS"

        submit = await client.post(
            f"/api/v1/compliance/tasks/{task_id}/submit-review?company_id={company.id}", headers=accountant_headers
        )
        assert submit.json()["data"]["status"] == "PENDING_REVIEW"

        # Accountant cannot verify — that's Auditor-only.
        forbidden = await client.post(
            f"/api/v1/compliance/tasks/{task_id}/verify?company_id={company.id}", headers=accountant_headers
        )
        assert forbidden.status_code == 403

        # Direct PENDING -> VERIFIED style jump is impossible by construction;
        # returning for changes sends it back to IN_PROGRESS.
        returned = await client.post(
            f"/api/v1/compliance/tasks/{task_id}/return-for-changes?company_id={company.id}",
            json={"reason": "Please attach the working file"},
            headers=auditor_headers,
        )
        assert returned.json()["data"]["status"] == "IN_PROGRESS"

        await client.post(
            f"/api/v1/compliance/tasks/{task_id}/submit-review?company_id={company.id}", headers=accountant_headers
        )
        verify = await client.post(
            f"/api/v1/compliance/tasks/{task_id}/verify?company_id={company.id}", headers=auditor_headers
        )
        assert verify.status_code == 200, verify.text
        assert verify.json()["data"]["status"] == "VERIFIED"

        lock = await client.post(
            f"/api/v1/compliance/tasks/{task_id}/lock?company_id={company.id}", headers=auditor_headers
        )
        assert lock.json()["data"]["status"] == "LOCKED"

        blocked_update = await client.patch(
            f"/api/v1/compliance/tasks/{task_id}?company_id={company.id}",
            json={"title": "Renamed"},
            headers=admin_headers,
        )
        assert blocked_update.status_code == 409
        assert blocked_update.json()["error"]["code"] == "COMPLIANCE_TASK_LOCKED"

    async def test_submit_review_requires_reviewer(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        create = await client.post(
            f"/api/v1/compliance/tasks?company_id={company.id}",
            json={
                "title": "Bank reconciliation review",
                "category": "BANK",
                "module": "BANK_RECONCILIATION",
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
            },
            headers=headers,
        )
        task_id = create.json()["data"]["id"]
        await client.post(f"/api/v1/compliance/tasks/{task_id}/start?company_id={company.id}", headers=headers)

        response = await client.post(
            f"/api/v1/compliance/tasks/{task_id}/submit-review?company_id={company.id}", headers=headers
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "COMPLIANCE_TASK_REVIEWER_REQUIRED"

    async def test_direct_complete_without_review(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        create = await client.post(
            f"/api/v1/compliance/tasks?company_id={company.id}",
            json={
                "title": "Simple accounting cleanup",
                "category": "ACCOUNTING",
                "module": "ACCOUNTING",
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
            },
            headers=headers,
        )
        task_id = create.json()["data"]["id"]
        await client.post(f"/api/v1/compliance/tasks/{task_id}/start?company_id={company.id}", headers=headers)
        complete = await client.post(
            f"/api/v1/compliance/tasks/{task_id}/complete?company_id={company.id}",
            json={"completion_notes": "Done"},
            headers=headers,
        )
        assert complete.status_code == 200, complete.text
        assert complete.json()["data"]["status"] == "COMPLETED"

    async def test_assign_rejects_non_member(self, client, company_a_with_admin, company_b_with_admin):
        company, admin = company_a_with_admin
        _company_b, outsider = company_b_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        create = await client.post(
            f"/api/v1/compliance/tasks?company_id={company.id}",
            json={
                "title": "Cross-tenant assignment attempt",
                "category": "GENERAL",
                "module": "GENERAL",
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
            },
            headers=headers,
        )
        task_id = create.json()["data"]["id"]

        response = await client.post(
            f"/api/v1/compliance/tasks/{task_id}/assign?company_id={company.id}",
            json={"assigned_to": str(outsider.id)},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "COMPLIANCE_USER_NOT_A_COMPANY_MEMBER"


class TestOverdueDetection:
    async def test_sweep_marks_past_due_open_task_overdue(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        create = await client.post(
            f"/api/v1/compliance/tasks?company_id={company.id}",
            json={
                "title": "Overdue GST filing prep",
                "category": "GST",
                "module": "GST",
                "due_date": (date.today() - timedelta(days=3)).isoformat(),
            },
            headers=headers,
        )
        task_id = create.json()["data"]["id"]
        assert create.json()["data"]["is_overdue"] is True
        assert create.json()["data"]["status"] == "PENDING"

        dashboard = await client.get(f"/api/v1/compliance/dashboard?company_id={company.id}", headers=headers)
        assert dashboard.status_code == 200
        assert dashboard.json()["data"]["overdue"] >= 1

        refreshed = await client.get(f"/api/v1/compliance/tasks/{task_id}?company_id={company.id}", headers=headers)
        assert refreshed.json()["data"]["status"] == "OVERDUE"

    async def test_completed_task_never_marked_overdue(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        create = await client.post(
            f"/api/v1/compliance/tasks?company_id={company.id}",
            json={
                "title": "Already handled",
                "category": "GENERAL",
                "module": "GENERAL",
                "due_date": (date.today() - timedelta(days=3)).isoformat(),
            },
            headers=headers,
        )
        task_id = create.json()["data"]["id"]
        await client.post(f"/api/v1/compliance/tasks/{task_id}/start?company_id={company.id}", headers=headers)
        await client.post(
            f"/api/v1/compliance/tasks/{task_id}/complete?company_id={company.id}", json={}, headers=headers
        )

        await client.get(f"/api/v1/compliance/dashboard?company_id={company.id}", headers=headers)

        refreshed = await client.get(f"/api/v1/compliance/tasks/{task_id}?company_id={company.id}", headers=headers)
        assert refreshed.json()["data"]["status"] == "COMPLETED"
        assert refreshed.json()["data"]["is_overdue"] is False


class TestComments:
    async def test_add_comment_and_evidence(self, client, document_storage, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        create = await client.post(
            f"/api/v1/compliance/tasks?company_id={company.id}",
            json={
                "title": "Audit checklist follow-up",
                "category": "AUDIT",
                "module": "AUDIT",
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
            },
            headers=headers,
        )
        task_id = create.json()["data"]["id"]

        comment = await client.post(
            f"/api/v1/compliance/tasks/{task_id}/comments?company_id={company.id}",
            json={"comment": "Started gathering supporting documents."},
            headers=headers,
        )
        assert comment.status_code == 201

        upload = await client.post(
            f"/api/v1/documents?company_id={company.id}",
            headers=headers,
            data={"document_type": "OTHER"},
            files={"file": ("evidence.pdf", MIN_PDF, "application/pdf")},
        )
        assert upload.status_code == 201, upload.text
        document_id = upload.json()["data"]["id"]

        evidence = await client.post(
            f"/api/v1/compliance/tasks/{task_id}/evidence?company_id={company.id}",
            json={"document_id": document_id, "description": "Working file"},
            headers=headers,
        )
        assert evidence.status_code == 201, evidence.text

        listed = await client.get(
            f"/api/v1/compliance/tasks/{task_id}/evidence?company_id={company.id}", headers=headers
        )
        assert len(listed.json()["data"]) == 1


class TestNotifications:
    async def test_assignment_creates_notification_and_read_flow(
        self, client, db_session, seeded_rbac, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        admin_data = await login(client, admin.email, "TestPass1!")
        admin_headers = auth_headers(admin_data["access_token"])

        accountant = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="notif-accountant@example.com",
            role_code=RoleCode.ACCOUNTANT.value,
        )
        accountant_data = await login(client, accountant.email, "TestPass1!")
        accountant_headers = auth_headers(accountant_data["access_token"])

        create = await client.post(
            f"/api/v1/compliance/tasks?company_id={company.id}",
            json={
                "title": "TDS challan reconciliation",
                "category": "TDS",
                "module": "TDS",
                "assigned_to": str(accountant.id),
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
            },
            headers=admin_headers,
        )
        assert create.status_code == 201

        unread = await client.get(
            f"/api/v1/notifications/unread-count?company_id={company.id}", headers=accountant_headers
        )
        assert unread.json()["data"]["unread_count"] == 1

        listed = await client.get(f"/api/v1/notifications?company_id={company.id}", headers=accountant_headers)
        notification_id = listed.json()["data"]["items"][0]["id"]
        assert listed.json()["data"]["items"][0]["type"] == "TASK_ASSIGNED"

        mark = await client.patch(
            f"/api/v1/notifications/{notification_id}/read?company_id={company.id}", headers=accountant_headers
        )
        assert mark.status_code == 200
        assert mark.json()["data"]["is_read"] is True

        unread_after = await client.get(
            f"/api/v1/notifications/unread-count?company_id={company.id}", headers=accountant_headers
        )
        assert unread_after.json()["data"]["unread_count"] == 0

    async def test_mark_all_read(self, client, db_session, seeded_rbac, company_a_with_admin):
        company, admin = company_a_with_admin
        admin_data = await login(client, admin.email, "TestPass1!")
        admin_headers = auth_headers(admin_data["access_token"])
        accountant = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="notif-accountant-2@example.com",
            role_code=RoleCode.ACCOUNTANT.value,
        )
        accountant_data = await login(client, accountant.email, "TestPass1!")
        accountant_headers = auth_headers(accountant_data["access_token"])

        for i in range(3):
            await client.post(
                f"/api/v1/compliance/tasks?company_id={company.id}",
                json={
                    "title": f"Task {i}",
                    "category": "GENERAL",
                    "module": "GENERAL",
                    "assigned_to": str(accountant.id),
                    "due_date": (date.today() + timedelta(days=5)).isoformat(),
                },
                headers=admin_headers,
            )

        await client.post(f"/api/v1/notifications/read-all?company_id={company.id}", headers=accountant_headers)
        unread = await client.get(
            f"/api/v1/notifications/unread-count?company_id={company.id}", headers=accountant_headers
        )
        assert unread.json()["data"]["unread_count"] == 0


class TestTenantIsolation:
    async def test_company_b_cannot_access_company_a_task(
        self, client, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        _company_b, admin_b = company_b_with_admin
        data_a = await login(client, admin_a.email, "TestPass1!")
        headers_a = auth_headers(data_a["access_token"])
        data_b = await login(client, admin_b.email, "TestPass1!")
        headers_b = auth_headers(data_b["access_token"])

        create = await client.post(
            f"/api/v1/compliance/tasks?company_id={company_a.id}",
            json={
                "title": "Company A only",
                "category": "GENERAL",
                "module": "GENERAL",
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
            },
            headers=headers_a,
        )
        task_id = create.json()["data"]["id"]

        no_membership = await client.get(
            f"/api/v1/compliance/tasks/{task_id}?company_id={company_a.id}", headers=headers_b
        )
        assert no_membership.status_code == 403

        own_company_wrong_resource = await client.get(
            f"/api/v1/compliance/tasks/{task_id}?company_id={_company_b.id}", headers=headers_b
        )
        assert own_company_wrong_resource.status_code == 404
        assert own_company_wrong_resource.json()["error"]["code"] == "COMPLIANCE_TASK_NOT_FOUND"


class TestComplianceReport:
    async def test_export_csv(self, client, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await client.post(
            f"/api/v1/compliance/tasks?company_id={company.id}",
            json={
                "title": "Export me",
                "category": "GENERAL",
                "module": "GENERAL",
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
            },
            headers=headers,
        )

        export = await client.get(
            f"/api/v1/compliance/reports/tasks/export?company_id={company.id}&format=csv", headers=headers
        )
        assert export.status_code == 200
        assert export.headers["content-type"].startswith("text/csv")


class TestComplianceOverdueSweep:
    async def test_overdue_sweep_detection_and_idempotency(self, client, db_session, company_a_with_admin):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        # Create past-due task
        past_date = (date.today() - timedelta(days=2)).isoformat()
        t1 = await client.post(
            f"/api/v1/compliance/tasks?company_id={company.id}",
            json={
                "title": "Overdue Task 1",
                "category": "GENERAL",
                "module": "GENERAL",
                "due_date": past_date,
                "assigned_to": str(admin.id),
            },
            headers=headers,
        )
        assert t1.status_code == 201
        t1_id = t1.json()["data"]["id"]

        # Create future task
        future_date = (date.today() + timedelta(days=5)).isoformat()
        t2 = await client.post(
            f"/api/v1/compliance/tasks?company_id={company.id}",
            json={
                "title": "Future Task 2",
                "category": "GENERAL",
                "module": "GENERAL",
                "due_date": future_date,
                "assigned_to": str(admin.id),
            },
            headers=headers,
        )
        assert t2.status_code == 201
        t2_id = t2.json()["data"]["id"]

        # Run sweep
        sweep1 = await client.post(
            f"/api/v1/compliance/tasks/sweep-overdue?company_id={company.id}",
            headers=headers,
        )
        assert sweep1.status_code == 200, sweep1.text
        assert sweep1.json()["data"]["swept_count"] == 1

        # Verify task 1 is now OVERDUE, task 2 is still PENDING
        get1 = await client.get(f"/api/v1/compliance/tasks/{t1_id}?company_id={company.id}", headers=headers)
        assert get1.json()["data"]["status"] == "OVERDUE"
        assert get1.json()["data"]["is_overdue"] is True

        get2 = await client.get(f"/api/v1/compliance/tasks/{t2_id}?company_id={company.id}", headers=headers)
        assert get2.json()["data"]["status"] == "PENDING"
        assert get2.json()["data"]["is_overdue"] is False

        # Run repeated sweep (Idempotency)
        sweep2 = await client.post(
            f"/api/v1/compliance/tasks/sweep-overdue?company_id={company.id}",
            headers=headers,
        )
        assert sweep2.status_code == 200
        assert sweep2.json()["data"]["swept_count"] == 0

        # Verify notifications deduplication: admin only received 1 notification
        notifs = await client.get(f"/api/v1/notifications?company_id={company.id}", headers=headers)
        overdue_notifs = [n for n in notifs.json()["data"]["items"] if n["type"] == "TASK_OVERDUE"]
        assert len(overdue_notifs) == 1
        assert overdue_notifs[0]["entity_id"] == t1_id

    async def test_overdue_sweep_company_isolation(
        self, client, db_session, company_a_with_admin, company_b_with_admin
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin
        data_a = await login(client, admin_a.email, "TestPass1!")
        headers_a = auth_headers(data_a["access_token"])
        data_b = await login(client, admin_b.email, "TestPass1!")
        headers_b = auth_headers(data_b["access_token"])

        past_date = (date.today() - timedelta(days=3)).isoformat()

        # Task in company A
        t_a = await client.post(
            f"/api/v1/compliance/tasks?company_id={company_a.id}",
            json={
                "title": "Comp A Task",
                "category": "GST",
                "module": "GST",
                "due_date": past_date,
            },
            headers=headers_a,
        )
        t_a_id = t_a.json()["data"]["id"]

        # Task in company B
        t_b = await client.post(
            f"/api/v1/compliance/tasks?company_id={company_b.id}",
            json={
                "title": "Comp B Task",
                "category": "TDS",
                "module": "TDS",
                "due_date": past_date,
            },
            headers=headers_b,
        )
        t_b_id = t_b.json()["data"]["id"]

        # Sweep only company A
        sweep_a = await client.post(
            f"/api/v1/compliance/tasks/sweep-overdue?company_id={company_a.id}",
            headers=headers_a,
        )
        assert sweep_a.status_code == 200
        assert sweep_a.json()["data"]["swept_count"] == 1

        # Company A's task is OVERDUE
        get_a = await client.get(f"/api/v1/compliance/tasks/{t_a_id}?company_id={company_a.id}", headers=headers_a)
        assert get_a.json()["data"]["status"] == "OVERDUE"

        # Company B's task is still PENDING because Company B was not swept
        get_b = await client.get(f"/api/v1/compliance/tasks/{t_b_id}?company_id={company_b.id}", headers=headers_b)
        assert get_b.json()["data"]["status"] == "PENDING"


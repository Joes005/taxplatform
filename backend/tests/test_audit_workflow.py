from app.core.permissions import RoleCode
from tests.conftest import add_membership, auth_headers, login
from tests.sample_files import MIN_PDF


async def _create_engagement(client, headers, company_id, financial_year_id, *, title="FY25-26 Compliance Review"):
    response = await client.post(
        f"/api/v1/audits/engagements?company_id={company_id}",
        json={
            "title": title,
            "financial_year_id": str(financial_year_id),
            "period_start": "2025-04-01",
            "period_end": "2026-03-31",
            "engagement_type": "TAX_COMPLIANCE_REVIEW",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _auditor_headers(client, db_session, seeded_rbac, company_id, *, email="auditor@example.com"):
    user = await add_membership(
        db_session, seeded_rbac, company_id=company_id, email=email, role_code=RoleCode.AUDITOR.value
    )
    data = await login(client, email, "TestPass1!")
    return user, auth_headers(data["access_token"])


class TestAuditEngagementLifecycle:
    async def test_create_engagement_defaults_to_draft(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        engagement = await _create_engagement(client, headers, company.id, financial_year_a.id)
        assert engagement["status"] == "DRAFT"
        assert engagement["engagement_code"] == "ENG-0001"
        assert engagement["is_locked"] is False

    async def test_full_lifecycle_open_assign_review_approve_signoff_close_lock(
        self, client, db_session, seeded_rbac, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        admin_data = await login(client, admin.email, "TestPass1!")
        admin_headers = auth_headers(admin_data["access_token"])

        auditor, auditor_headers = await _auditor_headers(client, db_session, seeded_rbac, company.id)

        engagement = await _create_engagement(client, admin_headers, company.id, financial_year_a.id)
        engagement_id = engagement["id"]

        opened = await client.post(
            f"/api/v1/audits/engagements/{engagement_id}/open?company_id={company.id}", headers=admin_headers
        )
        assert opened.json()["data"]["status"] == "OPEN"

        assign = await client.post(
            f"/api/v1/audits/engagements/{engagement_id}/assignments?company_id={company.id}",
            json={"user_id": str(auditor.id), "role": "LEAD_AUDITOR"},
            headers=admin_headers,
        )
        assert assign.status_code == 201, assign.text

        after_assign = await client.get(
            f"/api/v1/audits/engagements/{engagement_id}?company_id={company.id}", headers=admin_headers
        )
        assert after_assign.json()["data"]["status"] == "ASSIGNED"

        start_review = await client.post(
            f"/api/v1/audits/engagements/{engagement_id}/start-review?company_id={company.id}",
            headers=auditor_headers,
        )
        assert start_review.json()["data"]["status"] == "IN_REVIEW"

        submit = await client.post(
            f"/api/v1/audits/engagements/{engagement_id}/submit-for-review?company_id={company.id}",
            headers=admin_headers,
        )
        assert submit.json()["data"]["status"] == "PENDING_AUDITOR_REVIEW"

        finding = await client.post(
            f"/api/v1/audits/engagements/{engagement_id}/findings?company_id={company.id}",
            json={"title": "Large unexplained journal entry", "category": "ACCOUNTING", "severity": "HIGH"},
            headers=auditor_headers,
        )
        assert finding.status_code == 201, finding.text
        finding_id = finding.json()["data"]["finding"]["id"]

        blocked_approve = await client.post(
            f"/api/v1/audits/engagements/{engagement_id}/approve?company_id={company.id}",
            json={},
            headers=auditor_headers,
        )
        assert blocked_approve.status_code == 409
        assert blocked_approve.json()["error"]["code"] == "AUDIT_ENGAGEMENT_OPEN_FINDINGS_BLOCK_APPROVAL"

        resolve = await client.post(
            f"/api/v1/audits/findings/{finding_id}/resolve?company_id={company.id}",
            json={"resolution_summary": "Verified against supporting invoice; adjustment was legitimate."},
            headers=auditor_headers,
        )
        assert resolve.json()["data"]["status"] == "RESOLVED"

        approve = await client.post(
            f"/api/v1/audits/engagements/{engagement_id}/approve?company_id={company.id}",
            json={},
            headers=auditor_headers,
        )
        assert approve.status_code == 200, approve.text
        assert approve.json()["data"]["status"] == "APPROVED"

        blocked_signoff = await client.post(
            f"/api/v1/audits/engagements/{engagement_id}/mark-signed-off?company_id={company.id}",
            headers=auditor_headers,
        )
        assert blocked_signoff.status_code == 409
        assert blocked_signoff.json()["error"]["code"] == "AUDIT_ENGAGEMENT_MISSING_LEAD_SIGNOFF"

        signoff = await client.post(
            f"/api/v1/audits/engagements/{engagement_id}/sign-offs?company_id={company.id}",
            json={"sign_off_type": "LEAD_AUDITOR"},
            headers=auditor_headers,
        )
        assert signoff.status_code == 201, signoff.text
        assert "internal" in signoff.json()["data"]["statement"].lower()

        mark_signed_off = await client.post(
            f"/api/v1/audits/engagements/{engagement_id}/mark-signed-off?company_id={company.id}",
            headers=auditor_headers,
        )
        assert mark_signed_off.json()["data"]["status"] == "SIGNED_OFF"

        close = await client.post(
            f"/api/v1/audits/engagements/{engagement_id}/close?company_id={company.id}", headers=auditor_headers
        )
        assert close.json()["data"]["status"] == "CLOSED"

        lock = await client.post(
            f"/api/v1/audits/engagements/{engagement_id}/lock?company_id={company.id}", headers=auditor_headers
        )
        assert lock.json()["data"]["is_locked"] is True

        blocked_update = await client.patch(
            f"/api/v1/audits/engagements/{engagement_id}?company_id={company.id}",
            json={"title": "New title"},
            headers=admin_headers,
        )
        assert blocked_update.status_code == 409
        assert blocked_update.json()["error"]["code"] == "AUDIT_ENGAGEMENT_LOCKED"


class TestAuditAssignment:
    async def test_assign_requires_active_company_membership(
        self, client, company_a_with_admin, company_b_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        _company_b, outsider = company_b_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        engagement = await _create_engagement(client, headers, company.id, financial_year_a.id)
        response = await client.post(
            f"/api/v1/audits/engagements/{engagement['id']}/assignments?company_id={company.id}",
            json={"user_id": str(outsider.id), "role": "AUDITOR"},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "USER_NOT_A_COMPANY_MEMBER"

    async def test_duplicate_active_assignment_rejected(
        self, client, db_session, seeded_rbac, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        auditor, _headers = await _auditor_headers(client, db_session, seeded_rbac, company.id)

        engagement = await _create_engagement(client, headers, company.id, financial_year_a.id)
        payload = {"user_id": str(auditor.id), "role": "AUDITOR"}

        first = await client.post(
            f"/api/v1/audits/engagements/{engagement['id']}/assignments?company_id={company.id}",
            json=payload,
            headers=headers,
        )
        assert first.status_code == 201

        second = await client.post(
            f"/api/v1/audits/engagements/{engagement['id']}/assignments?company_id={company.id}",
            json=payload,
            headers=headers,
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "AUDIT_ASSIGNMENT_ALREADY_ACTIVE"


class TestAuditChecklist:
    async def test_get_checklist_seeds_standard_template(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        engagement = await _create_engagement(client, headers, company.id, financial_year_a.id)
        checklist = await client.get(
            f"/api/v1/audits/engagements/{engagement['id']}/checklist?company_id={company.id}", headers=headers
        )
        assert checklist.status_code == 200
        items = checklist.json()["data"]["items"]
        assert len(items) >= 10
        assert all(item["status"] == "NOT_STARTED" for item in items)

    async def test_complete_checklist_item(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        engagement = await _create_engagement(client, headers, company.id, financial_year_a.id)
        checklist = await client.get(
            f"/api/v1/audits/engagements/{engagement['id']}/checklist?company_id={company.id}", headers=headers
        )
        item_id = checklist.json()["data"]["items"][0]["id"]

        updated = await client.patch(
            f"/api/v1/audits/engagements/{engagement['id']}/checklist/items/{item_id}?company_id={company.id}",
            json={"status": "COMPLETED"},
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["status"] == "COMPLETED"
        assert updated.json()["data"]["completed_at"] is not None


class TestAuditFinding:
    async def test_create_finding_warns_on_open_duplicate_source(
        self, client, db_session, seeded_rbac, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        _auditor, auditor_headers = await _auditor_headers(client, db_session, seeded_rbac, company.id)

        engagement = await _create_engagement(client, headers, company.id, financial_year_a.id)
        payload = {
            "title": "Unmatched bank transaction",
            "category": "BANK",
            "severity": "MEDIUM",
            "source_type": "BANK_TRANSACTION",
            "source_id": "11111111-1111-1111-1111-111111111111",
        }

        first = await client.post(
            f"/api/v1/audits/engagements/{engagement['id']}/findings?company_id={company.id}",
            json=payload,
            headers=auditor_headers,
        )
        assert first.status_code == 201
        assert first.json()["data"]["duplicate_warning"] is False

        second = await client.post(
            f"/api/v1/audits/engagements/{engagement['id']}/findings?company_id={company.id}",
            json=payload,
            headers=auditor_headers,
        )
        assert second.status_code == 201
        assert second.json()["data"]["duplicate_warning"] is True
        assert second.json()["data"]["duplicate_finding_codes"] == ["F-001"]

    async def test_response_and_review_cycle_resolves_finding(
        self, client, db_session, seeded_rbac, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        accountant = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="accountant@example.com",
            role_code=RoleCode.ACCOUNTANT.value,
        )
        accountant_data = await login(client, accountant.email, "TestPass1!")
        accountant_headers = auth_headers(accountant_data["access_token"])
        _auditor, auditor_headers = await _auditor_headers(client, db_session, seeded_rbac, company.id)

        engagement = await _create_engagement(client, headers, company.id, financial_year_a.id)
        finding = await client.post(
            f"/api/v1/audits/engagements/{engagement['id']}/findings?company_id={company.id}",
            json={
                "title": "Missing supporting document",
                "category": "DOCUMENT",
                "severity": "LOW",
                "assigned_to": str(accountant.id),
            },
            headers=auditor_headers,
        )
        finding_id = finding.json()["data"]["finding"]["id"]
        assert finding.json()["data"]["finding"]["status"] == "ASSIGNED"

        comment = await client.post(
            f"/api/v1/audits/findings/{finding_id}/comments?company_id={company.id}",
            json={"comment": "Please attach the vendor invoice."},
            headers=auditor_headers,
        )
        assert comment.status_code == 201

        response = await client.post(
            f"/api/v1/audits/findings/{finding_id}/responses?company_id={company.id}",
            json={"response_text": "Invoice has been located and will be attached as evidence."},
            headers=accountant_headers,
        )
        assert response.status_code == 201
        response_id = response.json()["data"]["id"]

        after_response = await client.get(
            f"/api/v1/audits/findings/{finding_id}?company_id={company.id}", headers=auditor_headers
        )
        assert after_response.json()["data"]["status"] == "RESPONSE_SUBMITTED"

        review = await client.post(
            f"/api/v1/audits/findings/{finding_id}/responses/{response_id}/review?company_id={company.id}",
            json={"accept": True},
            headers=auditor_headers,
        )
        assert review.json()["data"]["status"] == "ACCEPTED"

        after_review = await client.get(
            f"/api/v1/audits/findings/{finding_id}?company_id={company.id}", headers=auditor_headers
        )
        assert after_review.json()["data"]["status"] == "RESOLVED"

    async def test_evidence_reuses_existing_document(
        self, client, db_session, seeded_rbac, document_storage, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        _auditor, auditor_headers = await _auditor_headers(client, db_session, seeded_rbac, company.id)

        upload = await client.post(
            f"/api/v1/documents?company_id={company.id}",
            headers=headers,
            data={"document_type": "OTHER"},
            files={"file": ("evidence.pdf", MIN_PDF, "application/pdf")},
        )
        assert upload.status_code == 201, upload.text
        document_id = upload.json()["data"]["id"]

        engagement = await _create_engagement(client, headers, company.id, financial_year_a.id)
        finding = await client.post(
            f"/api/v1/audits/engagements/{engagement['id']}/findings?company_id={company.id}",
            json={"title": "Cash payment above threshold", "category": "CONTROL", "severity": "MEDIUM"},
            headers=auditor_headers,
        )
        finding_id = finding.json()["data"]["finding"]["id"]

        evidence = await client.post(
            f"/api/v1/audits/findings/{finding_id}/evidence?company_id={company.id}",
            json={"document_id": document_id, "description": "Cash voucher"},
            headers=auditor_headers,
        )
        assert evidence.status_code == 201, evidence.text
        evidence_id = evidence.json()["data"]["id"]

        listed = await client.get(
            f"/api/v1/audits/findings/{finding_id}/evidence?company_id={company.id}", headers=auditor_headers
        )
        assert len(listed.json()["data"]) == 1

        removed = await client.delete(
            f"/api/v1/audits/findings/{finding_id}/evidence/{evidence_id}?company_id={company.id}",
            headers=auditor_headers,
        )
        assert removed.status_code == 200

        listed_after = await client.get(
            f"/api/v1/audits/findings/{finding_id}/evidence?company_id={company.id}", headers=auditor_headers
        )
        assert len(listed_after.json()["data"]) == 0

    async def test_reject_then_reopen_finding(
        self, client, db_session, seeded_rbac, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        _auditor, auditor_headers = await _auditor_headers(client, db_session, seeded_rbac, company.id)

        engagement = await _create_engagement(client, headers, company.id, financial_year_a.id)
        finding = await client.post(
            f"/api/v1/audits/engagements/{engagement['id']}/findings?company_id={company.id}",
            json={"title": "Possible duplicate payment", "category": "ACCOUNTING", "severity": "MEDIUM"},
            headers=auditor_headers,
        )
        finding_id = finding.json()["data"]["finding"]["id"]

        rejected = await client.post(
            f"/api/v1/audits/findings/{finding_id}/reject?company_id={company.id}",
            json={"reason": "Confirmed as two separate legitimate payments."},
            headers=auditor_headers,
        )
        assert rejected.json()["data"]["status"] == "REJECTED"

        reopened = await client.post(
            f"/api/v1/audits/findings/{finding_id}/reopen?company_id={company.id}",
            json={"reason": "New information surfaced during client follow-up."},
            headers=auditor_headers,
        )
        assert reopened.json()["data"]["status"] == "REOPENED"


class TestAuditRBAC:
    async def test_accountant_cannot_create_engagement(
        self, client, db_session, seeded_rbac, company_a_with_admin, financial_year_a
    ):
        company, _admin = company_a_with_admin
        accountant = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="rbac-accountant@example.com",
            role_code=RoleCode.ACCOUNTANT.value,
        )
        data = await login(client, accountant.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        response = await client.post(
            f"/api/v1/audits/engagements?company_id={company.id}",
            json={
                "title": "Unauthorized attempt",
                "financial_year_id": str(financial_year_a.id),
                "period_start": "2025-04-01",
                "period_end": "2026-03-31",
            },
            headers=headers,
        )
        assert response.status_code == 403

    async def test_accountant_cannot_approve_engagement(
        self, client, db_session, seeded_rbac, company_a_with_admin, financial_year_a
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])
        accountant = await add_membership(
            db_session, seeded_rbac, company_id=company.id, email="rbac-accountant-2@example.com",
            role_code=RoleCode.ACCOUNTANT.value,
        )
        accountant_data = await login(client, accountant.email, "TestPass1!")
        accountant_headers = auth_headers(accountant_data["access_token"])

        engagement = await _create_engagement(client, headers, company.id, financial_year_a.id)
        response = await client.post(
            f"/api/v1/audits/engagements/{engagement['id']}/approve?company_id={company.id}",
            json={},
            headers=accountant_headers,
        )
        assert response.status_code == 403


class TestAuditTenantIsolation:
    async def test_company_b_cannot_access_company_a_engagement(
        self, client, company_a_with_admin, company_b_with_admin, financial_year_a
    ):
        company_a, admin_a = company_a_with_admin
        company_b, admin_b = company_b_with_admin
        data_a = await login(client, admin_a.email, "TestPass1!")
        headers_a = auth_headers(data_a["access_token"])
        data_b = await login(client, admin_b.email, "TestPass1!")
        headers_b = auth_headers(data_b["access_token"])

        engagement = await _create_engagement(client, headers_a, company_a.id, financial_year_a.id)

        no_membership = await client.get(
            f"/api/v1/audits/engagements/{engagement['id']}?company_id={company_a.id}", headers=headers_b
        )
        assert no_membership.status_code == 403
        assert no_membership.json()["error"]["code"] == "PERMISSION_DENIED"

        own_company_wrong_resource = await client.get(
            f"/api/v1/audits/engagements/{engagement['id']}?company_id={company_b.id}", headers=headers_b
        )
        assert own_company_wrong_resource.status_code == 404
        assert own_company_wrong_resource.json()["error"]["code"] == "AUDIT_ENGAGEMENT_NOT_FOUND"


class TestAuditReportsDashboard:
    async def test_dashboard_and_export(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        await _create_engagement(client, headers, company.id, financial_year_a.id)

        dashboard = await client.get(f"/api/v1/audits/dashboard?company_id={company.id}", headers=headers)
        assert dashboard.status_code == 200
        assert dashboard.json()["data"]["engagements_by_status"]["DRAFT"] == 1

    async def test_export_engagement_findings_csv(self, client, company_a_with_admin, financial_year_a):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        engagement = await _create_engagement(client, headers, company.id, financial_year_a.id)
        export = await client.get(
            f"/api/v1/audits/engagements/{engagement['id']}/export?company_id={company.id}&format=csv",
            headers=headers,
        )
        assert export.status_code == 200
        assert export.headers["content-type"].startswith("text/csv")

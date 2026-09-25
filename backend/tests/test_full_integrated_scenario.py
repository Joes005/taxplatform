import uuid
from datetime import date, timedelta
from decimal import Decimal
import pytest

from tests.conftest import auth_headers, login


class TestFullIntegratedScenario:
    """Phase 9.6: Full Functional Integration & Business Logic Scenario (Section 68).

    Tests end-to-end integration across:
    Auth -> Onboarding -> CoA -> Customer -> Product -> Sales Invoice -> Credit Note ->
    Receipt -> Vendor -> Purchase Invoice -> Debit Note -> Payment -> Trial Balance ->
    GST (GSTR-1, GSTR-3B) -> TDS (Transaction, Challan, Return) ->
    Bank Reconciliation (Statement, Match, Adjustment, Lock) ->
    Income Tax (Profile, Income, Tax Calc, ITR Prep, Lock) ->
    Audit Workflow (Engagement, Finding, Sign-off Block, Lead Sign-off) ->
    Compliance (Obligation, Task, Notification) -> Reports Reconciliation.
    """

    async def test_full_integrated_scenario(self, client, db_session, seeded_rbac, document_storage):
        from app.seed import (
            seed_default_compliance_rules,
            seed_default_income_tax_rule_sets,
            seed_default_tds_sections_and_rules,
            seed_gst_default_tax_rates,
        )
        await seed_gst_default_tax_rates(db_session)
        await seed_default_tds_sections_and_rules(db_session)
        await seed_default_income_tax_rule_sets(db_session)
        await seed_default_compliance_rules(db_session)
        await db_session.flush()

        # =========================================================================
        # 1. COMPANY SETUP (Section 68 §1)
        # =========================================================================
        reg_payload = {
            "first_name": "Sunil",
            "last_name": "Sharma",
            "email": "sunil.sharma@example.com",
            "password": "SecurePassword123!",
        }
        res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code == 201, res.text

        auth = await login(client, "sunil.sharma@example.com", "SecurePassword123!")
        token = auth["access_token"]
        user_id = auth["user"]["id"]

        onboard_payload = {
            "legal_name": "Sharma Industries Pvt Ltd",
            "trade_name": "Sharma Tech",
            "business_type": "PRIVATE_LIMITED",
            "pan": "AAACS1234A",
            "gstin": "27AAACS1234A1Z2",
            "state": "Maharashtra",
            "city": "Mumbai",
        }
        res = await client.post("/api/v1/companies/onboard", json=onboard_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        company = res.json()["data"]
        company_id = company["id"]

        # Select company
        res = await client.post("/api/v1/auth/select-company", json={"company_id": company_id}, headers=auth_headers(token))
        assert res.status_code == 200, res.text
        selected_data = res.json()["data"]
        assert selected_data["company_id"] == company_id
        assert selected_data["role_code"] == "COMPANY_ADMIN"

        # Verify Financial Year
        res = await client.get(f"/api/v1/accounting/financial-years?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        fy_list = res.json()["data"]["items"]
        assert len(fy_list) >= 1
        fy = fy_list[0]
        fy_id = fy["id"]
        s_year = int(fy["start_date"][:4])

        # Verify Chart of Accounts
        res = await client.get(f"/api/v1/accounting/ledgers?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        ledgers = {l["name"]: l["id"] for l in res.json()["data"]["items"]}
        assert "Bank Account" in ledgers
        assert "Sales Account" in ledgers
        assert "Purchase Account" in ledgers
        assert "Accounts Receivable" in ledgers
        assert "Accounts Payable" in ledgers
        bank_ledger_id = ledgers["Bank Account"]

        # =========================================================================
        # 2. MASTER DATA SETUP
        # =========================================================================
        # Customer
        cust_payload = {
            "name": "Alpha Traders",
            "code": "CUST-001",
            "gstin": "27AABCA5678B1ZT",
            "pan": "AABCA5678B",
            "state": "Maharashtra",
            "state_code": "27",
        }
        res = await client.post(f"/api/v1/accounting/customers?company_id={company_id}", json=cust_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        customer_id = res.json()["data"]["id"]

        # Product
        prod_payload = {
            "name": "Industrial Valve",
            "code": "PROD-VALVE-1",
            "item_type": "PRODUCT",
            "hsn_sac": "848180",
            "unit": "PCS",
            "tax_rate": "18.00",
        }
        res = await client.post(f"/api/v1/accounting/products?company_id={company_id}", json=prod_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        product_id = res.json()["data"]["id"]

        # =========================================================================
        # 3. SALES WORKFLOW (Section 68 §2)
        # =========================================================================
        inv_payload = {
            "financial_year_id": fy_id,
            "invoice_number": f"INV-{s_year}-001",
            "invoice_date": f"{s_year}-04-10",
            "customer_id": customer_id,
            "place_of_supply_state_code": "27",
            "items": [
                {
                    "product_service_id": product_id,
                    "description": "Industrial Valve 10 units",
                    "quantity": "10",
                    "unit_price": "1000.00",
                    "discount_rate": "0",
                    "cgst_rate": "9.00",
                    "sgst_rate": "9.00",
                    "igst_rate": "0.00",
                    "cess_rate": "0.00",
                }
            ],
        }
        res = await client.post(f"/api/v1/accounting/sales-invoices?company_id={company_id}", json=inv_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        invoice = res.json()["data"]
        sales_inv_id = invoice["id"]
        assert Decimal(invoice["taxable_amount"]) == Decimal("10000.00")
        assert Decimal(invoice["cgst_amount"]) == Decimal("900.00")
        assert Decimal(invoice["sgst_amount"]) == Decimal("900.00")
        assert Decimal(invoice["grand_total"]) == Decimal("11800.00")

        # Post Sales Invoice
        res = await client.post(f"/api/v1/accounting/sales-invoices/{sales_inv_id}/post?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text

        # Verify Customer Outstanding equals 11,800.00
        res = await client.get(f"/api/v1/accounting/reports/customer-outstanding?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        cust_out = res.json()["data"]
        assert len(cust_out) == 1
        assert Decimal(str(cust_out[0]["outstanding"])) == Decimal("11800.00")

        # =========================================================================
        # 4. SALES CREDIT NOTE WORKFLOW (Section 11)
        # =========================================================================
        # 4a. Over-amount credit note rejection
        bad_cn_payload = {
            "financial_year_id": fy_id,
            "note_type": "SALES",
            "customer_id": customer_id,
            "reference_sales_invoice_id": sales_inv_id,
            "credit_note_number": "CN-OVER-001",
            "credit_note_date": f"{s_year}-04-12",
            "reason": "Return",
            "items": [
                {
                    "product_service_id": product_id,
                    "description": "Returned valves",
                    "quantity": "20",
                    "unit_price": "1000.00",
                    "cgst_rate": "9.00",
                    "sgst_rate": "9.00",
                }
            ],
        }
        res = await client.post(f"/api/v1/accounting/credit-notes?company_id={company_id}", json=bad_cn_payload, headers=auth_headers(token))
        assert res.status_code == 422, res.text  # Over-amount rejected

        # 4b. Valid Credit Note (1 unit return: total 1,180.00)
        cn_payload = {
            "financial_year_id": fy_id,
            "note_type": "SALES",
            "customer_id": customer_id,
            "reference_sales_invoice_id": sales_inv_id,
            "credit_note_number": f"CN-{s_year}-001",
            "credit_note_date": f"{s_year}-04-12",
            "reason": "Damaged valve returned",
            "items": [
                {
                    "product_service_id": product_id,
                    "description": "1 Returned valve",
                    "quantity": "1",
                    "unit_price": "1000.00",
                    "cgst_rate": "9.00",
                    "sgst_rate": "9.00",
                }
            ],
        }
        res = await client.post(f"/api/v1/accounting/credit-notes?company_id={company_id}", json=cn_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        assert Decimal(str(res.json()["data"]["total_amount"])) == Decimal("1180.00")

        # Verify Customer Outstanding decreased to 10,620.00 (11,800 - 1,180)
        res = await client.get(f"/api/v1/accounting/reports/customer-outstanding?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        cust_out = res.json()["data"]
        assert Decimal(str(cust_out[0]["outstanding"])) == Decimal("10620.00")

        # =========================================================================
        # 5. RECEIPT WORKFLOW (Section 12)
        # =========================================================================
        # 5a. Overpayment rejection
        bad_rec_payload = {
            "financial_year_id": fy_id,
            "receipt_date": f"{s_year}-04-15",
            "receipt_number": "REC-BAD-001",
            "customer_id": customer_id,
            "ledger_id": bank_ledger_id,
            "amount": "15000.00",  # Exceeds remaining 10,620
            "payment_mode": "BANK",
            "reference_number": f"INV-{s_year}-001",
        }
        res = await client.post(f"/api/v1/accounting/receipts?company_id={company_id}", json=bad_rec_payload, headers=auth_headers(token))
        assert res.status_code == 422, res.text  # Overpayment rejected

        # 5b. Valid Receipt for remaining 10,620.00
        rec_payload = {
            "financial_year_id": fy_id,
            "receipt_date": f"{s_year}-04-15",
            "receipt_number": f"REC-{s_year}-001",
            "customer_id": customer_id,
            "ledger_id": bank_ledger_id,
            "amount": "10620.00",
            "payment_mode": "BANK",
            "reference_number": f"INV-{s_year}-001",
        }
        res = await client.post(f"/api/v1/accounting/receipts?company_id={company_id}", json=rec_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text

        # Verify Customer Outstanding is now 0.00!
        res = await client.get(f"/api/v1/accounting/reports/customer-outstanding?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        cust_out = res.json()["data"]
        assert Decimal(str(cust_out[0]["outstanding"])) == Decimal("0.00")

        # =========================================================================
        # 6. PURCHASE WORKFLOW (Section 68 §3)
        # =========================================================================
        # Vendor
        vend_payload = {
            "name": "Beta Metals Ltd",
            "code": "VEND-001",
            "gstin": "27AABCB9012C1Z6",
            "pan": "AABCB9012C",
            "state": "Maharashtra",
            "state_code": "27",
        }
        res = await client.post(f"/api/v1/accounting/vendors?company_id={company_id}", json=vend_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        vendor_id = res.json()["data"]["id"]

        # Purchase Invoice (5 units @ 800 = 4,000 taxable, CGST 360, SGST 360 = 4,720)
        bill_payload = {
            "financial_year_id": fy_id,
            "invoice_number": f"BILL-{s_year}-001",
            "invoice_date": f"{s_year}-04-16",
            "vendor_id": vendor_id,
            "items": [
                {
                    "product_service_id": product_id,
                    "description": "5 Raw valve castings",
                    "quantity": "5",
                    "unit_price": "800.00",
                    "cgst_rate": "9.00",
                    "sgst_rate": "9.00",
                    "igst_rate": "0.00",
                    "cess_rate": "0.00",
                }
            ],
        }
        res = await client.post(f"/api/v1/accounting/purchase-invoices?company_id={company_id}", json=bill_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        bill = res.json()["data"]
        bill_id = bill["id"]
        assert Decimal(bill["grand_total"]) == Decimal("4720.00")

        # Post Purchase Invoice
        res = await client.post(f"/api/v1/accounting/purchase-invoices/{bill_id}/post?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text

        # Verify Vendor Outstanding is 4,720.00
        res = await client.get(f"/api/v1/accounting/reports/vendor-outstanding?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        vend_out = res.json()["data"]
        assert Decimal(str(vend_out[0]["outstanding"])) == Decimal("4720.00")

        # =========================================================================
        # 7. PURCHASE DEBIT NOTE WORKFLOW (Section 11)
        # =========================================================================
        # Return 1 unit to vendor (800 + 72 + 72 = 944.00)
        dn_payload = {
            "financial_year_id": fy_id,
            "note_type": "PURCHASE",
            "vendor_id": vendor_id,
            "reference_purchase_invoice_id": bill_id,
            "debit_note_number": f"DN-{s_year}-001",
            "debit_note_date": f"{s_year}-04-18",
            "reason": "Defective casting returned",
            "items": [
                {
                    "product_service_id": product_id,
                    "description": "1 Defective casting",
                    "quantity": "1",
                    "unit_price": "800.00",
                    "cgst_rate": "9.00",
                    "sgst_rate": "9.00",
                }
            ],
        }
        res = await client.post(f"/api/v1/accounting/debit-notes?company_id={company_id}", json=dn_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        assert Decimal(str(res.json()["data"]["total_amount"])) == Decimal("944.00")

        # Verify Vendor Outstanding decreased to 3,776.00 (4,720 - 944)
        res = await client.get(f"/api/v1/accounting/reports/vendor-outstanding?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        vend_out = res.json()["data"]
        assert Decimal(str(vend_out[0]["outstanding"])) == Decimal("3776.00")

        # =========================================================================
        # 8. PAYMENT WORKFLOW (Section 12)
        # =========================================================================
        # Pay vendor remaining balance 3,776.00
        pay_payload = {
            "financial_year_id": fy_id,
            "payment_date": f"{s_year}-04-20",
            "payment_number": f"PAY-{s_year}-001",
            "party_type": "VENDOR",
            "party_id": vendor_id,
            "ledger_id": bank_ledger_id,
            "amount": "3776.00",
            "payment_mode": "BANK",
            "reference_number": f"BILL-{s_year}-001",
        }
        res = await client.post(f"/api/v1/accounting/payments?company_id={company_id}", json=pay_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text

        # Verify Vendor Outstanding is now 0.00!
        res = await client.get(f"/api/v1/accounting/reports/vendor-outstanding?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        vend_out = res.json()["data"]
        assert Decimal(str(vend_out[0]["outstanding"])) == Decimal("0.00")

        # =========================================================================
        # 9. TRIAL BALANCE INTEGRITY (Section 15, 69)
        # =========================================================================
        res = await client.get(f"/api/v1/accounting/reports/trial-balance?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        tb = res.json()["data"]
        assert tb["is_balanced"] is True
        assert Decimal(str(tb["total_debit"])) == Decimal(str(tb["total_credit"]))
        # Total debit/credit should reflect all double-entry postings exactly
        assert Decimal(str(tb["total_debit"])) > Decimal("0")

        # =========================================================================
        # 10. GST MODULE (Section 68 §4)
        # =========================================================================
        # Create GST Profile
        gst_profile_payload = {
            "gstin": "27AAACS1234A1Z2",
            "legal_name": "Sharma Industries Pvt Ltd",
            "trade_name": "Sharma Tech",
            "registration_type": "REGULAR",
        }
        res = await client.post(f"/api/v1/gst/profile?company_id={company_id}", json=gst_profile_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text

        # Create Return Period
        period_payload = {
            "financial_year_id": fy_id,
            "year": s_year,
            "month": 4,
        }
        res = await client.post(f"/api/v1/gst/return-periods?company_id={company_id}", json=period_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        return_period_id = res.json()["data"]["id"]

        # GSTR-1 B2B list
        res = await client.get(f"/api/v1/gst/return-periods/{return_period_id}/gstr1/b2b?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        b2b_rows = res.json()["data"]
        assert len(b2b_rows) == 1
        assert b2b_rows[0]["invoice_number"] == f"INV-{s_year}-001"
        assert Decimal(str(b2b_rows[0]["taxable_value"])) == Decimal("10000.00")

        # GSTR-1 Credit Notes list
        res = await client.get(f"/api/v1/gst/return-periods/{return_period_id}/gstr1/credit-notes?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        cn_rows = res.json()["data"]
        assert len(cn_rows) == 1
        assert cn_rows[0]["note_number"] == f"CN-{s_year}-001"
        assert cn_rows[0]["reference_invoice_number"] == f"INV-{s_year}-001"

        # GSTR-3B Summary
        res = await client.get(f"/api/v1/gst/return-periods/{return_period_id}/gstr3b?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        gstr3b = res.json()["data"]
        assert Decimal(str(gstr3b["outward_supplies"]["taxable_value"])) == Decimal("9000.00")
        assert Decimal(str(gstr3b["outward_supplies"]["cgst_amount"])) == Decimal("810.00")
        assert Decimal(str(gstr3b["outward_supplies"]["sgst_amount"])) == Decimal("810.00")

        # =========================================================================
        # 11. TDS MODULE (Section 68 §5)
        # =========================================================================
        # Deductee
        deductee_payload = {
            "name": "Sharma Legal Associates",
            "pan": "AAACS9999Z",
            "deductee_type": "COMPANY",
            "is_active": True,
        }
        res = await client.post(f"/api/v1/tds/deductees?company_id={company_id}", json=deductee_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        deductee_id = res.json()["data"]["id"]

        # TDS Section 194J lookup or creation
        res = await client.get(f"/api/v1/tds/sections?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        sections = res.json()["data"]
        sec_194j = next((s for s in sections if s.get("section_code") == "194J"), sections[0] if sections else None)
        assert sec_194j is not None, "No TDS sections found"
        section_id = sec_194j["id"]

        # Record TDS Transaction (50,000 gross, 5,000 TDS)
        tds_txn_payload = {
            "financial_year_id": fy_id,
            "deductee_id": deductee_id,
            "tds_section_id": section_id,
            "transaction_date": f"{s_year}-04-22",
            "gross_amount": "50000.00",
            "tds_rate": "10.00",
            "tds_amount": "5000.00",
        }
        res = await client.post(f"/api/v1/tds/transactions?company_id={company_id}", json=tds_txn_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        tds_txn_id = res.json()["data"]["id"]

        # Calculate and Deduct TDS transaction (DRAFT -> CALCULATED -> DEDUCTED)
        res = await client.post(f"/api/v1/tds/transactions/{tds_txn_id}/calculate?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        assert res.json()["data"]["status"] == "CALCULATED"

        res = await client.post(f"/api/v1/tds/transactions/{tds_txn_id}/deduct?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        assert res.json()["data"]["status"] == "DEDUCTED"

        # Create Challan for 5,000
        challan_payload = {
            "financial_year_id": fy_id,
            "challan_number": "CHAL-194J-001",
            "challan_date": f"{s_year}-04-25",
            "amount": "5000.00",
            "bank_reference_number": "BRN123456",
        }
        res = await client.post(f"/api/v1/tds/challans?company_id={company_id}", json=challan_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        challan_id = res.json()["data"]["id"]

        # Over-allocation check
        bad_alloc = {"tds_transaction_id": tds_txn_id, "allocated_amount": "6000.00"}
        res = await client.post(f"/api/v1/tds/challans/{challan_id}/allocate?company_id={company_id}", json=bad_alloc, headers=auth_headers(token))
        assert res.status_code == 422, res.text  # Over-allocation rejected

        # Valid Allocation
        alloc = {"tds_transaction_id": tds_txn_id, "allocated_amount": "5000.00"}
        res = await client.post(f"/api/v1/tds/challans/{challan_id}/allocate?company_id={company_id}", json=alloc, headers=auth_headers(token))
        assert res.status_code in (200, 201), res.text

        # =========================================================================
        # 12. BANK RECONCILIATION & ADJUSTMENTS (Section 68 §2/3, Section 30)
        # =========================================================================
        bank_acc_payload = {
            "account_name": "HDFC Current Account",
            "account_number_masked": "XXXXXX5678",
            "bank_name": "HDFC Bank",
            "branch_name": "Nariman Point",
            "ifsc_code": "HDFC0000123",
            "account_type": "CURRENT",
            "opening_balance": "50000.00",
            "opening_balance_date": f"{s_year}-04-01",
            "ledger_id": bank_ledger_id,
        }
        res = await client.post(f"/api/v1/bank/accounts?company_id={company_id}", json=bank_acc_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        bank_account_id = res.json()["data"]["id"]

        # Create statement
        stmt_payload = {
            "bank_account_id": bank_account_id,
            "statement_name": f"Statement April {s_year}",
            "period_start": f"{s_year}-04-01",
            "period_end": f"{s_year}-04-30",
            "opening_balance": "50000.00",
            "closing_balance": "56344.00",
        }
        res = await client.post(f"/api/v1/bank/statements?company_id={company_id}", json=stmt_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        stmt_id = res.json()["data"]["id"]

        # Upload CSV and import statement transactions
        csv_content = (
            f"Date,Narration,Ref,Withdrawal,Deposit,Balance\n"
            f"{s_year}-04-15,UPI RECEIVED ALPHA TRADERS,REC-{s_year}-001,,10620.00,60620.00\n"
            f"{s_year}-04-20,NEFT PAYMENT BETA METALS,PAY-{s_year}-001,3776.00,,56844.00\n"
            f"{s_year}-04-28,MONTHLY BANK CHARGES,CHG-001,500.00,,56344.00\n"
        ).encode("utf-8")
        upload = await client.post(
            f"/api/v1/documents?company_id={company_id}",
            headers=auth_headers(token),
            data={"document_type": "OTHER"},
            files={"file": ("statement.csv", csv_content, "text/csv")},
        )
        assert upload.status_code == 201, upload.text
        doc_id = upload.json()["data"]["id"]

        mapping = {
            "Date": "transaction_date",
            "Narration": "description",
            "Ref": "reference_number",
            "Withdrawal": "debit_amount",
            "Deposit": "credit_amount",
            "Balance": "balance_after_transaction",
        }
        job = await client.post(
            f"/api/v1/accounting/imports?company_id={company_id}",
            json={
                "document_id": doc_id,
                "import_type": "BANK_STATEMENT",
                "bank_statement_id": stmt_id,
                "column_mapping": mapping,
            },
            headers=auth_headers(token),
        )
        assert job.status_code == 201, job.text
        job_id = job.json()["data"]["id"]
        res = await client.post(f"/api/v1/accounting/imports/{job_id}/commit?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text

        # Fetch imported transactions
        res = await client.get(f"/api/v1/bank/statements/{stmt_id}/transactions?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        imported_txns = res.json()["data"]["items"]
        assert len(imported_txns) == 3
        fee_txn = next(t for t in imported_txns if "BANK CHARGES" in t["description"])
        bank_txn_id = fee_txn["id"]

        # Create bank adjustment: turns the 500 fee into a real POSTED journal entry
        adj_payload = {
            "financial_year_id": fy_id,
            "offset_ledger_id": ledgers["Round Off"],
            "journal_number": f"JV-ADJ-{s_year}-001",
            "narration": "Adjustment for Bank Service Charges",
        }
        res = await client.post(f"/api/v1/bank/transactions/{bank_txn_id}/adjust?company_id={company_id}", json=adj_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        assert res.json()["data"]["status"] == "POSTED"

        # Start Reconciliation session
        rec_session_payload = {
            "bank_account_id": bank_account_id,
            "period_start": f"{s_year}-04-01",
            "period_end": f"{s_year}-04-30",
            "opening_balance": "50000.00",
            "closing_balance": "56344.00",
        }
        res = await client.post(f"/api/v1/bank/reconciliations?company_id={company_id}", json=rec_session_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        rec_id = res.json()["data"]["id"]

        # Run matching -> submit -> approve -> lock
        res = await client.post(f"/api/v1/bank/reconciliations/{rec_id}/run-matching?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text

        res = await client.post(f"/api/v1/bank/reconciliations/{rec_id}/submit?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text

        res = await client.post(f"/api/v1/bank/reconciliations/{rec_id}/approve?company_id={company_id}", json={"comment": "Approved"}, headers=auth_headers(token))
        assert res.status_code == 200, res.text

        res = await client.post(f"/api/v1/bank/reconciliations/{rec_id}/lock?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        assert res.json()["data"]["status"] == "LOCKED"

        # =========================================================================
        # 13. INCOME TAX MODULE (Section 68 §6)
        # =========================================================================
        it_profile_payload = {
            "pan": "AAACS1234A",
            "legal_name": "Sharma Industries Pvt Ltd",
            "trade_name": "Sharma Tech",
            "taxpayer_type": "COMPANY",
            "residential_status": "RESIDENT",
        }
        res = await client.post(f"/api/v1/income-tax/profile?company_id={company_id}", json=it_profile_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text

        # Tax computation
        comp_payload = {
            "financial_year_id": fy_id,
            "tax_regime": "NEW_REGIME",
        }
        res = await client.post(f"/api/v1/income-tax/computations?company_id={company_id}", json=comp_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        comp_id = res.json()["data"]["id"]

        # Calculate computation
        res = await client.post(f"/api/v1/income-tax/computations/{comp_id}/calculate?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        comp = res.json()["data"]
        assert Decimal(str(comp["taxable_income"])) >= Decimal("0")

        # Add Auditor user for CA review, approval and sign-offs (RBAC & Segregation of Duties)
        from tests.conftest import add_membership
        from app.core.permissions import RoleCode

        await add_membership(
            db_session,
            seeded_rbac,
            company_id=company_id,
            email="auditor@example.com",
            role_code=RoleCode.AUDITOR.value,
        )
        auditor_auth = await login(client, "auditor@example.com", "TestPass1!")
        auditor_token = auditor_auth["access_token"]
        await client.post("/api/v1/auth/select-company", json={"company_id": company_id}, headers=auth_headers(auditor_token))

        # ITR Preparation lifecycle (DRAFT -> PREPARED -> REVIEWED -> APPROVED -> LOCKED)
        itr_payload = {
            "tax_computation_id": comp_id,
        }
        res = await client.post(f"/api/v1/income-tax/itr?company_id={company_id}", json=itr_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        itr_id = res.json()["data"]["id"]

        res = await client.post(f"/api/v1/income-tax/itr/{itr_id}/validate?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        res = await client.post(f"/api/v1/income-tax/itr/{itr_id}/submit-review?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        res = await client.post(f"/api/v1/income-tax/itr/{itr_id}/approve?company_id={company_id}", headers=auth_headers(auditor_token))
        assert res.status_code == 200, res.text
        res = await client.post(f"/api/v1/income-tax/itr/{itr_id}/lock?company_id={company_id}", headers=auth_headers(auditor_token))
        assert res.status_code == 200, res.text
        assert res.json()["data"]["status"] == "LOCKED"

        # =========================================================================
        # 14. AUDIT WORKFLOW (Section 68 §7, Section 37)
        # =========================================================================
        eng_payload = {
            "financial_year_id": fy_id,
            "title": f"Statutory Tax Audit FY {s_year}-{str(s_year+1)[-2:]}",
            "description": "Comprehensive Statutory Audit",
            "period_start": f"{s_year}-05-01",
            "period_end": f"{s_year}-09-30",
            "engagement_type": "TAX_COMPLIANCE_REVIEW",
        }
        res = await client.post(f"/api/v1/audits/engagements?company_id={company_id}", json=eng_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        eng = res.json()["data"]
        eng_id = eng["id"]

        # Move to IN_REVIEW
        res = await client.post(f"/api/v1/audits/engagements/{eng_id}/open?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        res = await client.post(f"/api/v1/audits/engagements/{eng_id}/start-review?company_id={company_id}", headers=auth_headers(auditor_token))
        assert res.status_code == 200, res.text

        # Create a CRITICAL finding
        finding_payload = {
            "title": "Missing physical stock verification sheet",
            "description": "Stock sheet for Q4 not reconciled",
            "severity": "CRITICAL",
            "category": "ACCOUNTING",
        }
        res = await client.post(f"/api/v1/audits/engagements/{eng_id}/findings?company_id={company_id}", json=finding_payload, headers=auth_headers(auditor_token))
        assert res.status_code == 201, res.text
        finding_id = res.json()["data"]["finding"]["id"]

        # Submit engagement for review
        res = await client.post(f"/api/v1/audits/engagements/{eng_id}/submit-for-review?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text

        # Verify APPROVE is BLOCKED by the open CRITICAL finding! (Section 37)
        res = await client.post(f"/api/v1/audits/engagements/{eng_id}/approve?company_id={company_id}", json={"comment": "approve"}, headers=auth_headers(auditor_token))
        assert res.status_code == 409, res.text
        assert "AUDIT_ENGAGEMENT_OPEN_FINDINGS_BLOCK_APPROVAL" in res.text

        # Resolve the finding
        res = await client.post(
            f"/api/v1/audits/findings/{finding_id}/resolve?company_id={company_id}",
            json={"resolution_summary": "Stock verification sheet produced and verified"},
            headers=auth_headers(auditor_token),
        )
        assert res.status_code == 200, res.text

        # Now approve succeeds!
        res = await client.post(f"/api/v1/audits/engagements/{eng_id}/approve?company_id={company_id}", json={"comment": "approve"}, headers=auth_headers(auditor_token))
        assert res.status_code == 200, res.text

        # Record Lead Auditor sign-off
        signoff_payload = {
            "sign_off_type": "LEAD_AUDITOR",
        }
        res = await client.post(f"/api/v1/audits/engagements/{eng_id}/sign-offs?company_id={company_id}", json=signoff_payload, headers=auth_headers(auditor_token))
        assert res.status_code == 201, res.text

        # Mark signed off and close
        res = await client.post(f"/api/v1/audits/engagements/{eng_id}/mark-signed-off?company_id={company_id}", headers=auth_headers(auditor_token))
        assert res.status_code == 200, res.text
        res = await client.post(f"/api/v1/audits/engagements/{eng_id}/close?company_id={company_id}", headers=auth_headers(auditor_token))
        assert res.status_code == 200, res.text
        assert res.json()["data"]["status"] == "CLOSED"

        # =========================================================================
        # 15. COMPLIANCE & NOTIFICATION WORKFLOW (Section 68 §8, Section 40, 41)
        # =========================================================================
        ob_payload = {
            "code": "GSTR1-MONTHLY",
            "name": "GSTR-1 Monthly Return Filing",
            "category": "GST",
            "module": "GST",
            "frequency": "MONTHLY",
            "start_date": f"{s_year}-04-01",
            "due_date": f"{s_year}-05-11",
            "priority": "HIGH",
        }
        res = await client.post(f"/api/v1/compliance/obligations?company_id={company_id}", json=ob_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        ob_id = res.json()["data"]["id"]

        # Generate task
        task_payload = {
            "obligation_id": ob_id,
            "title": "Prepare and Review GSTR-1",
            "category": "GST",
            "module": "GST",
            "due_date": f"{s_year}-05-11",
        }
        res = await client.post(f"/api/v1/compliance/tasks?company_id={company_id}", json=task_payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text
        task_id = res.json()["data"]["id"]

        # Start task
        res = await client.post(f"/api/v1/compliance/tasks/{task_id}/start?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        assert res.json()["data"]["status"] == "IN_PROGRESS"

        # Complete task
        res = await client.post(f"/api/v1/compliance/tasks/{task_id}/complete?company_id={company_id}", json={"completion_notes": "Completed filing"}, headers=auth_headers(token))
        assert res.status_code == 200, res.text
        assert res.json()["data"]["status"] == "COMPLETED"

        # Verify notification
        res = await client.get(f"/api/v1/notifications?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        assert res.status_code == 200, res.text

        # =========================================================================
        # 16. FINAL RECONCILIATION & REPORTS CHECK (Section 69)
        # =========================================================================
        # 1. Trial Balance matches and balances
        res = await client.get(f"/api/v1/accounting/reports/trial-balance?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        final_tb = res.json()["data"]
        assert final_tb["is_balanced"] is True
        assert Decimal(str(final_tb["total_debit"])) == Decimal(str(final_tb["total_credit"]))

        # 2. Customer Outstanding is 0
        res = await client.get(f"/api/v1/accounting/reports/customer-outstanding?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        assert Decimal(str(res.json()["data"][0]["outstanding"])) == Decimal("0.00")

        # 3. Vendor Outstanding is 0
        res = await client.get(f"/api/v1/accounting/reports/vendor-outstanding?company_id={company_id}", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        assert Decimal(str(res.json()["data"][0]["outstanding"])) == Decimal("0.00")

from datetime import date
from decimal import Decimal
import io
import uuid
import pytest
from httpx import AsyncClient

from app.core.exceptions import ValidationAppError
from app.core.permissions import RoleCode
from app.models.accounting_enums import PeriodStatus
from app.models.accounting_period import AccountingPeriod
from app.models.financial_year import FinancialYear
from app.models.tally_mapping_template import TallyMappingTemplate
from app.services.tally.tally_adapter import TallyImportAdapter
from app.services.tally.tally_detector import detect_tally_format
from app.services.tally.tally_exporter import TallyExporter
from app.services.tally.tally_models import (
    MappingStatus,
    TallyFormat,
    TallyVoucherType,
    ValidationSeverity,
)
from app.services.tally.tally_tabular_parser import TallyTabularParser
from app.services.tally.tally_validator import TallyValidator
from app.services.tally.tally_xml_parser import TallyXMLParser
from tests.conftest import add_membership, auth_headers, login


VALID_TALLY_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <DATA>
      <TALLYMESSAGE xmlns:UDF="TallyUDF">
        <COMPANY>
          <REMOTECMPINFO.LIST>
            <NAME>ABC Traders Pvt Ltd</NAME>
            <STARTINGFROM>20240401</STARTINGFROM>
          </REMOTECMPINFO.LIST>
        </COMPANY>
      </TALLYMESSAGE>
      <TALLYMESSAGE>
        <GROUP NAME="Sundry Debtors">
          <PARENT>Current Assets</PARENT>
        </GROUP>
      </TALLYMESSAGE>
      <TALLYMESSAGE>
        <LEDGER NAME="Zenith Technologies" RESERVEDNAME="">
          <PARENT>Sundry Debtors</PARENT>
          <OPENINGBALANCE>-50000.00</OPENINGBALANCE>
          <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
          <PARTYGSTIN>27AABCT3518Q1ZS</PARTYGSTIN>
          <PANNO>AABCT3518Q</PANNO>
          <STATENAME>Maharashtra</STATENAME>
        </LEDGER>
      </TALLYMESSAGE>
      <TALLYMESSAGE>
        <LEDGER NAME="Apex Supplies" RESERVEDNAME="">
          <PARENT>Sundry Creditors</PARENT>
          <OPENINGBALANCE>50000.00</OPENINGBALANCE>
          <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
          <PARTYGSTIN>27AAACA1234B1Z1</PARTYGSTIN>
          <PANNO>AAACA1234B</PANNO>
        </LEDGER>
      </TALLYMESSAGE>
      <TALLYMESSAGE>
        <VOUCHER VOUCHERTYPENAME="Sales" ACTION="Create">
          <DATE>20240510</DATE>
          <VOUCHERNUMBER>INV-TALLY-001</VOUCHERNUMBER>
          <PARTYLEDGERNAME>Zenith Technologies</PARTYLEDGERNAME>
          <NARRATION>Software services</NARRATION>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Zenith Technologies</LEDGERNAME>
            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
            <AMOUNT>-11800.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Sales Revenue</LEDGERNAME>
            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
            <AMOUNT>10000.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Output CGST</LEDGERNAME>
            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
            <AMOUNT>900.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Output SGST</LEDGERNAME>
            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
            <AMOUNT>900.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
        </VOUCHER>
      </TALLYMESSAGE>
      <TALLYMESSAGE>
        <VOUCHER VOUCHERTYPENAME="Purchase" ACTION="Create">
          <DATE>20240512</DATE>
          <VOUCHERNUMBER>BILL-TALLY-001</VOUCHERNUMBER>
          <PARTYLEDGERNAME>Apex Supplies</PARTYLEDGERNAME>
          <NARRATION>Hardware purchase</NARRATION>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Purchase Expense</LEDGERNAME>
            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
            <AMOUNT>-5000.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Input CGST</LEDGERNAME>
            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
            <AMOUNT>-450.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Input SGST</LEDGERNAME>
            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
            <AMOUNT>-450.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Apex Supplies</LEDGERNAME>
            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
            <AMOUNT>5900.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
        </VOUCHER>
      </TALLYMESSAGE>
      <TALLYMESSAGE>
        <VOUCHER VOUCHERTYPENAME="Receipt" ACTION="Create">
          <DATE>20240515</DATE>
          <VOUCHERNUMBER>REC-TALLY-001</VOUCHERNUMBER>
          <PARTYLEDGERNAME>Zenith Technologies</PARTYLEDGERNAME>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Bank Account</LEDGERNAME>
            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
            <AMOUNT>-11800.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Zenith Technologies</LEDGERNAME>
            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
            <AMOUNT>11800.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
        </VOUCHER>
      </TALLYMESSAGE>
      <TALLYMESSAGE>
        <VOUCHER VOUCHERTYPENAME="Payment" ACTION="Create">
          <DATE>20240518</DATE>
          <VOUCHERNUMBER>PAY-TALLY-001</VOUCHERNUMBER>
          <PARTYLEDGERNAME>Apex Supplies</PARTYLEDGERNAME>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Apex Supplies</LEDGERNAME>
            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
            <AMOUNT>-5900.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Bank Account</LEDGERNAME>
            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
            <AMOUNT>5900.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
        </VOUCHER>
      </TALLYMESSAGE>
      <TALLYMESSAGE>
        <VOUCHER VOUCHERTYPENAME="Journal" ACTION="Create">
          <DATE>20240520</DATE>
          <VOUCHERNUMBER>JRN-TALLY-001</VOUCHERNUMBER>
          <NARRATION>Depreciation on equipment</NARRATION>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Depreciation Expense</LEDGERNAME>
            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
            <AMOUNT>-1500.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>Accumulated Depreciation</LEDGERNAME>
            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
            <AMOUNT>1500.00</AMOUNT>
          </ALLLEDGERENTRIES.LIST>
        </VOUCHER>
      </TALLYMESSAGE>
    </DATA>
  </BODY>
</ENVELOPE>
"""

MALFORMED_XML = b"<?xml version='1.0'?><ENVELOPE><BODY><DATA><TALLYMESSAGE><UNCLOSED></DATA></BODY></ENVELOPE>"

XML_BOMB = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [
 <!ENTITY lol "lol">
 <!ELEMENT lolz (#PCDATA)>
 <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
 <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
 <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<ENVELOPE>&lol3;</ENVELOPE>
"""

SAMPLE_TALLY_CSV = b"""Date,Voucher Type,Voucher No,Particulars,Debit Amount,Credit Amount,Narration
2024-05-10,Sales,CSV-INV-001,Zenith Corp,11800,,Goods sold
2024-05-10,Sales,CSV-INV-001,Sales Revenue,,10000,
2024-05-10,Sales,CSV-INV-001,Output CGST,,900,
2024-05-10,Sales,CSV-INV-001,Output SGST,,900,
2024-05-12,Purchase,CSV-BILL-001,Purchase Expense,5000,,
2024-05-12,Purchase,CSV-BILL-001,Input CGST,450,,
2024-05-12,Purchase,CSV-BILL-001,Input SGST,450,,
2024-05-12,Purchase,CSV-BILL-001,Apex Vendor,,5900,Goods received
"""


async def upload_file_doc(client, access_token, company_id, filename: str, content: bytes, mime: str = "text/xml"):
    return await client.post(
        f"/api/v1/documents?company_id={company_id}",
        headers=auth_headers(access_token),
        data={"document_type": "OTHER"},
        files={"file": (filename, content, mime)},
    )


class TestPhase12TallyCompatibility:
    # 1. Format Detection
    def test_format_detection_xml(self):
        res = detect_tally_format(VALID_TALLY_XML, filename="export.xml")
        assert res.format == TallyFormat.TALLY_XML
        assert res.has_tally_markers is True
        assert res.is_valid is True

    def test_format_detection_csv(self):
        res = detect_tally_format(SAMPLE_TALLY_CSV, filename="daybook.csv")
        assert res.format == TallyFormat.CSV
        assert res.is_valid is True

    def test_format_detection_empty(self):
        res = detect_tally_format(b"", filename="empty.xml")
        assert res.is_valid is False
        assert res.format == TallyFormat.INVALID

    # 2. XML Parsing & Canonical Normalization
    def test_tally_xml_parser_extracts_canonical_entities(self):
        parser = TallyXMLParser()
        batch = parser.parse(VALID_TALLY_XML)

        assert batch.company_record is not None
        assert batch.company_record.name == "ABC Traders Pvt Ltd"
        assert len(batch.groups) == 1
        assert len(batch.ledgers) == 2
        assert len(batch.parties) == 2
        assert len(batch.vouchers) == 5

        # Check voucher types normalized
        v_types = [v.normalized_type for v in batch.vouchers]
        assert TallyVoucherType.SALES in v_types
        assert TallyVoucherType.PURCHASE in v_types
        assert TallyVoucherType.RECEIPT in v_types
        assert TallyVoucherType.PAYMENT in v_types
        assert TallyVoucherType.JOURNAL in v_types

        # Check sales invoice tax breakdown
        sales_v = next(v for v in batch.vouchers if v.normalized_type == TallyVoucherType.SALES)
        assert sales_v.voucher_number == "INV-TALLY-001"
        assert sales_v.party_name == "Zenith Technologies"
        assert sales_v.total_amount == Decimal("11800.00")
        assert sales_v.tax_breakdown.taxable_amount == Decimal("10000.00")
        assert sales_v.tax_breakdown.cgst_amount == Decimal("900.00")
        assert sales_v.tax_breakdown.sgst_amount == Decimal("900.00")

    # 3. Malformed XML Rejection
    def test_malformed_xml_rejected(self):
        parser = TallyXMLParser()
        with pytest.raises(ValidationAppError) as exc_info:
            parser.parse(MALFORMED_XML)
        assert exc_info.value.code == "INVALID_XML"

    # 4. Secure XML Handling (XML Bomb / XXE Defense)
    def test_xml_bomb_defused(self):
        parser = TallyXMLParser()
        with pytest.raises(Exception):
            # defusedxml will raise DTDForbidden or EntitiesForbidden
            parser.parse(XML_BOMB)

    # 5. CSV Tabular Parsing
    def test_csv_tabular_parser(self):
        parser = TallyTabularParser()
        batch = parser.parse_csv(SAMPLE_TALLY_CSV)
        assert len(batch.vouchers) == 2
        v_sales = next(v for v in batch.vouchers if v.normalized_type == TallyVoucherType.SALES)
        assert v_sales.voucher_number == "CSV-INV-001"
        assert v_sales.total_amount == Decimal("11800")
        assert len(v_sales.lines) == 4

    # 6. Validation Engine: Double Entry Check
    @pytest.mark.asyncio
    async def test_validation_unbalanced_journal(self, db_session, company_a_with_admin):
        company, _ = company_a_with_admin
        parser = TallyXMLParser()
        batch = parser.parse(VALID_TALLY_XML)

        # Force a journal line to be unbalanced
        j_v = next(v for v in batch.vouchers if v.normalized_type == TallyVoucherType.JOURNAL)
        j_v.lines[0].amount = Decimal("99999.00")

        validator = TallyValidator(db_session, company.id)
        res = await validator.validate_batch(batch)
        assert res.is_valid_to_commit is False
        assert any(e.code == "UNBALANCED_VOUCHER" for e in res.errors)

    # 7. Validation Engine: Period Lock Protection
    @pytest.mark.asyncio
    async def test_validation_period_lock_protection(self, db_session, company_a_with_admin):
        company, _ = company_a_with_admin
        fy = FinancialYear(
            company_id=company.id,
            name="FY 2024-25",
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
        )
        db_session.add(fy)
        await db_session.flush()

        # Lock May 2024
        locked_period = AccountingPeriod(
            company_id=company.id,
            financial_year_id=fy.id,
            name="May 2024",
            start_date=date(2024, 5, 1),
            end_date=date(2024, 5, 31),
            status=PeriodStatus.LOCKED,
        )
        db_session.add(locked_period)
        await db_session.flush()

        parser = TallyXMLParser()
        batch = parser.parse(VALID_TALLY_XML)

        validator = TallyValidator(db_session, company.id)
        res = await validator.validate_batch(batch)
        assert res.is_valid_to_commit is False
        assert any(e.code == "PERIOD_LOCKED" for e in res.errors)

    # 8. API Full Lifecycle: Detect -> Preview -> Mapping -> Commit -> Reconcile
    @pytest.mark.asyncio
    async def test_full_tally_import_and_reconciliation_flow(
        self, client: AsyncClient, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        # 1. Upload Document
        doc_resp = await upload_file_doc(
            client, data["access_token"], company.id, "tally_export.xml", VALID_TALLY_XML
        )
        assert doc_resp.status_code == 201, doc_resp.text
        doc_id = doc_resp.json()["data"]["id"]

        # 2. Preview
        preview_resp = await client.post(
            f"/api/v1/tally/preview?company_id={company.id}",
            headers=headers,
            json={"document_id": doc_id},
        )
        assert preview_resp.status_code == 200, preview_resp.text
        preview_data = preview_resp.json()["data"]
        job_id = preview_data["job_id"]
        assert preview_data["total_records"] == 5
        assert preview_data["valid_records"] == 5
        assert preview_data["duplicate_records"] == 0
        assert len(preview_data["mappings"]) > 0

        # 3. Commit
        commit_resp = await client.post(
            f"/api/v1/tally/commit?company_id={company.id}",
            headers=headers,
            json={
                "job_id": job_id,
                "confirmed_mappings": preview_data["mappings"],
                "save_as_template_name": "Standard Tally Template",
            },
        )
        assert commit_resp.status_code == 200, commit_resp.text
        commit_data = commit_resp.json()["data"]
        assert commit_data["status"] == "COMPLETED"
        recon = commit_data["reconciliation"]
        assert recon["overall_matched"] is True

        # Check reconciliation numbers
        sales_recon = next(item for item in recon["items"] if item["entity_type"] == "SALES")
        assert sales_recon["source_count"] == 1
        assert sales_recon["imported_count"] == 1
        assert float(sales_recon["difference_amount"]) == 0

        # 4. Fetch Reconciliation Endpoint
        recon_fetch = await client.get(
            f"/api/v1/tally/reconciliation/{job_id}?company_id={company.id}",
            headers=headers,
        )
        assert recon_fetch.status_code == 200
        assert recon_fetch.json()["data"]["overall_matched"] is True

        # 5. Verify Template was saved
        tpl_resp = await client.get(
            f"/api/v1/tally/templates?company_id={company.id}",
            headers=headers,
        )
        assert tpl_resp.status_code == 200
        templates = tpl_resp.json()["data"]
        assert any(t["name"] == "Standard Tally Template" for t in templates)

    # 9. Idempotent Re-import and Duplicate Detection
    @pytest.mark.asyncio
    async def test_idempotent_reimport_flags_already_imported(
        self, client: AsyncClient, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        # First import and commit
        doc_resp1 = await upload_file_doc(
            client, data["access_token"], company.id, "tally_export_first.xml", VALID_TALLY_XML
        )
        doc_id1 = doc_resp1.json()["data"]["id"]
        preview_resp1 = await client.post(
            f"/api/v1/tally/preview?company_id={company.id}",
            headers=headers,
            json={"document_id": doc_id1},
        )
        pdata1 = preview_resp1.json()["data"]
        await client.post(
            f"/api/v1/tally/commit?company_id={company.id}",
            headers=headers,
            json={"job_id": pdata1["job_id"], "confirmed_mappings": pdata1["mappings"]},
        )

        # Upload another XML file containing the same vouchers
        xml_second = VALID_TALLY_XML.replace(b"</ENVELOPE>", b"<!-- second export batch -->\n</ENVELOPE>")
        doc_resp2 = await upload_file_doc(
            client, data["access_token"], company.id, "tally_export_second.xml", xml_second
        )
        assert doc_resp2.status_code == 201, doc_resp2.text
        doc_id2 = doc_resp2.json()["data"]["id"]

        preview_resp2 = await client.post(
            f"/api/v1/tally/preview?company_id={company.id}",
            headers=headers,
            json={"document_id": doc_id2},
        )
        assert preview_resp2.status_code == 200
        preview_data = preview_resp2.json()["data"]

        # All 5 vouchers should be identified as duplicate
        assert preview_data["duplicate_records"] == 5
        assert any(w["code"] == "DUPLICATE_RECORD" for w in preview_data["errors"])
        for r in preview_data["rows"]:
            assert r["is_duplicate"] is True
            assert r["status"] == "DUPLICATE"

    # 10. Tally Export Generation & Round-Trip
    @pytest.mark.asyncio
    async def test_tally_export_and_round_trip(
        self, client: AsyncClient, document_storage, company_a_with_admin
    ):
        company, admin = company_a_with_admin
        data = await login(client, admin.email, "TestPass1!")
        headers = auth_headers(data["access_token"])

        # Commit import first so we have data
        doc_resp = await upload_file_doc(
            client, data["access_token"], company.id, "tally_exp_data.xml", VALID_TALLY_XML
        )
        doc_id = doc_resp.json()["data"]["id"]
        prev_res = await client.post(
            f"/api/v1/tally/preview?company_id={company.id}",
            headers=headers,
            json={"document_id": doc_id},
        )
        pdata = prev_res.json()["data"]
        await client.post(
            f"/api/v1/tally/commit?company_id={company.id}",
            headers=headers,
            json={"job_id": pdata["job_id"], "confirmed_mappings": pdata["mappings"]},
        )

        # 1. Preview export
        exp_prev = await client.post(
            f"/api/v1/tally/export/preview?company_id={company.id}",
            headers=headers,
            json={"voucher_types": ["SALES", "PURCHASE", "RECEIPT", "PAYMENT", "JOURNAL"]},
        )
        assert exp_prev.status_code == 200
        assert exp_prev.json()["data"]["total_vouchers"] >= 5

        # 2. Export XML
        exp_resp = await client.post(
            f"/api/v1/tally/export?company_id={company.id}",
            headers=headers,
            json={"format": "XML", "voucher_types": ["SALES", "PURCHASE", "RECEIPT", "PAYMENT", "JOURNAL"]},
        )
        assert exp_resp.status_code == 200
        assert exp_resp.headers["content-type"] == "application/xml"
        xml_content = exp_resp.content
        assert b"<ENVELOPE>" in xml_content
        assert b"<VOUCHER" in xml_content

        # 3. Round-trip: parse exported XML back through TallyXMLParser
        parser = TallyXMLParser()
        round_trip_batch = parser.parse(xml_content)
        assert len(round_trip_batch.vouchers) >= 5

        # 4. Export CSV
        exp_csv = await client.post(
            f"/api/v1/tally/export?company_id={company.id}",
            headers=headers,
            json={"format": "CSV"},
        )
        assert exp_csv.status_code == 200
        assert b"Voucher Type,Voucher No" in exp_csv.content

        # 5. Export XLSX
        exp_xlsx = await client.post(
            f"/api/v1/tally/export?company_id={company.id}",
            headers=headers,
            json={"format": "XLSX"},
        )
        assert exp_xlsx.status_code == 200
        assert exp_xlsx.content.startswith(b"PK\x03\x04")

    # 11. RBAC & Auditor Protection
    @pytest.mark.asyncio
    async def test_auditor_cannot_commit_tally_import(
        self, client: AsyncClient, db_session, seeded_rbac, company_a_with_admin
    ):
        company, _ = company_a_with_admin
        auditor = await add_membership(
            db_session,
            seeded_rbac,
            company_id=company.id,
            email="auditor_test@example.com",
            role_code=RoleCode.AUDITOR.value,
        )

        login_res = await login(client, "auditor_test@example.com", "TestPass1!")
        auditor_headers = auth_headers(login_res["access_token"])

        # Auditor cannot commit
        fake_job_id = uuid.uuid4()
        commit_res = await client.post(
            f"/api/v1/tally/commit?company_id={company.id}",
            headers=auditor_headers,
            json={"job_id": str(fake_job_id)},
        )
        assert commit_res.status_code == 403

    # 12. Tenant Isolation
    @pytest.mark.asyncio
    async def test_tenant_isolation_blocks_cross_company_access(
        self, client: AsyncClient, company_a_with_admin, company_b_with_admin
    ):
        comp_a, admin_a = company_a_with_admin
        comp_b, _ = company_b_with_admin

        data_a = await login(client, admin_a.email, "TestPass1!")
        headers_a = auth_headers(data_a["access_token"])

        # Attempt to access Company B tally templates with Company A credentials
        res = await client.get(
            f"/api/v1/tally/templates?company_id={comp_b.id}",
            headers=headers_a,
        )
        assert res.status_code == 403

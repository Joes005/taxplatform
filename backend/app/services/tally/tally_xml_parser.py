from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import io
import re
from typing import Any

from defusedxml.ElementTree import fromstring, ParseError

from app.core.exceptions import ValidationAppError
from app.services.tally.tally_models import (
    TallyCompanyRecord,
    TallyGroupRecord,
    TallyImportBatch,
    TallyInventoryLine,
    TallyLedgerRecord,
    TallyOpeningBalanceRecord,
    TallyPartyRecord,
    TallyStockItemRecord,
    TallyTaxBreakdown,
    TallyValidationError,
    TallyVoucherLine,
    TallyVoucherRecord,
    TallyVoucherType,
    ValidationSeverity,
    TallyFormat,
)

# Date regexes
DATE_YMD_COMPACT = re.compile(r"^\d{8}$")  # 20240515
DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # 2024-05-15
DATE_DMY_HYPHEN = re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$")  # 15-05-2024
DATE_DMY_SLASH = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")  # 15/05/2024


def parse_tally_date(val: str | None) -> date | None:
    if not val:
        return None
    cleaned = val.strip()
    if not cleaned:
        return None

    # YYYYMMDD
    if DATE_YMD_COMPACT.match(cleaned):
        try:
            return date(int(cleaned[:4]), int(cleaned[4:6]), int(cleaned[6:8]))
        except ValueError:
            pass

    # YYYY-MM-DD
    if DATE_ISO.match(cleaned):
        try:
            parts = cleaned.split("-")
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            pass

    # DD-MM-YYYY
    if DATE_DMY_HYPHEN.match(cleaned):
        try:
            parts = cleaned.split("-")
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
        except ValueError:
            pass

    # DD/MM/YYYY
    if DATE_DMY_SLASH.match(cleaned):
        try:
            parts = cleaned.split("/")
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
        except ValueError:
            pass

    # Try DD-Mon-YYYY (e.g. 1-Apr-2024 or 15-May-2024)
    for fmt in ("%d-%b-%Y", "%d-%b-%y", "%d %b %Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    return None


def parse_tally_amount(val: str | None, default: Decimal = Decimal(0)) -> Decimal:
    if not val:
        return default
    cleaned = val.strip().replace(",", "").replace("₹", "").replace("$", "")
    if not cleaned:
        return default
    # If wrapped in parens e.g. (100.00), it means negative
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    # In Tally, amounts may end with Dr or Cr
    if cleaned.upper().endswith("DR"):
        cleaned = "-" + cleaned[:-2].strip()
    elif cleaned.upper().endswith("CR"):
        cleaned = cleaned[:-2].strip()

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return default


def _clean_tag(tag: str) -> str:
    """Strips XML namespaces and lowercases the tag name."""
    if "}" in tag:
        tag = tag.split("}", 1)[1]
    return tag.lower()


def _find_child(element, tag_name: str):
    """Finds first child whose tag matches tag_name case-insensitively."""
    target = tag_name.lower()
    for child in element:
        if _clean_tag(child.tag) == target:
            return child
    return None


def _find_all_children(element, tag_name: str):
    """Finds all children whose tag matches tag_name case-insensitively."""
    target = tag_name.lower()
    matches = []
    for child in element:
        if _clean_tag(child.tag) == target:
            matches.append(child)
    return matches


def _get_text(element, tag_name: str, default: str = "") -> str:
    child = _find_child(element, tag_name)
    if child is not None and child.text:
        return child.text.strip()
    return default


def normalize_voucher_type(vtype_str: str) -> TallyVoucherType:
    v = vtype_str.strip().upper()
    if "SALE" in v or "INVOICE" in v:
        return TallyVoucherType.SALES
    if "PURCHASE" in v:
        return TallyVoucherType.PURCHASE
    if "RECEIPT" in v:
        return TallyVoucherType.RECEIPT
    if "PAYMENT" in v:
        return TallyVoucherType.PAYMENT
    if "CONTRA" in v:
        return TallyVoucherType.CONTRA
    if "CREDIT NOTE" in v or "CREDITNOTE" in v:
        return TallyVoucherType.CREDIT_NOTE
    if "DEBIT NOTE" in v or "DEBITNOTE" in v:
        return TallyVoucherType.DEBIT_NOTE
    if "JOURNAL" in v:
        return TallyVoucherType.JOURNAL
    return TallyVoucherType.OTHER


class TallyXMLParser:
    """Safe, tolerant parser for Tally XML exports."""

    def __init__(self, company_id: str = "") -> None:
        self.company_id = company_id
        self.errors: list[TallyValidationError] = []

    def parse(self, content: bytes) -> TallyImportBatch:
        """Parses Tally XML bytes safely using defusedxml."""
        if not content:
            raise ValidationAppError("Empty XML content", code="EMPTY_IMPORT_FILE")

        try:
            # defusedxml protects against entity expansion, external entities, etc.
            root = fromstring(content)
        except ParseError as exc:
            raise ValidationAppError(f"Malformed XML document: {exc}", code="INVALID_XML") from exc
        except Exception as exc:
            raise ValidationAppError(f"Failed to parse XML content: {exc}", code="INVALID_XML") from exc

        batch = TallyImportBatch(
            company_id=self.company_id,
            detected_format=TallyFormat.TALLY_XML,
        )

        # Locate DATA node or iterate children directly
        data_nodes = self._find_data_nodes(root)
        if not data_nodes:
            # The root itself might be the container
            data_nodes = [root]

        record_count = 0
        for data_node in data_nodes:
            for message_or_elem in data_node:
                clean_name = _clean_tag(message_or_elem.tag)
                elem_to_inspect = message_or_elem

                # If wrapped in <TALLYMESSAGE>, drill into its first substantive child
                if clean_name == "tallymessage":
                    sub_elems = [c for c in message_or_elem if isinstance(c.tag, str)]
                    if not sub_elems:
                        continue
                    elem_to_inspect = sub_elems[0]
                    clean_name = _clean_tag(elem_to_inspect.tag)

                record_count += 1
                if clean_name == "company":
                    batch.company_record = self._parse_company(elem_to_inspect)
                elif clean_name == "group":
                    group = self._parse_group(elem_to_inspect)
                    if group:
                        batch.groups.append(group)
                elif clean_name == "ledger":
                    ledger, party = self._parse_ledger_and_party(elem_to_inspect)
                    if ledger:
                        batch.ledgers.append(ledger)
                    if party:
                        batch.parties.append(party)
                elif clean_name == "stockitem":
                    item = self._parse_stock_item(elem_to_inspect)
                    if item:
                        batch.stock_items.append(item)
                elif clean_name == "voucher":
                    voucher = self._parse_voucher(elem_to_inspect, record_count)
                    if voucher:
                        batch.vouchers.append(voucher)

        batch.raw_record_count = record_count
        return batch

    def _find_data_nodes(self, root) -> list[Any]:
        """Navigates through <ENVELOPE> -> <BODY> -> <DATA> if present."""
        data_nodes = []
        body = _find_child(root, "body")
        if body is not None:
            data = _find_child(body, "data")
            if data is not None:
                data_nodes.append(data)
                return data_nodes

        # Check if root has direct <DATA>
        data = _find_child(root, "data")
        if data is not None:
            data_nodes.append(data)
            return data_nodes

        # Fallback: check if root has <TALLYMESSAGE>
        messages = _find_all_children(root, "tallymessage")
        if messages:
            data_nodes.append(root)

        return data_nodes

    def _parse_company(self, elem) -> TallyCompanyRecord:
        comp = TallyCompanyRecord()
        remotecmp = _find_child(elem, "remotecmpinfo.list")

        name = elem.attrib.get("NAME") or _get_text(elem, "name") or _get_text(elem, "companyname")
        if not name and remotecmp is not None:
            name = _get_text(remotecmp, "name")
        comp.name = name

        books_from_str = _get_text(elem, "startingfrom") or _get_text(elem, "booksfrom")
        if not books_from_str and remotecmp is not None:
            books_from_str = _get_text(remotecmp, "startingfrom")
        comp.books_from = parse_tally_date(books_from_str)

        comp.gstin = _get_text(elem, "gstin") or _get_text(elem, "partygstin")
        comp.pan = _get_text(elem, "panno") or _get_text(elem, "pan")
        comp.state = _get_text(elem, "statename")
        comp.address = _get_text(elem, "address")
        return comp

    def _parse_group(self, elem) -> TallyGroupRecord | None:
        name = elem.attrib.get("NAME") or _get_text(elem, "name")
        if not name:
            return None
        parent = _get_text(elem, "parent")
        is_revenue_str = _get_text(elem, "isrevenue").lower()
        is_revenue = True if is_revenue_str == "yes" else (False if is_revenue_str == "no" else None)
        return TallyGroupRecord(
            name=name,
            parent=parent if parent else None,
            is_revenue=is_revenue,
        )

    def _parse_ledger_and_party(self, elem) -> tuple[TallyLedgerRecord | None, TallyPartyRecord | None]:
        name = elem.attrib.get("NAME") or _get_text(elem, "name")
        if not name:
            return None, None

        parent = _get_text(elem, "parent")
        opening_bal_raw = _get_text(elem, "openingbalance")
        closing_bal_raw = _get_text(elem, "closingbalance")
        is_deemed_positive = _get_text(elem, "isdeemedpositive").strip().lower()

        opening_amt = parse_tally_amount(opening_bal_raw)
        is_debit = True
        if is_deemed_positive == "no":
            is_debit = False
        elif is_deemed_positive == "yes":
            is_debit = True
        else:
            # If not specified, negative amount in Tally ledger is credit (liability/income)
            is_debit = opening_amt >= Decimal(0)

        opening_amt = abs(opening_amt)
        closing_amt = abs(parse_tally_amount(closing_bal_raw)) if closing_bal_raw else None

        gstin = _get_text(elem, "partypanno") or _get_text(elem, "gstin") or _get_text(elem, "partygstin")
        pan = _get_text(elem, "panno") or _get_text(elem, "pan")
        state = _get_text(elem, "statename") or _get_text(elem, "ledstatename")
        address = _get_text(elem, "address")

        ledger = TallyLedgerRecord(
            name=name,
            parent_group=parent if parent else None,
            opening_balance=opening_amt,
            is_debit=is_debit,
            closing_balance=closing_amt,
            gstin=gstin if gstin else None,
            pan=pan if pan else None,
            state=state if state else None,
            address=address if address else None,
        )

        party = None
        parent_upper = parent.upper() if parent else ""
        if "SUNDRY DEBTOR" in parent_upper or "CUSTOMER" in parent_upper:
            party = TallyPartyRecord(
                name=name,
                party_type="CUSTOMER",
                gstin=gstin if gstin else None,
                pan=pan if pan else None,
                state=state if state else None,
                address=address if address else None,
                opening_balance=opening_amt,
                is_debit=is_debit,
            )
        elif "SUNDRY CREDITOR" in parent_upper or "VENDOR" in parent_upper or "SUPPLIER" in parent_upper:
            party = TallyPartyRecord(
                name=name,
                party_type="VENDOR",
                gstin=gstin if gstin else None,
                pan=pan if pan else None,
                state=state if state else None,
                address=address if address else None,
                opening_balance=opening_amt,
                is_debit=is_debit,
            )

        return ledger, party

    def _parse_stock_item(self, elem) -> TallyStockItemRecord | None:
        name = elem.attrib.get("NAME") or _get_text(elem, "name")
        if not name:
            return None
        parent = _get_text(elem, "parent")
        unit = _get_text(elem, "basetitle") or _get_text(elem, "baseunits")
        hsn_sac = _get_text(elem, "hsncode") or _get_text(elem, "hsnsac")
        tax_rate_str = _get_text(elem, "gstrate") or _get_text(elem, "rateoftax")
        tax_rate = parse_tally_amount(tax_rate_str) if tax_rate_str else None

        return TallyStockItemRecord(
            name=name,
            parent_group=parent if parent else None,
            unit=unit if unit else None,
            hsn_sac=hsn_sac if hsn_sac else None,
            tax_rate=tax_rate,
        )

    def _parse_voucher(self, elem, row_idx: int) -> TallyVoucherRecord | None:
        vtype_str = elem.attrib.get("VOUCHERTYPENAME") or _get_text(elem, "vouchertypename") or _get_text(elem, "vouchertype") or "Journal"
        norm_type = normalize_voucher_type(vtype_str)

        date_str = _get_text(elem, "date")
        voucher_date = parse_tally_date(date_str)
        if not voucher_date:
            voucher_date = date.today()

        v_number = _get_text(elem, "vouchernumber") or elem.attrib.get("VOUCHERNUMBER")
        if not v_number:
            v_number = f"VCH-{row_idx}"

        party_name = _get_text(elem, "partyledgername") or _get_text(elem, "partyname")
        ref_no = _get_text(elem, "reference")
        ref_date = parse_tally_date(_get_text(elem, "referencedate"))
        narration = _get_text(elem, "narration")

        # Parse Ledger Entries
        lines: list[TallyVoucherLine] = []
        all_ledger_entries = _find_all_children(elem, "allledgerentries.list") + _find_all_children(elem, "ledgerentries.list")

        for l_elem in all_ledger_entries:
            lname = _get_text(l_elem, "ledgername")
            if not lname:
                continue

            amt_raw = _get_text(l_elem, "amount")
            is_deemed = _get_text(l_elem, "isdeemedpositive").strip().lower()
            l_narration = _get_text(l_elem, "narration") or None

            raw_amt = parse_tally_amount(amt_raw)
            # Determine is_debit
            if is_deemed == "yes":
                is_debit = True
            elif is_deemed == "no":
                is_debit = False
            else:
                # If negative, Tally marks debit as negative amount
                is_debit = raw_amt < Decimal(0)

            abs_amt = abs(raw_amt)

            # Check nested inventory in ledger entry
            inventory_items: list[TallyInventoryLine] = []
            inv_entries = _find_all_children(l_elem, "allinventoryentries.list") + _find_all_children(l_elem, "inventoryentries.list")
            for inv_elem in inv_entries:
                item_name = _get_text(inv_elem, "stockitemname")
                if item_name:
                    qty = abs(parse_tally_amount(_get_text(inv_elem, "actualqty") or _get_text(inv_elem, "billedqty"), Decimal(1)))
                    rate = abs(parse_tally_amount(_get_text(inv_elem, "rate"), Decimal(0)))
                    inv_amt = abs(parse_tally_amount(_get_text(inv_elem, "amount"), Decimal(0)))
                    unit = _get_text(inv_elem, "unit") or None
                    hsn = _get_text(inv_elem, "hsncode") or None
                    inventory_items.append(
                        TallyInventoryLine(
                            item_name=item_name,
                            quantity=qty,
                            rate=rate,
                            amount=inv_amt,
                            unit=unit,
                            hsn_sac=hsn,
                        )
                    )

            lines.append(
                TallyVoucherLine(
                    ledger_name=lname,
                    amount=abs_amt,
                    is_debit=is_debit,
                    narration=l_narration,
                    inventory_items=inventory_items,
                )
            )

        # Also check top-level inventory entries
        top_inventory: list[TallyInventoryLine] = []
        top_inv_entries = _find_all_children(elem, "allinventoryentries.list") + _find_all_children(elem, "inventoryentries.list")
        for inv_elem in top_inv_entries:
            item_name = _get_text(inv_elem, "stockitemname")
            if item_name:
                qty = abs(parse_tally_amount(_get_text(inv_elem, "actualqty") or _get_text(inv_elem, "billedqty"), Decimal(1)))
                rate = abs(parse_tally_amount(_get_text(inv_elem, "rate"), Decimal(0)))
                inv_amt = abs(parse_tally_amount(_get_text(inv_elem, "amount"), Decimal(0)))
                unit = _get_text(inv_elem, "unit") or None
                hsn = _get_text(inv_elem, "hsncode") or None
                top_inventory.append(
                    TallyInventoryLine(
                        item_name=item_name,
                        quantity=qty,
                        rate=rate,
                        amount=inv_amt,
                        unit=unit,
                        hsn_sac=hsn,
                    )
                )

        # Total amount is max of debit sum / credit sum
        debit_sum = sum((l.amount for l in lines if l.is_debit), Decimal(0))
        credit_sum = sum((l.amount for l in lines if not l.is_debit), Decimal(0))
        total_amount = max(debit_sum, credit_sum)

        # Tax breakdown calculation
        tax_breakdown = self._extract_tax_breakdown(lines, norm_type, total_amount)

        # Party name fallback if party ledger not specified
        if not party_name and lines:
            if norm_type == TallyVoucherType.SALES:
                # Sales party is usually the debit line
                debit_lines = [l for l in lines if l.is_debit]
                if debit_lines:
                    party_name = debit_lines[0].ledger_name
            elif norm_type == TallyVoucherType.PURCHASE:
                # Purchase party is usually the credit line
                credit_lines = [l for l in lines if not l.is_debit]
                if credit_lines:
                    party_name = credit_lines[0].ledger_name
            elif norm_type == TallyVoucherType.RECEIPT:
                # Receipt party is credit line
                credit_lines = [l for l in lines if not l.is_debit]
                if credit_lines:
                    party_name = credit_lines[0].ledger_name
            elif norm_type == TallyVoucherType.PAYMENT:
                # Payment party is debit line
                debit_lines = [l for l in lines if l.is_debit]
                if debit_lines:
                    party_name = debit_lines[0].ledger_name

        voucher = TallyVoucherRecord(
            voucher_type=vtype_str,
            normalized_type=norm_type,
            voucher_number=v_number,
            voucher_date=voucher_date,
            party_name=party_name if party_name else None,
            reference_no=ref_no if ref_no else None,
            reference_date=ref_date,
            narration=narration if narration else None,
            lines=lines,
            inventory=top_inventory,
            total_amount=total_amount,
            tax_breakdown=tax_breakdown,
        )
        return voucher

    def _extract_tax_breakdown(
        self, lines: list[TallyVoucherLine], norm_type: TallyVoucherType, total_amount: Decimal
    ) -> TallyTaxBreakdown:
        cgst = Decimal(0)
        sgst = Decimal(0)
        igst = Decimal(0)
        cess = Decimal(0)

        for line in lines:
            lname = line.ledger_name.upper()
            if "CGST" in lname or "CENTRAL GST" in lname or "CENTRAL TAX" in lname:
                cgst += line.amount
            elif "SGST" in lname or "STATE GST" in lname or "STATE TAX" in lname or "UTGST" in lname:
                sgst += line.amount
            elif "IGST" in lname or "INTEGRATED GST" in lname or "INTEGRATED TAX" in lname:
                igst += line.amount
            elif "CESS" in lname:
                cess += line.amount

        total_tax = cgst + sgst + igst + cess
        taxable = max(Decimal(0), total_amount - total_tax) if (total_tax > 0 and total_amount >= total_tax) else total_amount

        return TallyTaxBreakdown(
            taxable_amount=taxable,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            cess_amount=cess,
            total_tax=total_tax,
        )

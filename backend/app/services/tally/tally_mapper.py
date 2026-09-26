from datetime import datetime, timezone
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.ledger import Ledger
from app.models.tally_mapping_template import TallyMappingTemplate
from app.models.vendor import Vendor
from app.services.tally.tally_models import (
    MappingStatus,
    TallyImportBatch,
    TallyMappingRule,
    TallyVoucherType,
)


def normalize_name(s: str) -> str:
    if not s:
        return ""
    # remove punctuation, multiple spaces
    cleaned = re.sub(r"[^\w\s]", " ", s).lower().strip()
    return re.sub(r"\s+", " ", cleaned)


# Standard Ledger Aliases in Indian Accounting / Tally
STANDARD_LEDGER_ALIASES: dict[str, list[str]] = {
    "sales": ["sales", "sales account", "sales revenue", "revenue from operations", "domestic sales"],
    "purchase": ["purchase", "purchases", "purchase account", "purchase expense", "domestic purchases"],
    "output_cgst": ["output cgst", "cgst output", "central gst output", "cgst payable", "output central tax"],
    "output_sgst": ["output sgst", "sgst output", "state gst output", "sgst payable", "output state tax"],
    "output_igst": ["output igst", "igst output", "integrated gst output", "igst payable", "output integrated tax"],
    "input_cgst": ["input cgst", "cgst input", "central gst input", "cgst receivable", "input central tax"],
    "input_sgst": ["input sgst", "sgst input", "state gst input", "sgst receivable", "input state tax"],
    "input_igst": ["input igst", "igst input", "integrated gst input", "igst receivable", "input integrated tax"],
    "round_off": ["round off", "round off account", "rounding off"],
    "cash": ["cash", "cash in hand", "petty cash"],
    "bank": ["bank", "bank account", "hdfc bank", "sbi bank", "icici bank", "axis bank"],
}


class TallyMapper:
    """Intelligent Ledger, Party, and Voucher mapping for Tally import adapter."""

    def __init__(self, db: AsyncSession, company_id: uuid.UUID) -> None:
        self.db = db
        self.company_id = company_id
        self._customers_by_gstin: dict[str, Customer] = {}
        self._customers_by_pan: dict[str, Customer] = {}
        self._customers_by_name: dict[str, Customer] = {}

        self._vendors_by_gstin: dict[str, Vendor] = {}
        self._vendors_by_pan: dict[str, Vendor] = {}
        self._vendors_by_name: dict[str, Vendor] = {}

        self._ledgers_by_name: dict[str, Ledger] = {}
        self._ledgers_by_id: dict[str, Ledger] = {}
        self._loaded = False

    async def load_cache(self) -> None:
        if self._loaded:
            return

        # 1. Customers
        c_res = await self.db.execute(select(Customer).where(Customer.company_id == self.company_id))
        for c in c_res.scalars().all():
            if c.gstin:
                self._customers_by_gstin[c.gstin.strip().upper()] = c
            if c.pan:
                self._customers_by_pan[c.pan.strip().upper()] = c
            self._customers_by_name[normalize_name(c.name)] = c

        # 2. Vendors
        v_res = await self.db.execute(select(Vendor).where(Vendor.company_id == self.company_id))
        for v in v_res.scalars().all():
            if v.gstin:
                self._vendors_by_gstin[v.gstin.strip().upper()] = v
            if v.pan:
                self._vendors_by_pan[v.pan.strip().upper()] = v
            self._vendors_by_name[normalize_name(v.name)] = v

        # 3. Ledgers
        l_res = await self.db.execute(select(Ledger).where(Ledger.company_id == self.company_id))
        for l in l_res.scalars().all():
            self._ledgers_by_name[normalize_name(l.name)] = l
            self._ledgers_by_id[str(l.id)] = l

        self._loaded = True

    async def map_batch(
        self,
        batch: TallyImportBatch,
        template_rules: dict[str, Any] | None = None,
        manual_mappings: dict[str, str] | None = None,
    ) -> list[TallyMappingRule]:
        await self.load_cache()

        template_ledgers = (template_rules or {}).get("ledgers", []) if template_rules else []
        template_parties = (template_rules or {}).get("parties", []) if template_rules else []

        # Convert template rules to lookup dicts
        tpl_ledger_map: dict[str, tuple[str, str]] = {}
        for r in template_ledgers:
            src = normalize_name(r.get("source_name", ""))
            if src and r.get("target_id"):
                tpl_ledger_map[src] = (r["target_id"], r.get("target_name", ""))

        tpl_party_map: dict[str, tuple[str, str]] = {}
        for r in template_parties:
            src = normalize_name(r.get("source_name", ""))
            if src and r.get("target_id"):
                tpl_party_map[src] = (r["target_id"], r.get("target_name", ""))

        manual = manual_mappings or {}

        rules: list[TallyMappingRule] = []
        seen_keys: set[tuple[str, str]] = set()

        # 1. Map Ledgers mentioned in Vouchers and Ledgers list
        all_ledger_names: set[str] = set()
        for l in batch.ledgers:
            all_ledger_names.add(l.name)
        for v in batch.vouchers:
            for line in v.lines:
                all_ledger_names.add(line.ledger_name)

        for l_name in sorted(all_ledger_names):
            norm_l = normalize_name(l_name)
            key = ("LEDGER", norm_l)
            if key in seen_keys or not norm_l:
                continue
            seen_keys.add(key)

            # Check manual mapping first
            if l_name in manual or norm_l in manual:
                target_id = manual.get(l_name) or manual.get(norm_l)
                target_ledger = self._ledgers_by_id.get(target_id) if target_id else None
                rules.append(
                    TallyMappingRule(
                        source_type="LEDGER",
                        source_name=l_name,
                        target_id=target_id,
                        target_name=target_ledger.name if target_ledger else target_id,
                        status=MappingStatus.MANUALLY_MAPPED,
                        confidence=1.0,
                    )
                )
                continue

            # Check template rule
            if norm_l in tpl_ledger_map:
                t_id, t_name = tpl_ledger_map[norm_l]
                rules.append(
                    TallyMappingRule(
                        source_type="LEDGER",
                        source_name=l_name,
                        target_id=t_id,
                        target_name=t_name,
                        status=MappingStatus.AUTO_MAPPED,
                        confidence=1.0,
                        notes="Template match",
                    )
                )
                continue

            # Check exact normalized match in system Chart of Accounts
            if norm_l in self._ledgers_by_name:
                matched = self._ledgers_by_name[norm_l]
                rules.append(
                    TallyMappingRule(
                        source_type="LEDGER",
                        source_name=l_name,
                        target_id=str(matched.id),
                        target_name=matched.name,
                        status=MappingStatus.AUTO_MAPPED,
                        confidence=1.0,
                        notes="Exact CoA match",
                    )
                )
                continue

            # Check standard alias match
            alias_matched = self._match_standard_alias(norm_l)
            if alias_matched:
                rules.append(
                    TallyMappingRule(
                        source_type="LEDGER",
                        source_name=l_name,
                        target_id=str(alias_matched.id),
                        target_name=alias_matched.name,
                        status=MappingStatus.AUTO_MAPPED,
                        confidence=0.9,
                        notes="Standard accounting alias match",
                    )
                )
                continue

            # Unmapped ledger -> NEW / REVIEW_REQUIRED
            rules.append(
                TallyMappingRule(
                    source_type="LEDGER",
                    source_name=l_name,
                    target_id=None,
                    target_name=None,
                    status=MappingStatus.NEW,
                    confidence=0.0,
                    notes="New ledger - will be created in Chart of Accounts on import",
                )
            )

        # 2. Map Parties
        all_parties: dict[str, dict[str, Any]] = {}
        for p in batch.parties:
            all_parties[p.name] = {
                "name": p.name,
                "party_type": p.party_type,
                "gstin": p.gstin,
                "pan": p.pan,
            }

        for v in batch.vouchers:
            if v.party_name and v.party_name not in all_parties:
                p_type = "CUSTOMER" if v.normalized_type == TallyVoucherType.SALES else "VENDOR"
                all_parties[v.party_name] = {
                    "name": v.party_name,
                    "party_type": p_type,
                    "gstin": None,
                    "pan": None,
                }

        for p_name, p_info in sorted(all_parties.items()):
            norm_p = normalize_name(p_name)
            key = ("PARTY", norm_p)
            if key in seen_keys or not norm_p:
                continue
            seen_keys.add(key)

            # Manual mapping
            if p_name in manual or norm_p in manual:
                t_id = manual.get(p_name) or manual.get(norm_p)
                rules.append(
                    TallyMappingRule(
                        source_type="PARTY",
                        source_name=p_name,
                        target_id=t_id,
                        target_name=t_id,
                        status=MappingStatus.MANUALLY_MAPPED,
                        confidence=1.0,
                    )
                )
                continue

            # Template match
            if norm_p in tpl_party_map:
                t_id, t_name = tpl_party_map[norm_p]
                rules.append(
                    TallyMappingRule(
                        source_type="PARTY",
                        source_name=p_name,
                        target_id=t_id,
                        target_name=t_name,
                        status=MappingStatus.AUTO_MAPPED,
                        confidence=1.0,
                        notes="Template match",
                    )
                )
                continue

            # Match priority 1: GSTIN
            gstin = (p_info.get("gstin") or "").strip().upper()
            if gstin:
                if gstin in self._customers_by_gstin:
                    c = self._customers_by_gstin[gstin]
                    rules.append(
                        TallyMappingRule(
                            source_type="PARTY",
                            source_name=p_name,
                            target_id=str(c.id),
                            target_name=c.name,
                            status=MappingStatus.AUTO_MAPPED,
                            confidence=1.0,
                            notes=f"Matched Customer by GSTIN {gstin}",
                        )
                    )
                    continue
                if gstin in self._vendors_by_gstin:
                    v = self._vendors_by_gstin[gstin]
                    rules.append(
                        TallyMappingRule(
                            source_type="PARTY",
                            source_name=p_name,
                            target_id=str(v.id),
                            target_name=v.name,
                            status=MappingStatus.AUTO_MAPPED,
                            confidence=1.0,
                            notes=f"Matched Vendor by GSTIN {gstin}",
                        )
                    )
                    continue

            # Match priority 2: PAN
            pan = (p_info.get("pan") or "").strip().upper()
            if pan:
                if pan in self._customers_by_pan:
                    c = self._customers_by_pan[pan]
                    rules.append(
                        TallyMappingRule(
                            source_type="PARTY",
                            source_name=p_name,
                            target_id=str(c.id),
                            target_name=c.name,
                            status=MappingStatus.AUTO_MAPPED,
                            confidence=0.95,
                            notes=f"Matched Customer by PAN {pan}",
                        )
                    )
                    continue
                if pan in self._vendors_by_pan:
                    v = self._vendors_by_pan[pan]
                    rules.append(
                        TallyMappingRule(
                            source_type="PARTY",
                            source_name=p_name,
                            target_id=str(v.id),
                            target_name=v.name,
                            status=MappingStatus.AUTO_MAPPED,
                            confidence=0.95,
                            notes=f"Matched Vendor by PAN {pan}",
                        )
                    )
                    continue

            # Match priority 3: Exact normalized name
            if norm_p in self._customers_by_name:
                c = self._customers_by_name[norm_p]
                rules.append(
                    TallyMappingRule(
                        source_type="PARTY",
                        source_name=p_name,
                        target_id=str(c.id),
                        target_name=c.name,
                        status=MappingStatus.AUTO_MAPPED,
                        confidence=0.9,
                        notes="Matched Customer by name",
                    )
                )
                continue

            if norm_p in self._vendors_by_name:
                v = self._vendors_by_name[norm_p]
                rules.append(
                    TallyMappingRule(
                        source_type="PARTY",
                        source_name=p_name,
                        target_id=str(v.id),
                        target_name=v.name,
                        status=MappingStatus.AUTO_MAPPED,
                        confidence=0.9,
                        notes="Matched Vendor by name",
                    )
                )
                continue

            # Otherwise: NEW Party
            p_type = p_info.get("party_type", "CUSTOMER")
            rules.append(
                TallyMappingRule(
                    source_type="PARTY",
                    source_name=p_name,
                    target_id=None,
                    target_name=None,
                    status=MappingStatus.NEW,
                    confidence=0.0,
                    notes=f"New {p_type} will be created during import",
                )
            )

        return rules

    def _match_standard_alias(self, norm_name: str) -> Ledger | None:
        for alias_key, alias_phrases in STANDARD_LEDGER_ALIASES.items():
            if norm_name in alias_phrases:
                # Look for corresponding ledger in loaded CoA
                for phrase in alias_phrases:
                    if phrase in self._ledgers_by_name:
                        return self._ledgers_by_name[phrase]
                # If specific name not matched, look by keyword in existing ledger names
                for l_norm, ledger in self._ledgers_by_name.items():
                    if any(p in l_norm for p in alias_phrases):
                        return ledger
        return None


class TallyMappingTemplateService:
    """Service to create, update, and retrieve company-scoped mapping templates."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_templates(self, company_id: uuid.UUID) -> list[TallyMappingTemplate]:
        result = await self.db.execute(
            select(TallyMappingTemplate)
            .where(TallyMappingTemplate.company_id == company_id)
            .order_by(TallyMappingTemplate.name.asc())
        )
        return list(result.scalars().all())

    async def get_template(self, company_id: uuid.UUID, template_id: uuid.UUID) -> TallyMappingTemplate | None:
        result = await self.db.execute(
            select(TallyMappingTemplate).where(
                TallyMappingTemplate.id == template_id,
                TallyMappingTemplate.company_id == company_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_template(
        self,
        company_id: uuid.UUID,
        name: str,
        rules: dict[str, Any],
        created_by: uuid.UUID,
    ) -> TallyMappingTemplate:
        template = TallyMappingTemplate(
            company_id=company_id,
            name=name,
            version=1,
            rules=rules,
            created_by=created_by,
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def update_template(
        self,
        company_id: uuid.UUID,
        template_id: uuid.UUID,
        name: str | None,
        rules: dict[str, Any] | None,
    ) -> TallyMappingTemplate | None:
        template = await self.get_template(company_id, template_id)
        if not template:
            return None
        if name:
            template.name = name
        if rules is not None:
            template.rules = rules
            template.version += 1
        template.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return template

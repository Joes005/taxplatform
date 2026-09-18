"""Deterministic duplicate-detection checksum for bank transactions
(PHASE6 §15). A hash, not a heuristic — the same five inputs always
produce the same checksum, so two rows describing the same real-world
transaction collide and are caught, both within one import batch and
against previously committed transactions (the DB unique index on
`(company_id, bank_account_id, checksum)` is the final backstop).
"""

import hashlib
import uuid
from datetime import date
from decimal import Decimal


def compute_bank_transaction_checksum(
    *,
    company_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    transaction_date: date,
    amount: Decimal,
    reference_number: str | None,
    description: str,
) -> str:
    parts = [
        str(company_id),
        str(bank_account_id),
        transaction_date.isoformat(),
        str(amount),
        (reference_number or "").strip().lower(),
        description.strip().lower(),
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest

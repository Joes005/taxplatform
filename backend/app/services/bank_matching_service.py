"""Deterministic bank-transaction match-candidate generation and scoring
(PHASE6 §18-20). No AI, no fuzzy ML — a fixed point system over exact
signals, so the same inputs always produce the same score and the same
candidates. Amount is used as the base filter (a candidate must match the
bank transaction's amount exactly to be considered at all) rather than as
a scored signal on its own — this is deliberately conservative: two
transactions merely sharing an amount are never enough by themselves to
imply they're the same transaction (§20), so every amount-matched
candidate is surfaced for a human to choose between rather than the
engine picking the closest one.
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_enums import (
    BankMatchSourceType,
    BankMatchType,
    BankTransactionReconciliationStatus,
    BankTransactionType,
)
from app.models.bank_transaction import BankTransaction
from app.models.customer import Customer
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.accounting_enums import PartyType, TransactionStatus
from app.models.user import User
from app.models.vendor import Vendor
from app.repositories.bank_transaction_match_repository import BankTransactionMatchRepository
from app.repositories.bank_transaction_repository import BankTransactionRepository
from app.schemas.bank_match import BankMatchCandidate, ManualMatchCreate
from app.services.auth_service import RequestMeta

DATE_WINDOW_DAYS = 10

SCORE_EXACT_AMOUNT = 40
SCORE_EXACT_REFERENCE = 30
SCORE_EXACT_DATE = 15
SCORE_COUNTERPARTY_MATCH = 10
SCORE_DESCRIPTION_MATCH = 5

STRONG_MATCH_THRESHOLD = 90
MATCH_SUGGESTED_THRESHOLD = 70
REVIEW_REQUIRED_THRESHOLD = 50


def confidence_label(score: int) -> str:
    if score >= STRONG_MATCH_THRESHOLD:
        return "STRONG_MATCH"
    if score >= MATCH_SUGGESTED_THRESHOLD:
        return "MATCH_SUGGESTED"
    if score >= REVIEW_REQUIRED_THRESHOLD:
        return "REVIEW_REQUIRED"
    return "NO_MATCH"


@dataclass
class _RawCandidate:
    source_type: BankMatchSourceType
    source_id: uuid.UUID
    label: str
    source_date: date
    source_amount: Decimal
    reference_number: str | None
    counterparty_name: str | None
    narration: str | None


class BankMatchingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.matches = BankTransactionMatchRepository(db)

    async def find_candidates(
        self, company_id: uuid.UUID, bank_transaction: BankTransaction, *, limit: int = 10
    ) -> list[BankMatchCandidate]:
        window_start = bank_transaction.transaction_date - timedelta(days=DATE_WINDOW_DAYS)
        window_end = bank_transaction.transaction_date + timedelta(days=DATE_WINDOW_DAYS)

        raw_candidates: list[_RawCandidate] = []
        if bank_transaction.transaction_type == BankTransactionType.CREDIT:
            raw_candidates += await self._find_receipts(company_id, bank_transaction.amount, window_start, window_end)
        else:
            raw_candidates += await self._find_payments(company_id, bank_transaction.amount, window_start, window_end)
        raw_candidates += await self._find_journal_lines(
            company_id, bank_transaction, window_start, window_end
        )

        scored: list[BankMatchCandidate] = []
        for candidate in raw_candidates:
            if await self.matches.has_active_match(candidate.source_type, candidate.source_id):
                continue  # already fully claimed by another bank transaction

            score = SCORE_EXACT_AMOUNT
            if (
                candidate.reference_number
                and bank_transaction.reference_number
                and candidate.reference_number.strip().lower() == bank_transaction.reference_number.strip().lower()
            ):
                score += SCORE_EXACT_REFERENCE
            if candidate.source_date == bank_transaction.transaction_date:
                score += SCORE_EXACT_DATE
            description = bank_transaction.normalized_description or ""
            if candidate.counterparty_name and candidate.counterparty_name.lower() in description:
                score += SCORE_COUNTERPARTY_MATCH
            if candidate.narration:
                narration_words = set(candidate.narration.lower().split())
                if narration_words & set(description.split()):
                    score += SCORE_DESCRIPTION_MATCH

            scored.append(
                BankMatchCandidate(
                    source_type=candidate.source_type,
                    source_id=candidate.source_id,
                    label=candidate.label,
                    source_date=candidate.source_date,
                    source_amount=candidate.source_amount,
                    counterparty_name=candidate.counterparty_name,
                    reference_number=candidate.reference_number,
                    score=score,
                    confidence=confidence_label(score),
                )
            )

        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:limit]

    async def run_auto_matching(
        self,
        company_id: uuid.UUID,
        transactions: list[BankTransaction],
        current_user: User,
        meta: RequestMeta,
    ) -> dict[str, int]:
        """Auto-matches only the unambiguous, strong case (PHASE6 §18-20):
        exactly one candidate at the top score, and that score clears
        STRONG_MATCH_THRESHOLD. Everything else is left for a human —
        MATCH_SUGGESTED when there's a decent single lead, REVIEW_REQUIRED
        when candidates are weak or tied, UNMATCHED when there's nothing
        at all. Never called on a transaction that already has an active
        match (only truly-open transactions are passed in).
        """
        from app.services.bank_match_service import BankMatchService

        match_service = BankMatchService(self.db)
        counts = {"auto_matched": 0, "suggested": 0, "review_required": 0, "unmatched": 0}

        for transaction in transactions:
            candidates = await self.find_candidates(company_id, transaction)
            if not candidates:
                transaction.reconciliation_status = BankTransactionReconciliationStatus.UNMATCHED
                counts["unmatched"] += 1
                continue

            top = candidates[0]
            tied_for_top = sum(1 for c in candidates if c.score == top.score)

            if top.score >= STRONG_MATCH_THRESHOLD and tied_for_top == 1:
                await match_service.create_manual_match(
                    company_id,
                    transaction.id,
                    ManualMatchCreate(
                        source_type=top.source_type,
                        source_id=top.source_id,
                        matched_amount=transaction.amount,
                        notes=f"Auto-matched (score {top.score})",
                    ),
                    current_user,
                    meta,
                    match_type=BankMatchType.AUTO,
                )
                counts["auto_matched"] += 1
            elif top.score >= MATCH_SUGGESTED_THRESHOLD:
                transaction.reconciliation_status = BankTransactionReconciliationStatus.MATCH_SUGGESTED
                counts["suggested"] += 1
            else:
                transaction.reconciliation_status = BankTransactionReconciliationStatus.REVIEW_REQUIRED
                counts["review_required"] += 1

        await self.db.flush()
        return counts

    async def _find_receipts(
        self, company_id: uuid.UUID, amount: Decimal, window_start: date, window_end: date
    ) -> list[_RawCandidate]:
        result = await self.db.execute(
            select(Receipt, Customer.name)
            .join(Customer, Customer.id == Receipt.customer_id)
            .where(
                Receipt.company_id == company_id,
                Receipt.status == TransactionStatus.POSTED,
                Receipt.amount == amount,
                Receipt.receipt_date >= window_start,
                Receipt.receipt_date <= window_end,
            )
        )
        return [
            _RawCandidate(
                source_type=BankMatchSourceType.RECEIPT,
                source_id=receipt.id,
                label=f"Receipt #{receipt.receipt_number}",
                source_date=receipt.receipt_date,
                source_amount=receipt.amount,
                reference_number=receipt.reference_number,
                counterparty_name=customer_name,
                narration=None,
            )
            for receipt, customer_name in result.all()
        ]

    async def _find_payments(
        self, company_id: uuid.UUID, amount: Decimal, window_start: date, window_end: date
    ) -> list[_RawCandidate]:
        result = await self.db.execute(
            select(Payment).where(
                Payment.company_id == company_id,
                Payment.status == TransactionStatus.POSTED,
                Payment.amount == amount,
                Payment.payment_date >= window_start,
                Payment.payment_date <= window_end,
            )
        )
        payments = list(result.scalars().all())

        vendor_ids = [p.party_id for p in payments if p.party_type == PartyType.VENDOR and p.party_id]
        vendor_names: dict[str, str] = {}
        if vendor_ids:
            vendor_result = await self.db.execute(select(Vendor.id, Vendor.name).where(Vendor.id.in_(vendor_ids)))
            vendor_names = {str(vid): name for vid, name in vendor_result.all()}

        return [
            _RawCandidate(
                source_type=BankMatchSourceType.PAYMENT,
                source_id=payment.id,
                label=f"Payment #{payment.payment_number}",
                source_date=payment.payment_date,
                source_amount=payment.amount,
                reference_number=payment.reference_number,
                counterparty_name=vendor_names.get(str(payment.party_id)) if payment.party_id else None,
                narration=payment.notes,
            )
            for payment in payments
        ]

    async def _find_journal_lines(
        self, company_id: uuid.UUID, bank_transaction: BankTransaction, window_start: date, window_end: date
    ) -> list[_RawCandidate]:
        """A journal entry that debits the bank's own ledger is money in
        (matches a CREDIT bank transaction); one that credits it is money
        out (matches a DEBIT bank transaction) — standard double-entry
        convention. Only applies when the bank account has a linked
        Ledger (PHASE6 §7)."""
        from app.repositories.bank_account_repository import BankAccountRepository

        account = await BankAccountRepository(self.db).get_by_id_for_company(
            bank_transaction.bank_account_id, company_id
        )
        if account is None or account.ledger_id is None:
            return []

        amount_column = (
            JournalEntryLine.debit_amount
            if bank_transaction.transaction_type == BankTransactionType.CREDIT
            else JournalEntryLine.credit_amount
        )

        result = await self.db.execute(
            select(JournalEntry, JournalEntryLine)
            .join(JournalEntryLine, JournalEntryLine.journal_entry_id == JournalEntry.id)
            .where(
                JournalEntry.company_id == company_id,
                JournalEntry.status == TransactionStatus.POSTED,
                JournalEntryLine.ledger_id == account.ledger_id,
                amount_column == bank_transaction.amount,
                JournalEntry.journal_date >= window_start,
                JournalEntry.journal_date <= window_end,
                or_(
                    JournalEntry.source_reference.is_(None),
                    and_(
                        ~JournalEntry.source_reference.like("receipt:%"),
                        ~JournalEntry.source_reference.like("payment:%"),
                    ),
                ),
            )
        )
        return [
            _RawCandidate(
                source_type=BankMatchSourceType.JOURNAL_ENTRY,
                source_id=entry.id,
                label=f"Journal #{entry.journal_number}",
                source_date=entry.journal_date,
                source_amount=bank_transaction.amount,
                reference_number=None,
                counterparty_name=None,
                narration=entry.narration or line.description,
            )
            for entry, line in result.all()
        ]

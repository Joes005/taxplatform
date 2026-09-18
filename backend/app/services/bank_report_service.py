"""Read-only bank reconciliation reporting (PHASE6 §44). Reuses the same
transaction/match repositories the workflow itself uses, so a report can
never show numbers the reconciliation screen itself couldn't produce.
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_enums import BankMatchSourceType, BankMatchStatus, BankTransactionReconciliationStatus
from app.models.bank_transaction_match import BankTransactionMatch
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.accounting_enums import TransactionStatus
from app.repositories.bank_transaction_match_repository import BankTransactionMatchRepository
from app.repositories.bank_transaction_repository import BankTransactionRepository
from app.schemas.bank_reports import MatchReportRow, UnmatchedBankTransactionRow, UnmatchedBookTransactionRow

_UNMATCHED_BANK_STATUSES = {
    BankTransactionReconciliationStatus.UNMATCHED,
    BankTransactionReconciliationStatus.MATCH_SUGGESTED,
    BankTransactionReconciliationStatus.REVIEW_REQUIRED,
    BankTransactionReconciliationStatus.PARTIALLY_MATCHED,
}


class BankReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.transactions = BankTransactionRepository(db)
        self.matches = BankTransactionMatchRepository(db)

    async def unmatched_bank_transactions(
        self, company_id: uuid.UUID, bank_account_id: uuid.UUID, *, period_start: date, period_end: date
    ) -> list[UnmatchedBankTransactionRow]:
        transactions = await self.transactions.list_for_account_period(
            company_id, bank_account_id, period_start=period_start, period_end=period_end
        )
        return [
            UnmatchedBankTransactionRow(
                bank_transaction_id=t.id,
                transaction_date=t.transaction_date,
                description=t.description,
                reference_number=t.reference_number,
                amount=t.amount,
                status=t.reconciliation_status,
            )
            for t in transactions
            if t.reconciliation_status in _UNMATCHED_BANK_STATUSES
        ]

    async def unmatched_book_transactions(
        self, company_id: uuid.UUID, ledger_id: uuid.UUID, *, period_start: date, period_end: date
    ) -> list[UnmatchedBookTransactionRow]:
        rows: list[UnmatchedBookTransactionRow] = []

        receipts = (
            await self.db.execute(
                select(Receipt).where(
                    Receipt.company_id == company_id,
                    Receipt.ledger_id == ledger_id,
                    Receipt.status == TransactionStatus.POSTED,
                    Receipt.receipt_date >= period_start,
                    Receipt.receipt_date <= period_end,
                )
            )
        ).scalars().all()
        for r in receipts:
            matched = await self.matches.sum_active_matched_amount_for_source(BankMatchSourceType.RECEIPT, r.id)
            if matched < r.amount:
                rows.append(
                    UnmatchedBookTransactionRow(
                        source_type=BankMatchSourceType.RECEIPT,
                        source_id=r.id,
                        source_label=f"Receipt #{r.receipt_number}",
                        source_date=r.receipt_date,
                        amount=r.amount,
                        unmatched_amount=r.amount - matched,
                    )
                )

        payments = (
            await self.db.execute(
                select(Payment).where(
                    Payment.company_id == company_id,
                    Payment.ledger_id == ledger_id,
                    Payment.status == TransactionStatus.POSTED,
                    Payment.payment_date >= period_start,
                    Payment.payment_date <= period_end,
                )
            )
        ).scalars().all()
        for p in payments:
            matched = await self.matches.sum_active_matched_amount_for_source(BankMatchSourceType.PAYMENT, p.id)
            if matched < p.amount:
                rows.append(
                    UnmatchedBookTransactionRow(
                        source_type=BankMatchSourceType.PAYMENT,
                        source_id=p.id,
                        source_label=f"Payment #{p.payment_number}",
                        source_date=p.payment_date,
                        amount=p.amount,
                        unmatched_amount=p.amount - matched,
                    )
                )

        return sorted(rows, key=lambda r: r.source_date)

    async def matching_report(
        self, company_id: uuid.UUID, bank_account_id: uuid.UUID, *, period_start: date, period_end: date
    ) -> list[MatchReportRow]:
        transactions = await self.transactions.list_for_account_period(
            company_id, bank_account_id, period_start=period_start, period_end=period_end
        )
        rows: list[MatchReportRow] = []
        for t in transactions:
            result = await self.db.execute(
                select(BankTransactionMatch).where(
                    BankTransactionMatch.bank_transaction_id == t.id,
                    BankTransactionMatch.status == BankMatchStatus.ACTIVE,
                )
            )
            for match in result.scalars().all():
                rows.append(
                    MatchReportRow(
                        match_id=match.id,
                        bank_transaction_id=t.id,
                        bank_transaction_date=t.transaction_date,
                        bank_transaction_description=t.description,
                        source_type=match.source_type,
                        source_id=match.source_id,
                        matched_amount=match.matched_amount,
                        match_type=match.match_type,
                        match_score=match.match_score,
                        matched_by=match.matched_by,
                        matched_at=match.matched_at,
                    )
                )
        return rows

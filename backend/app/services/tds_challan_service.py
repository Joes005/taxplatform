import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.tds_challan import TDSChallan, TDSChallanAllocation
from app.models.tds_enums import TDSChallanStatus, TDSTransactionStatus
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.tds_challan_repository import TDSChallanRepository
from app.repositories.tds_transaction_repository import TDSTransactionRepository
from app.schemas.tds_challan import TDSChallanAllocateRequest, TDSChallanCreate, TDSChallanUpdate
from app.services.accounting_calculation_service import round_money
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

# Forward-only status transitions a plain PATCH may make. RECONCILED is
# reachable only through the reconciliation flow (PHASE5 section 21), not
# through this map — it reflects a *computed* match against allocations,
# not something a user should be able to just declare true.
_ALLOWED_STATUS_TRANSITIONS: dict[TDSChallanStatus, set[TDSChallanStatus]] = {
    TDSChallanStatus.DRAFT: {TDSChallanStatus.GENERATED, TDSChallanStatus.CANCELLED},
    TDSChallanStatus.GENERATED: {TDSChallanStatus.PAID, TDSChallanStatus.CANCELLED},
    TDSChallanStatus.PAID: {TDSChallanStatus.CANCELLED},
    TDSChallanStatus.RECONCILED: set(),
    TDSChallanStatus.CANCELLED: set(),
}


class TDSChallanService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TDSChallanRepository(db)
        self.transactions = TDSTransactionRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: TDSChallanCreate, current_user: User, meta: RequestMeta
    ) -> TDSChallan:
        financial_year = await self.fy_repo.get_by_id_for_company(payload.financial_year_id, company_id)
        if financial_year is None:
            raise ValidationAppError(
                "Financial year not found for this company", code="INVALID_FINANCIAL_YEAR"
            )

        challan = TDSChallan(
            company_id=company_id,
            financial_year_id=financial_year.id,
            challan_number=payload.challan_number,
            challan_date=payload.challan_date,
            amount=round_money(payload.amount),
            bank_reference_number=payload.bank_reference_number,
            notes=payload.notes,
        )
        await self.repo.create(challan)

        await self.audit.log(
            action=AuditAction.TDS_CHALLAN_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_challan",
            resource_id=str(challan.id),
            description=f"TDS challan {challan.challan_number} created for {challan.amount}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return challan

    async def get(self, company_id: uuid.UUID, challan_id: uuid.UUID) -> TDSChallan:
        challan = await self.repo.get_by_id_for_company(challan_id, company_id)
        if challan is None:
            raise NotFoundError("TDS challan not found", code="TDS_CHALLAN_NOT_FOUND")
        return challan

    async def list(
        self, company_id: uuid.UUID, *, financial_year_id: uuid.UUID | None, page: int, page_size: int
    ) -> tuple[list[TDSChallan], int]:
        return await self.repo.list_for_company(
            company_id,
            financial_year_id=financial_year_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    async def allocated_amount(self, challan_id: uuid.UUID) -> Decimal:
        return await self.repo.sum_allocated(challan_id)

    async def update(
        self,
        company_id: uuid.UUID,
        challan_id: uuid.UUID,
        payload: TDSChallanUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> TDSChallan:
        challan = await self.get(company_id, challan_id)
        if challan.status in (TDSChallanStatus.RECONCILED, TDSChallanStatus.CANCELLED):
            raise ConflictError(
                f"A {challan.status.value} challan cannot be edited", code="INVALID_TDS_CHALLAN_STATUS"
            )

        updates = payload.model_dump(exclude_unset=True)

        if "status" in updates:
            new_status = updates["status"]
            if new_status == TDSChallanStatus.RECONCILED:
                raise ValidationAppError(
                    "RECONCILED is set automatically by the reconciliation run, not directly",
                    code="INVALID_TDS_CHALLAN_STATUS_TRANSITION",
                )
            if new_status not in _ALLOWED_STATUS_TRANSITIONS[challan.status]:
                raise ConflictError(
                    f"Cannot move a TDS challan from {challan.status.value} to {new_status.value}",
                    code="INVALID_TDS_CHALLAN_STATUS_TRANSITION",
                )

        if "amount" in updates:
            allocated = await self.repo.sum_allocated(challan.id)
            if updates["amount"] < allocated:
                raise ValidationAppError(
                    f"Cannot reduce challan amount below its already-allocated total ({allocated})",
                    code="CHALLAN_AMOUNT_BELOW_ALLOCATED",
                )
            updates["amount"] = round_money(updates["amount"])

        for field, value in updates.items():
            setattr(challan, field, value)

        await self.db.flush()
        await self.db.refresh(challan)
        return challan

    async def allocate(
        self,
        company_id: uuid.UUID,
        challan_id: uuid.UUID,
        payload: TDSChallanAllocateRequest,
        current_user: User,
        meta: RequestMeta,
    ) -> TDSChallanAllocation:
        challan = await self.get(company_id, challan_id)
        if challan.status in (TDSChallanStatus.CANCELLED,):
            raise ConflictError(
                "Cannot allocate against a cancelled challan", code="INVALID_TDS_CHALLAN_STATUS"
            )

        transaction = await self.transactions.get_by_id_for_company(payload.tds_transaction_id, company_id)
        if transaction is None:
            raise ValidationAppError(
                "TDS transaction not found for this company", code="TDS_TRANSACTION_NOT_FOUND"
            )
        if transaction.status not in (TDSTransactionStatus.DEDUCTED, TDSTransactionStatus.PAID):
            raise ValidationAppError(
                "Only a DEDUCTED TDS transaction can be allocated against a challan",
                code="INVALID_TDS_TRANSACTION_STATUS",
            )

        allocated_amount = round_money(payload.allocated_amount)

        challan_allocated = await self.repo.sum_allocated(challan.id)
        if challan_allocated + allocated_amount > challan.amount:
            raise ValidationAppError(
                f"Allocation of {allocated_amount} would exceed the challan's remaining balance "
                f"of {challan.amount - challan_allocated}",
                code="CHALLAN_OVER_ALLOCATION",
            )

        txn_allocated = await self.repo.sum_allocated_for_transaction(transaction.id)
        if txn_allocated + allocated_amount > transaction.tds_amount:
            raise ValidationAppError(
                f"Allocation of {allocated_amount} would exceed the transaction's remaining "
                f"unallocated TDS of {transaction.tds_amount - txn_allocated}",
                code="TRANSACTION_OVER_ALLOCATION",
            )

        allocation = TDSChallanAllocation(
            challan_id=challan.id, tds_transaction_id=transaction.id, allocated_amount=allocated_amount
        )
        await self.repo.create_allocation(allocation)

        # A transaction whose full TDS is now allocated against a PAID
        # challan is, transitively, paid — this is the only place
        # TDSTransactionStatus.PAID is ever set (PHASE5 section 7).
        if challan.status == TDSChallanStatus.PAID:
            new_txn_allocated = txn_allocated + allocated_amount
            if new_txn_allocated >= transaction.tds_amount:
                transaction.status = TDSTransactionStatus.PAID

        await self.audit.log(
            action=AuditAction.TDS_CHALLAN_ALLOCATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_challan",
            resource_id=str(challan.id),
            description=f"Allocated {allocated_amount} from challan {challan.challan_number} "
            f"to TDS transaction {transaction.id}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return allocation

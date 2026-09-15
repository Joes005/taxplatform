from app.models.ledger import Ledger
from app.repositories.base import CompanyScopedRepository


class LedgerRepository(CompanyScopedRepository[Ledger]):
    model = Ledger
    search_fields = ("name", "code")

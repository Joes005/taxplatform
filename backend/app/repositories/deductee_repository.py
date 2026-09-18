from app.models.deductee import Deductee
from app.repositories.base import CompanyScopedRepository


class DeducteeRepository(CompanyScopedRepository[Deductee]):
    model = Deductee
    search_fields = ("name", "code", "pan")

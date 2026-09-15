from app.models.customer import Customer
from app.repositories.base import CompanyScopedRepository


class CustomerRepository(CompanyScopedRepository[Customer]):
    model = Customer
    search_fields = ("name", "code", "gstin", "email")

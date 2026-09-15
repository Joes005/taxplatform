from app.models.vendor import Vendor
from app.repositories.base import CompanyScopedRepository


class VendorRepository(CompanyScopedRepository[Vendor]):
    model = Vendor
    search_fields = ("name", "code", "gstin", "email")

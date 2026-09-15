from app.models.product_service import ProductService
from app.repositories.base import CompanyScopedRepository


class ProductServiceRepository(CompanyScopedRepository[ProductService]):
    model = ProductService
    search_fields = ("name", "code", "hsn_sac")

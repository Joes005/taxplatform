from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_service import ProductService
from app.repositories.product_service_repository import ProductServiceRepository
from app.services.base_master_data_service import SimpleMasterDataService


class ProductCatalogService(SimpleMasterDataService[ProductService]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(
            db,
            ProductServiceRepository(db),
            model_cls=ProductService,
            resource_type="product_service",
            not_found_code="PRODUCT_NOT_FOUND",
        )

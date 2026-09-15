from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.repositories.customer_repository import CustomerRepository
from app.services.base_master_data_service import SimpleMasterDataService


class CustomerService(SimpleMasterDataService[Customer]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(
            db,
            CustomerRepository(db),
            model_cls=Customer,
            resource_type="customer",
            not_found_code="CUSTOMER_NOT_FOUND",
        )

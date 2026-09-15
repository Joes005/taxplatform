from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vendor import Vendor
from app.repositories.vendor_repository import VendorRepository
from app.services.base_master_data_service import SimpleMasterDataService


class VendorService(SimpleMasterDataService[Vendor]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(
            db,
            VendorRepository(db),
            model_cls=Vendor,
            resource_type="vendor",
            not_found_code="VENDOR_NOT_FOUND",
        )

from functools import lru_cache

from app.core.config import settings
from app.storage.base import StorageProvider
from app.storage.local import LocalStorageProvider


@lru_cache
def get_storage_provider() -> StorageProvider:
    """Selects the active storage backend from configuration.

    Phase 2 only ships LocalStorageProvider. Adding a cloud backend later
    means adding a new provider class and a branch here — DocumentService
    and every API route stay untouched because they depend only on the
    StorageProvider interface.
    """
    return LocalStorageProvider(settings.DOCUMENT_STORAGE_PATH)


__all__ = ["StorageProvider", "LocalStorageProvider", "get_storage_provider"]

from abc import ABC, abstractmethod
from pathlib import Path


class StorageProvider(ABC):
    """Storage abstraction the document service depends on.

    Business logic (DocumentService) talks only to this interface — never to
    `open()`, `os.path`, or any filesystem call directly — so a future cloud
    provider (e.g. S3StorageProvider) can be swapped in via configuration
    without touching the service, the API routes, the database model, or the
    frontend. `key` is always a storage-relative path such as
    "companies/{company_id}/documents/{document_id}/{stored_filename}",
    never an absolute filesystem path and never derived from
    user-supplied input beyond validated UUIDs and a whitelisted extension.
    """

    @abstractmethod
    async def save(self, key: str, content: bytes) -> None:
        """Persist `content` under `key`, creating any needed structure."""

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Return the full content stored under `key`."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove the content stored under `key`. No-op if it doesn't exist."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Whether `key` currently has content stored."""

    async def get_local_path(self, key: str) -> Path | None:
        """Return a real filesystem path for `key`, if this provider has one.

        Local disk storage can serve downloads far more efficiently via a
        direct path (FastAPI's `FileResponse` streams it in chunks without
        loading it into memory) than by round-tripping through `get()`. A
        provider without a local filesystem backing (e.g. a future S3
        provider) simply returns None, and callers fall back to `get()`.
        """
        return None

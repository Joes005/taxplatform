from pathlib import Path

import anyio

from app.storage.base import StorageProvider


class StorageKeyError(ValueError):
    """Raised when a storage key resolves outside the storage root.

    This is the path-traversal guard: every key this class touches is
    resolved and checked against the storage root before any filesystem
    operation runs, regardless of what produced the key.
    """


class LocalStorageProvider(StorageProvider):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # Reject absolute paths and any attempt to escape the storage root
        # (e.g. "../../etc/passwd") before ever touching the filesystem.
        candidate = (self.root / key).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise StorageKeyError(f"Storage key resolves outside the storage root: {key!r}")
        return candidate

    async def save(self, key: str, content: bytes) -> None:
        path = self._resolve(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

        await anyio.to_thread.run_sync(_write)

    async def get(self, key: str) -> bytes:
        path = self._resolve(key)
        return await anyio.to_thread.run_sync(path.read_bytes)

    async def delete(self, key: str) -> None:
        path = self._resolve(key)

        def _delete() -> None:
            path.unlink(missing_ok=True)

        await anyio.to_thread.run_sync(_delete)

    async def exists(self, key: str) -> bool:
        path = self._resolve(key)
        return await anyio.to_thread.run_sync(path.is_file)

    async def get_local_path(self, key: str) -> Path | None:
        path = self._resolve(key)
        return path if path.is_file() else None

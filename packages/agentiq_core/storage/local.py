"""Local filesystem storage implementation for AgentIQ datasets."""

import hashlib
import logging
import os
from pathlib import Path
from typing import AsyncIterable, AsyncIterator, BinaryIO, Optional
from uuid import uuid4

from agentiq_core.storage.base import (
    BaseStorageService,
    StorageFileNotFoundError,
    StorageQuotaExceededError,
)

logger = logging.getLogger("agentiq.storage.local")


class LocalStorageService(BaseStorageService):
    """Local filesystem-backed storage service honoring tenant key boundaries."""

    def __init__(self, base_path: str = "./storage"):
        self.base_dir = Path(base_path).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, key: str) -> Path:
        """Resolve storage key to a secure path inside the base directory."""
        # Normalize and prevent directory traversal
        clean_key = os.path.normpath(key).lstrip("\\/").replace("\\", "/")
        target_path = (self.base_dir / clean_key).resolve()
        if not str(target_path).startswith(str(self.base_dir)):
            raise ValueError(f"Path traversal attempt detected in key: {key}")
        return target_path

    async def save_stream(
        self,
        key: str,
        stream: AsyncIterable[bytes],
        max_size_bytes: Optional[int] = None,
    ) -> tuple[str, str, int]:
        """Atomically stream bytes to disk, computing SHA-256 and enforcing size limit."""
        target_path = self._resolve_path(key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Unique temporary file in the same directory for atomic rename
        temp_path = target_path.parent / f".tmp_{uuid4().hex}_{target_path.name}.part"
        hasher = hashlib.sha256()
        total_bytes = 0

        try:
            with open(temp_path, "wb") as f:
                async for chunk in stream:
                    if not chunk:
                        continue
                    chunk_len = len(chunk)
                    total_bytes += chunk_len

                    if max_size_bytes is not None and total_bytes > max_size_bytes:
                        raise StorageQuotaExceededError(max_size_bytes, total_bytes)

                    hasher.update(chunk)
                    f.write(chunk)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename to final path
            os.replace(temp_path, target_path)
            sha256_hex = hasher.hexdigest()
            logger.info(f"Stored file '{key}' ({total_bytes} bytes, sha256={sha256_hex})")
            return key, sha256_hex, total_bytes

        except Exception as exc:
            # Clean up partial temporary file immediately on failure
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError as cleanup_err:
                    logger.warning(f"Failed to remove temporary file {temp_path}: {cleanup_err}")
            raise exc

    async def read_stream(
        self,
        key: str,
        chunk_size: int = 64 * 1024,
    ) -> AsyncIterator[bytes]:
        """Stream chunks from disk asynchronously."""
        path = self._resolve_path(key)
        if not path.is_file():
            raise StorageFileNotFoundError(f"File not found for key: {key}")

        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def open_reader(self, key: str) -> BinaryIO:
        """Open synchronous binary stream reader."""
        path = self._resolve_path(key)
        if not path.is_file():
            raise StorageFileNotFoundError(f"File not found for key: {key}")
        return open(path, "rb")

    async def get_bytes(self, key: str) -> bytes:
        """Read full file bytes into memory."""
        path = self._resolve_path(key)
        if not path.is_file():
            raise StorageFileNotFoundError(f"File not found for key: {key}")
        return path.read_bytes()

    async def calculate_hash(self, key: str) -> str:
        """Compute SHA-256 hash of stored file using streaming buffer."""
        path = self._resolve_path(key)
        if not path.is_file():
            raise StorageFileNotFoundError(f"File not found for key: {key}")

        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(128 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    async def exists(self, key: str) -> bool:
        """Check if file exists on disk."""
        return self._resolve_path(key).is_file()

    async def delete(self, key: str) -> bool:
        """Remove file from disk if present."""
        path = self._resolve_path(key)
        if path.is_file():
            path.unlink()
            return True
        return False

    def get_local_path(self, key: str) -> Optional[Path]:
        """Return direct Path on disk."""
        return self._resolve_path(key)

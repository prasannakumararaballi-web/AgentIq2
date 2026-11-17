"""Abstract interface for dataset file storage."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterable, AsyncIterator, BinaryIO, Optional
from uuid import UUID
import re


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class StorageQuotaExceededError(StorageError):
    """Raised when an upload exceeds maximum allowable byte size."""
    def __init__(self, max_bytes: int, current_bytes: int):
        super().__init__(f"File size exceeds maximum limit of {max_bytes} bytes (reached {current_bytes} bytes).")
        self.max_bytes = max_bytes
        self.current_bytes = current_bytes


class StorageFileNotFoundError(StorageError):
    """Raised when a requested storage key does not exist."""
    pass


class StorageIntegrityError(StorageError):
    """Raised when a file's SHA-256 hash does not match expected hash."""
    pass


def sanitize_filename(filename: str) -> str:
    """Sanitize user-supplied filename to prevent directory traversal and invalid characters."""
    clean = Path(filename).name
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean)
    return clean or "unnamed_file"


class BaseStorageService(ABC):
    """Abstract contract for key-based dataset storage services (Local disk, S3, Supabase Storage)."""

    @abstractmethod
    async def save_stream(
        self,
        key: str,
        stream: AsyncIterable[bytes],
        max_size_bytes: Optional[int] = None,
    ) -> tuple[str, str, int]:
        """Save a streamed byte sequence to the target storage key.
        
        Enforces max_size_bytes on actual consumed bytes.
        Returns:
            (key, sha256_hex_digest, total_bytes_written)
        """
        raise NotImplementedError

    @abstractmethod
    async def read_stream(
        self,
        key: str,
        chunk_size: int = 64 * 1024,
    ) -> AsyncIterator[bytes]:
        """Stream chunks of bytes from the storage key."""
        raise NotImplementedError

    @abstractmethod
    def open_reader(self, key: str) -> BinaryIO:
        """Open a synchronous binary stream reader for the target key."""
        raise NotImplementedError

    @abstractmethod
    async def get_bytes(self, key: str) -> bytes:
        """Retrieve full byte content for a storage key."""
        raise NotImplementedError

    @abstractmethod
    async def calculate_hash(self, key: str) -> str:
        """Calculate and return the SHA-256 hex digest of the stored file."""
        raise NotImplementedError

    async def verify_integrity(self, key: str, expected_hash: str) -> bool:
        """Verify that the stored file's current SHA-256 matches expected_hash.
        
        Raises:
            StorageIntegrityError: If computed hash differs from expected hash.
        """
        actual_hash = await self.calculate_hash(key)
        if actual_hash != expected_hash:
            raise StorageIntegrityError(
                f"File integrity violation for key '{key}': expected {expected_hash}, got {actual_hash}"
            )
        return True

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if target storage key exists."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete file associated with the storage key."""
        raise NotImplementedError

    @abstractmethod
    def get_local_path(self, key: str) -> Optional[Path]:
        """Return direct local Path if supported by backend, or None if pure remote object."""
        raise NotImplementedError

    def build_raw_storage_key(
        self,
        workspace_id: UUID,
        project_id: UUID,
        upload_id: UUID,
        filename: str,
    ) -> str:
        """Generate structured storage key providing strict workspace and project isolation for raw inputs."""
        safe_name = sanitize_filename(filename)
        return f"raw/{workspace_id}/{project_id}/{upload_id}_{safe_name}"

    def build_cleaned_storage_key(
        self,
        workspace_id: UUID,
        project_id: UUID,
        run_id: UUID,
        format: str = "parquet",
    ) -> str:
        """Generate structured storage key for cleaned outputs, strictly isolated from raw uploads."""
        return f"cleaned/{workspace_id}/{project_id}/{run_id}_cleaned.{format}"

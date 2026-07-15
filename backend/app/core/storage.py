"""
Storage Abstraction Layer

Provides a provider-agnostic interface for file storage, supporting:
- LocalStorage: Files on the local filesystem (development, single-instance)
- S3Storage: AWS S3 or any S3-compatible service (production, multi-instance)

Why an abstraction instead of just using local disk everywhere?
- Multi-instance: With multiple backend containers behind a load balancer,
  each has its own filesystem. A file uploaded via container A is invisible
  to container B unless stored in shared external storage.
- Durability: Container filesystems are ephemeral. Redeployments lose data.
- Scalability: S3 handles unlimited files without disk management.

Usage:
    from app.core.storage import get_storage

    storage = get_storage()
    key = await storage.upload("uploads/user_1/data.csv", file_bytes)
    content = await storage.download(key)
    await storage.delete(key)

The factory function (get_storage) selects the backend based on STORAGE_BACKEND
config: "local" (default) or "s3".
"""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("app.storage")


class StorageBackend(ABC):
    """Abstract interface for file storage operations."""

    @abstractmethod
    async def upload(self, key: str, content: bytes) -> str:
        """
        Store content at the given key.
        
        Args:
            key: Logical path/name for the file (e.g. "uploads/1/data.csv")
            content: Raw file bytes
            
        Returns:
            The storage key (may be the same as input or a generated path)
        """
        ...

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """
        Retrieve file content by key.
        
        Raises:
            FileNotFoundError: If the key doesn't exist
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a file by key. Returns True if deleted, False if not found.
        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a file exists at the given key."""
        ...

    @abstractmethod
    def get_local_path(self, key: str) -> Optional[Path]:
        """
        Get a local filesystem path for the file (if available).
        
        Returns None for cloud storage backends where files aren't on local disk.
        Used by services that need direct file access (pandas read_csv, etc.)
        """
        ...


class LocalStorage(StorageBackend):
    """
    Local filesystem storage (development / single-instance).
    
    Files are stored under a configurable base directory, preserving the
    key as a relative path. This is what the app used before this abstraction
    existed — same behavior, just behind the interface.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, key: str, content: bytes) -> str:
        file_path = self.base_dir / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return key

    async def download(self, key: str) -> bytes:
        file_path = self.base_dir / key
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return file_path.read_bytes()

    async def delete(self, key: str) -> bool:
        file_path = self.base_dir / key
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def exists(self, key: str) -> bool:
        return (self.base_dir / key).exists()

    def get_local_path(self, key: str) -> Optional[Path]:
        path = self.base_dir / key
        return path if path.exists() else None


class S3Storage(StorageBackend):
    """
    AWS S3 (or S3-compatible) storage for production multi-instance deployments.
    
    Requires: boto3 + AWS credentials configured via environment variables
    or IAM role (ECS task role, EC2 instance profile).
    
    Also works with S3-compatible services (MinIO, DigitalOcean Spaces,
    Backblaze B2) by setting S3_ENDPOINT_URL.
    """

    def __init__(self):
        import boto3

        session_kwargs = {}
        if settings.AWS_ACCESS_KEY_ID:
            session_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            session_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

        client_kwargs = {"region_name": settings.AWS_REGION}
        if settings.S3_ENDPOINT_URL:
            client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL

        self._client = boto3.client("s3", **session_kwargs, **client_kwargs)
        self._bucket = settings.S3_BUCKET_NAME

        logger.info("S3Storage initialized (bucket=%s, region=%s)", self._bucket, settings.AWS_REGION)

    async def upload(self, key: str, content: bytes) -> str:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=content)
        return key

    async def download(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()
        except self._client.exceptions.NoSuchKey:
            raise FileNotFoundError(f"S3 object not found: {key}")

    async def delete(self, key: str) -> bool:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    def get_local_path(self, key: str) -> Optional[Path]:
        """S3 files aren't on local disk — return None."""
        return None


# ─── Factory ──────────────────────────────────────────────────

_storage_instance: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """
    Get the configured storage backend (singleton).
    
    Uses STORAGE_BACKEND setting:
    - "local" (default): LocalStorage on filesystem
    - "s3": AWS S3 / S3-compatible storage
    """
    global _storage_instance

    if _storage_instance is None:
        backend = getattr(settings, "STORAGE_BACKEND", "local")

        if backend == "s3":
            _storage_instance = S3Storage()
        else:
            _storage_instance = LocalStorage()

        logger.info("Storage backend: %s", backend)

    return _storage_instance

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class StorageError(Exception):
    pass


class StorageBackend(Protocol):
    async def write(self, key: str, content: bytes, content_type: str) -> None: ...

    async def read(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...


class LocalStorageBackend:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for_key(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if self.root not in target.parents:
            raise StorageError("Invalid storage key")
        return target

    async def write(self, key: str, content: bytes, content_type: str) -> None:
        del content_type
        target = self.path_for_key(key)

        def write_file() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        try:
            await asyncio.to_thread(write_file)
        except OSError as exc:
            raise StorageError("Failed to write image") from exc

    async def read(self, key: str) -> bytes:
        try:
            return await asyncio.to_thread(self.path_for_key(key).read_bytes)
        except OSError as exc:
            raise StorageError("Image object not found") from exc

    async def delete(self, key: str) -> None:
        target = self.path_for_key(key)

        def delete_file() -> None:
            target.unlink(missing_ok=True)

        try:
            await asyncio.to_thread(delete_file)
        except OSError as exc:
            raise StorageError("Failed to delete image") from exc


class S3StorageBackend:
    def __init__(self) -> None:
        import boto3

        settings = get_settings()
        required = (
            settings.storage_endpoint,
            settings.storage_bucket,
            settings.storage_access_key,
            settings.storage_secret_key,
        )
        if not all(required):
            raise StorageError("S3 storage is not configured")
        self.bucket = settings.storage_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name=settings.storage_region,
        )

    async def write(self, key: str, content: bytes, content_type: str) -> None:
        try:
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
        except Exception as exc:
            raise StorageError("Failed to write image") from exc

    async def read(self, key: str) -> bytes:
        try:
            response = await asyncio.to_thread(
                self.client.get_object,
                Bucket=self.bucket,
                Key=key,
            )
            return await asyncio.to_thread(response["Body"].read)
        except Exception as exc:
            raise StorageError("Image object not found") from exc

    async def delete(self, key: str) -> None:
        try:
            await asyncio.to_thread(
                self.client.delete_object,
                Bucket=self.bucket,
                Key=key,
            )
        except Exception as exc:
            raise StorageError("Failed to delete image") from exc


@lru_cache
def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.storage_driver == "local":
        return LocalStorageBackend(settings.storage_local_path)
    if settings.storage_driver == "s3":
        return S3StorageBackend()
    raise StorageError(f"Unsupported storage driver: {settings.storage_driver}")

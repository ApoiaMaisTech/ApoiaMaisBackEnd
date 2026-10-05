import asyncio
import re
from pathlib import Path
from typing import Protocol

from app.core.config import Settings

# chaves sempre relativas, sem "..", sem barra inicial
_KEY = re.compile(r"^[a-z0-9-]+(/[A-Za-z0-9._-]+)+$")


class InvalidStorageKey(ValueError):
    pass


def validate_key(key: str) -> str:
    if not _KEY.match(key) or ".." in key:
        raise InvalidStorageKey(key)
    return key


class ObjectStorage(Protocol):
    """Interface única de armazenamento de mídia (volume local em dev, S3 em produção)."""

    async def get(self, key: str) -> bytes | None: ...


class LocalObjectStorage:
    def __init__(self, base_dir: str):
        self._base = Path(base_dir).resolve()

    def _path(self, key: str) -> Path:
        path = (self._base / validate_key(key)).resolve()
        if not path.is_relative_to(self._base):
            raise InvalidStorageKey(key)
        return path

    async def get(self, key: str) -> bytes | None:
        path = self._path(key)

        def _read() -> bytes | None:
            try:
                return path.read_bytes()
            except FileNotFoundError:
                return None

        return await asyncio.to_thread(_read)


class S3ObjectStorage:
    def __init__(self, bucket: str, endpoint_url: str, region: str, access_key: str, secret_key: str):
        import boto3

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or None,
            region_name=region,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
        )

    async def get(self, key: str) -> bytes | None:
        validate_key(key)

        def _read() -> bytes | None:
            try:
                response = self._client.get_object(Bucket=self._bucket, Key=key)
            except self._client.exceptions.NoSuchKey:
                return None
            return response["Body"].read()

        return await asyncio.to_thread(_read)


def build_storage(settings: Settings) -> ObjectStorage:
    if settings.STORAGE_BACKEND == "s3":
        if not settings.S3_BUCKET:
            raise ValueError("S3_BUCKET é obrigatório com STORAGE_BACKEND=s3")
        return S3ObjectStorage(
            bucket=settings.S3_BUCKET,
            endpoint_url=settings.S3_ENDPOINT_URL,
            region=settings.S3_REGION,
            access_key=settings.S3_ACCESS_KEY_ID,
            secret_key=settings.S3_SECRET_ACCESS_KEY,
        )
    if settings.STORAGE_BACKEND == "local":
        return LocalObjectStorage(settings.STORAGE_LOCAL_DIR)
    raise ValueError(f"STORAGE_BACKEND inválido: {settings.STORAGE_BACKEND!r}")

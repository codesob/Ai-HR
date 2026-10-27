import asyncio
import re
from functools import lru_cache
from pathlib import Path

from shared.core.config import get_settings


@lru_cache
def _s3_client():
    import boto3

    settings = get_settings()
    return boto3.client("s3", region_name=settings.s3_region, endpoint_url=settings.s3_endpoint_url)


_SAFE_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*")


def _validate_key(key: str) -> None:
    """Relative, slash-separated segments of safe characters; no '..', empty or hidden segments."""
    if not _SAFE_KEY.fullmatch(key) or any(part in (".", "..") for part in key.split("/")):
        raise ValueError(f"Unsafe storage key: {key!r}")


async def store_file(data: bytes, key: str, content_type: str | None = None) -> str:
    """Persist bytes and return a storage reference (local path or s3:// URI)."""
    settings = get_settings()
    _validate_key(key)
    if settings.storage_backend == "s3":
        extra = {"ContentType": content_type} if content_type else {}
        await asyncio.to_thread(
            _s3_client().put_object,
            Bucket=settings.s3_bucket,
            Key=key,
            Body=data,
            ServerSideEncryption="AES256",
            **extra,
        )
        return f"s3://{settings.s3_bucket}/{key}"

    root = Path(settings.upload_dir).resolve()
    destination = (root / key).resolve()
    if not destination.is_relative_to(root):
        raise ValueError(f"Storage key escapes upload directory: {key!r}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(destination.write_bytes, data)
    return str(destination)

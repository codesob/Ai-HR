import asyncio
from functools import lru_cache
from pathlib import Path

from shared.core.config import get_settings


@lru_cache
def _s3_client():
    import boto3

    settings = get_settings()
    return boto3.client("s3", region_name=settings.s3_region, endpoint_url=settings.s3_endpoint_url)


async def store_file(data: bytes, key: str, content_type: str | None = None) -> str:
    """Persist bytes and return a storage reference (local path or s3:// URI)."""
    settings = get_settings()
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

    destination = Path(settings.upload_dir) / key
    destination.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(destination.write_bytes, data)
    return str(destination)

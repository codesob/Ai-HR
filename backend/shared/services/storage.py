from pathlib import Path

from fastapi import UploadFile

from shared.core.config import get_settings


async def save_upload(file: UploadFile, filename: str) -> Path:
    settings = get_settings()
    if settings.storage_backend != "local":
        # S3-compatible storage is configured here for production wiring; local dev keeps files on disk.
        # A real deployment should replace this branch with boto3/aioboto3 upload code.
        raise NotImplementedError("Only local storage is implemented in this MVP runtime")
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / filename
    destination.write_bytes(await file.read())
    return destination

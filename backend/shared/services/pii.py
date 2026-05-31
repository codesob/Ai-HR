import re
from typing import Any


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\+?[\d\s().-]{10,}")


def mask_text(value: str) -> str:
    value = EMAIL_RE.sub("[email]", value)
    return PHONE_RE.sub("[phone]", value)


def mask_pii(value: Any) -> Any:
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, list):
        return [mask_pii(item) for item in value]
    if isinstance(value, dict):
        return {key: mask_pii(item) for key, item in value.items()}
    return value

import logging
from typing import Any

from shared.services.pii import mask_pii

audit_logger = logging.getLogger("audit")


async def write_audit_event(
    *,
    actor: str | None,
    organization_id: int | None,
    action: str,
    resource: str,
    status_code: int,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Emits one structured audit record to stdout for the log pipeline to retain."""
    audit_logger.info(
        "audit",
        extra={
            "audit": True,
            "actor": actor or "anonymous",
            "organization_id": organization_id,
            "action": action,
            "resource": resource,
            "status_code": status_code,
            "metadata": mask_pii(metadata or {}),
        },
    )

import asyncio
import logging
from typing import Any

from shared.db.session import AsyncSessionLocal
from shared.models.entities import AuditLog
from shared.services.pii import mask_pii

audit_logger = logging.getLogger("audit")

# Strong references so pending writes aren't garbage-collected mid-flight.
_pending: set[asyncio.Task] = set()


async def write_audit_event(
    *,
    actor: str | None,
    organization_id: int | None,
    action: str,
    resource: str,
    status_code: int,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Emits one structured audit record to stdout and stores it so workspace admins can review it in-app."""
    masked = mask_pii(metadata or {})
    audit_logger.info(
        "audit",
        extra={
            "audit": True,
            "actor": actor or "anonymous",
            "organization_id": organization_id,
            "action": action,
            "resource": resource,
            "status_code": status_code,
            "metadata": masked,
        },
    )
    if organization_id is None:
        return
    # Stored in the background: the request's own transaction commits only after its response is sent,
    # and the audit write must neither wait on that nor add latency to the request.
    task = asyncio.create_task(_persist(AuditLog(
        organization_id=organization_id, actor=actor or "anonymous", action=action,
        resource=resource[:512], metadata_json={**masked, "status_code": status_code},
    )))
    _pending.add(task)
    task.add_done_callback(_pending.discard)


async def _persist(entry: AuditLog) -> None:
    try:
        async with AsyncSessionLocal() as db:
            db.add(entry)
            await db.commit()
    except Exception:
        # The stdout record above is the source of truth; a database hiccup must not fail anything.
        audit_logger.exception("Failed to persist audit event")


async def flush_pending_audit_events() -> None:
    """Wait for in-flight audit writes (used on shutdown and in tests)."""
    if _pending:
        await asyncio.gather(*list(_pending), return_exceptions=True)

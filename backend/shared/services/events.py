from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.entities import Notification


async def publish_notification(
    db: AsyncSession,
    *,
    recipient: str,
    subject: str,
    body: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    channel: str = "in_app",
) -> Notification:
    notification = Notification(
        recipient=recipient,
        channel=channel,
        subject=subject,
        body=body,
        event_type=event_type,
        payload=payload or {},
        status="queued",
    )
    db.add(notification)
    await db.flush()
    await db.refresh(notification)
    return notification

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.entities import Notification
from shared.services.email import send_email


async def deliver(notification: Notification) -> Notification:
    if notification.channel == "email":
        sent = await send_email(notification.recipient, notification.subject, notification.body)
        notification.status = "sent" if sent else "failed"
    else:
        notification.status = "sent"
    return notification


async def publish_notification(
    db: AsyncSession,
    *,
    organization_id: int,
    recipient: str,
    subject: str,
    body: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    channel: str = "in_app",
    send_now: bool = False,
) -> Notification:
    notification = Notification(
        organization_id=organization_id,
        recipient=recipient,
        channel=channel,
        subject=subject,
        body=body,
        event_type=event_type,
        payload=payload or {},
        status="queued",
    )
    db.add(notification)
    if send_now:
        await deliver(notification)
    await db.flush()
    await db.refresh(notification)
    return notification

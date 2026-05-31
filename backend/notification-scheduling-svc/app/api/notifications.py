from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.entities import Notification, User, UserRole
from shared.schemas.common import NotificationCreate, NotificationOut
from shared.services.events import publish_notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationOut)
async def create_notification(
    payload: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER)),
):
    return await publish_notification(
        db,
        recipient=payload.recipient,
        subject=payload.subject,
        body=payload.body,
        event_type=payload.event_type,
        payload=payload.payload,
        channel=payload.channel,
    )


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    recipient: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER)),
):
    query = select(Notification).order_by(Notification.created_at.desc())
    if recipient:
        query = query.where(Notification.recipient == recipient)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{notification_id}/dispatch", response_model=NotificationOut)
async def dispatch_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER)),
):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalar_one()
    notification.status = "sent"
    await db.flush()
    await db.refresh(notification)
    return notification

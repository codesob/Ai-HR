from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.deps import require_user
from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.entities import Notification, User, UserRole
from shared.schemas.common import NotificationCreate, NotificationOut
from shared.services.events import deliver, publish_notification

router = APIRouter(prefix="/notifications", tags=["notifications"])

hr_staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER)


@router.post("", response_model=NotificationOut, status_code=201)
async def create_notification(
    payload: NotificationCreate, db: AsyncSession = Depends(get_db), user: User = Depends(hr_staff)
):
    return await publish_notification(
        db,
        organization_id=user.organization_id,
        recipient=payload.recipient,
        subject=payload.subject,
        body=payload.body,
        event_type=payload.event_type,
        payload=payload.payload,
        channel=payload.channel,
    )


@router.get("/mine", response_model=list[NotificationOut])
async def my_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.organization_id == user.organization_id, Notification.recipient == user.email)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    recipient: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(hr_staff),
):
    query = select(Notification).where(Notification.organization_id == user.organization_id)
    if recipient:
        query = query.where(Notification.recipient == recipient)
    result = await db.execute(query.order_by(Notification.created_at.desc()).limit(limit))
    return result.scalars().all()


@router.post("/{notification_id}/dispatch", response_model=NotificationOut)
async def dispatch_notification(
    notification_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(hr_staff)
):
    notification = (await db.execute(
        select(Notification).where(
            Notification.id == notification_id, Notification.organization_id == user.organization_id
        )
    )).scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    await deliver(notification)
    await db.flush()
    await db.refresh(notification)
    return notification

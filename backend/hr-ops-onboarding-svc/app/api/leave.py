from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.deps import get_db
from shared.api.rbac import require_roles
from shared.models.entities import User, UserRole
from shared.models.leave import LeaveRequest, LeaveStatus
from shared.schemas.leave import BurnoutRiskOut, LeaveRequestCreate, LeaveRequestOut, LeaveReview
from shared.services.hr_actions import NotFoundError
from shared.services.hr_actions import review_leave as review
from app.services.burnout import predict_burnout

router = APIRouter(prefix="/leave", tags=["leave"])

staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER, UserRole.EMPLOYEE)
admin_only = require_roles(UserRole.ADMIN)


@router.post("", response_model=LeaveRequestOut, status_code=201)
async def create_leave_request(
    payload: LeaveRequestCreate, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(staff)
):
    leave = LeaveRequest(
        organization_id=user.organization_id,
        user_id=user.id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
    )
    db.add(leave)
    await db.flush()
    await db.refresh(leave)
    return leave


@router.get("/mine", response_model=list[LeaveRequestOut])
async def my_leave(db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(staff)):
    result = await db.execute(
        select(LeaveRequest).where(LeaveRequest.user_id == user.id).order_by(LeaveRequest.start_date.desc())
    )
    return result.scalars().all()


@router.get("", response_model=list[LeaveRequestOut])
async def list_leave(
    status: LeaveStatus | None = None, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(admin_only)
):
    query = select(LeaveRequest).where(LeaveRequest.organization_id == user.organization_id)
    if status:
        query = query.where(LeaveRequest.status == status)
    result = await db.execute(query.order_by(LeaveRequest.start_date.desc()))
    return result.scalars().all()


@router.post("/{leave_id}/review", response_model=LeaveRequestOut)
async def review_leave(
    leave_id: int, payload: LeaveReview, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(admin_only)
):
    try:
        return await review(db, user.organization_id, leave_id, payload.status, user.id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Leave request not found") from None
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None


@router.get("/burnout-risk", response_model=BurnoutRiskOut)
async def get_burnout_risk(db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(staff)):
    return await predict_burnout(user.id, db)

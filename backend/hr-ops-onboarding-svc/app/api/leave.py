from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.api.deps import get_db, require_user
from shared.api.rbac import require_roles
from shared.models.entities import User
from shared.models.entities import UserRole
from shared.models.leave import LeaveRequest
from shared.schemas.leave import LeaveRequestCreate, LeaveRequestOut, BurnoutRiskOut
from app.services.burnout import predict_burnout

router = APIRouter(prefix="/leave", tags=["leave"])

@router.post("/", response_model=LeaveRequestOut)
async def create_leave_request(payload: LeaveRequestCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_user)):
    leave = LeaveRequest(
        user_id=current_user.id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)
    return leave

@router.get("/burnout-risk", response_model=BurnoutRiskOut)
async def get_burnout_risk(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER, UserRole.EMPLOYEE)),
):
    return await predict_burnout(current_user.id, db)

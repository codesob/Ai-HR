from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models.leave import LeaveRequest, LeaveStatus

async def predict_burnout(user_id: int, db: AsyncSession):
    # Dummy predictive model logic based on recent leave
    result = await db.execute(
        select(LeaveRequest)
        .where(LeaveRequest.user_id == user_id)
        .where(LeaveRequest.status == LeaveStatus.APPROVED)
    )
    leaves = result.scalars().all()
    
    # If no leaves taken recently, high risk
    days_taken = sum((l.end_date - l.start_date).days for l in leaves)
    
    if days_taken == 0:
        return {"user_id": user_id, "risk_score": 0.85, "risk_level": "High", "recommendation": "Mandatory time off recommended."}
    elif days_taken < 5:
        return {"user_id": user_id, "risk_score": 0.50, "risk_level": "Medium", "recommendation": "Monitor workload and encourage taking vacation."}
    else:
        return {"user_id": user_id, "risk_score": 0.10, "risk_level": "Low", "recommendation": "Healthy work-life balance."}

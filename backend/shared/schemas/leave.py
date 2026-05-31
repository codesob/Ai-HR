from pydantic import BaseModel
from datetime import date
from shared.models.leave import LeaveType, LeaveStatus

class LeaveRequestCreate(BaseModel):
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str

class LeaveRequestOut(BaseModel):
    id: int
    user_id: int
    leave_type: LeaveType
    start_date: date
    end_date: date
    status: LeaveStatus
    reason: str
    
    class Config:
        from_attributes = True

class BurnoutRiskOut(BaseModel):
    user_id: int
    risk_score: float
    risk_level: str
    recommendation: str

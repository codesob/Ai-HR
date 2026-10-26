from datetime import date

from pydantic import BaseModel, Field, model_validator

from shared.models.leave import LeaveStatus, LeaveType


class LeaveRequestCreate(BaseModel):
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str = Field(default="", max_length=1024)

    @model_validator(mode="after")
    def _check_dates(self) -> "LeaveRequestCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class LeaveReview(BaseModel):
    status: LeaveStatus


class LeaveRequestOut(BaseModel):
    id: int
    user_id: int
    leave_type: LeaveType
    start_date: date
    end_date: date
    status: LeaveStatus
    reason: str

    model_config = {"from_attributes": True}


class BurnoutRiskOut(BaseModel):
    user_id: int
    risk_score: float
    risk_level: str
    recommendation: str

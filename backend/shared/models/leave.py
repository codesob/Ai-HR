from datetime import date
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum, Float
import enum
from shared.db.session import Base

class LeaveType(str, enum.Enum):
    ANNUAL = "annual"
    SICK = "sick"
    UNPAID = "unpaid"
    MATERNITY = "maternity"

class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    leave_type = Column(Enum(LeaveType))
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING)
    reason = Column(String)

class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    annual_days = Column(Integer, default=20)
    sick_days = Column(Integer, default=10)

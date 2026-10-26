import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    leave_type: Mapped[LeaveType] = mapped_column(Enum(LeaveType))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[LeaveStatus] = mapped_column(Enum(LeaveStatus), default=LeaveStatus.PENDING)
    reason: Mapped[str] = mapped_column(String(1024), default="")
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    annual_days: Mapped[int] = mapped_column(Integer, default=20)
    sick_days: Mapped[int] = mapped_column(Integer, default=10)

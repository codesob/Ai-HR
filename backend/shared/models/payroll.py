from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import Base


class SalaryProfile(Base):
    __tablename__ = "salary_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    annual_base: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")


class Payslip(Base):
    __tablename__ = "payslips"
    __table_args__ = (UniqueConstraint("user_id", "period_start", "period_end", name="uq_payslip_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    gross_amount: Mapped[float] = mapped_column(Float)
    tax_deduction: Mapped[float] = mapped_column(Float)
    net_amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="processed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

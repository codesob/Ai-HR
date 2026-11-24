from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import Base


class SalaryProfile(Base):
    __tablename__ = "salary_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    annual_base: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="NPR")
    # Nepal statutory details. Basic pay drives SSF; the rest of monthly pay is allowances.
    basic_monthly: Mapped[float | None] = mapped_column(Float, nullable=True)
    ssf_enrolled: Mapped[bool] = mapped_column(Boolean, default=True)
    married: Mapped[bool] = mapped_column(Boolean, default=False)
    female: Mapped[bool] = mapped_column(Boolean, default=False)
    remote_category: Mapped[str | None] = mapped_column(String(1), nullable=True)
    cit_monthly: Mapped[float] = mapped_column(Float, default=0)
    life_insurance_annual: Mapped[float] = mapped_column(Float, default=0)
    health_insurance_annual: Mapped[float] = mapped_column(Float, default=0)
    pan: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ssf_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    joined_on: Mapped[date | None] = mapped_column(Date, nullable=True)


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
    fiscal_year: Mapped[str | None] = mapped_column(String(7), nullable=True, index=True)
    bs_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bs_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ssf_employee: Mapped[float] = mapped_column(Float, default=0)
    ssf_employer: Mapped[float] = mapped_column(Float, default=0)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

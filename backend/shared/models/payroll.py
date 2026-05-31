from datetime import date
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Float
from shared.db.session import Base

class SalaryProfile(Base):
    __tablename__ = "salary_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    annual_base = Column(Float)
    currency = Column(String, default="USD")

class Payslip(Base):
    __tablename__ = "payslips"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    period_start = Column(Date)
    period_end = Column(Date)
    gross_amount = Column(Float)
    tax_deduction = Column(Float)
    net_amount = Column(Float)
    status = Column(String, default="processed")

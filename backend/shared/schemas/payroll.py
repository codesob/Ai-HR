from pydantic import BaseModel
from datetime import date

class SalaryProfileCreate(BaseModel):
    user_id: int
    annual_base: float
    currency: str = "USD"

class PayslipOut(BaseModel):
    id: int
    user_id: int
    period_start: date
    period_end: date
    gross_amount: float
    tax_deduction: float
    net_amount: float
    status: str
    
    class Config:
        from_attributes = True

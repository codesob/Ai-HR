from datetime import date

from pydantic import BaseModel, Field, model_validator


class SalaryProfileCreate(BaseModel):
    user_id: int
    annual_base: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class PayrollRun(BaseModel):
    user_id: int
    period_start: date
    period_end: date

    @model_validator(mode="after")
    def _check_dates(self) -> "PayrollRun":
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


class PayslipOut(BaseModel):
    id: int
    user_id: int
    period_start: date
    period_end: date
    gross_amount: float
    tax_deduction: float
    net_amount: float
    status: str

    model_config = {"from_attributes": True}

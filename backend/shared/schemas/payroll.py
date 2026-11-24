from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SalaryProfileCreate(BaseModel):
    user_id: int
    annual_base: float = Field(gt=0, description="Yearly pay in NPR before deductions, festival allowance excluded")
    currency: Literal["NPR"] = "NPR"
    basic_monthly: float | None = Field(default=None, gt=0, description="Basic pay; SSF is charged on this")
    ssf_enrolled: bool = True
    married: bool = False
    female: bool = False
    remote_category: Literal["A", "B", "C", "D", "E"] | None = None
    cit_monthly: float = Field(default=0, ge=0)
    life_insurance_annual: float = Field(default=0, ge=0)
    health_insurance_annual: float = Field(default=0, ge=0)
    pan: str | None = Field(default=None, max_length=16)
    ssf_number: str | None = Field(default=None, max_length=32)
    joined_on: date | None = None

    @model_validator(mode="after")
    def _check_basic(self) -> "SalaryProfileCreate":
        if self.basic_monthly is not None and self.basic_monthly > self.annual_base / 12 + 0.01:
            raise ValueError("basic_monthly can't be more than monthly pay (annual_base / 12)")
        return self


class PayrollRun(BaseModel):
    user_id: int
    period_start: date
    period_end: date
    festival_allowance: bool = False

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
    fiscal_year: str | None = None
    bs_year: int | None = None
    bs_month: int | None = None
    ssf_employee: float = 0
    ssf_employer: float = 0
    breakdown: dict = {}

    model_config = {"from_attributes": True}


class PayrollPeriod(BaseModel):
    period_start: date
    period_end: date
    festival_allowance: bool = False

    @model_validator(mode="after")
    def _check_dates(self) -> "PayrollPeriod":
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self

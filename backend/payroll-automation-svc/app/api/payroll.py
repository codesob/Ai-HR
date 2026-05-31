from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from shared.api.deps import get_db
from shared.api.rbac import require_roles
from shared.models.entities import User, UserRole
from shared.models.payroll import SalaryProfile, Payslip
from shared.schemas.payroll import SalaryProfileCreate, PayslipOut
from app.services.calculator import calculate_net_salary

router = APIRouter(prefix="/payroll", tags=["payroll"])

@router.post("/profile")
async def create_salary_profile(
    payload: SalaryProfileCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    profile = SalaryProfile(**payload.model_dump())
    db.add(profile)
    await db.commit()
    return {"status": "created"}

@router.post("/run", response_model=PayslipOut)
async def run_payroll_for_user(
    user_id: int,
    period_start: date,
    period_end: date,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    result = await db.execute(select(SalaryProfile).where(SalaryProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Salary profile not found")
        
    gross, tax, net = calculate_net_salary(profile.annual_base)
    
    payslip = Payslip(
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
        gross_amount=gross,
        tax_deduction=tax,
        net_amount=net
    )
    db.add(payslip)
    await db.commit()
    await db.refresh(payslip)
    
    return payslip

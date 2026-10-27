from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.deps import get_db
from shared.api.rbac import require_roles
from shared.models.entities import User, UserRole
from shared.models.payroll import Payslip, SalaryProfile
from shared.schemas.payroll import PayrollPeriod, PayrollRun, PayslipOut, SalaryProfileCreate
from app.services.calculator import calculate_net_salary

router = APIRouter(prefix="/payroll", tags=["payroll"])

admin_only = require_roles(UserRole.ADMIN)
staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER, UserRole.EMPLOYEE)


async def _org_member(db: AsyncSession, user_id: int, organization_id: int) -> User:
    member = (await db.execute(
        select(User).where(User.id == user_id, User.organization_id == organization_id)
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Employee not found")
    return member


@router.put("/profile")
async def upsert_salary_profile(
    payload: SalaryProfileCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(admin_only)
):
    await _org_member(db, payload.user_id, admin.organization_id)
    profile = (await db.execute(
        select(SalaryProfile).where(SalaryProfile.user_id == payload.user_id)
    )).scalar_one_or_none()
    if profile:
        profile.annual_base = payload.annual_base
        profile.currency = payload.currency.upper()
    else:
        db.add(SalaryProfile(
            organization_id=admin.organization_id,
            user_id=payload.user_id,
            annual_base=payload.annual_base,
            currency=payload.currency.upper(),
        ))
    await db.flush()
    return {"status": "saved"}


@router.post("/run", response_model=PayslipOut, status_code=201)
async def run_payroll_for_user(
    payload: PayrollRun, db: AsyncSession = Depends(get_db), admin: User = Depends(admin_only)
):
    await _org_member(db, payload.user_id, admin.organization_id)
    profile = (await db.execute(
        select(SalaryProfile).where(
            SalaryProfile.user_id == payload.user_id, SalaryProfile.organization_id == admin.organization_id
        )
    )).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Salary profile not found")

    gross, tax, net = calculate_net_salary(profile.annual_base)
    payslip = Payslip(
        organization_id=admin.organization_id,
        user_id=payload.user_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        gross_amount=gross,
        tax_deduction=tax,
        net_amount=net,
    )
    db.add(payslip)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Payroll already run for this period") from None
    await db.refresh(payslip)
    return payslip


@router.get("/payslips/mine", response_model=list[PayslipOut])
async def my_payslips(db: AsyncSession = Depends(get_db), user: User = Depends(staff)):
    result = await db.execute(
        select(Payslip).where(Payslip.user_id == user.id).order_by(Payslip.period_start.desc())
    )
    return result.scalars().all()


@router.get("/profiles")
async def salary_profiles(db: AsyncSession = Depends(get_db), admin: User = Depends(admin_only)):
    """Every active staff member with their salary profile (if any) and most recent payslip."""
    members = (await db.execute(
        select(User).where(
            User.organization_id == admin.organization_id,
            User.role.in_([UserRole.ADMIN, UserRole.RECRUITER, UserRole.EMPLOYEE]),
            User.is_active,
        ).order_by(User.full_name)
    )).scalars().all()
    ids = [m.id for m in members]
    profiles = {p.user_id: p for p in (await db.execute(
        select(SalaryProfile).where(SalaryProfile.user_id.in_(ids))
    )).scalars()} if ids else {}
    latest: dict[int, Payslip] = {}
    for slip in (await db.execute(
        select(Payslip).where(Payslip.user_id.in_(ids)).order_by(Payslip.period_start)
    )).scalars() if ids else []:
        latest[slip.user_id] = slip
    return [
        {
            "user_id": m.id,
            "full_name": m.full_name,
            "role": m.role.value,
            "annual_base": profiles[m.id].annual_base if m.id in profiles else None,
            "currency": profiles[m.id].currency if m.id in profiles else None,
            "last_period_end": latest[m.id].period_end if m.id in latest else None,
            "last_net_amount": latest[m.id].net_amount if m.id in latest else None,
        }
        for m in members
    ]


@router.post("/run-all")
async def run_payroll_for_organization(
    payload: PayrollPeriod, db: AsyncSession = Depends(get_db), admin: User = Depends(admin_only)
):
    """Issue payslips for everyone with a salary profile; people already paid for the period are skipped."""
    profiles = (await db.execute(
        select(SalaryProfile)
        .join(User, User.id == SalaryProfile.user_id)
        .where(SalaryProfile.organization_id == admin.organization_id, User.is_active)
    )).scalars().all()
    already_paid = set((await db.execute(
        select(Payslip.user_id).where(
            Payslip.organization_id == admin.organization_id,
            Payslip.period_start == payload.period_start,
            Payslip.period_end == payload.period_end,
        )
    )).scalars())

    processed, total_net = 0, 0.0
    for profile in profiles:
        if profile.user_id in already_paid:
            continue
        gross, tax, net = calculate_net_salary(profile.annual_base)
        db.add(Payslip(
            organization_id=admin.organization_id, user_id=profile.user_id,
            period_start=payload.period_start, period_end=payload.period_end,
            gross_amount=gross, tax_deduction=tax, net_amount=net,
        ))
        processed += 1
        total_net += net
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Payroll is already running for this period") from None
    return {"processed": processed, "skipped": len(already_paid), "total_net": round(total_net, 2)}

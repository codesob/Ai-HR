import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.deps import get_db
from shared.api.rbac import require_roles
from shared.models.entities import User, UserRole
from shared.models.payroll import Payslip, SalaryProfile
from shared.schemas.payroll import PayrollPeriod, PayrollRun, PayslipOut, SalaryProfileCreate
from shared.services.hr_actions import ConflictError, issue_payslip, remittance, run_org_payroll
from shared.services.nepal.calendar import MONTH_DAYS, BSMonth, last_completed_month

router = APIRouter(prefix="/payroll", tags=["payroll"])

admin_only = require_roles(UserRole.ADMIN)
staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER, UserRole.EMPLOYEE)

PROFILE_FIELDS = ("annual_base", "currency", "basic_monthly", "ssf_enrolled", "married", "female", "remote_category",
                  "cit_monthly", "life_insurance_annual", "health_insurance_annual", "pan", "ssf_number", "joined_on")


async def _org_member(db: AsyncSession, user_id: int, organization_id: int) -> User:
    member = (await db.execute(
        select(User).where(User.id == user_id, User.organization_id == organization_id)
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Employee not found")
    return member


def _bs_month(bs_year: int, bs_month: int) -> BSMonth:
    if bs_year not in MONTH_DAYS:
        raise HTTPException(status_code=422, detail=f"No Bikram Sambat calendar loaded for {bs_year} BS")
    return BSMonth(bs_year, bs_month)


def _period(month: BSMonth) -> dict:
    return {"bs_year": month.year, "bs_month": month.month, "label": month.label, "fiscal_year": month.fiscal_year,
            "period_start": month.start, "period_end": month.end, "days": month.days}


@router.get("/period")
async def payroll_period(_: User = Depends(staff)):
    """The Nepali (BS) month that's due to be paid: the last one that has fully ended."""
    return _period(last_completed_month(date.today()))


@router.put("/profile")
async def upsert_salary_profile(
    payload: SalaryProfileCreate, db: AsyncSession = Depends(get_db, scope="function"), admin: User = Depends(admin_only)
):
    await _org_member(db, payload.user_id, admin.organization_id)
    profile = (await db.execute(
        select(SalaryProfile).where(SalaryProfile.user_id == payload.user_id)
    )).scalar_one_or_none()
    if not profile:
        profile = SalaryProfile(organization_id=admin.organization_id, user_id=payload.user_id)
        db.add(profile)
    for name in PROFILE_FIELDS:
        setattr(profile, name, getattr(payload, name))
    await db.flush()
    return {"status": "saved"}


@router.post("/run", response_model=PayslipOut, status_code=201)
async def run_payroll_for_user(
    payload: PayrollRun, db: AsyncSession = Depends(get_db, scope="function"), admin: User = Depends(admin_only)
):
    await _org_member(db, payload.user_id, admin.organization_id)
    profile = (await db.execute(
        select(SalaryProfile).where(
            SalaryProfile.user_id == payload.user_id, SalaryProfile.organization_id == admin.organization_id
        )
    )).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Salary profile not found")
    try:
        payslip = await issue_payslip(db, profile, payload.period_start, payload.period_end,
                                      payload.festival_allowance)
        await db.flush()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Payroll already run for this period") from None
    await db.refresh(payslip)
    return payslip


@router.get("/payslips/mine", response_model=list[PayslipOut])
async def my_payslips(db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(staff)):
    result = await db.execute(
        select(Payslip).where(Payslip.user_id == user.id).order_by(Payslip.period_start.desc())
    )
    return result.scalars().all()


@router.get("/profiles")
async def salary_profiles(db: AsyncSession = Depends(get_db, scope="function"), admin: User = Depends(admin_only)):
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
    rows = []
    for m in members:
        profile, slip = profiles.get(m.id), latest.get(m.id)
        row = {"user_id": m.id, "full_name": m.full_name, "role": m.role.value}
        row |= {name: getattr(profile, name) if profile else None for name in PROFILE_FIELDS}
        row |= {
            "last_period_end": slip.period_end if slip else None,
            "last_net_amount": slip.net_amount if slip else None,
            "last_bs_month": (slip.breakdown or {}).get("bs_month") if slip else None,
        }
        rows.append(row)
    return rows


@router.post("/run-all")
async def run_payroll_for_organization(
    payload: PayrollPeriod, db: AsyncSession = Depends(get_db, scope="function"), admin: User = Depends(admin_only)
):
    """Issue payslips for everyone with a salary; people already paid for the period are skipped."""
    try:
        return await run_org_payroll(db, admin.organization_id, payload.period_start, payload.period_end,
                                     payload.festival_allowance)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.get("/remittance")
async def payroll_remittance(
    bs_year: int, bs_month: int = Query(ge=1, le=12), format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db, scope="function"), admin: User = Depends(admin_only),
):
    """SSF and TDS owed for one BS month. CSV is one row per person, ready to key into the SSF and IRD portals."""
    report = await remittance(db, admin.organization_id, _bs_month(bs_year, bs_month))
    if format == "json":
        return report
    out = io.StringIO()
    columns = ["full_name", "pan", "ssf_number", "basic", "gross", "ssf_employee", "ssf_employer", "ssf_total",
               "sst", "income_tax", "tds", "net"]
    writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(report["people"])
    name = f"remittance-{bs_year}-{bs_month:02d}.csv"
    return Response(out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})

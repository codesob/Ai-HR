"""Nepal salary maths: SSF contributions, income tax (TDS) by fiscal year, festival allowance.

Every number here has a source in research_notes/Nepal HR wedge research/payroll_compliance_rules.md.
Rules are versioned by fiscal year so arrears for an old year are taxed under that year's Finance Act.
Anything a primary source didn't confirm is listed in FiscalRules.unverified and shown on the payslip.

Monthly TDS follows the usual employer method: project the year's taxable income (what's been paid so far
plus this month's regular pay for every month left), tax it, and withhold what's still owed spread evenly
over the months left. A one-off like the festival allowance is taxed in the remaining months from when it's paid.
"""
from dataclasses import dataclass, field

from shared.services.nepal.calendar import BSMonth

Slabs = tuple[tuple[float | None, float], ...]  # (upper bound of the band or None for the top band, rate)

# Minimum remuneration from 1 Shrawan 2082 (Himalayan Times / Himal Press reporting the government notice).
MINIMUM_MONTHLY = 19_550
MINIMUM_BASIC = 12_170


@dataclass(frozen=True)
class FiscalRules:
    fiscal_year: str
    single: Slabs
    couple: Slabs | None  # FY 2083/84 dropped the separate couple table
    building_insurance_cap: float
    ssf_employee_rate: float = 0.11
    ssf_employer_rate: float = 0.20
    retirement_cap: float = 500_000
    retirement_income_share: float = 1 / 3
    life_insurance_cap: float = 40_000
    health_insurance_cap: float = 20_000
    female_credit_rate: float = 0.10
    remote_area: dict[str, float] = field(default_factory=lambda: {
        "A": 50_000, "B": 40_000, "C": 30_000, "D": 20_000, "E": 10_000,
    })
    unverified: tuple[str, ...] = ()


RULES: dict[str, FiscalRules] = {
    # PKF T R Upadhya FY 2082-83 rate sheet; unchanged from 2081/82.
    "2082/83": FiscalRules(
        fiscal_year="2082/83",
        single=((500_000, 0.01), (700_000, 0.10), (1_000_000, 0.20), (2_000_000, 0.30), (5_000_000, 0.36), (None, 0.39)),
        couple=((600_000, 0.01), (800_000, 0.10), (1_100_000, 0.20), (2_000_000, 0.30), (5_000_000, 0.36), (None, 0.39)),
        building_insurance_cap=5_000,
        unverified=("Employer SSF share is added to taxable income before the retirement deduction (common practice).",),
    ),
    # Finance Act 2083 as quoted in ICAN Budget Highlights 2083/84, effective 1 Shrawan 2083.
    "2083/84": FiscalRules(
        fiscal_year="2083/84",
        single=((1_000_000, 0.01), (1_500_000, 0.10), (2_500_000, 0.20), (4_000_000, 0.27), (None, 0.29)),
        couple=None,
        building_insurance_cap=10_000,
        unverified=(
            "Top band is '27% + 2% surcharge'; taken as 29% per ICAN's 'reduced by ten percentage points'.",
            "Employer SSF share is added to taxable income before the retirement deduction (common practice).",
        ),
    ),
}


def rules_for(month: BSMonth) -> FiscalRules:
    if month.fiscal_year not in RULES:
        raise ValueError(f"No Nepal tax rules loaded for FY {month.fiscal_year}")
    return RULES[month.fiscal_year]


@dataclass(frozen=True)
class Employee:
    basic_monthly: float
    allowances_monthly: float = 0
    ssf_enrolled: bool = True
    married: bool = False  # files as a couple (FY 2082/83 and earlier only)
    female: bool = False  # 10% credit applies when salary is her only income
    remote_category: str | None = None  # A–E
    cit_monthly: float = 0
    life_insurance_annual: float = 0
    health_insurance_annual: float = 0


@dataclass(frozen=True)
class YearToDate:
    """Totals from this fiscal year's earlier payslips."""
    assessable: float = 0
    retirement: float = 0
    tds: float = 0
    sst: float = 0


@dataclass(frozen=True)
class AnnualTax:
    total: float
    sst: float  # 1% first-band Social Security Tax, deposited to revenue head 11211
    female_credit: float


def annual_tax(rules: FiscalRules, taxable: float, *, married: bool, ssf_enrolled: bool, female: bool) -> AnnualTax:
    slabs = rules.couple if married and rules.couple else rules.single
    total = sst = 0.0
    lower = 0.0
    for upper, rate in slabs:
        if taxable <= lower:
            break
        band = (taxable if upper is None else min(taxable, upper)) - lower
        if lower == 0:
            # SSF contributors don't pay the 1% Social Security Tax on the first band.
            sst = 0.0 if ssf_enrolled else band * rate
            total += sst
        else:
            total += band * rate
        lower = upper if upper is not None else taxable
    credit = total * rules.female_credit_rate if female else 0.0
    return AnnualTax(total=total - credit, sst=sst - (sst * rules.female_credit_rate if female else 0.0),
                     female_credit=credit)


def _r(x: float) -> float:
    return round(x + 0.0, 2)


def payslip(emp: Employee, month: BSMonth, ytd: YearToDate = YearToDate(), festival_allowance: float = 0) -> dict:
    """One month's pay. Returns the full breakdown stored on the payslip."""
    rules = rules_for(month)
    months_left = 12 - month.fiscal_index + 1  # including this one

    ssf_employee = emp.basic_monthly * rules.ssf_employee_rate if emp.ssf_enrolled else 0.0
    ssf_employer = emp.basic_monthly * rules.ssf_employer_rate if emp.ssf_enrolled else 0.0
    gross = emp.basic_monthly + emp.allowances_monthly + festival_allowance

    regular_assessable = emp.basic_monthly + emp.allowances_monthly + ssf_employer
    regular_retirement = ssf_employee + ssf_employer + emp.cit_monthly
    projected_assessable = ytd.assessable + festival_allowance + regular_assessable * months_left
    projected_retirement = ytd.retirement + regular_retirement * months_left

    retirement_deduction = min(projected_retirement, projected_assessable * rules.retirement_income_share,
                               rules.retirement_cap)
    insurance_deduction = (min(emp.life_insurance_annual, rules.life_insurance_cap)
                           + min(emp.health_insurance_annual, rules.health_insurance_cap))
    remote_deduction = rules.remote_area.get(emp.remote_category or "", 0.0)
    taxable = max(0.0, projected_assessable - retirement_deduction - insurance_deduction - remote_deduction)

    married = emp.married and rules.couple is not None
    tax = annual_tax(rules, taxable, married=married, ssf_enrolled=emp.ssf_enrolled, female=emp.female)
    tds = max(0.0, (tax.total - ytd.tds) / months_left)
    sst = min(tds, max(0.0, (tax.sst - ytd.sst) / months_left))

    net = gross - ssf_employee - emp.cit_monthly - tds
    warnings = []
    if emp.basic_monthly + emp.allowances_monthly < MINIMUM_MONTHLY:
        warnings.append(f"Monthly pay is below the NPR {MINIMUM_MONTHLY:,} legal minimum.")
    elif emp.basic_monthly < MINIMUM_BASIC:
        warnings.append(f"Basic pay is below the NPR {MINIMUM_BASIC:,} legal minimum basic.")
    return {
        "fiscal_year": rules.fiscal_year,
        "bs_month": month.label,
        "basic": _r(emp.basic_monthly),
        "allowances": _r(emp.allowances_monthly),
        "festival_allowance": _r(festival_allowance),
        "gross": _r(gross),
        "ssf_employee": _r(ssf_employee),
        "ssf_employer": _r(ssf_employer),
        "cit": _r(emp.cit_monthly),
        "tds": _r(tds),
        "sst": _r(sst),
        "income_tax": _r(tds - sst),
        "net": _r(net),
        # What went into the year's tax, so anyone can check the TDS figure by hand.
        "assessable_this_month": _r(regular_assessable + festival_allowance),
        "retirement_this_month": _r(regular_retirement),
        "projection": {
            "months_left": months_left,
            "assessable": _r(projected_assessable),
            "retirement_deduction": _r(retirement_deduction),
            "insurance_deduction": _r(insurance_deduction),
            "remote_area_deduction": _r(remote_deduction),
            "taxable": _r(taxable),
            "annual_tax": _r(tax.total),
            "female_credit": _r(tax.female_credit),
            "tax_table": "couple" if married else "single",
            "tds_already_withheld": _r(ytd.tds),
        },
        "warnings": warnings,
        "unverified": list(rules.unverified),
    }


def festival_allowance(basic_monthly: float, months_served: int) -> float:
    """Labour Act 2074 s.37: one month's pay a year, prorated under a year of service. Basic pay is used,
    as law-firm summaries read it; the Act says 'monthly remuneration'."""
    return basic_monthly * min(max(months_served, 0), 12) / 12

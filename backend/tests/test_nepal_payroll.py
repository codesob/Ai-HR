from datetime import date

import pytest

from shared.services.nepal import payroll as nepal
from shared.services.nepal.calendar import BSMonth, last_completed_month, month_of
from tests.conftest import bearer, signup

API = "/api/v1"


def test_bs_calendar_lines_up_with_known_dates():
    assert BSMonth(2082, 1).start == date(2025, 4, 14)  # Nepali new year 2082
    assert BSMonth(2082, 4).start == date(2025, 7, 17)  # 1 Shrawan 2082, FY 2082/83 begins
    assert BSMonth(2083, 1).start == date(2026, 4, 14)
    assert BSMonth(2083, 4).start == date(2026, 7, 17)
    assert month_of(date(2026, 10, 28)) == BSMonth(2083, 7)  # Kartik 2083
    assert month_of(BSMonth(2083, 6).end) == BSMonth(2083, 6)
    assert month_of(BSMonth(2083, 7).start) == BSMonth(2083, 7)
    assert last_completed_month(date(2026, 10, 28)).label == "Asoj 2083"


def test_fiscal_year_runs_shrawan_to_asar():
    assert BSMonth(2083, 3).fiscal_year == "2082/83" and BSMonth(2083, 3).fiscal_index == 12
    assert BSMonth(2083, 4).fiscal_year == "2083/84" and BSMonth(2083, 4).fiscal_index == 1
    assert BSMonth(2084, 1).fiscal_year == "2083/84" and BSMonth(2084, 1).fiscal_index == 10


@pytest.mark.parametrize("fy, ssf, female, expected", [
    # Worked checks from the research rulebook.
    ("2083/84", True, False, 20_000),   # first NPR 10L waived for SSF members, next 2L at 10%
    ("2083/84", False, False, 30_000),  # 1% Social Security Tax on the first 10L
    ("2082/83", False, False, 145_000),  # 5,000 + 20,000 + 60,000 + 60,000
    ("2082/83", True, False, 140_000),
    ("2083/84", False, True, 27_000),   # 10% female credit
])
def test_annual_tax_matches_worked_examples(fy, ssf, female, expected):
    tax = nepal.annual_tax(nepal.RULES[fy], 1_200_000, married=False, ssf_enrolled=ssf, female=female)
    assert round(tax.total, 2) == expected


def test_couple_table_only_exists_before_2083():
    old = nepal.annual_tax(nepal.RULES["2082/83"], 600_000, married=True, ssf_enrolled=False, female=False)
    assert old.total == 6_000 and old.sst == 6_000
    emp = nepal.Employee(basic_monthly=50_000, married=True)
    assert nepal.payslip(emp, BSMonth(2083, 4))["projection"]["tax_table"] == "single"


def test_payslip_spreads_tds_and_charges_ssf_on_basic_only():
    emp = nepal.Employee(basic_monthly=60_000, allowances_monthly=40_000)
    slip = nepal.payslip(emp, BSMonth(2083, 4))
    assert (slip["ssf_employee"], slip["ssf_employer"]) == (6_600, 12_000)
    assert slip["projection"]["taxable"] == 1_120_800  # 12 × 1,12,000 − 2,23,200 retirement deduction
    assert slip["projection"]["annual_tax"] == 12_080
    assert (slip["tds"], slip["sst"], slip["net"]) == (1_006.67, 0, 92_393.33)
    assert slip["warnings"] == [] and slip["unverified"]


def test_retirement_deduction_is_capped():
    rich = nepal.payslip(nepal.Employee(basic_monthly=400_000, cit_monthly=100_000), BSMonth(2083, 4))
    assert rich["projection"]["retirement_deduction"] == 500_000


def test_minimum_wage_and_festival_allowance():
    low = nepal.payslip(nepal.Employee(basic_monthly=10_000), BSMonth(2083, 4))
    assert low["warnings"] == ["Monthly pay is below the NPR 19,550 legal minimum."]
    assert nepal.festival_allowance(60_000, 6) == 30_000
    assert nepal.festival_allowance(60_000, 40) == 60_000


def test_unknown_fiscal_year_is_refused():
    with pytest.raises(ValueError):
        nepal.payslip(nepal.Employee(basic_monthly=50_000), BSMonth(2078, 4))


async def test_nepal_payroll_month_by_month_with_remittance(clients):
    gw, pay = clients["api-gateway"], clients["payroll-automation-svc"]
    owner = await signup(gw, "Acme", "a@acme.io")
    admin, uid = bearer(owner["access_token"]), owner["user"]["id"]
    profile = {"user_id": uid, "annual_base": 1_200_000, "basic_monthly": 60_000}
    assert (await pay.put(f"{API}/payroll/profile", json=profile, headers=admin)).status_code == 200
    bad = await pay.put(f"{API}/payroll/profile", json=profile | {"basic_monthly": 200_000}, headers=admin)
    assert bad.status_code == 422

    def period(month: BSMonth, festival: bool = False) -> dict:
        return {"period_start": str(month.start), "period_end": str(month.end), "festival_allowance": festival}

    shrawan, bhadra, asoj = BSMonth(2083, 4), BSMonth(2083, 5), BSMonth(2083, 6)
    first = (await pay.post(f"{API}/payroll/run-all", json=period(shrawan), headers=admin)).json()
    assert first == {"processed": 1, "skipped": 0, "total_net": 92_393.33, "bs_month": "Shrawan 2083",
                     "fiscal_year": "2083/84"}
    await pay.post(f"{API}/payroll/run-all", json=period(bhadra), headers=admin)
    third = (await pay.post(f"{API}/payroll/run-all", json=period(asoj, festival=True), headers=admin)).json()
    # Dashain month: a month's basic on top, and the extra tax spread over the ten months left.
    assert third["total_net"] == 151_793.33
    again = (await pay.post(f"{API}/payroll/run-all", json=period(asoj), headers=admin)).json()
    assert again["processed"] == 0 and again["skipped"] == 1

    slips = (await pay.get(f"{API}/payroll/payslips/mine", headers=admin)).json()
    assert [(s["bs_month"], s["tax_deduction"]) for s in slips] == [(6, 1_606.67), (5, 1_006.67), (4, 1_006.67)]
    assert slips[0]["breakdown"]["festival_allowance"] == 60_000

    report = (await pay.get(f"{API}/payroll/remittance", params={"bs_year": 2083, "bs_month": 4},
                            headers=admin)).json()
    assert report["ssf"] == {"employee": 6_600, "employer": 12_000, "total": 18_600, "due": "2026-08-31"}
    assert report["ird"]["total"] == 1_006.67 and report["ird"]["sst_11211"] == 0
    assert report["missing_pan"] == ["Owner"]
    csv = await pay.get(f"{API}/payroll/remittance", params={"bs_year": 2083, "bs_month": 4, "format": "csv"},
                        headers=admin)
    assert csv.headers["content-type"].startswith("text/csv")
    assert csv.text.splitlines()[0].startswith("full_name,pan,ssf_number,basic")

    period_now = (await pay.get(f"{API}/payroll/period", headers=admin)).json()
    assert period_now["label"] == last_completed_month(date.today()).label
    assert (await pay.get(f"{API}/payroll/remittance", params={"bs_year": 2050, "bs_month": 1},
                          headers=admin)).status_code == 422

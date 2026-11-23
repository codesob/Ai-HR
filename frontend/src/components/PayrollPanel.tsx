"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Download, Pencil } from "lucide-react";
import { api, type PayrollPeriod, type Remittance, type SalaryInput, type SalaryRow } from "@/lib/api";

// Nepali digit grouping: NPR 1,00,000.
const money = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "NPR", maximumFractionDigits: 0 }).format(n);
const fmtDay = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

type Draft = Record<keyof Omit<SalaryInput, "user_id">, string | boolean>;

function draftFrom(r: SalaryRow): Draft {
  const text = (v: number | string | null) => (v === null || v === 0 ? "" : String(v));
  return {
    annual_base: text(r.annual_base),
    basic_monthly: text(r.basic_monthly),
    ssf_enrolled: r.ssf_enrolled ?? true,
    married: r.married ?? false,
    female: r.female ?? false,
    remote_category: r.remote_category ?? "",
    cit_monthly: text(r.cit_monthly),
    life_insurance_annual: text(r.life_insurance_annual),
    health_insurance_annual: text(r.health_insurance_annual),
    pan: r.pan ?? "",
    ssf_number: r.ssf_number ?? "",
    joined_on: r.joined_on ?? "",
  };
}

function toInput(userId: number, d: Draft): SalaryInput | string {
  const num = (v: string | boolean) => (v === "" ? 0 : Number(v));
  const annual = num(d.annual_base);
  if (!annual || annual <= 0) return "Enter a yearly salary above zero.";
  const basic = d.basic_monthly === "" ? null : num(d.basic_monthly);
  if (basic !== null && basic > annual / 12) return "Basic pay can't be more than monthly pay.";
  const str = (v: string | boolean) => (v === "" ? null : String(v).trim());
  return {
    user_id: userId,
    annual_base: annual,
    basic_monthly: basic,
    ssf_enrolled: Boolean(d.ssf_enrolled),
    married: Boolean(d.married),
    female: Boolean(d.female),
    remote_category: (str(d.remote_category) as SalaryInput["remote_category"]) ?? null,
    cit_monthly: num(d.cit_monthly),
    life_insurance_annual: num(d.life_insurance_annual),
    health_insurance_annual: num(d.health_insurance_annual),
    pan: str(d.pan),
    ssf_number: str(d.ssf_number),
    joined_on: str(d.joined_on),
  };
}

function SalaryForm({ row, onDone }: { row: SalaryRow; onDone: (saved: boolean) => void }) {
  const [d, setD] = useState<Draft>(() => draftFrom(row));
  const [error, setError] = useState("");
  const field = (key: keyof Draft, label: string, hint?: string, type = "number") => (
    <label className="space-y-1 text-sm">
      <span className="font-semibold">{label}</span>
      <input
        className="input py-2"
        type={type}
        min={type === "number" ? 0 : undefined}
        value={String(d[key])}
        onChange={(e) => setD({ ...d, [key]: e.target.value })}
      />
      {hint && <span className="block text-muted">{hint}</span>}
    </label>
  );
  const check = (key: keyof Draft, label: string) => (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" checked={Boolean(d[key])} onChange={(e) => setD({ ...d, [key]: e.target.checked })} />
      {label}
    </label>
  );

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const input = toInput(row.user_id, d);
    if (typeof input === "string") return setError(input);
    try {
      await api.setSalary(input);
      onDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save salary");
    }
  }

  return (
    <form className="space-y-4 rounded-card bg-surface-2/60 p-4" onSubmit={save} onKeyDown={(e) => e.key === "Escape" && onDone(false)}>
      <div className="grid gap-4 sm:grid-cols-3">
        {field("annual_base", "Yearly pay (NPR)", "Before SSF and tax, without the Dashain allowance")}
        {field("basic_monthly", "Basic pay per month", "SSF is charged on this. Blank means all of it is basic.")}
        {field("cit_monthly", "CIT per month")}
        {field("life_insurance_annual", "Life insurance premium a year", "Up to NPR 40,000 is deductible")}
        {field("health_insurance_annual", "Health insurance premium a year", "Up to NPR 20,000 is deductible")}
        <label className="space-y-1 text-sm">
          <span className="font-semibold">Remote area</span>
          <select className="input py-2" value={String(d.remote_category)} onChange={(e) => setD({ ...d, remote_category: e.target.value })}>
            <option value="">Not remote</option>
            {["A", "B", "C", "D", "E"].map((c) => <option key={c} value={c}>Category {c}</option>)}
          </select>
        </label>
        {field("pan", "PAN", undefined, "text")}
        {field("ssf_number", "SSF number", undefined, "text")}
        {field("joined_on", "Joined on", "Used to prorate the festival allowance", "date")}
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-2">
        {check("ssf_enrolled", "Contributes to SSF")}
        {check("female", "Woman with salary as her only income (10% tax credit)")}
        {check("married", "Files as a couple (FY 2082/83 and earlier)")}
      </div>
      {error && <p role="alert" className="text-danger">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className="btn-primary px-4 py-2 text-sm">Save</button>
        <button type="button" className="btn-ghost" onClick={() => onDone(false)}>Cancel</button>
      </div>
    </form>
  );
}

export function PayrollPanel() {
  const [rows, setRows] = useState<SalaryRow[]>([]);
  const [period, setPeriod] = useState<PayrollPeriod | null>(null);
  const [report, setReport] = useState<Remittance | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [festival, setFestival] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);

  const load = useCallback(() => {
    api.salaryProfiles().then(setRows).catch((e) => setError(e.message));
    api
      .payrollPeriod()
      .then((p) => {
        setPeriod(p);
        return api.remittance(p.bs_year, p.bs_month).then(setReport);
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  async function run() {
    if (!period) return;
    setRunning(true);
    setError("");
    setMessage("");
    try {
      const res = await api.runPayroll(period.period_start, period.period_end, festival);
      setMessage(
        res.processed
          ? `Done. ${res.processed} ${res.processed === 1 ? "person was" : "people were"} paid for ${res.bs_month}, ${money(res.total_net)} in total after SSF and tax. Their payslips are ready.`
          : `Everyone with a salary is already paid for ${res.bs_month}.`,
      );
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payroll run failed");
    } finally {
      setRunning(false);
    }
  }

  async function downloadSheet() {
    if (!period) return;
    try {
      const blob = await api.remittanceCsv(period.bs_year, period.bs_month);
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `remittance-${period.bs_year}-${String(period.bs_month).padStart(2, "0")}.csv`;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    }
  }

  const missing = rows.filter((r) => r.annual_base === null).length;
  const salaried = rows.filter((r) => r.annual_base !== null);
  const monthly = salaried.reduce((sum, r) => sum + (r.annual_base ?? 0) / 12, 0);
  const allPaid = period !== null && salaried.length > 0 && salaried.every((r) => r.last_bs_month === period.label);
  const label = period?.label ?? "This month";

  return (
    <div id="payroll" className="card scroll-mt-8 space-y-5">
      <div className="space-y-1">
        <h2 className="text-2xl">Payroll</h2>
        <p className="text-muted">
          Paid by Nepali month, with SSF and income tax worked out under the Finance Act for the fiscal year. Every payslip shows how its tax was reached.
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-card bg-navy p-5 text-white">
        <div className="space-y-3">
          <div>
            <p className="font-semibold">{allPaid ? `Done. ${label} is paid.` : `${label} payroll is ready.`}</p>
            <p className="text-sm text-white/60">
              {period && `${fmtDay(period.period_start)} to ${fmtDay(period.period_end)} · FY ${period.fiscal_year} · `}
              {salaried.length} {salaried.length === 1 ? "person" : "people"} · before SSF and tax
            </p>
          </div>
          {allPaid ? (
            <p className="flex items-center gap-2 text-sm font-semibold text-accent"><Check className="h-4 w-4" aria-hidden />Payslips sent</p>
          ) : (
            <div className="flex flex-wrap items-center gap-4">
              <button type="button" className="btn-accent" onClick={run} disabled={running || salaried.length === 0 || !period}>
                {running ? "Paying everyone…" : "Run payroll"}
              </button>
              <label className="flex items-center gap-2 text-sm text-white/80">
                <input type="checkbox" checked={festival} onChange={(e) => setFestival(e.target.checked)} />
                Add the Dashain allowance this month
              </label>
            </div>
          )}
        </div>
        <p className="font-display text-4xl tabular-nums">{money(monthly)}</p>
      </div>
      {message && <p role="status" className="rounded-xl bg-success-soft px-4 py-3 text-success">{message}</p>}
      {error && <p role="alert" className="rounded-xl bg-danger-soft px-4 py-3 text-danger">{error}</p>}
      {missing > 0 && (
        <p className="text-warning">
          {missing} {missing === 1 ? "person has" : "people have"} no salary yet and won&apos;t be paid. Click <b>Set salary</b> next to their name.
        </p>
      )}

      {report && report.people.length > 0 && (
        <div className="space-y-3 rounded-card border border-line p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-lg">What to deposit for {report.bs_month}</h3>
            <button type="button" className="btn-ghost text-sm" onClick={downloadSheet}>
              <Download className="h-4 w-4" aria-hidden /> Sheet for the SSF and IRD portals
            </button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-sm text-muted">Social Security Fund, by {fmtDay(report.ssf.due)}</p>
              <p className="font-display text-2xl tabular-nums">{money(report.ssf.total)}</p>
              <p className="text-sm text-muted">{money(report.ssf.employee)} from staff (11%) + {money(report.ssf.employer)} from you (20%)</p>
            </div>
            <div>
              <p className="text-sm text-muted">Salary TDS to IRD, by {fmtDay(report.ird.due)}</p>
              <p className="font-display text-2xl tabular-nums">{money(report.ird.total)}</p>
              <p className="text-sm text-muted">
                {report.ird.sst_11211 > 0 ? `${money(report.ird.sst_11211)} of it is Social Security Tax (revenue head 11211)` : "No 1% Social Security Tax: everyone is in SSF"}
              </p>
            </div>
          </div>
          {(report.missing_pan.length > 0 || report.missing_ssf_number.length > 0) && (
            <p className="text-sm text-warning">
              {report.missing_pan.length > 0 && <>No PAN for {report.missing_pan.join(", ")}. </>}
              {report.missing_ssf_number.length > 0 && <>No SSF number for {report.missing_ssf_number.join(", ")}.</>}
            </p>
          )}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="text-left text-sm text-muted">
            <tr>
              <th className="py-2 pr-4 font-semibold">Person</th>
              <th className="py-2 pr-4 font-semibold">Monthly pay</th>
              <th className="py-2 pr-4 font-semibold">SSF</th>
              <th className="py-2 pr-4 font-semibold">Last paid</th>
              <th className="py-2 font-semibold"><span className="sr-only">Edit</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((r) =>
              editing === r.user_id ? (
                <tr key={r.user_id}>
                  <td colSpan={5} className="py-3">
                    <p className="mb-2 font-semibold">{r.full_name}</p>
                    <SalaryForm
                      row={r}
                      onDone={(saved) => {
                        setEditing(null);
                        if (saved) load();
                      }}
                    />
                  </td>
                </tr>
              ) : (
                <tr key={r.user_id}>
                  <td className="py-3 pr-4 font-semibold">{r.full_name}</td>
                  <td className="py-3 pr-4 tabular-nums">
                    {r.annual_base !== null ? (
                      <>
                        {money(r.annual_base / 12)}
                        {r.basic_monthly !== null && <span className="block text-sm text-muted">{money(r.basic_monthly)} basic</span>}
                      </>
                    ) : (
                      <span className="text-muted">Not set</span>
                    )}
                  </td>
                  <td className="py-3 pr-4 text-muted">{r.annual_base === null ? "" : r.ssf_enrolled ? "Yes" : "No"}</td>
                  <td className="py-3 pr-4 text-muted">
                    {r.last_net_amount !== null
                      ? `${money(r.last_net_amount)} for ${r.last_bs_month ?? (r.last_period_end && fmtDay(r.last_period_end))}`
                      : "Not paid yet"}
                  </td>
                  <td className="py-3 text-right">
                    <button
                      type="button"
                      className={r.annual_base !== null ? "btn-ghost px-2 py-1" : "btn-secondary px-3 py-1.5 text-sm"}
                      onClick={() => setEditing(r.user_id)}
                    >
                      {r.annual_base !== null ? <><Pencil className="h-4 w-4" aria-hidden /> Edit</> : "Set salary"}
                    </button>
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

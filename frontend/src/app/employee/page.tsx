"use client";

import { useCallback, useEffect, useState } from "react";
import { CalendarCheck, Receipt } from "lucide-react";
import { AuthGate } from "@/components/AuthGate";
import { PageHeader } from "@/components/PageHeader";
import { Alert, Avatar, EmptyState, StatusBadge } from "@/components/ui";
import { api, type LeaveRequest, type Payslip } from "@/lib/api";
import type { SessionUser } from "@/lib/auth";

const money = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "NPR", maximumFractionDigits: 0 }).format(n);
const LEAVE_LABELS: Record<string, string> = { annual: "Annual leave", sick: "Sick leave", unpaid: "Unpaid leave", maternity: "Parental leave" };

function fmtDate(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
function days(l: LeaveRequest) {
  return Math.round((Date.parse(l.end_date) - Date.parse(l.start_date)) / 86_400_000) + 1;
}
function range(l: LeaveRequest) {
  const n = days(l);
  return `${fmtDate(l.start_date)} – ${fmtDate(l.end_date)} · ${n} day${n === 1 ? "" : "s"}`;
}

function Employee({ user }: { user: SessionUser }) {
  const [leave, setLeave] = useState<LeaveRequest[]>([]);
  const [pending, setPending] = useState<LeaveRequest[]>([]);
  const [names, setNames] = useState<Record<number, string>>({});
  const [payslips, setPayslips] = useState<Payslip[] | null>(null);
  const [form, setForm] = useState({ leave_type: "annual", start_date: "", end_date: "", reason: "" });
  const [notice, setNotice] = useState<{ tone: "success" | "danger"; text: string } | null>(null);
  const isAdmin = user.role === "admin";

  const load = useCallback(
    () =>
      Promise.all([api.myLeave(), api.myPayslips(), isAdmin ? api.pendingLeave() : Promise.resolve([])])
        .then(([l, p, pend]) => {
          setLeave(l);
          setPayslips(p);
          setPending(pend);
        })
        .catch((e) => setNotice({ tone: "danger", text: e.message })),
    [isAdmin],
  );

  useEffect(() => {
    void load();
    if (isAdmin) api.users().then((us) => setNames(Object.fromEntries(us.map((u) => [u.id, u.full_name])))).catch(() => undefined);
  }, [load, isAdmin]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.requestLeave(form);
      setForm({ ...form, start_date: "", end_date: "", reason: "" });
      setNotice({ tone: "success", text: "Request sent. You'll see the decision here." });
      await load();
    } catch (err) {
      setNotice({ tone: "danger", text: err instanceof Error ? err.message : "Request failed" });
    }
  }

  async function review(id: number, status: "approved" | "rejected") {
    try {
      await api.reviewLeave(id, status);
      await load();
    } catch (err) {
      setNotice({ tone: "danger", text: err instanceof Error ? err.message : "Review failed" });
    }
  }

  const reviewable = pending.filter((l) => l.user_id !== user.id);

  return (
    <div className="space-y-8">
      <PageHeader title="Time off & payslips" subtitle="Ask for days off, see what was approved, and check your payslips." />
      {notice && <Alert tone={notice.tone}>{notice.text}</Alert>}

      {isAdmin && (
        <section className="card space-y-4">
          <div className="flex items-baseline justify-between">
            <h2 className="text-xl">Waiting for your yes or no</h2>
            <span className="text-sm text-subtle">{reviewable.length} open</span>
          </div>
          {reviewable.length === 0 ? (
            <p className="text-sm text-muted">You&apos;re all caught up.</p>
          ) : (
            <ul className="divide-y divide-line">
              {reviewable.map((l) => (
                <li key={l.id} className="flex flex-wrap items-center gap-4 py-3">
                  <Avatar name={names[l.user_id]} />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-ink">
                      {names[l.user_id] ?? "Team member"} <span className="font-normal text-muted">· {LEAVE_LABELS[l.leave_type] ?? l.leave_type}</span>
                    </p>
                    <p className="text-sm text-muted">{range(l)}{l.reason ? ` · “${l.reason}”` : ""}</p>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" className="btn-secondary py-2" onClick={() => review(l.id, "rejected")}>Decline</button>
                    <button type="button" className="btn-primary py-2" onClick={() => review(l.id, "approved")}>Approve</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <form onSubmit={submit} className="card space-y-4">
          <h2 className="">Request time off</h2>
          <label className="block">
            <span className="label">Type</span>
            <select className="input" value={form.leave_type} onChange={(e) => setForm({ ...form, leave_type: e.target.value })}>
              {Object.entries(LEAVE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label>
              <span className="label">First day</span>
              <input className="input" type="date" required value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
            </label>
            <label>
              <span className="label">Last day</span>
              <input className="input" type="date" required min={form.start_date} value={form.end_date}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
            </label>
          </div>
          <label className="block">
            <span className="label">Note for your manager <span className="font-normal text-subtle">(optional)</span></span>
            <input className="input" maxLength={1024} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
          </label>
          <button className="btn-primary w-full" type="submit">Send request</button>
        </form>

        <section className="card space-y-4">
          <h2 className="">My time off</h2>
          {leave.length === 0 ? (
            <EmptyState icon={CalendarCheck} title="No requests yet">Requests you send appear here with their status.</EmptyState>
          ) : (
            <ul className="divide-y divide-line">
              {leave.map((l) => (
                <li key={l.id} className="flex items-center justify-between gap-3 py-3">
                  <div>
                    <p className="text-sm font-medium text-ink">{LEAVE_LABELS[l.leave_type] ?? l.leave_type}</p>
                    <p className="text-xs text-muted">{range(l)}</p>
                  </div>
                  <StatusBadge status={l.status} />
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="card space-y-4">
        <h2 className="">Payslips</h2>
        {payslips === null ? (
          <div className="h-16 animate-pulse rounded-xl bg-surface-2/60" />
        ) : payslips.length === 0 ? (
          <EmptyState icon={Receipt} title="No payslips yet">They appear here after your company runs payroll.</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-muted">
                <tr>
                  <th className="py-2 pr-4 font-medium">Period</th>
                  <th className="py-2 pr-4 text-right font-medium">Gross</th>
                  <th className="py-2 pr-4 text-right font-medium">SSF</th>
                  <th className="py-2 pr-4 text-right font-medium">Tax (TDS)</th>
                  <th className="py-2 text-right font-medium">Net pay</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line tabular-nums">
                {payslips.map((p) => {
                  const b = p.breakdown;
                  return (
                    <tr key={p.id} className="align-top">
                      <td className="py-2.5 pr-4 text-ink">
                        {b.bs_month ?? new Date(`${p.period_start}T00:00:00`).toLocaleDateString(undefined, { month: "long", year: "numeric" })}
                        {b.projection && (
                          <span className="block max-w-md text-xs text-muted">
                            {b.festival_allowance ? `Includes ${money(b.festival_allowance)} Dashain allowance. ` : ""}
                            Tax for FY {b.fiscal_year}: {money(b.projection.annual_tax)} on {money(b.projection.taxable)} expected
                            taxable income, after {money(b.projection.retirement_deduction)} retirement deduction; spread over the{" "}
                            {b.projection.months_left} months left.
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 text-right text-muted">{money(p.gross_amount)}</td>
                      <td className="py-2.5 pr-4 text-right text-muted">−{money(p.ssf_employee ?? 0)}</td>
                      <td className="py-2.5 pr-4 text-right text-muted">−{money(p.tax_deduction)}</td>
                      <td className="py-2.5 text-right font-semibold text-ink">{money(p.net_amount)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default function EmployeePage() {
  return (
    <AuthGate title="My HR" roles={["admin", "recruiter", "employee"]} demoEmail="employee@aihr.demo">
      {(user) => <Employee user={user} />}
    </AuthGate>
  );
}

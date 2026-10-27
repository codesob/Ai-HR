"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Pencil } from "lucide-react";
import { api, type SalaryRow } from "@/lib/api";

const money = (n: number, currency = "USD") =>
  new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0 }).format(n);

function lastMonth(): { start: string; end: string; label: string } {
  const now = new Date();
  const start = new Date(Date.UTC(now.getFullYear(), now.getMonth() - 1, 1));
  const end = new Date(Date.UTC(now.getFullYear(), now.getMonth(), 0));
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { start: iso(start), end: iso(end), label: start.toLocaleString(undefined, { month: "long", year: "numeric", timeZone: "UTC" }) };
}

export function PayrollPanel() {
  const [rows, setRows] = useState<SalaryRow[]>([]);
  const [editing, setEditing] = useState<Record<number, string>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const period = lastMonth();

  const load = useCallback(() => {
    api.salaryProfiles().then(setRows).catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  async function saveSalary(userId: number) {
    const value = Number(editing[userId]);
    if (!value || value <= 0) return setError("Enter an annual salary above zero.");
    setError("");
    try {
      await api.setSalary(userId, value);
      cancel(userId);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save salary");
    }
  }

  async function run() {
    setRunning(true);
    setError("");
    setMessage("");
    try {
      const res = await api.runPayroll(period.start, period.end);
      setMessage(
        res.processed
          ? `Done. ${res.processed} ${res.processed === 1 ? "person was" : "people were"} paid for ${period.label}, ${money(res.total_net)} in total after tax. Their payslips are ready.`
          : `Everyone with a salary is already paid for ${period.label}.`,
      );
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payroll run failed");
    } finally {
      setRunning(false);
    }
  }

  const missing = rows.filter((r) => r.annual_base === null).length;
  const salaried = rows.filter((r) => r.annual_base !== null);
  // Paid for this period once every salaried person has a payslip reaching its last day.
  const monthly = salaried.reduce((sum, r) => sum + (r.annual_base ?? 0) / 12, 0);
  const allPaid = salaried.length > 0 && salaried.every((r) => r.last_period_end != null && r.last_period_end >= period.end);
  const fmtDay = (iso: string) =>
    new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  const cancel = (userId: number) =>
    setEditing((prev) => {
      const next = { ...prev };
      delete next[userId];
      return next;
    });

  return (
    <div id="payroll" className="card scroll-mt-8 space-y-5">
      <div className="space-y-1">
        <h2 className="text-2xl">Payroll</h2>
        <p className="text-muted">Set each person&apos;s yearly salary, then pay everyone for the month in one click.</p>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-card bg-navy p-5 text-white">
        <div className="space-y-3">
          <div>
            <p className="font-semibold">{allPaid ? `Done. ${period.label} is paid.` : `${period.label} payroll is ready.`}</p>
            <p className="text-sm text-white/60">
              {salaried.length} {salaried.length === 1 ? "person" : "people"} · before tax
            </p>
          </div>
          {allPaid ? (
            <p className="flex items-center gap-2 text-sm font-semibold text-accent"><Check className="h-4 w-4" aria-hidden />Payslips sent</p>
          ) : (
            <button type="button" className="btn-accent" onClick={run} disabled={running || salaried.length === 0}>
              {running ? "Paying everyone…" : "Run payroll"}
            </button>
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
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="text-left text-sm text-muted">
            <tr>
              <th className="py-2 pr-4 font-semibold">Person</th>
              <th className="py-2 pr-4 font-semibold">Yearly salary</th>
              <th className="py-2 pr-4 font-semibold">Last paid</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((r) => (
              <tr key={r.user_id}>
                <td className="py-3 pr-4 font-semibold">{r.full_name}</td>
                <td className="py-3 pr-4">
                  {r.user_id in editing ? (
                    <form
                      className="flex items-center gap-2"
                      onSubmit={(e) => {
                        e.preventDefault();
                        void saveSalary(r.user_id);
                      }}
                    >
                      <input
                        className="input max-w-40 py-2"
                        type="number"
                        min={1}
                        autoFocus
                        aria-label={`Yearly salary for ${r.full_name}`}
                        value={editing[r.user_id]}
                        onKeyDown={(e) => e.key === "Escape" && cancel(r.user_id)}
                        onChange={(e) => setEditing({ ...editing, [r.user_id]: e.target.value })}
                      />
                      <button type="submit" className="btn-primary px-4 py-2 text-sm">Save</button>
                      <button type="button" className="btn-ghost" onClick={() => cancel(r.user_id)}>Cancel</button>
                    </form>
                  ) : (
                    <span className="flex items-center gap-3">
                      {r.annual_base !== null && <span className="tabular-nums">{money(r.annual_base, r.currency ?? "USD")}</span>}
                      <button
                        type="button"
                        className={r.annual_base !== null ? "btn-ghost px-2 py-1" : "btn-secondary px-3 py-1.5 text-sm"}
                        onClick={() => setEditing({ ...editing, [r.user_id]: String(r.annual_base ?? "") })}
                      >
                        {r.annual_base !== null ? <><Pencil className="h-4 w-4" aria-hidden /> Edit</> : "Set salary"}
                      </button>
                    </span>
                  )}
                </td>
                <td className="py-3 pr-4 text-muted">
                  {r.last_period_end && r.last_net_amount !== null
                    ? `${money(r.last_net_amount, r.currency ?? "USD")} on ${fmtDay(r.last_period_end)}`
                    : "Not paid yet"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

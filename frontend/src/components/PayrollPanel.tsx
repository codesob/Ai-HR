"use client";

import { useCallback, useEffect, useState } from "react";
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
      setEditing((prev) => {
        const next = { ...prev };
        delete next[userId];
        return next;
      });
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
          ? `Issued ${res.processed} payslip${res.processed === 1 ? "" : "s"} for ${period.label}, ${money(res.total_net)} net in total.`
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

  return (
    <div className="card space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold">Payroll</h2>
          <p className="text-sm text-muted">
            Payslips use a simplified progressive tax estimate. Review before paying.
          </p>
        </div>
        <button type="button" className="btn-primary" onClick={run} disabled={running || rows.length === missing}>
          {running ? "Running…" : `Run payroll for ${period.label}`}
        </button>
      </div>
      {message && <p className="text-sm text-success">{message}</p>}
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      {missing > 0 && (
        <p className="text-sm text-warning">
          {missing} teammate{missing === 1 ? " has" : "s have"} no salary yet and won&apos;t be paid.
        </p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-muted">
            <tr>
              <th className="py-2 pr-4 font-medium">Name</th>
              <th className="py-2 pr-4 font-medium">Annual salary</th>
              <th className="py-2 pr-4 font-medium">Last payslip</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((r) => (
              <tr key={r.user_id}>
                <td className="py-2 pr-4">
                  {r.full_name} <span className="text-xs capitalize text-subtle">· {r.role}</span>
                </td>
                <td className="py-2 pr-4">
                  {r.user_id in editing ? (
                    <span className="flex items-center gap-2">
                      <input
                        className="input max-w-36 py-1.5"
                        type="number"
                        min={1}
                        aria-label={`Annual salary for ${r.full_name}`}
                        value={editing[r.user_id]}
                        onChange={(e) => setEditing({ ...editing, [r.user_id]: e.target.value })}
                      />
                      <button type="button" className="btn-secondary px-3 py-1.5 text-xs" onClick={() => saveSalary(r.user_id)}>
                        Save
                      </button>
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="text-left hover:text-brand"
                      onClick={() => setEditing({ ...editing, [r.user_id]: String(r.annual_base ?? "") })}
                    >
                      {r.annual_base !== null ? money(r.annual_base, r.currency ?? "USD") : <span className="text-brand">Set salary</span>}
                    </button>
                  )}
                </td>
                <td className="py-2 pr-4 text-muted">
                  {r.last_period_end && r.last_net_amount !== null
                    ? `${money(r.last_net_amount, r.currency ?? "USD")} net · ${r.last_period_end}`
                    : "None yet"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

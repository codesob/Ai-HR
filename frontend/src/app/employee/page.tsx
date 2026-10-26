"use client";

import { useCallback, useEffect, useState } from "react";
import { AuthGate } from "@/components/AuthGate";
import { PageHeader } from "@/components/PageHeader";
import { api, type LeaveRequest, type Payslip } from "@/lib/api";
import type { SessionUser } from "@/lib/auth";

const money = (n: number) => n.toLocaleString(undefined, { style: "currency", currency: "USD" });

function Employee({ user }: { user: SessionUser }) {
  const [leave, setLeave] = useState<LeaveRequest[]>([]);
  const [pending, setPending] = useState<LeaveRequest[]>([]);
  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [form, setForm] = useState({ leave_type: "annual", start_date: "", end_date: "", reason: "" });
  const [message, setMessage] = useState("");

  const load = useCallback(
    () =>
      Promise.all([api.myLeave(), api.myPayslips(), user.role === "admin" ? api.pendingLeave() : []])
        .then(([l, p, pend]) => {
          setLeave(l);
          setPayslips(p);
          setPending(pend);
        })
        .catch((e) => setMessage(e.message)),
    [user.role],
  );

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.requestLeave(form);
      setForm({ ...form, start_date: "", end_date: "", reason: "" });
      setMessage("Leave request submitted for approval.");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Request failed");
    }
  }

  async function review(id: number, status: "approved" | "rejected") {
    try {
      await api.reviewLeave(id, status);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Review failed");
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader title={`Hi, ${user.full_name}`} subtitle="Leave requests and payslips" />
      {message && <p className="text-sm text-indigo-300">{message}</p>}

      <div className="grid gap-6 md:grid-cols-2">
        <form onSubmit={submit} className="card space-y-3">
          <h2 className="font-semibold">Request leave</h2>
          <select className="input" value={form.leave_type} onChange={(e) => setForm({ ...form, leave_type: e.target.value })}>
            <option value="annual">Annual leave</option>
            <option value="sick">Sick leave</option>
            <option value="unpaid">Unpaid leave</option>
            <option value="maternity">Parental leave</option>
          </select>
          <div className="grid grid-cols-2 gap-3">
            <label className="space-y-1 text-sm">
              <span className="text-slate-400">From</span>
              <input className="input" type="date" required value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate-400">To</span>
              <input className="input" type="date" required min={form.start_date} value={form.end_date}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
            </label>
          </div>
          <input className="input" placeholder="Reason (optional)" maxLength={1024} value={form.reason}
            onChange={(e) => setForm({ ...form, reason: e.target.value })} />
          <button className="btn-primary w-full" type="submit">Submit request</button>
        </form>

        <div className="card">
          <h2 className="mb-3 font-semibold">My leave</h2>
          {leave.length === 0 && <p className="text-sm text-slate-500">No leave requests yet.</p>}
          <ul className="space-y-2 text-sm">
            {leave.map((l) => (
              <li key={l.id} className="flex justify-between">
                <span className="capitalize">{l.leave_type} · {l.start_date} → {l.end_date}</span>
                <span className="capitalize text-indigo-300">{l.status}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {user.role === "admin" && (
        <div className="card">
          <h2 className="mb-3 font-semibold">Pending approvals</h2>
          {pending.length === 0 && <p className="text-sm text-slate-500">Nothing to review.</p>}
          <ul className="space-y-3 text-sm">
            {pending.map((l) => (
              <li key={l.id} className="flex flex-wrap items-center justify-between gap-2">
                <span className="capitalize">#{l.user_id} · {l.leave_type} · {l.start_date} → {l.end_date}</span>
                {l.user_id !== user.id && (
                  <span className="flex gap-2">
                    <button type="button" className="btn-secondary px-3 py-1 text-xs" onClick={() => review(l.id, "approved")}>Approve</button>
                    <button type="button" className="btn-secondary px-3 py-1 text-xs" onClick={() => review(l.id, "rejected")}>Reject</button>
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <h2 className="mb-3 font-semibold">Payslips</h2>
        {payslips.length === 0 && <p className="text-sm text-slate-500">No payslips yet.</p>}
        <ul className="space-y-2 text-sm">
          {payslips.map((p) => (
            <li key={p.id} className="flex justify-between">
              <span>{p.period_start} → {p.period_end}</span>
              <span>Net {money(p.net_amount)} <span className="text-slate-500">(gross {money(p.gross_amount)})</span></span>
            </li>
          ))}
        </ul>
      </div>
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

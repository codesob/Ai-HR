"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { Check, Plus, X } from "lucide-react";
import { Alert, Avatar } from "@/components/ui";
import { api, type Onboarding } from "@/lib/api";

const EMPTY = { employee_name: "", employee_email: "", role: "" };

/** New hires' first-week checklists. Hiring someone starts one automatically; HR or the agent ticks tasks off. */
export function OnboardingPanel() {
  const [plans, setPlans] = useState<Onboarding[] | null>(null);
  const [form, setForm] = useState<typeof EMPTY | null>(null);
  const [showDone, setShowDone] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => api.onboarding().then(setPlans).catch((e) => setError(e.message)), []);
  useEffect(() => {
    void load();
  }, [load]);

  async function toggle(plan: Onboarding, taskId: string, completed: boolean) {
    // Optimistic: the box ticks at once; a failure reloads the real state.
    setPlans((ps) => ps?.map((p) => p.id !== plan.id ? p : { ...p, tasks: p.tasks.map((t) => t.id === taskId ? { ...t, completed } : t) }) ?? null);
    try {
      const updated = await api.setOnboardingTask(plan.id, taskId, completed);
      setPlans((ps) => ps?.map((p) => (p.id === updated.id ? updated : p)) ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't update that task.");
      void load();
    }
  }

  async function start(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    try {
      await api.startOnboarding(form);
      setForm(null);
      setError("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't start onboarding.");
    }
  }

  const open = plans?.filter((p) => p.status === "in_progress") ?? [];
  const done = plans?.filter((p) => p.status === "completed") ?? [];

  return (
    <section className="card space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-2xl">New hires</h2>
          <p className="text-muted">Their first-week checklist. It starts by itself when you mark someone hired, and they get a welcome email.</p>
        </div>
        {!form && (
          <button type="button" className="btn-secondary py-2 text-sm" onClick={() => setForm(EMPTY)}>
            <Plus className="h-4 w-4" aria-hidden /> Add a new hire
          </button>
        )}
      </div>
      {error && <Alert>{error}</Alert>}

      {form && (
        <form onSubmit={start} className="grid gap-3 rounded-xl bg-surface-2 p-4 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end">
          <label>
            <span className="label">Name</span>
            <input className="input py-2" required value={form.employee_name} onChange={(e) => setForm({ ...form, employee_name: e.target.value })} />
          </label>
          <label>
            <span className="label">Email</span>
            <input className="input py-2" type="email" required value={form.employee_email} onChange={(e) => setForm({ ...form, employee_email: e.target.value })} />
          </label>
          <label>
            <span className="label">Role</span>
            <input className="input py-2" required value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
          </label>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary py-2 text-sm">Start</button>
            <button type="button" className="btn-ghost px-2" onClick={() => setForm(null)} aria-label="Cancel"><X className="h-4 w-4" aria-hidden /></button>
          </div>
        </form>
      )}

      {plans !== null && open.length === 0 && <p className="text-muted">Nobody is onboarding right now.</p>}
      <ul className="grid gap-4 lg:grid-cols-2">
        {open.map((p) => {
          const left = p.tasks.filter((t) => !t.completed).length;
          const pct = Math.round(((p.tasks.length - left) / Math.max(p.tasks.length, 1)) * 100);
          return (
            <li key={p.id} className="space-y-3 rounded-xl border border-line p-4">
              <div className="flex items-center gap-3">
                <Avatar name={p.employee_name} size="h-10 w-10 text-xs" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold">{p.employee_name}</p>
                  <p className="truncate text-xs text-muted">{p.role} · {p.employee_email}</p>
                </div>
                <span className="font-display text-xl tabular-nums">{pct}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-surface-2">
                <div className="h-1.5 rounded-full bg-brand transition-all" style={{ width: `${pct}%` }} />
              </div>
              <ul className="space-y-1">
                {p.tasks.map((t) => (
                  <li key={t.id}>
                    <label className="flex cursor-pointer items-center gap-2.5 rounded-lg px-1 py-1 text-sm hover:bg-surface-2">
                      <input type="checkbox" className="sr-only" checked={t.completed} onChange={(e) => toggle(p, t.id, e.target.checked)} />
                      <span aria-hidden className={clsx(
                        "flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded-md border",
                        t.completed ? "border-brand bg-brand text-white" : "border-line-strong bg-surface",
                      )}>
                        {t.completed && <Check className="h-3 w-3" />}
                      </span>
                      <span className={t.completed ? "text-muted line-through" : "text-ink-soft"}>{t.title}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </li>
          );
        })}
      </ul>

      {done.length > 0 && (
        <button type="button" className="text-sm font-semibold text-brand underline underline-offset-4" onClick={() => setShowDone((v) => !v)}>
          {showDone ? "Hide" : "Show"} {done.length} finished
        </button>
      )}
      {showDone && (
        <ul className="divide-y divide-line text-sm">
          {done.map((p) => (
            <li key={p.id} className="flex justify-between py-2">
              <span><b className="font-semibold">{p.employee_name}</b> · {p.role}</span>
              <span className="flex items-center gap-1 text-brand"><Check className="h-4 w-4" aria-hidden />All done</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

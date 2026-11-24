"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowUp, CalendarDays } from "lucide-react";
import { AuthGate } from "@/components/AuthGate";
import { PageHeader } from "@/components/PageHeader";
import { ApprovalCard, StepList } from "@/components/Agent";
import { Alert } from "@/components/ui";
import { api, type AgentAction, type AgentRun, type Analytics, type Application, type Interview } from "@/lib/api";
import type { SessionUser } from "@/lib/auth";

// Plain-language names for pipeline stages.
const PIPELINE: [string, string][] = [
  ["applied", "New applicants"],
  ["screening", "Being screened"],
  ["assessment", "Taking a test"],
  ["interview", "Interviewing"],
  ["offer", "Offer sent"],
  ["hired", "Hired"],
];

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

/** The HR agent: run the day's work, give it an instruction, and approve what it proposes. */
function AgentPanel() {
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [run, setRun] = useState<AgentRun | null>(null);
  const [waiting, setWaiting] = useState<AgentAction[]>([]);
  const [instruction, setInstruction] = useState("");
  const [working, setWorking] = useState<"day" | "ask" | null>(null);
  const [error, setError] = useState("");

  const loadWaiting = useCallback(() => api.agentActions().then(setWaiting).catch(() => undefined), []);

  useEffect(() => {
    api.agentStatus().then((s) => setConfigured(s.configured)).catch(() => setConfigured(false));
    api.agentRuns().then((runs) => setRun(runs[0] ?? null)).catch(() => undefined);
    void loadWaiting();
  }, [loadWaiting]);

  async function go(kind: "day" | "ask") {
    setWorking(kind);
    setError("");
    try {
      const result = await api.agentRun(kind === "ask" ? instruction : undefined);
      setRun(result);
      if (kind === "ask") setInstruction("");
      await loadWaiting();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The agent couldn't run.");
    } finally {
      setWorking(null);
    }
  }

  async function decide(id: number, approve: boolean) {
    try {
      const done = approve ? await api.approveAction(id) : await api.rejectAction(id);
      if (done.status === "failed") setError(done.result.error ?? "That didn't work.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "That didn't work.");
    }
    await loadWaiting();
  }

  return (
    <section className="space-y-6">
      <div className="grid gap-4 rounded-2xl bg-navy p-6 text-white sm:p-8 lg:grid-cols-[1fr_1.1fr] lg:items-center">
        <div className="space-y-3">
          <p className="note text-accent">your HR agent</p>
          <h2 className="text-3xl text-white">It does the HR work. You make the big calls.</h2>
          <p className="text-white/70">
            It screens applicants, books interviews, approves time off that fits the policy, answers employees and
            prepares payroll. Rejections, offers and payroll wait below for your OK.
          </p>
        </div>
        <div className="space-y-3">
          {configured === false ? (
            <p className="rounded-xl bg-white/10 p-4 text-sm text-white/80">
              The agent needs a language model. Add <code className="font-semibold text-accent">GROQ_API_KEY</code> to the server&apos;s
              .env and restart.
            </p>
          ) : (
            <>
              <button type="button" className="btn-accent w-full py-3 text-base" onClick={() => go("day")} disabled={working !== null}>
                {working === "day" ? "Working… this takes a few seconds" : "Do today's HR work"}
              </button>
              <form
                className="flex gap-2 rounded-full bg-white/10 p-1.5"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (instruction.trim()) void go("ask");
                }}
              >
                <label htmlFor="agent-instruction" className="sr-only">Tell the agent what to do</label>
                <input
                  id="agent-instruction"
                  className="min-w-0 flex-1 bg-transparent px-3 text-sm text-white placeholder:text-white/50 focus:outline-hidden"
                  placeholder="Or tell it: “Book interviews with the top 2 for Senior ML Engineer”"
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                />
                <button type="submit" className="btn-accent h-9 w-9 shrink-0 p-0" disabled={working !== null || !instruction.trim()} aria-label="Send">
                  <ArrowUp className="h-4 w-4" aria-hidden />
                </button>
              </form>
            </>
          )}
        </div>
      </div>

      {error && <Alert>{error}</Alert>}

      <div className="grid gap-6 lg:grid-cols-2">
        <div id="approvals" className="scroll-mt-8 space-y-3">
          <h2 className="text-2xl">Waiting for your OK</h2>
          {waiting.length === 0 ? (
            <p className="card text-muted">Nothing waiting. The agent will put rejections, offers and payroll here for you.</p>
          ) : (
            <ul className="space-y-3">
              {waiting.map((a) => <ApprovalCard key={a.id} action={a} onDecide={decide} />)}
            </ul>
          )}
        </div>
        <div className="space-y-3">
          <h2 className="text-2xl">What it did</h2>
          {!run ? (
            <p className="card text-muted">Nothing yet. Press <b>Do today&apos;s HR work</b> to start.</p>
          ) : (
            <div className="card space-y-4">
              <p className="text-xs text-muted">
                {new Date(run.created_at).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" })}
                {run.trigger === "schedule" ? " · scheduled run" : ""}
              </p>
              <p className="whitespace-pre-wrap text-ink-soft">{run.reply}</p>
              <StepList steps={run.steps} className="border-t border-line pt-3" />
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function StatCard({ value, label }: { value: React.ReactNode; label: string }) {
  return (
    <div className="card p-5">
      <p className="font-display text-4xl tabular-nums">{value}</p>
      <p className="mt-1 text-sm text-muted">{label}</p>
    </div>
  );
}

function Home({ user }: { user: SessionUser }) {
  const [data, setData] = useState<Analytics | null>(null);
  const [interviews, setInterviews] = useState<(Interview & { who?: string; role?: string })[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.analytics().then(setData).catch((e) => setError(e.message));
    Promise.all([api.interviews(), api.applications()])
      .then(([ivs, apps]) => {
        const byId = new Map<number, Application>(apps.map((a) => [a.id, a]));
        setInterviews(
          ivs
            .filter((i) => i.status === "scheduled" && new Date(i.scheduled_at) >= new Date())
            .sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at))
            .slice(0, 4)
            .map((i) => ({ ...i, who: byId.get(i.application_id)?.candidate_name, role: byId.get(i.application_id)?.job_title })),
        );
      })
      .catch(() => undefined);
  }, []);

  return (
    <div className="space-y-12">
      <PageHeader
        title={`${greeting()}, ${user.full_name.split(" ")[0]}`}
        subtitle="Your HR agent handles the routine work. Check what it did and approve the big calls."
      />
      {error && <Alert>{error}</Alert>}

      <AgentPanel />

      <section className="space-y-5">
        <h2 className="text-xl">Hiring at a glance</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard value={data?.open_jobs ?? "–"} label="open jobs" />
          <StatCard value={data?.total_applications ?? "–"} label="people applied" />
          <StatCard value={data?.avg_time_to_hire_days != null ? `${Math.round(data.avg_time_to_hire_days)}d` : "–"} label="average time to hire" />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card space-y-4">
            <h3 className="text-lg font-semibold">Where everyone is</h3>
            <ul className="space-y-3">
              {PIPELINE.map(([stage, label]) => {
                const count = data?.funnel[stage] ?? 0;
                const pct = data ? Math.round((count / Math.max(data.total_applications, 1)) * 100) : 0;
                return (
                  <li key={stage} className="grid grid-cols-[8.5rem_1fr_2rem] items-center gap-3">
                    <span className="text-sm text-ink-soft">{label}</span>
                    <div className="h-2.5 rounded-full bg-surface-2">
                      <div className="h-2.5 rounded-full bg-brand" style={{ width: `${Math.max(pct, count ? 4 : 0)}%` }} />
                    </div>
                    <span className="text-right font-semibold tabular-nums">{data ? count : "–"}</span>
                  </li>
                );
              })}
            </ul>
          </div>

          <div className="card space-y-4">
            <h3 className="text-lg font-semibold">Coming up: interviews</h3>
            {interviews.length === 0 ? (
              <p className="text-muted">No interviews scheduled.</p>
            ) : (
              <ul className="divide-y divide-line">
                {interviews.map((i) => (
                  <li key={i.id} className="flex items-center gap-4 py-3">
                    <CalendarDays className="h-5 w-5 shrink-0 text-muted" aria-hidden />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold">{i.who ?? "Candidate"}</p>
                      <p className="truncate text-sm text-muted">{i.role}</p>
                    </div>
                    <time className="text-right text-sm text-muted" dateTime={i.scheduled_at}>
                      {new Date(i.scheduled_at).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}
                      <br />
                      {new Date(i.scheduled_at).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
                    </time>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

export default function AdminPage() {
  return (
    <AuthGate title="Home" roles={["admin", "recruiter"]} demoEmail="admin@aihr.demo">
      {(user) => <Home user={user} />}
    </AuthGate>
  );
}

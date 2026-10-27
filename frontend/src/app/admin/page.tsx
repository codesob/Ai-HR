"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, CalendarDays, Inbox } from "lucide-react";
import { AuthGate } from "@/components/AuthGate";
import { PageHeader } from "@/components/PageHeader";
import { Alert, EmptyState, Stat } from "@/components/ui";
import { api, type Analytics, type Application, type Interview, type LeaveRequest } from "@/lib/api";
import type { SessionUser } from "@/lib/auth";

const SOURCE_LABELS: Record<string, string> = {
  careers_page: "Careers page", linkedin: "LinkedIn", job_board: "Job boards", referral: "Referrals", other: "Other",
};

const PIPELINE = ["applied", "screening", "assessment", "interview", "offer", "hired"];

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

function Overview({ user }: { user: SessionUser }) {
  const [data, setData] = useState<Analytics | null>(null);
  const [interviews, setInterviews] = useState<(Interview & { who?: string; role?: string })[]>([]);
  const [pending, setPending] = useState<LeaveRequest[]>([]);
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
            .slice(0, 5)
            .map((i) => ({ ...i, who: byId.get(i.application_id)?.candidate_name, role: byId.get(i.application_id)?.job_title })),
        );
      })
      .catch(() => undefined);
    if (user.role === "admin") api.pendingLeave().then(setPending).catch(() => undefined);
  }, [user.role]);

  const firstName = user.full_name.split(" ")[0];
  const active = data ? PIPELINE.reduce((n, s) => n + (data.funnel[s] ?? 0), 0) : 0;
  const sources = data ? Object.entries(data.source_effectiveness).sort((a, b) => b[1] - a[1]) : [];

  return (
    <div className="space-y-8">
      <PageHeader title={`${greeting()}, ${firstName}`} subtitle="Here's where hiring stands today" />
      {error && <Alert>{error}</Alert>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Open roles" value={data?.open_jobs ?? "–"} hint={data ? `${data.total_jobs} total` : undefined} />
        <Stat label="Applicants" value={data?.total_applications ?? "–"} hint={data ? `${data.funnel.rejected ?? 0} rejected` : undefined} />
        <Stat
          label="Average match"
          value={data?.avg_match_score != null ? Math.round(data.avg_match_score * 100) : "–"}
          hint="Out of 100, across all applicants"
        />
        <Stat
          label="Time to hire"
          value={data?.avg_time_to_hire_days != null ? `${Math.round(data.avg_time_to_hire_days)}d` : "–"}
          hint="Application to hire, average"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <section className="card space-y-5">
          <div className="flex items-baseline justify-between">
            <h2 className="font-semibold">Pipeline</h2>
            <span className="text-sm text-subtle">{active} active or hired</span>
          </div>
          {!data ? (
            <div className="h-48 animate-pulse rounded-xl bg-surface-2/60" />
          ) : data.total_applications === 0 ? (
            <EmptyState icon={Inbox} title="No applications yet">Publish a role and share your careers page.</EmptyState>
          ) : (
            <ol className="space-y-3">
              {PIPELINE.map((stage) => {
                const count = data.funnel[stage] ?? 0;
                const pct = Math.round((count / Math.max(data.total_applications, 1)) * 100);
                return (
                  <li key={stage} className="grid grid-cols-[6.5rem_1fr_2.5rem] items-center gap-3 text-sm">
                    <span className="capitalize text-ink-soft">{stage}</span>
                    <div className="h-2.5 rounded-full bg-surface-2">
                      <div className="h-2.5 rounded-full bg-brand" style={{ width: `${Math.max(pct, count ? 3 : 0)}%` }} />
                    </div>
                    <span className="text-right font-medium tabular-nums text-ink">{count}</span>
                  </li>
                );
              })}
            </ol>
          )}
        </section>

        <section className="card space-y-5">
          <h2 className="font-semibold">Where applicants come from</h2>
          {sources.length === 0 ? (
            <p className="text-sm text-muted">No applications yet.</p>
          ) : (
            <ul className="space-y-3">
              {sources.map(([src, pct]) => (
                <li key={src} className="space-y-1.5 text-sm">
                  <div className="flex justify-between">
                    <span className="text-ink-soft">{SOURCE_LABELS[src] ?? src.replace(/_/g, " ")}</span>
                    <span className="font-medium tabular-nums">{pct}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-surface-2">
                    <div className="h-1.5 rounded-full bg-navy" style={{ width: `${pct}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Upcoming interviews</h2>
            <Link href="/recruiter" className="btn-ghost px-2 text-brand">Recruiting <ArrowRight className="h-4 w-4" aria-hidden /></Link>
          </div>
          {interviews.length === 0 ? (
            <p className="text-sm text-muted">Nothing scheduled.</p>
          ) : (
            <ul className="divide-y divide-line">
              {interviews.map((i) => (
                <li key={i.id} className="flex items-center gap-3 py-3">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-soft">
                    <CalendarDays className="h-4 w-4 text-brand" aria-hidden />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">{i.who ?? "Candidate"}</p>
                    <p className="truncate text-xs text-muted">{i.role}</p>
                  </div>
                  <time className="text-right text-xs text-muted" dateTime={i.scheduled_at}>
                    {new Date(i.scheduled_at).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}
                    <br />
                    {new Date(i.scheduled_at).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
                  </time>
                </li>
              ))}
            </ul>
          )}
        </section>

        {user.role === "admin" && (
          <section className="card space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">Needs your approval</h2>
              <Link href="/employee" className="btn-ghost px-2 text-brand">Review <ArrowRight className="h-4 w-4" aria-hidden /></Link>
            </div>
            {pending.length === 0 ? (
              <p className="text-sm text-muted">You&apos;re all caught up.</p>
            ) : (
              <p className="text-sm text-ink-soft">
                <span className="text-3xl font-semibold text-ink">{pending.length}</span>{" "}
                leave request{pending.length === 1 ? "" : "s"} waiting for a decision.
              </p>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

export default function AdminPage() {
  return (
    <AuthGate title="Overview" roles={["admin", "recruiter"]} demoEmail="admin@aihr.demo">
      {(user) => <Overview user={user} />}
    </AuthGate>
  );
}

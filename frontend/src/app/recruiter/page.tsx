"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { ArrowRight, Briefcase, Check, ChevronDown, CircleAlert, PenLine, Plus, Share2, Users, X } from "lucide-react";
import { AuthGate } from "@/components/AuthGate";
import { PageHeader } from "@/components/PageHeader";
import { ScreeningPanel } from "@/components/ScreeningPanel";
import { Alert, Avatar, EmptyState, Label, MiniBar } from "@/components/ui";
import { api, type Job, type RankedCandidate } from "@/lib/api";

const STATUSES = ["applied", "screening", "assessment", "interview", "offer", "hired", "rejected"];
const EMPTY_JOB = { title: "", department: "Engineering", description: "", required_skills: "", min_experience_years: 0 };

function JobForm({ onCreated, onCancel }: { onCreated: (job: Job) => void; onCancel: () => void }) {
  const [job, setJob] = useState(EMPTY_JOB);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      onCreated(await api.createJob({
        ...job,
        required_skills: job.required_skills.split(",").map((s) => s.trim()).filter(Boolean),
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create job");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-xl">Post a job</h2>
        <button type="button" className="btn-ghost px-2" onClick={onCancel} aria-label="Close">
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>
      {error && <Alert>{error}</Alert>}
      <div className="grid gap-4 sm:grid-cols-2">
        <label>
          <span className="label">Job title</span>
          <input className="input" required minLength={2} value={job.title} placeholder="e.g. Backend Engineer"
            onChange={(e) => setJob({ ...job, title: e.target.value })} />
        </label>
        <label>
          <span className="label">Department</span>
          <input className="input" value={job.department} onChange={(e) => setJob({ ...job, department: e.target.value })} />
        </label>
        <label className="sm:col-span-2">
          <span className="label">Description</span>
          <textarea className="input" rows={4} required minLength={10} value={job.description}
            placeholder="What will this person do, and what does success look like?"
            onChange={(e) => setJob({ ...job, description: e.target.value })} />
        </label>
        <label>
          <span className="label">Required skills</span>
          <input className="input" value={job.required_skills} placeholder="Python, SQL, Docker"
            onChange={(e) => setJob({ ...job, required_skills: e.target.value })} />
          <span className="mt-1 block text-xs text-subtle">Comma separated. Used to show matches and gaps.</span>
        </label>
        <label>
          <span className="label">Minimum years of experience</span>
          <input className="input" type="number" min={0} step={0.5} value={job.min_experience_years}
            onChange={(e) => setJob({ ...job, min_experience_years: Number(e.target.value) })} />
        </label>
      </div>
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
        <button className="btn-primary" type="submit" disabled={saving}>{saving ? "Posting…" : "Post job"}</button>
      </div>
    </form>
  );
}

// Each stage, in order, with how it reads as a next step and as a current state.
const STAGES: { key: string; next: string; now: string }[] = [
  { key: "applied", next: "", now: "New applicant" },
  { key: "screening", next: "Move to Screening", now: "Being screened" },
  { key: "assessment", next: "Send a test", now: "Taking a test" },
  { key: "interview", next: "Move to Interview", now: "Interviewing" },
  { key: "offer", next: "Make an offer", now: "Offer sent" },
  { key: "hired", next: "Mark as hired", now: "Hired" },
];

function verdict(score: number | null) {
  if (score == null) return { label: "Not scored yet", tone: "bg-surface-2 text-muted" };
  if (score >= 0.75) return { label: "Strong match", tone: "bg-brand-soft text-brand" };
  if (score >= 0.55) return { label: "Good match", tone: "bg-brand-soft text-brand" };
  if (score >= 0.4) return { label: "Partial match", tone: "bg-accent-soft text-warning" };
  return { label: "Weak match", tone: "bg-surface-2 text-muted" };
}

function stageLabel(status: string) {
  return status === "rejected" ? "Rejected" : STAGES.find((s) => s.key === status)?.now ?? status;
}

function StageBadge({ status }: { status: string }) {
  if (status === "applied") return <span className="badge bg-accent-soft text-warning">New</span>;
  if (status === "hired") return <span className="badge bg-brand text-white">Hired</span>;
  if (status === "rejected") return <span className="badge bg-surface-2 text-muted">Rejected</span>;
  return <span className="badge hidden bg-brand-soft text-brand sm:inline-flex">{stageLabel(status)}</span>;
}

function score(c: RankedCandidate) {
  return c.match_score == null ? null : Math.round(c.match_score * 100);
}

/** Right-hand panel: one applicant, the reasons for the score, and the next step. */
function CandidateDetail({ c, jobTitle, onStatus, onChanged }: {
  c: RankedCandidate; jobTitle: string; onStatus: (s: string) => void; onChanged: () => void;
}) {
  const [open, setOpen] = useState(false);
  const exp = c.match_explanation;
  const matched = exp?.matched_skills ?? [];
  const missing = exp?.missing_skills ?? [];
  const total = matched.length + missing.length;
  const v = verdict(c.match_score);
  const pct = score(c);
  const idx = STAGES.findIndex((s) => s.key === c.status);
  const next = idx >= 0 ? STAGES[idx + 1] : undefined;
  const done = c.status === "hired" || c.status === "rejected";
  const skills = exp?.skill_gap_score == null ? undefined : 1 - exp.skill_gap_score;

  return (
    <div className="space-y-5 p-5 sm:p-6">
      <div className="flex items-center gap-3">
        <Avatar name={c.candidate_name} size="h-12 w-12 text-sm" />
        <div className="min-w-0">
          <p className="truncate font-display text-2xl leading-tight">{c.candidate_name ?? "Unnamed candidate"}</p>
          <p className="text-sm text-muted">
            {stageLabel(c.status)} · <span className={clsx("rounded-full px-2 py-0.5 text-xs font-semibold", v.tone)}>{v.label}</span>
            {c.source === "linkedin" && <span className="ml-1 rounded-full bg-[#e8f0fb] px-2 py-0.5 text-xs font-semibold text-[#0a66c2]">via LinkedIn</span>}
          </p>
        </div>
      </div>

      {pct != null && (
        <div className="space-y-1.5">
          <p className="flex justify-between text-sm font-semibold"><span>Match with the job</span><span className="tabular-nums">{pct} / 100</span></p>
          <div className="h-2 rounded-full bg-surface-2">
            <div className="h-2 rounded-full bg-brand transition-all duration-300" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      <div className="space-y-2">
        <Label>Why</Label>
        <ul className="space-y-2 text-[0.95rem]">
          {total > 0 && (
            <li className="flex gap-2.5">
              {missing.length === 0
                ? <Check className="mt-0.5 h-4.5 w-4.5 shrink-0 text-brand" aria-label="Meets" />
                : <CircleAlert className="mt-0.5 h-4.5 w-4.5 shrink-0 text-warning" aria-label="Gap" />}
              <span>
                {missing.length === 0
                  ? `Matches all ${total} required skills`
                  : `Matches ${matched.length} of ${total} required skills. Missing: ${missing.join(", ")}`}
              </span>
            </li>
          )}
          {exp?.experience_fit != null && (
            <li className="flex gap-2.5">
              {exp.experience_fit >= 1
                ? <Check className="mt-0.5 h-4.5 w-4.5 shrink-0 text-brand" aria-label="Meets" />
                : <CircleAlert className="mt-0.5 h-4.5 w-4.5 shrink-0 text-warning" aria-label="Gap" />}
              <span>{exp.experience_fit >= 1 ? "Enough experience for the role" : "Less experience than the job asks for"}</span>
            </li>
          )}
          {total === 0 && exp?.experience_fit == null && <li className="text-muted">No details yet. The resume may still be processing.</li>}
        </ul>
      </div>

      <div className="flex flex-wrap gap-2">
        {!done && <button type="button" className="btn-secondary flex-1 py-2.5" onClick={() => onStatus("rejected")}>Reject</button>}
        {!done && next && (
          <button type="button" className="btn-primary flex-1 py-2.5" onClick={() => onStatus(next.key)}>
            {next.next} <ArrowRight className="h-4 w-4" aria-hidden />
          </button>
        )}
        {c.status === "hired" && (
          <p className="flex items-center gap-2 font-semibold text-brand"><Check className="h-4 w-4" aria-hidden />Hired</p>
        )}
        {c.status === "rejected" && (
          <button type="button" className="btn-secondary py-2.5" onClick={() => onStatus("screening")}>Undo reject</button>
        )}
      </div>

      <ScreeningPanel applicationId={c.application_id} jobTitle={jobTitle} closed={done} onChange={onChanged} />

      <div className="border-t border-line pt-3">
        <button type="button" className="flex w-full items-center justify-between py-1 text-sm font-semibold text-ink" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
          How the score adds up
          <ChevronDown className={clsx("h-4 w-4 transition", open && "rotate-180")} aria-hidden />
        </button>
        {open && (
          <div className="mt-3 space-y-4">
            <div className="flex flex-col gap-3">
              <MiniBar label="Resume fits the job (45%)" value={exp?.semantic_similarity} />
              <MiniBar label="Required skills (35%)" value={skills} />
              <MiniBar label="Experience (20%)" value={exp?.experience_fit} />
            </div>
            {total > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {matched.map((s) => (
                  <span key={s} className="badge bg-brand-soft text-brand"><Check className="h-3 w-3" aria-hidden />{s}</span>
                ))}
                {missing.map((s) => (
                  <span key={s} className="badge bg-accent-soft text-warning"><X className="h-3 w-3" aria-hidden />{s}</span>
                ))}
              </div>
            )}
            <label className="flex items-center gap-2 text-sm text-muted">
              Set step manually
              <select className="input w-auto py-1.5 text-sm capitalize" value={c.status} onChange={(e) => onStatus(e.target.value)}>
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
          </div>
        )}
      </div>
    </div>
  );
}

function Recruiter() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [applicants, setApplicants] = useState<Record<number, number>>({});
  const [selectedJob, setSelectedJob] = useState<number | null>(null);
  const [ranked, setRanked] = useState<RankedCandidate[] | null>(null);
  const [selectedApp, setSelectedApp] = useState<number | null>(null);
  const [orgSlug, setOrgSlug] = useState<string | null>(null);
  const [jd, setJd] = useState<Record<string, unknown> | null>(null);
  const [drafting, setDrafting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  const loadJobs = useCallback(
    () => Promise.all([api.jobs(), api.applications().catch(() => [])]).then(([all, apps]) => {
      const counts: Record<number, number> = {};
      for (const a of apps) counts[a.job_id] = (counts[a.job_id] ?? 0) + 1;
      setApplicants(counts);
      // Open jobs first, busiest first, so the page opens on the job with the most to review.
      const byCount = (x: Job, y: Job) => (counts[y.id] ?? 0) - (counts[x.id] ?? 0);
      const j = [...all.filter((x) => x.status === "open").sort(byCount), ...all.filter((x) => x.status !== "open")];
      setJobs(j);
      setSelectedJob((current) => current ?? j.find((x) => x.status === "open")?.id ?? j[0]?.id ?? null);
    }).catch((e) => setError(e.message)),
    [],
  );
  const loadRanked = useCallback(
    (jobId: number) => api.ranked(jobId).then(setRanked).catch((e) => setError(e.message)),
    [],
  );

  useEffect(() => { void loadJobs(); }, [loadJobs]);
  useEffect(() => { api.organization().then((o) => setOrgSlug(o.slug)).catch(() => undefined); }, []);
  useEffect(() => {
    if (selectedJob) void loadRanked(selectedJob);
  }, [selectedJob, loadRanked]);

  function selectJob(id: number) {
    if (id === selectedJob) return;
    setRanked(null);
    setSelectedApp(null);
    setJd(null);
    setSelectedJob(id);
  }

  async function generateJD() {
    const job = jobs.find((j) => j.id === selectedJob);
    if (!job) return;
    setDrafting(true);
    try {
      setJd(await api.generateJD({ title: job.title, department: job.department, seniority: "senior", key_skills: job.required_skills }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't draft a description");
    } finally {
      setDrafting(false);
    }
  }

  async function setStatus(applicationId: number, status: string) {
    try {
      await api.setApplicationStatus(applicationId, status);
      if (selectedJob) await loadRanked(selectedJob);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  const job = jobs.find((j) => j.id === selectedJob);
  const openJobs = jobs.filter((j) => j.status === "open");
  const closedJobs = jobs.filter((j) => j.status !== "open");
  const current = ranked?.find((c) => c.application_id === selectedApp) ?? ranked?.[0];
  const newCount = ranked?.filter((c) => c.status === "applied").length ?? 0;

  const jobButton = (j: Job) => (
    <li key={j.id}>
      <button
        type="button"
        onClick={() => selectJob(j.id)}
        aria-current={selectedJob === j.id ? "true" : undefined}
        className={clsx(
          "flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition",
          selectedJob === j.id ? "bg-brand-soft font-semibold text-brand" : "text-ink-soft hover:bg-surface-2",
        )}
      >
        <span className="truncate">{j.title}</span>
        <span className="tabular-nums">{applicants[j.id] ?? 0}</span>
      </button>
    </li>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Hiring"
        subtitle="Pick a job, then a person. The closest fits are at the top, with the reasons written down."
        action={!showForm && (
          <button type="button" className="btn-primary" onClick={() => setShowForm(true)}>
            <Plus className="h-4 w-4" aria-hidden />
            Post a job
          </button>
        )}
      />
      {error && <Alert>{error}</Alert>}

      {showForm && (
        <JobForm
          onCancel={() => setShowForm(false)}
          onCreated={async (created) => {
            setShowForm(false);
            await loadJobs();
            selectJob(created.id);
          }}
        />
      )}

      {jd && (
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <p className="eyebrow">Draft job ad · {job?.title}</p>
            <button type="button" className="btn-ghost px-2" onClick={() => setJd(null)} aria-label="Dismiss draft">
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
          <p className="text-ink-soft">{String(jd.description ?? "")}</p>
          {Array.isArray(jd.responsibilities) && (
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
              {(jd.responsibilities as string[]).map((r) => <li key={r}>{r}</li>)}
            </ul>
          )}
          {jd.salary_band ? <p className="text-sm font-medium text-brand">{String(jd.salary_band)}</p> : null}
        </div>
      )}

      {jobs.length > 0 && (
        <label className="block lg:hidden">
          <span className="label">Job</span>
          <select className="input" value={selectedJob ?? ""} onChange={(e) => selectJob(Number(e.target.value))}>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>{j.title} ({applicants[j.id] ?? 0}){j.status !== "open" ? ` · ${j.status}` : ""}</option>
            ))}
          </select>
        </label>
      )}

      <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-(--shadow-lift)">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2.5 text-sm">
          <p className="text-muted">Hiring › <span className="font-semibold text-ink">{job?.title ?? "No job selected"}</span></p>
          <div className="flex items-center gap-3">
            {ranked && <span className="text-muted">{newCount} new · {ranked.length} applied</span>}
            {job && orgSlug && (
              <a className="btn-ghost py-1" target="_blank" rel="noopener noreferrer"
                href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(
                  `${window.location.origin}/careers/${orgSlug}?source=linkedin&job=${job.id}`)}`}>
                <Share2 className="h-4 w-4" aria-hidden /> Share on LinkedIn
              </a>
            )}
            {job && (
              <button type="button" className="btn-ghost py-1" onClick={generateJD} disabled={drafting}>
                <PenLine className="h-4 w-4" aria-hidden />
                {drafting ? "Drafting…" : "Draft a job ad"}
              </button>
            )}
          </div>
        </div>

        <div className="grid lg:grid-cols-[13rem_1fr_1.1fr]">
          <nav aria-label="Jobs" className="hidden space-y-5 border-r border-line p-3 lg:block">
            <div className="space-y-1">
              <Label className="px-2.5 pb-1">Open jobs</Label>
              {openJobs.length === 0 && <p className="px-2.5 text-sm text-muted">No open jobs. Post one.</p>}
              <ul className="space-y-0.5">{openJobs.map(jobButton)}</ul>
            </div>
            {closedJobs.length > 0 && (
              <div className="space-y-1">
                <Label className="px-2.5 pb-1">Closed</Label>
                <ul className="space-y-0.5">{closedJobs.map(jobButton)}</ul>
              </div>
            )}
          </nav>

          <section aria-label="Applicants" className="min-w-0 border-b border-line p-3 lg:border-r lg:border-b-0">
            <div className="flex justify-between px-2.5 pb-2">
              <Label>Applicant</Label>
              <Label>Match</Label>
            </div>
            {!job ? (
              <EmptyState icon={Briefcase} title="Pick a job to see who applied" />
            ) : ranked === null ? (
              <div className="space-y-2" aria-busy="true">
                {[0, 1, 2, 3].map((i) => <div key={i} className="h-14 animate-pulse rounded-xl bg-surface-2" />)}
              </div>
            ) : ranked.length === 0 ? (
              <EmptyState icon={Users} title="No applicants yet">
                Share your careers page (link on <b>Team &amp; payroll</b>). New applicants show up here, already scored.
              </EmptyState>
            ) : (
              <ol className="space-y-1">
                {ranked.map((c) => (
                  <li key={c.application_id}>
                    <button
                      type="button"
                      onClick={() => setSelectedApp(c.application_id)}
                      aria-pressed={current?.application_id === c.application_id}
                      className={clsx(
                        "flex w-full items-center gap-3 rounded-xl border px-2.5 py-2 text-left transition",
                        current?.application_id === c.application_id ? "border-brand bg-brand-soft/60" : "border-transparent hover:bg-surface-2",
                        c.status === "rejected" && "opacity-60",
                      )}
                    >
                      <Avatar name={c.candidate_name} size="h-9 w-9 text-xs" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-semibold">{c.candidate_name ?? "Unnamed candidate"}</span>
                        <span className="block truncate text-xs text-muted">{verdict(c.match_score).label}</span>
                      </span>
                      <StageBadge status={c.status} />
                      <span className="w-9 text-right font-display text-xl tabular-nums">{score(c) ?? "–"}</span>
                    </button>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section aria-label="Selected applicant" aria-live="polite" className="min-w-0">
            {current ? (
              <CandidateDetail key={current.application_id} c={current} jobTitle={job?.title ?? "this job"}
                onStatus={(s) => setStatus(current.application_id, s)}
                onChanged={() => { if (selectedJob) void loadRanked(selectedJob); }} />
            ) : (
              <p className="p-6 text-sm text-muted">Pick a person to see why they scored what they did.</p>
            )}
          </section>
        </div>
      </div>

      <p className="text-sm text-muted">The score helps you decide where to start. It never rejects anyone; you do.</p>
    </div>
  );
}

export default function RecruiterPage() {
  return (
    <AuthGate title="Recruiting" roles={["admin", "recruiter"]} demoEmail="recruiter@aihr.demo">
      {() => <Recruiter />}
    </AuthGate>
  );
}

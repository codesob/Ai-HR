"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { AlertTriangle, Briefcase, Check, Plus, Sparkles, Users, X } from "lucide-react";
import { AuthGate } from "@/components/AuthGate";
import { PageHeader } from "@/components/PageHeader";
import { Alert, Avatar, EmptyState, MiniBar, ScoreRing, StatusBadge } from "@/components/ui";
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
        <h2 className="text-lg font-semibold">New role</h2>
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
        <button className="btn-primary" type="submit" disabled={saving}>{saving ? "Publishing…" : "Publish role"}</button>
      </div>
    </form>
  );
}

function CandidateCard({ c, rank, onStatus }: { c: RankedCandidate; rank: number; onStatus: (s: string) => void }) {
  const exp = c.match_explanation;
  const skills = exp?.skill_gap_score == null ? undefined : 1 - exp.skill_gap_score;
  return (
    <li className="card space-y-4 p-5">
      <div className="flex items-start gap-4">
        <Avatar name={c.candidate_name} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-ink">{c.candidate_name ?? "Unnamed candidate"}</p>
            <span className="text-xs text-subtle">#{rank}</span>
            <StatusBadge status={c.status} />
          </div>
        </div>
        <ScoreRing value={c.match_score} />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:gap-6">
        <MiniBar label="Meaning match" value={exp?.semantic_similarity} />
        <MiniBar label="Skills covered" value={skills} />
        <MiniBar label="Experience fit" value={exp?.experience_fit} />
      </div>

      {(exp?.matched_skills?.length || exp?.missing_skills?.length) ? (
        <div className="flex flex-wrap gap-1.5">
          {exp?.matched_skills?.map((s) => (
            <span key={s} className="badge bg-success-soft text-success">
              <Check className="h-3 w-3" aria-hidden />
              {s}
            </span>
          ))}
          {exp?.missing_skills?.map((s) => (
            <span key={s} className="badge bg-warning-soft text-warning">
              <AlertTriangle className="h-3 w-3" aria-hidden />
              Missing: {s}
            </span>
          ))}
        </div>
      ) : null}

      <div className="flex items-center justify-end gap-2 border-t border-line pt-3">
        <label htmlFor={`stage-${c.application_id}`} className="text-sm text-muted">Stage</label>
        <select id={`stage-${c.application_id}`} className="input w-auto py-1.5 capitalize" value={c.status}
          onChange={(e) => onStatus(e.target.value)}>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
    </li>
  );
}

function Recruiter() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<number | null>(null);
  const [ranked, setRanked] = useState<RankedCandidate[] | null>(null);
  const [jd, setJd] = useState<Record<string, unknown> | null>(null);
  const [drafting, setDrafting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  const loadJobs = useCallback(
    () => api.jobs().then((all) => {
      // Open roles first; the API's order is kept within each group.
      const j = [...all.filter((x) => x.status === "open"), ...all.filter((x) => x.status !== "open")];
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
  useEffect(() => {
    if (selectedJob) void loadRanked(selectedJob);
  }, [selectedJob, loadRanked]);

  function selectJob(id: number) {
    if (id === selectedJob) return;
    setRanked(null);
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

  return (
    <div className="space-y-8">
      <PageHeader
        title="Recruiting"
        subtitle="Your roles and an explained shortlist for each one"
        action={!showForm && (
          <button type="button" className="btn-primary" onClick={() => setShowForm(true)}>
            <Plus className="h-4 w-4" aria-hidden />
            New role
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

      <div className="grid gap-6 lg:grid-cols-[18rem_1fr]">
        {jobs.length > 0 && (
          <label className="block lg:hidden">
            <span className="label">Role</span>
            <select className="input" value={selectedJob ?? ""} onChange={(e) => selectJob(Number(e.target.value))}>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>{j.title}{j.status !== "open" ? ` (${j.status})` : ""}</option>
              ))}
            </select>
          </label>
        )}
        <nav aria-label="Roles" className="hidden space-y-2 lg:block">
          <p className="px-1 text-xs font-semibold uppercase tracking-wider text-subtle">Roles · {jobs.length}</p>
          {jobs.length === 0 && <p className="px-1 text-sm text-muted">No roles yet. Create your first one.</p>}
          <ul className="space-y-1">
            {jobs.map((j) => (
              <li key={j.id}>
                <button
                  type="button"
                  onClick={() => selectJob(j.id)}
                  aria-current={selectedJob === j.id ? "true" : undefined}
                  className={clsx(
                    "w-full rounded-xl border px-3 py-2.5 text-left transition",
                    selectedJob === j.id ? "border-brand/40 bg-surface shadow-sm" : "border-transparent hover:bg-surface-2",
                  )}
                >
                  <span className="block text-sm font-medium text-ink">{j.title}</span>
                  <span className="mt-0.5 flex items-center gap-2 text-xs text-subtle">
                    {j.department}
                    {j.status !== "open" && <StatusBadge status={j.status} />}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <section className="min-w-0 space-y-4" aria-live="polite">
          {job && (
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">{job.title}</h2>
                <p className="text-sm text-muted">
                  {job.required_skills.length ? `Needs ${job.required_skills.join(", ")}` : "No required skills listed"}
                  {job.min_experience_years ? ` · ${job.min_experience_years}+ years` : ""}
                </p>
              </div>
              <button type="button" className="btn-secondary" onClick={generateJD} disabled={drafting}>
                <Sparkles className="h-4 w-4 text-brand" aria-hidden />
                {drafting ? "Drafting…" : "Draft job description"}
              </button>
            </div>
          )}

          {jd && (
            <div className="card space-y-3 border-brand/30">
              <div className="flex items-center justify-between">
                <p className="eyebrow">Draft description</p>
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

          {!job ? (
            <EmptyState icon={Briefcase} title="Pick a role to see its candidates" />
          ) : ranked === null ? (
            <div className="space-y-3" aria-busy="true">
              {[0, 1, 2].map((i) => <div key={i} className="card h-40 animate-pulse bg-surface-2/60" />)}
            </div>
          ) : ranked.length === 0 ? (
            <EmptyState icon={Users} title="No applicants yet">
              Share your careers page from <b>Team &amp; payroll</b> and new applicants will be scored here automatically.
            </EmptyState>
          ) : (
            <>
              <ol className="space-y-3">
                {ranked.map((c, i) => (
                  <CandidateCard key={c.application_id} c={c} rank={i + 1} onStatus={(s) => setStatus(c.application_id, s)} />
                ))}
              </ol>
              <p className="text-xs text-subtle">
                Scores support your judgment; they never reject anyone. Review candidates before changing their stage.
              </p>
            </>
          )}
        </section>
      </div>
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

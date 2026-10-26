"use client";

import { useCallback, useEffect, useState } from "react";
import { AuthGate } from "@/components/AuthGate";
import { PageHeader } from "@/components/PageHeader";
import { api, type Job, type RankedCandidate } from "@/lib/api";

const STATUSES = ["applied", "screening", "assessment", "interview", "offer", "hired", "rejected"];
const EMPTY_JOB = { title: "", department: "Engineering", description: "", required_skills: "", min_experience_years: 0 };

function Recruiter() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<number | null>(null);
  const [ranked, setRanked] = useState<RankedCandidate[]>([]);
  const [jd, setJd] = useState<Record<string, unknown> | null>(null);
  const [newJob, setNewJob] = useState(EMPTY_JOB);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  const loadJobs = useCallback(
    () =>
      api
        .jobs()
        .then((j) => {
          setJobs(j);
          setSelectedJob((current) => current ?? j[0]?.id ?? null);
        })
        .catch((e) => setError(e.message)),
    [],
  );

  const loadRanked = useCallback(
    (jobId: number) =>
      api
        .ranked(jobId)
        .then(setRanked)
        .catch((e) => setError(e.message)),
    [],
  );

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    if (selectedJob) void loadRanked(selectedJob);
  }, [selectedJob, loadRanked]);

  async function createJob(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const job = await api.createJob({
        ...newJob,
        required_skills: newJob.required_skills.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setNewJob(EMPTY_JOB);
      setShowForm(false);
      await loadJobs();
      setSelectedJob(job.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create job");
    }
  }

  async function generateJD() {
    const job = jobs.find((j) => j.id === selectedJob);
    if (!job) return;
    try {
      setJd(await api.generateJD({ title: job.title, department: job.department, seniority: "senior",
        key_skills: job.required_skills }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "JD generation failed");
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

  return (
    <div className="space-y-8">
      <PageHeader
        title="Recruiting"
        subtitle="Roles, AI-ranked candidates, and pipeline status"
        action={
          <button type="button" className="btn-primary w-full sm:w-auto" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "New job"}
          </button>
        }
      />
      {error && <p role="alert" className="text-sm text-red-400">{error}</p>}

      {showForm && (
        <form onSubmit={createJob} className="card grid gap-3 sm:grid-cols-2">
          <input className="input" placeholder="Job title" required minLength={2} value={newJob.title}
            onChange={(e) => setNewJob({ ...newJob, title: e.target.value })} />
          <input className="input" placeholder="Department" value={newJob.department}
            onChange={(e) => setNewJob({ ...newJob, department: e.target.value })} />
          <textarea className="input sm:col-span-2" rows={4} placeholder="Description" required minLength={10}
            value={newJob.description} onChange={(e) => setNewJob({ ...newJob, description: e.target.value })} />
          <input className="input" placeholder="Required skills (comma separated)" value={newJob.required_skills}
            onChange={(e) => setNewJob({ ...newJob, required_skills: e.target.value })} />
          <input className="input" type="number" min={0} step={0.5} placeholder="Min. years experience"
            value={newJob.min_experience_years}
            onChange={(e) => setNewJob({ ...newJob, min_experience_years: Number(e.target.value) })} />
          <button className="btn-primary sm:col-span-2" type="submit">Publish job</button>
        </form>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-1">
          <h2 className="mb-4 font-semibold">Roles</h2>
          {jobs.length === 0 && <p className="text-sm text-slate-500">No roles yet. Create your first job.</p>}
          <ul className="space-y-2">
            {jobs.map((j) => (
              <li key={j.id}>
                <button
                  type="button"
                  onClick={() => setSelectedJob(j.id)}
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm ${
                    selectedJob === j.id ? "bg-indigo-600" : "hover:bg-slate-800"
                  }`}
                >
                  {j.title}
                  <span className="block text-xs text-slate-400">
                    {j.department} · {j.status}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {selectedJob && (
            <button type="button" className="btn-secondary mt-4 w-full" onClick={generateJD}>
              AI-generate job description
            </button>
          )}
        </div>

        <div className="card lg:col-span-2">
          <h2 className="mb-4 font-semibold">Ranked candidates</h2>
          {ranked.length === 0 ? (
            <p className="text-slate-500">No applications yet. Share your careers page from the Team tab.</p>
          ) : (
            <div className="space-y-4">
              {ranked.map((c, i) => {
                const exp = c.match_explanation;
                return (
                  <div key={c.application_id} className="rounded-lg border border-slate-700 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium">
                        #{i + 1} {c.candidate_name}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="badge bg-indigo-900 text-indigo-200">Rank {c.rank_score?.toFixed(2)}</span>
                        <select
                          aria-label="Application status"
                          className="rounded-lg border border-slate-600 bg-slate-900 px-2 py-1 text-xs"
                          value={c.status}
                          onChange={(e) => setStatus(c.application_id, e.target.value)}
                        >
                          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                      </div>
                    </div>
                    <p className="mt-2 text-sm text-slate-400">
                      Match {c.match_score?.toFixed(2)} · {exp?.explanation ?? ""}
                    </p>
                    {exp && (
                      <div className="mt-2 flex flex-wrap gap-2 text-xs">
                        <span className="badge bg-green-900/50 text-green-300">
                          Matched: {exp.matched_skills?.join(", ") || "—"}
                        </span>
                        <span className="badge bg-amber-900/50 text-amber-300">
                          Gaps: {exp.missing_skills?.join(", ") || "none"}
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
              <p className="text-xs text-slate-500">
                AI scores are decision support only. A person must review candidates before rejection.
              </p>
            </div>
          )}
        </div>
      </div>

      {jd && (
        <div className="card">
          <h2 className="font-semibold">AI job description draft</h2>
          <p className="mt-2 text-sm text-slate-300">{String(jd.description)}</p>
          <ul className="mt-4 list-disc pl-5 text-sm text-slate-400">
            {(jd.responsibilities as string[])?.map((r) => <li key={r}>{r}</li>)}
          </ul>
          <p className="mt-2 text-sm text-indigo-300">{String(jd.salary_band)}</p>
        </div>
      )}
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

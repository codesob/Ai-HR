"use client";

import { useCallback, useEffect, useState } from "react";
import { LoginForm } from "@/components/LoginForm";
import { PageHeader } from "@/components/PageHeader";
import { api, Application, Job } from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth";

export default function RecruiterPage() {
  const [authed, setAuthed] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<number | null>(null);
  const [ranked, setRanked] = useState<Record<string, unknown>[]>([]);
  const [jd, setJd] = useState<Record<string, unknown> | null>(null);

  const load = useCallback(async () => {
    if (!getToken()) return;
    const j = await api.jobs();
    setJobs(j);
    if (j.length && !selectedJob) setSelectedJob(j[0].id);
  }, [selectedJob]);

  useEffect(() => {
    if (getToken()) {
      setAuthed(true);
    }
  }, []);

  useEffect(() => {
    if (!authed) return;
    load().catch(console.error);
  }, [authed, load]);

  useEffect(() => {
    if (!selectedJob || !authed) return;
    api.ranked(selectedJob).then(setRanked).catch(console.error);
  }, [selectedJob, authed]);

  async function generateJD() {
    const job = jobs.find((j) => j.id === selectedJob);
    if (!job) return;
    try {
      const result = await api.generateJD({
        title: job.title,
        department: job.department,
        seniority: "senior",
        key_skills: job.required_skills,
      });
      setJd(result);
    } catch (error) {
      console.error(error instanceof Error ? error.message : error);
    }
  }

  function handleLogout() {
    clearToken();
    setAuthed(false);
    setJobs([]);
    setSelectedJob(null);
    setRanked([]);
    setJd(null);
  }

  if (!authed) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Recruiter Dashboard</h1>
        <p className="text-slate-400">Use recruiter@aihr.demo / demo12345</p>
        <LoginForm onSuccess={() => setAuthed(true)} />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Recruiter Dashboard"
        subtitle="Pipeline, AI ranking, JD generation, scheduling"
        action={
          <button type="button" className="btn-secondary w-full sm:w-auto" onClick={handleLogout}>
            Logout
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-1">
          <h2 className="mb-4 font-semibold">Open Roles</h2>
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
                  <span className="block text-xs text-slate-400">{j.department}</span>
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="btn-secondary mt-4 w-full" onClick={generateJD}>
            AI Generate JD
          </button>
        </div>

        <div className="card lg:col-span-2">
          <h2 className="mb-4 font-semibold">Ranked Candidates (Explainable AI)</h2>
          {ranked.length === 0 ? (
            <p className="text-slate-500">No applications yet. Candidates apply from the Candidate portal.</p>
          ) : (
            <div className="space-y-4">
              {ranked.map((c, i) => {
                const exp = c.match_explanation as Record<string, unknown> | undefined;
                return (
                  <div key={String(c.application_id)} className="rounded-lg border border-slate-700 p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">
                        #{i + 1} {String(c.candidate_name)}
                      </span>
                      <span className="badge bg-indigo-900 text-indigo-200">
                        Rank {(c.rank_score as number)?.toFixed(2)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-slate-400">
                      Match: {(c.match_score as number)?.toFixed(2)} · {String(exp?.explanation || "")}
                    </p>
                    {exp && (
                      <div className="mt-2 flex flex-wrap gap-2 text-xs">
                        <span className="badge bg-green-900/50 text-green-300">
                          Matched: {((exp.matched_skills as string[]) || []).join(", ") || "—"}
                        </span>
                        <span className="badge bg-amber-900/50 text-amber-300">
                          Gaps: {((exp.missing_skills as string[]) || []).join(", ") || "none"}
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {jd && (
        <div className="card">
          <h2 className="font-semibold">AI Job Description</h2>
          <p className="mt-2 text-sm text-slate-300">{String(jd.description)}</p>
          <ul className="mt-4 list-disc pl-5 text-sm text-slate-400">
            {(jd.responsibilities as string[])?.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <p className="mt-2 text-sm text-indigo-300">{String(jd.salary_band)}</p>
        </div>
      )}
    </div>
  );
}

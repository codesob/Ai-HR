"use client";

import { useCallback, useEffect, useState } from "react";
import { AuthGate } from "@/components/AuthGate";
import { PageHeader } from "@/components/PageHeader";
import { api, type Application, type Job } from "@/lib/api";

function Candidate() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [parsed, setParsed] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState("");
  const [uploading, setUploading] = useState(false);

  const load = useCallback(
    () =>
      Promise.all([api.jobs(), api.myApplications()])
        .then(([j, a]) => {
          setJobs(j);
          setApplications(a);
        })
        .catch((e) => setMessage(e.message)),
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  async function handleApply(jobId: number) {
    try {
      await api.apply(jobId);
      setMessage("Application submitted.");
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not apply");
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      setParsed(await api.uploadResume(file));
      setMessage("Resume uploaded and parsed.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const appliedJobIds = new Set(applications.map((a) => a.job_id));

  return (
    <div className="space-y-8">
      <PageHeader title="My applications" subtitle="Upload your resume, apply, and track your status" />
      {message && <p className="text-sm text-indigo-300">{message}</p>}

      <div className="card">
        <h2 className="font-semibold">Resume</h2>
        <p className="mt-1 text-sm text-slate-400">PDF, DOCX or TXT, up to 5 MB. Upload before applying for the best match.</p>
        <input type="file" accept=".pdf,.docx,.txt,.md" className="mt-4" disabled={uploading} onChange={handleUpload} />
        {parsed && (
          <div className="mt-4 text-sm text-slate-300">
            <p>Skills detected: {(parsed.skills as string[])?.join(", ") || "none"}</p>
            <p>Experience: {String(parsed.experience_years ?? 0)} years</p>
          </div>
        )}
      </div>

      {applications.length > 0 && (
        <div className="card">
          <h2 className="mb-3 font-semibold">Your applications</h2>
          <ul className="space-y-2 text-sm">
            {applications.map((a) => (
              <li key={a.id} className="flex justify-between">
                <span>{a.job_title}</span>
                <span className="capitalize text-indigo-300">{a.status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="space-y-4">
        <h2 className="font-semibold">Open positions</h2>
        {jobs.map((j) => (
          <div key={j.id} className="card flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="font-medium">{j.title}</h3>
              <p className="text-sm text-slate-400">{j.department}</p>
              <p className="mt-2 line-clamp-2 text-sm">{j.description}</p>
            </div>
            <button type="button" className="btn-primary shrink-0" disabled={appliedJobIds.has(j.id)}
              onClick={() => handleApply(j.id)}>
              {appliedJobIds.has(j.id) ? "Applied" : "Apply"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function CandidatePage() {
  return (
    <AuthGate title="Candidate portal" roles={["candidate"]} demoEmail="candidate@aihr.demo">
      {() => <Candidate />}
    </AuthGate>
  );
}

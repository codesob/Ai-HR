"use client";

import { useEffect, useState } from "react";
import { LoginForm } from "@/components/LoginForm";
import { PageHeader } from "@/components/PageHeader";
import { api, Job } from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth";

export default function CandidatePage() {
  const [authed, setAuthed] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [parsed, setParsed] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (getToken()) {
      setAuthed(true);
    }
  }, []);

  useEffect(() => {
    if (!authed) return;
    api.jobs().then(setJobs).catch(console.error);
  }, [authed]);

  async function handleApply(jobId: number) {
    try {
      await api.apply(jobId);
      setMessage("Application submitted with AI match score!");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Apply failed");
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await api.uploadResume(file);
      setParsed(result);
      setMessage("Resume parsed successfully");
    } catch {
      setMessage("Upload failed — sign in as candidate@aihr.demo first");
    }
  }

  async function parseSample() {
    const sample = `John Doe
john@example.com
Senior ML Engineer with 6 years experience
Skills: Python, PyTorch, RAG, FastAPI, Docker, Kubernetes
BSc Computer Science
AWS Certified Machine Learning`;
    try {
      const result = await api.parseResumeText(sample);
      setParsed(result);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Resume parsing failed");
    }
  }

  function handleLogout() {
    clearToken();
    setAuthed(false);
    setJobs([]);
    setParsed(null);
    setMessage("");
  }

  if (!authed) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Candidate Portal</h1>
        <p className="text-slate-400">Use candidate@aihr.demo / demo12345</p>
        <LoginForm
          defaultEmail="candidate@aihr.demo"
          onSuccess={() => {
            setAuthed(true);
          }}
        />
        <button type="button" className="btn-secondary" onClick={parseSample}>
          Try resume parser (no login)
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Candidate Portal"
        subtitle="Apply, upload resume, track AI match scores"
        action={
          <button type="button" className="btn-secondary w-full sm:w-auto" onClick={handleLogout}>
            Logout
          </button>
        }
      />

      {message && <p className="text-sm text-indigo-300">{message}</p>}

      <div className="card">
        <h2 className="font-semibold">Upload Resume</h2>
        <input type="file" accept=".pdf,.docx,.txt" className="mt-4" onChange={handleUpload} />
        {parsed && (
          <pre className="mt-4 overflow-x-auto rounded bg-slate-950 p-4 text-xs">
            {JSON.stringify(parsed, null, 2)}
          </pre>
        )}
      </div>

      <div className="space-y-4">
        <h2 className="font-semibold">Open Positions</h2>
        {jobs.map((j) => (
          <div key={j.id} className="card flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="font-medium">{j.title}</h3>
              <p className="text-sm text-slate-400">{j.department}</p>
              <p className="mt-2 text-sm line-clamp-2">{j.description}</p>
            </div>
            <button type="button" className="btn-primary shrink-0" onClick={() => handleApply(j.id)}>
              Apply with AI Match
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

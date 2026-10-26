"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Job } from "@/lib/api";
import { setSession } from "@/lib/auth";
import { useSession } from "@/lib/useSession";

export default function CareersPage() {
  const { slug } = useParams<{ slug: string }>();
  const { session } = useSession();
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });

  useEffect(() => {
    api.publicJobs(slug).then(setJobs).catch((e) => setError(e.message));
  }, [slug]);

  const isCandidateHere = session?.user.role === "candidate";

  async function register(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const { access_token, user } = await api.registerCandidate({ ...form, org_slug: slug });
      setSession({ token: access_token, user });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  async function apply(jobId: number) {
    setMessage("");
    try {
      await api.apply(jobId);
      setMessage("Application submitted. Upload your resume on My Applications to improve your match.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not apply");
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold">Open positions</h1>
      {error && <p role="alert" className="text-sm text-red-400">{error}</p>}
      {message && <p className="text-sm text-indigo-300">{message}</p>}

      {!session && (
        <form onSubmit={register} className="card max-w-xl space-y-3">
          <h2 className="font-semibold">Create a candidate profile to apply</h2>
          <input className="input" placeholder="Full name" required value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          <input className="input" type="email" placeholder="Email" required value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input className="input" type="password" placeholder="Password (10+ characters)" minLength={10} required
            value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <button className="btn-primary" type="submit">Create profile</button>
        </form>
      )}

      {jobs === null && !error && <p className="text-slate-400">Loading roles…</p>}
      {jobs?.length === 0 && <p className="text-slate-400">No open roles right now.</p>}
      <div className="space-y-4">
        {jobs?.map((j) => (
          <div key={j.id} className="card flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="font-medium">{j.title}</h3>
              <p className="text-sm text-slate-400">{j.department}</p>
              <p className="mt-2 line-clamp-3 text-sm">{j.description}</p>
            </div>
            {isCandidateHere && (
              <button type="button" className="btn-primary shrink-0" onClick={() => apply(j.id)}>
                Apply
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

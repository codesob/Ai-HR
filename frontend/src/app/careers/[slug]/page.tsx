"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Check, Search } from "lucide-react";
import { Alert, EmptyState } from "@/components/ui";
import { api, type Job } from "@/lib/api";
import { setSession } from "@/lib/auth";
import { useSession } from "@/lib/useSession";

const money = (n: number) => n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });

function SignUpToApply({ slug, onDone, onCancel }: { slug: string; onDone: () => void; onCancel: () => void }) {
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { user } = await api.registerCandidate({ ...form, org_slug: slug });
      setSession({ user });
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't create your profile");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3 border-t border-line pt-4">
      <p className="text-sm font-medium text-ink">Create a candidate profile to apply</p>
      {error && <Alert>{error}</Alert>}
      <div className="grid gap-3 sm:grid-cols-3">
        <label>
          <span className="label">Full name</span>
          <input className="input" required autoComplete="name" value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        </label>
        <label>
          <span className="label">Email</span>
          <input className="input" type="email" required autoComplete="email" value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </label>
        <label>
          <span className="label">Password</span>
          <input className="input" type="password" minLength={10} required autoComplete="new-password" value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </label>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-subtle">
          Already have one? <Link href="/login" className="text-brand-ink hover:underline">Sign in</Link>
        </p>
        <div className="flex gap-2">
          <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={busy}>{busy ? "Applying…" : "Create profile & apply"}</button>
        </div>
      </div>
    </form>
  );
}

export default function CareersPage() {
  const { slug } = useParams<{ slug: string }>();
  const { session } = useSession();
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [error, setError] = useState("");
  const [applied, setApplied] = useState<Set<number>>(new Set());
  const [signingUpFor, setSigningUpFor] = useState<number | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    api.publicJobs(slug).then(setJobs).catch((e) => setError(e.message));
  }, [slug]);

  const isCandidate = session?.user.role === "candidate";
  const isStaff = !!session && !isCandidate;

  async function apply(jobId: number) {
    setNotice("");
    try {
      await api.apply(jobId, new URLSearchParams(window.location.search).get("source") ?? undefined);
      setApplied((s) => new Set(s).add(jobId));
      setNotice("Application sent. Add your resume in My applications to strengthen your match.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not apply");
    }
  }

  const byDept = (jobs ?? []).reduce<Record<string, Job[]>>((acc, j) => {
    (acc[j.department] ??= []).push(j);
    return acc;
  }, {});

  return (
    <div className="mx-auto max-w-4xl space-y-10">
      <header className="space-y-3 text-center">
        <p className="eyebrow">Careers</p>
        <h1 className="text-4xl">Come build with us</h1>
        <p className="text-muted">
          {jobs ? `${jobs.length} open role${jobs.length === 1 ? "" : "s"}` : "Loading open roles…"}
          {" · "}Every application is read by a person.
        </p>
      </header>

      {error && <Alert>{error}</Alert>}
      {notice && (
        <Alert tone="success">
          {notice} <Link href="/candidate" className="font-semibold underline">Go to My applications</Link>
        </Alert>
      )}
      {isStaff && <Alert tone="warning">You&apos;re signed in as staff. Candidates see Apply buttons here.</Alert>}

      {jobs === null && !error && (
        <div className="space-y-3" aria-busy="true">
          {[0, 1, 2].map((i) => <div key={i} className="card h-28 animate-pulse bg-surface-2/60" />)}
        </div>
      )}
      {jobs?.length === 0 && <EmptyState icon={Search} title="No open roles right now">Check back soon.</EmptyState>}

      {Object.entries(byDept).map(([dept, list]) => (
        <section key={dept} className="space-y-3">
          <h2 className="font-sans text-xs font-semibold uppercase tracking-wider text-muted">{dept}</h2>
          <ul className="space-y-3">
            {list.map((j) => (
              <li key={j.id} className="card space-y-4 p-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-1.5">
                    <h3 className="text-lg font-semibold">{j.title}</h3>
                    <p className="text-sm text-muted">
                      {j.salary_min && j.salary_max ? `${money(j.salary_min)} – ${money(j.salary_max)}` : "Salary on request"}
                      {j.min_experience_years ? ` · ${j.min_experience_years}+ years` : ""}
                    </p>
                    <p className="text-sm text-ink-soft">{j.description}</p>
                    {j.required_skills.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {j.required_skills.map((s) => <span key={s} className="badge bg-surface-2 text-ink-soft">{s}</span>)}
                      </div>
                    )}
                  </div>
                  {!isStaff && (
                    applied.has(j.id) ? (
                      <span className="btn-secondary shrink-0 cursor-default"><Check className="h-4 w-4 text-success" aria-hidden /> Applied</span>
                    ) : (
                      <button type="button" className="btn-primary shrink-0"
                        onClick={() => (isCandidate ? apply(j.id) : setSigningUpFor(j.id))}>
                        Apply
                      </button>
                    )
                  )}
                </div>
                {signingUpFor === j.id && !session && (
                  <SignUpToApply
                    slug={slug}
                    onCancel={() => setSigningUpFor(null)}
                    onDone={() => {
                      setSigningUpFor(null);
                      void apply(j.id);
                    }}
                  />
                )}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

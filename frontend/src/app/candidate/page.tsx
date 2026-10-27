"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { Check, FileUp, Search } from "lucide-react";
import { ApplicantScreening } from "@/components/ApplicantScreening";
import { AuthGate } from "@/components/AuthGate";
import { PageHeader } from "@/components/PageHeader";
import { Alert, EmptyState } from "@/components/ui";
import { api, type Application, type Job } from "@/lib/api";

const STEPS = ["applied", "screening", "interview", "offer", "hired"];

function stepIndex(status: string) {
  if (status === "assessment") return 1;
  return STEPS.indexOf(status);
}

function Tracker({ status }: { status: string }) {
  if (status === "rejected") {
    return <p className="text-sm text-muted">This role has moved forward with other candidates. Thank you for applying.</p>;
  }
  const current = stepIndex(status);
  return (
    <ol className="flex items-center gap-1" aria-label={`Current stage: ${status}`}>
      {STEPS.map((s, i) => (
        <li key={s} className="flex flex-1 flex-col gap-1.5">
          <span className={clsx("h-1.5 rounded-full", i <= current ? "bg-brand" : "bg-surface-2")} />
          <span className={clsx("text-xs capitalize", i === current ? "font-semibold text-ink" : "text-subtle")}>{s}</span>
        </li>
      ))}
    </ol>
  );
}

function Candidate() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [parsed, setParsed] = useState<Record<string, unknown> | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "danger"; text: string } | null>(null);
  const [uploading, setUploading] = useState(false);

  const load = useCallback(
    () => Promise.all([api.jobs(), api.myApplications()])
      .then(([j, a]) => {
        setJobs(j.filter((x) => x.status === "open"));
        setApplications(a);
      })
      .catch((e) => setNotice({ tone: "danger", text: e.message })),
    [],
  );
  useEffect(() => { void load(); }, [load]);

  async function apply(jobId: number) {
    try {
      await api.apply(jobId);
      setNotice({ tone: "success", text: "Application sent. Track its progress below." });
      await load();
    } catch (e) {
      setNotice({ tone: "danger", text: e instanceof Error ? e.message : "Could not apply" });
    }
  }

  async function upload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      setParsed(await api.uploadResume(file));
      setNotice({ tone: "success", text: "Resume read. New applications will use it." });
    } catch (err) {
      setNotice({ tone: "danger", text: err instanceof Error ? err.message : "Upload failed" });
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  const applied = new Set(applications.map((a) => a.job_id));
  const skills = (parsed?.skills as string[] | undefined) ?? [];

  return (
    <div className="space-y-8">
      <PageHeader title="My applications" subtitle="Step 1: add your resume. Step 2: apply to a job with one click. Then follow your progress here." />
      {notice && <Alert tone={notice.tone}>{notice.text}</Alert>}

      <label className={clsx(
        "flex cursor-pointer flex-col items-center gap-3 rounded-card border-2 border-dashed border-line-strong bg-surface px-6 py-8 text-center transition hover:border-brand/50",
        uploading && "pointer-events-none opacity-60",
      )}>
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-soft">
          <FileUp className="h-5 w-5 text-brand-ink" aria-hidden />
        </span>
        <span className="font-medium text-ink">{uploading ? "Reading your resume…" : parsed ? "Replace your resume" : "Upload your resume"}</span>
        <span className="text-sm text-muted">PDF, Word, text, or a photo of your resume (also your LinkedIn profile PDF), up to 5 MB</span>
        <input type="file" accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp" className="sr-only" disabled={uploading} onChange={upload} />
      </label>
      {parsed && (
        <div className="card space-y-2 p-5">
          <p className="text-sm font-medium text-ink">
            We found {skills.length} skill{skills.length === 1 ? "" : "s"} and {String(parsed.experience_years ?? 0)} years of experience
          </p>
          <div className="flex flex-wrap gap-1.5">
            {skills.map((s) => <span key={s} className="badge bg-brand-soft text-brand-ink">{s}</span>)}
          </div>
        </div>
      )}

      <ApplicantScreening />

      {applications.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl">Your applications</h2>
          <ul className="space-y-3">
            {applications.map((a) => (
              <li key={a.id} className="card space-y-4 p-5">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="font-medium text-ink">{a.job_title}</p>
                  <time className="text-xs text-subtle" dateTime={a.created_at}>
                    Applied {new Date(a.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                  </time>
                </div>
                <Tracker status={a.status} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="text-xl">Jobs you can apply to</h2>
        {jobs.length === 0 ? (
          <EmptyState icon={Search} title="No open roles right now">Check back soon.</EmptyState>
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {jobs.map((j) => (
              <li key={j.id} className="card flex flex-col gap-4 p-5">
                <div className="flex-1 space-y-1">
                  <p className="text-xs font-medium text-subtle">{j.department}</p>
                  <h3 className="font-semibold">{j.title}</h3>
                  <p className="line-clamp-2 text-sm text-muted">{j.description}</p>
                </div>
                {j.required_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {j.required_skills.map((s) => <span key={s} className="badge bg-surface-2 text-ink-soft">{s}</span>)}
                  </div>
                )}
                <button type="button" className={applied.has(j.id) ? "btn-secondary" : "btn-primary"} disabled={applied.has(j.id)}
                  onClick={() => apply(j.id)}>
                  {applied.has(j.id) ? <><Check className="h-4 w-4" aria-hidden /> Applied</> : "Apply"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default function CandidatePage() {
  return (
    <AuthGate title="My applications" roles={["candidate"]} demoEmail="candidate@aihr.demo">
      {() => <Candidate />}
    </AuthGate>
  );
}

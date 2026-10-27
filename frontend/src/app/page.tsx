import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Briefcase,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  FileSearch,
  Lock,
  MessageCircle,
  Scale,
  Star,
  UserCheck,
} from "lucide-react";
import { DEMO_ENABLED, DemoLauncher } from "@/components/DemoLauncher";

const problems = [
  { title: "Screening eats the week", desc: "Recruiters read every resume by hand, and strong applicants wait days for a first reply." },
  { title: "AI tools you can't defend", desc: "Black-box scores are hard to explain to a hiring manager, a candidate, or an auditor." },
  { title: "HR lives in five tools", desc: "Jobs, interviews, onboarding, leave and payroll sit in separate systems that never agree." },
];

const steps = [
  { icon: Briefcase, title: "Post a role", desc: "Write it yourself or generate a draft, then publish it to your careers page." },
  { icon: FileSearch, title: "Candidates apply", desc: "Resumes are parsed and scored against the role the moment they arrive." },
  { icon: UserCheck, title: "Your team decides", desc: "Review a ranked shortlist with the reasons behind each score." },
];

const features = [
  { icon: Star, title: "Explainable screening", desc: "Every score shows matched skills, gaps and experience fit." },
  { icon: Briefcase, title: "Careers page", desc: "A public jobs page for your company, live in a minute." },
  { icon: CalendarDays, title: "Interview scheduling", desc: "Schedule interviews and notify everyone automatically." },
  { icon: ClipboardList, title: "Onboarding, leave & payroll", desc: "Checklists, approvals, salaries and payslips." },
  { icon: BarChart3, title: "Hiring analytics", desc: "Funnel, time to hire and source quality from real data." },
  { icon: MessageCircle, title: "HR policy assistant", desc: "Answers employee questions and cites the policy." },
];

const trust = [
  { icon: Scale, text: "Humans make every decision" },
  { icon: Lock, text: "Data isolated per company" },
  { icon: CheckCircle2, text: "Scores you can explain" },
];

function ScoreRow({ label, weight, value }: { label: string; weight: string; value: number }) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-muted">
          {label} <span className="text-subtle">· {weight}</span>
        </span>
        <span className="font-semibold text-ink">{Math.round(value * 100)}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-surface-2">
        <div className="h-1.5 rounded-full bg-brand" style={{ width: `${value * 100}%` }} />
      </div>
    </div>
  );
}

/** Illustrative only: the weights and fields match the real matching engine; the candidate is invented. */
function ExampleMatchCard() {
  return (
    <div className="card w-full max-w-md space-y-5 p-6 shadow-2xl shadow-black/30" aria-label="Example candidate match explanation">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium text-subtle">Example · Senior ML Engineer</p>
          <p className="mt-1 text-lg font-semibold text-ink">Candidate A</p>
          <p className="text-sm text-muted">7 years · MSc Computer Science</p>
        </div>
        <div className="flex h-16 w-16 flex-col items-center justify-center rounded-full border-4 border-brand bg-brand-soft">
          <span className="text-xl font-bold leading-none text-brand-ink">86</span>
        </div>
      </div>
      <div className="space-y-3">
        <ScoreRow label="Meaning match" weight="45%" value={0.69} />
        <ScoreRow label="Required skills" weight="35%" value={1} />
        <ScoreRow label="Experience fit" weight="20%" value={1} />
      </div>
      <div className="flex flex-wrap gap-1.5">
        {["Python", "PyTorch", "RAG", "FastAPI", "Docker"].map((s) => (
          <span key={s} className="badge bg-success-soft text-success">
            <CheckCircle2 className="h-3 w-3" aria-hidden />
            {s}
          </span>
        ))}
      </div>
      <p className="border-t border-line pt-3 text-xs text-muted">
        No required skills missing. The recruiter decides what happens next.
      </p>
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="space-y-24 pb-8">
      <section className="relative -mx-4 overflow-hidden rounded-none bg-navy px-6 py-14 sm:mx-0 sm:rounded-[2rem] sm:px-12 lg:py-20">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_85%_15%,#2b2f7a_0%,transparent_55%)]"
        />
        <div className="relative grid items-center gap-12 lg:grid-cols-[1.1fr_1fr]">
          <div className="space-y-7">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[#a5a8ff]">AI-HR</p>
            <h1 className="text-4xl font-bold leading-[1.05] tracking-tight text-white sm:text-6xl">
              Hire faster with AI that shows its work.
            </h1>
            <p className="max-w-xl text-lg text-[#c9cce0]">
              AI-HR ranks every applicant against the role, explains each score, and runs interviews,
              onboarding, leave and payroll in one workspace built for growing teams.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href={DEMO_ENABLED ? "#demo" : "/signup"} className="btn-primary px-5 py-3 text-base">
                {DEMO_ENABLED ? "Try the live demo" : "Create your workspace"}
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
              <Link
                href={DEMO_ENABLED ? "/signup" : "/login"}
                className="inline-flex items-center rounded-xl border border-white/20 px-5 py-3 text-base font-semibold text-white transition hover:bg-white/10"
              >
                {DEMO_ENABLED ? "Create your workspace" : "Sign in"}
              </Link>
            </div>
            <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-[#c9cce0]">
              {trust.map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-[#a5a8ff]" aria-hidden />
                  {text}
                </li>
              ))}
            </ul>
          </div>
          <div className="flex justify-center lg:justify-end">
            <ExampleMatchCard />
          </div>
        </div>
      </section>

      <section className="space-y-8">
        <div className="max-w-2xl space-y-3">
          <p className="eyebrow">The problem</p>
          <h2 className="text-3xl font-semibold tracking-tight">Hiring is still mostly manual, and AI made it harder to trust</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {problems.map((p, i) => (
            <div key={p.title} className="card">
              <p className="text-sm font-semibold text-subtle">0{i + 1}</p>
              <h3 className="mt-3 text-lg font-semibold">{p.title}</h3>
              <p className="mt-2 text-muted">{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-8">
        <div className="max-w-2xl space-y-3">
          <p className="eyebrow">How it works</p>
          <h2 className="text-3xl font-semibold tracking-tight">From job post to shortlist in three steps</h2>
        </div>
        <ol className="grid gap-px overflow-hidden rounded-[var(--radius-card)] border border-line bg-line md:grid-cols-3">
          {steps.map(({ icon: Icon, title, desc }, i) => (
            <li key={title} className="space-y-3 bg-surface p-6">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-soft text-sm font-bold text-brand-ink">
                  {i + 1}
                </span>
                <Icon className="h-5 w-5 text-brand" aria-hidden />
              </div>
              <h3 className="text-lg font-semibold">{title}</h3>
              <p className="text-muted">{desc}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="space-y-8">
        <div className="max-w-2xl space-y-3">
          <p className="eyebrow">The platform</p>
          <h2 className="text-3xl font-semibold tracking-tight">Everything from job post to first payslip</h2>
        </div>
        <div className="grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
          {features.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="flex gap-4">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-soft">
                <Icon className="h-5 w-5 text-brand" aria-hidden />
              </span>
              <div>
                <h3 className="font-semibold">{title}</h3>
                <p className="mt-1 text-sm text-muted">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {DEMO_ENABLED && (
        <section id="demo" className="card scroll-mt-24 space-y-5 border-brand/30 bg-brand-soft/40 p-8">
          <div className="space-y-2">
            <p className="eyebrow">Live demo</p>
            <h2 className="text-2xl font-semibold tracking-tight">See it with real data, no sign-up</h2>
          </div>
          <DemoLauncher />
        </section>
      )}

      <section className="space-y-5 text-center">
        <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Your next hire, explained.</h2>
        <p className="mx-auto max-w-xl text-muted">
          Set up a workspace in a minute, post your first role, and share your careers page today.
        </p>
        <Link href="/signup" className="btn-primary px-5 py-3 text-base">
          Create your workspace
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </section>
    </div>
  );
}

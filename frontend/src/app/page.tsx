import Link from "next/link";
import { BarChart3, Briefcase, CalendarDays, ClipboardList, MessageCircle, Star } from "lucide-react";

const features = [
  { icon: Briefcase, title: "Jobs & careers page", desc: "Publish roles and share a branded careers page per workspace." },
  { icon: Star, title: "Explainable AI screening", desc: "Rank applicants with match scores that show matched skills and gaps." },
  { icon: CalendarDays, title: "Interview scheduling", desc: "Schedule interviews and notify candidates and interviewers by email." },
  { icon: ClipboardList, title: "Leave & payroll", desc: "Leave requests with approvals, salary profiles and payslips." },
  { icon: BarChart3, title: "Hiring analytics", desc: "Funnel, time-to-hire and source effectiveness from your real data." },
  { icon: MessageCircle, title: "HR policy assistant", desc: "Answers employee policy questions with cited sources." },
];

export default function HomePage() {
  return (
    <div className="space-y-12">
      <section className="space-y-6 rounded-4xl border border-slate-700/60 bg-slate-900/85 p-8 sm:p-12">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-indigo-300">AI-HR</p>
        <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
          Hiring and HR operations for growing teams, with AI that shows its work.
        </h1>
        <p className="max-w-2xl text-lg text-slate-400">
          One workspace for your jobs, candidates, interviews, leave and payroll. Every AI score comes with an
          explanation, and every decision stays with a person.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/signup" className="btn-primary">
            Create your workspace
          </Link>
          <Link href="/login" className="btn-secondary">
            Sign in
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {features.map(({ icon: Icon, title, desc }) => (
          <div key={title} className="card">
            <Icon className="h-6 w-6 text-indigo-300" aria-hidden />
            <h2 className="mt-4 font-semibold">{title}</h2>
            <p className="mt-2 text-sm text-slate-400">{desc}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

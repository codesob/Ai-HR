import Link from "next/link";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Briefcase,
  CalendarDays,
  ClipboardList,
  MessageCircle,
  Sparkles,
  Star,
  Users,
} from "lucide-react";

const workflows = [
  { icon: Briefcase, title: "Create Job", desc: "Publish roles and align hiring priorities.", href: "/recruiter" },
  { icon: Users, title: "Source Candidates", desc: "Collect applicants from resumes and networks.", href: "/candidate" },
  { icon: Star, title: "AI Screening", desc: "Rank and score candidates with explainable matches.", href: "/recruiter" },
  { icon: CalendarDays, title: "Interview Pipeline", desc: "Track scheduled interviews and next steps.", href: "/recruiter" },
  { icon: ClipboardList, title: "Offer Management", desc: "Review offers, approvals, and hiring decisions.", href: "/admin" },
  { icon: MessageCircle, title: "HR Copilot", desc: "Ask policy, hiring, and compliance questions instantly.", href: "/chat" },
];

const metrics = [
  { label: "Active Jobs", value: "24", accent: "text-emerald-300" },
  { label: "Candidates", value: "1,247", accent: "text-cyan-300" },
  { label: "Interviews Today", value: "18", accent: "text-fuchsia-300" },
  { label: "Avg Match Score", value: "86%", accent: "text-indigo-300" },
];

const leaderboard = [
  { name: "Sarah Chen", score: "94%" },
  { name: "Alex Johnson", score: "92%" },
  { name: "David Kumar", score: "90%" },
];

const activityFeed = [
  "Generated JD for Backend Engineer",
  "Ranked 126 applicants",
  "Scheduled 8 interviews",
  "Answered HR policy question",
  "Flagged missing compliance form",
];

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-6 rounded-[2rem] border border-slate-700/60 bg-slate-900/85 p-8 shadow-[0_32px_120px_-64px_rgba(15,23,42,0.9)] backdrop-blur">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-indigo-300">
                Recruiting Command Center
              </p>
              <h1 className="mt-4 text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                Active hiring insights, not marketing promises.
              </h1>
            </div>
            <div className="rounded-3xl bg-slate-950/90 px-5 py-4 text-right">
              <p className="text-sm uppercase tracking-[0.18em] text-slate-400">Demo user</p>
              <p className="mt-2 text-lg font-semibold text-white">recruiter@aihr.demo</p>
            </div>
          </div>

          <p className="max-w-3xl text-base leading-7 text-slate-300">
            See hiring velocity, candidate quality, and AI activity up front. The platform is designed to help
            recruiters move from discovery to decisions faster.
          </p>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {metrics.map((metric) => (
              <div key={metric.label} className="rounded-3xl bg-slate-950/90 p-5">
                <p className="text-sm uppercase tracking-[0.24em] text-slate-500">{metric.label}</p>
                <p className={`mt-3 text-3xl font-semibold ${metric.accent}`}>{metric.value}</p>
              </div>
            ))}
          </div>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <Link href="/recruiter" className="btn-primary inline-flex items-center gap-2">
              View Recruiter Dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/chat" className="btn-secondary inline-flex items-center gap-2">
              Open HR Copilot
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-500">AI Copilot Activity</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Live intelligence feed</h2>
              </div>
              <Sparkles className="h-7 w-7 text-indigo-300" />
            </div>
            <ul className="mt-6 space-y-3 text-sm text-slate-300">
              {activityFeed.map((item) => (
                <li key={item} className="flex items-start gap-3 rounded-3xl border border-slate-700/80 bg-slate-950/90 p-4">
                  <span className="mt-1 inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Recruitment Funnel</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Hiring flow</h2>
              </div>
              <Activity className="h-7 w-7 text-cyan-300" />
            </div>
            <div className="mt-6 space-y-4">
              {[
                { step: "Applicants", value: "1,250" },
                { step: "Screened", value: "650" },
                { step: "Interviewed", value: "145" },
                { step: "Offers", value: "32" },
                { step: "Hired", value: "18" },
              ].map((item) => (
                <div key={item.step} className="rounded-3xl border border-slate-700/80 bg-slate-950/90 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm text-slate-400">{item.step}</p>
                    <p className="font-semibold text-white">{item.value}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="space-y-6">
          <div className="card">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Hiring Pipeline</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Candidate progress</h2>
              </div>
              <BarChart3 className="h-7 w-7 text-fuchsia-300" />
            </div>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {[
                { label: "Applied", value: "145" },
                { label: "Screening", value: "87" },
                { label: "Interview", value: "43" },
                { label: "Offer", value: "12" },
                { label: "Hired", value: "8" },
              ].map((item) => (
                <div key={item.label} className="rounded-3xl bg-slate-950/90 p-5">
                  <p className="text-sm text-slate-400">{item.label}</p>
                  <p className="mt-3 text-2xl font-semibold text-white">{item.value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Actions</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Workflow shortcuts</h2>
              </div>
              <Briefcase className="h-7 w-7 text-emerald-300" />
            </div>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {workflows.map(({ icon: Icon, title, desc, href }) => (
                <Link
                  key={title}
                  href={href}
                  className="rounded-3xl border border-slate-700/70 bg-slate-950/90 p-5 transition hover:border-indigo-500/50"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-indigo-300">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">{title}</p>
                      <p className="mt-1 text-sm text-slate-400">{desc}</p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-500">AI Match Leaderboard</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Top candidates</h2>
              </div>
              <Star className="h-7 w-7 text-yellow-300" />
            </div>
            <div className="mt-6 space-y-4">
              {leaderboard.map((item) => (
                <div key={item.name} className="rounded-3xl border border-slate-700/80 bg-slate-950/90 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <p className="font-medium text-white">{item.name}</p>
                    <p className="text-sm text-indigo-300">{item.score}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <p className="text-sm uppercase tracking-[0.24em] text-slate-500">HR Copilot</p>
            <div className="mt-4 rounded-3xl border border-slate-700/80 bg-slate-950/90 p-6">
              <p className="text-sm text-slate-400">Ask HR Copilot</p>
              <div className="mt-4 rounded-3xl bg-slate-900 p-5 text-sm text-slate-200">
                <p className="font-medium text-white">How many engineers should we hire next quarter?</p>
                <p className="mt-3 text-slate-400">
                  Based on forecasted growth and current backlog, hire 3 Backend Engineers and 2 Data
                  Scientists.
                </p>
              </div>
            </div>
            <Link href="/chat" className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500">
              Open HR Copilot
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

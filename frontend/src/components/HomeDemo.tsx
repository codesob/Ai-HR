"use client";

// Interactive previews on the home page. Everything here is local state with invented people;
// nothing is sent to the server.
import { useState } from "react";
import clsx from "clsx";
import { Check, CircleAlert } from "lucide-react";

const AVATAR_TONES = ["bg-brand-soft text-brand", "bg-[#e9e5f8] text-[#4b3f8f]", "bg-accent-soft text-warning", "bg-[#fbe4d8] text-[#8a3b1a]"];

function Avatar({ name, tone, size = "h-9 w-9 text-xs" }: { name: string; tone: number; size?: string }) {
  const initials = name.split(" ").map((p) => p[0]).join("");
  return (
    <span aria-hidden className={clsx("flex shrink-0 items-center justify-center rounded-full font-semibold", size, AVATAR_TONES[tone % AVATAR_TONES.length])}>
      {initials}
    </span>
  );
}

type Applicant = { name: string; years: number; skills: string; score: number; why: { ok: boolean; text: string }[] };

const APPLICANTS: Applicant[] = [
  {
    name: "Aisha Gurung", years: 6, skills: "PyTorch, model serving", score: 92,
    why: [
      { ok: true, text: "Shipped two ML systems to production" },
      { ok: true, text: "Matches 5 of 5 must-have skills" },
      { ok: false, text: "No Kubernetes listed (a nice-to-have)" },
    ],
  },
  {
    name: "Priya Shah", years: 4, skills: "NLP, data pipelines", score: 81,
    why: [
      { ok: true, text: "Matches 4 of 5 must-have skills" },
      { ok: true, text: "Built and ran data pipelines at scale" },
      { ok: false, text: "No model serving experience listed" },
    ],
  },
  {
    name: "Rohan Basnet", years: 3, skills: "Computer vision", score: 74,
    why: [
      { ok: true, text: "Strong PyTorch and Python" },
      { ok: false, text: "Less experience than the 5 years asked for" },
      { ok: false, text: "No production deployments listed" },
    ],
  },
  {
    name: "Daniel Okoro", years: 2, skills: "Analytics, SQL", score: 55,
    why: [
      { ok: true, text: "Solid Python and SQL" },
      { ok: false, text: "Matches 2 of 5 must-have skills" },
      { ok: false, text: "Less experience than the 5 years asked for" },
    ],
  },
];

const JOBS = [["ML Engineer", 4], ["Product Designer", 9], ["Support Lead", 6]] as const;

/** A working miniature of the hiring screen: pick a person, shortlist or pass. */
export function HiringPreview() {
  const [selected, setSelected] = useState(0);
  const [seen, setSeen] = useState<Set<number>>(new Set([0]));
  const [decision, setDecision] = useState<Record<number, "shortlisted" | "passed">>({});
  const a = APPLICANTS[selected];
  const shortlisted = Object.values(decision).filter((d) => d === "shortlisted").length;

  function pick(i: number) {
    setSelected(i);
    setSeen((s) => new Set(s).add(i));
  }

  function decide(d: "shortlisted" | "passed") {
    setDecision((prev) => ({ ...prev, [selected]: d }));
    const next = APPLICANTS.findIndex((_, i) => i !== selected && !decision[i]);
    if (next !== -1) pick(next);
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-(--shadow-lift)">
      <div className="flex items-center justify-between gap-4 border-b border-line px-4 py-2.5 text-xs text-muted">
        <span className="flex items-center gap-3">
          <span className="flex gap-1.5" aria-hidden>
            <span className="h-2.5 w-2.5 rounded-full bg-line-strong" />
            <span className="h-2.5 w-2.5 rounded-full bg-line-strong" />
            <span className="h-2.5 w-2.5 rounded-full bg-line-strong" />
          </span>
          Hiring › ML Engineer
        </span>
        <span>{shortlisted} shortlisted · {seen.size} of {APPLICANTS.length} reviewed</span>
      </div>

      <div className="grid md:grid-cols-[11rem_1fr_1fr]">
        <nav aria-label="Example menu" className="hidden space-y-5 border-r border-line p-3 text-sm md:block">
          <div className="space-y-1">
            <p className="px-2 text-[0.7rem] font-semibold tracking-wider text-muted uppercase">Open jobs</p>
            {JOBS.map(([title, n], i) => (
              <p key={title} className={clsx("flex justify-between rounded-lg px-2 py-1.5", i === 0 ? "bg-brand-soft font-semibold text-brand" : "text-ink-soft")}>
                {title} <span className="tabular-nums">{n}</span>
              </p>
            ))}
          </div>
          <div className="space-y-1">
            <p className="px-2 text-[0.7rem] font-semibold tracking-wider text-muted uppercase">People</p>
            {["Time off", "Payroll", "Ask HR"].map((l) => <p key={l} className="px-2 py-1.5 text-ink-soft">{l}</p>)}
          </div>
        </nav>

        <div className="border-b border-line p-3 md:border-r md:border-b-0">
          <p className="flex justify-between px-2 pb-2 text-[0.7rem] font-semibold tracking-wider text-muted uppercase">
            <span>Applicant</span><span>Match</span>
          </p>
          <ul className="space-y-1">
            {APPLICANTS.map((p, i) => (
              <li key={p.name}>
                <button
                  type="button"
                  onClick={() => pick(i)}
                  aria-pressed={selected === i}
                  className={clsx(
                    "flex w-full items-center gap-3 rounded-xl border px-2.5 py-2 text-left transition",
                    selected === i ? "border-brand bg-brand-soft/60" : "border-transparent hover:bg-surface-2",
                  )}
                >
                  <Avatar name={p.name} tone={i} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold">{p.name}</span>
                    <span className="block truncate text-xs text-muted">{p.years} yrs · {p.skills}</span>
                  </span>
                  {decision[i] === "shortlisted" ? (
                    <span className="badge bg-brand text-white">Shortlisted</span>
                  ) : decision[i] === "passed" ? (
                    <span className="badge bg-surface-2 text-muted">Not now</span>
                  ) : !seen.has(i) ? (
                    <span className="badge bg-accent-soft text-warning">New</span>
                  ) : null}
                  <span className="w-8 text-right font-display text-xl tabular-nums">{p.score}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-4 p-5" aria-live="polite">
          <div className="flex items-center gap-3">
            <Avatar name={a.name} tone={selected} size="h-11 w-11 text-sm" />
            <div>
              <p className="font-display text-2xl leading-tight">{a.name}</p>
              <p className="text-xs text-muted">{a.years} yrs · {a.skills}</p>
            </div>
          </div>
          <div className="space-y-1.5">
            <p className="flex justify-between text-xs font-semibold"><span>Match with the job</span><span className="tabular-nums">{a.score} / 100</span></p>
            <div className="h-1.5 rounded-full bg-surface-2">
              <div className="h-1.5 rounded-full bg-brand transition-all duration-300" style={{ width: `${a.score}%` }} />
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-[0.7rem] font-semibold tracking-wider text-muted uppercase">Why</p>
            <ul className="space-y-2 text-sm">
              {a.why.map((w) => (
                <li key={w.text} className="flex gap-2">
                  {w.ok
                    ? <Check className="mt-0.5 h-4 w-4 shrink-0 text-brand" aria-label="Meets" />
                    : <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-label="Gap" />}
                  {w.text}
                </li>
              ))}
            </ul>
          </div>
          <div className="grid grid-cols-2 gap-2 pt-1">
            <button type="button" className="btn-secondary py-2 text-sm" onClick={() => decide("passed")}>Not now</button>
            <button type="button" className="btn-primary py-2 text-sm" onClick={() => decide("shortlisted")}>Shortlist</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Moment({ time, children }: { time: string; children: React.ReactNode }) {
  return (
    <li className="grid grid-cols-[3.5rem_1fr] gap-4 sm:grid-cols-[4.5rem_1fr]">
      <span className="pt-4 text-right font-display text-lg tabular-nums">{time}</span>
      <div className="relative">
        {children}
      </div>
    </li>
  );
}

/** "A Monday" timeline: four small HR moments, each clickable. */
export function MondayTimeline() {
  const [leave, setLeave] = useState<"open" | "approved" | "declined">("open");
  const [answer, setAnswer] = useState(false);
  const [paid, setPaid] = useState(false);

  return (
    <ol className="relative space-y-4 before:absolute before:top-6 before:bottom-6 before:left-[4.25rem] before:w-px before:bg-line-strong sm:before:left-[5.25rem]">
      <Moment time="9:02">
        <div className="card space-y-3 p-4">
          <div className="flex gap-3">
            <Avatar name="Sam Rai" tone={2} />
            <div>
              <p className="text-sm font-semibold">Sam Rai wants Nov 3 – 7 off</p>
              <p className="text-xs text-muted">Vacation · 5 days · nobody else on the team is out</p>
            </div>
          </div>
          {leave === "open" ? (
            <div className="flex gap-2">
              <button type="button" className="btn-primary px-4 py-1.5 text-sm" onClick={() => setLeave("approved")}>Approve</button>
              <button type="button" className="btn-secondary px-4 py-1.5 text-sm" onClick={() => setLeave("declined")}>Decline</button>
            </div>
          ) : (
            <p className="flex items-center gap-2 text-sm">
              <span className={clsx("badge", leave === "approved" ? "bg-brand-soft text-brand" : "bg-surface-2 text-muted")}>
                {leave === "approved" ? "Approved" : "Declined"}
              </span>
              Sam has been told.
              <button type="button" className="text-muted underline underline-offset-2" onClick={() => setLeave("open")}>Undo</button>
            </p>
          )}
        </div>
      </Moment>

      <Moment time="11:40">
        <div className="card space-y-3 p-4">
          <div className="flex gap-3">
            <Avatar name="Priya Shah" tone={1} />
            <div>
              <p className="text-sm font-semibold">Priya asks: “Can I carry unused vacation into next year?”</p>
              <p className="text-xs text-muted">Asked in AI-HR, not in your inbox</p>
            </div>
          </div>
          {answer ? (
            <p className="rounded-xl bg-surface-2 px-3 py-2 text-sm text-ink-soft">
              Yes, up to 5 unused days carry over and must be used by March 31.{" "}
              <span className="text-muted">· Leave policy, §4</span>
            </p>
          ) : (
            <button type="button" className="btn-secondary px-4 py-1.5 text-sm" onClick={() => setAnswer(true)}>See what AI-HR answered</button>
          )}
        </div>
      </Moment>

      <Moment time="14:15">
        <div className="card space-y-3 p-4">
          <div>
            <p className="text-sm font-semibold">New applications for Product Designer</p>
            <p className="text-xs text-muted">Already read and ranked. Two look strong.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {[["Maya K.", 88], ["Jon T.", 84]].map(([n, s], i) => (
              <span key={n} className="inline-flex items-center gap-2 rounded-full border border-line bg-surface-2 py-1 pr-3 pl-1 text-xs font-semibold">
                <Avatar name={String(n)} tone={i} size="h-6 w-6 text-[0.6rem]" />
                {n} · {s}
              </span>
            ))}
            <span className="inline-flex items-center rounded-full border border-line px-3 py-1 text-xs text-muted">+ 7 more</span>
          </div>
        </div>
      </Moment>

      <Moment time="17:30">
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-card bg-navy p-4 text-white">
          <div className="space-y-3">
            <div>
              <p className="text-sm font-semibold">{paid ? "Done. Everyone's been paid." : "It's payday. October payroll is ready."}</p>
              <p className="text-xs text-white/60">24 people · salaries checked · payslips ready</p>
            </div>
            {paid ? (
              <p className="flex items-center gap-2 text-sm text-accent"><Check className="h-4 w-4" aria-hidden />Payslips sent</p>
            ) : (
              <button type="button" className="btn-accent px-4 py-1.5 text-sm" onClick={() => setPaid(true)}>Run payroll</button>
            )}
          </div>
          <p className="font-display text-3xl tabular-nums">$48,250.00</p>
        </div>
      </Moment>
    </ol>
  );
}

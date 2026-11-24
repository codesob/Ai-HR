import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { HiringPreview, MondayTimeline } from "@/components/HomeDemo";

/** Hand-drawn yellow underline. */
function Swoosh({ className }: { className: string }) {
  return (
    <svg aria-hidden viewBox="0 0 300 16" preserveAspectRatio="none" className={className}>
      <path d="M3 11 C 70 4, 180 3, 297 8" fill="none" stroke="var(--color-accent)" strokeWidth="5" strokeLinecap="round" />
    </svg>
  );
}

/** Hand-drawn arrow for margin notes; points down by default. */
function DoodleArrow({ className }: { className: string }) {
  return (
    <svg aria-hidden viewBox="0 0 40 30" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M4 4 C 16 4, 26 10, 30 24" />
      <path d="M23 19 L 30 25 L 34 16" />
    </svg>
  );
}

export default function HomePage() {
  return (
    <div className="space-y-28 pb-8">
      <section id="product" className="space-y-6 pt-4">
        <div className="grid gap-10 lg:grid-cols-[1.35fr_1fr] lg:items-end">
          <div className="relative pb-6">
            <h1 className="text-5xl leading-[1.02] sm:text-6xl lg:text-7xl">
              Read every resume. Call the{" "}
              <span className="relative inline-block">
                right five.
                <Swoosh className="absolute -bottom-3 left-0 h-4 w-full" />
              </span>
            </h1>
            <p className="note absolute -bottom-4 left-0 hidden items-end gap-1 sm:flex">
              click a person <DoodleArrow className="h-6 w-8 translate-y-2" />
            </p>
          </div>
          <div className="space-y-5 lg:pb-6">
            <p className="text-lg leading-relaxed text-ink-soft">
              AI-HR goes through every application, ranks it against the job, and writes down why. Time off, payroll
              and HR questions sit in the same place. You make every call.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/signup" className="btn-primary px-6 py-3">
                Set up your company <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
              <Link href="/login" className="btn-secondary px-6 py-3">Sign in</Link>
            </div>
            <div className="flex items-start justify-between gap-4">
              <p className="text-sm text-muted">Free to start. Post your first job in a few minutes.</p>
              <p className="note hidden shrink-0 items-center gap-1 lg:flex">
                <DoodleArrow className="h-6 w-8 -scale-x-100" /> the “why”, every time
              </p>
            </div>
          </div>
        </div>
        <HiringPreview />
      </section>

      <section className="grid gap-12 lg:grid-cols-[1fr_1.3fr]">
        <div className="space-y-5">
          <p className="eyebrow">The rest of HR</p>
          <h2 className="text-5xl leading-[1.05]">A Monday, without the spreadsheet.</h2>
          <p className="max-w-md text-ink-soft">
            Hiring is the big one, but most HR is small stuff that piles up. Here&apos;s what a normal day looks like.
            Each card works, so go ahead and click.
          </p>
          <p className="note flex items-center gap-2">all of this used to be emails <ArrowRight className="h-5 w-5" aria-hidden /></p>
        </div>
        <MondayTimeline />
      </section>

      <section className="grid items-center gap-10 rounded-3xl bg-brand-soft px-8 py-14 sm:px-14 lg:grid-cols-2">
        <h2 className="text-5xl leading-[1.05]">
          The score never says no. <span className="text-brand">You do.</span>
        </h2>
        <div className="space-y-5">
          <p className="leading-relaxed text-ink-soft">
            We built AI-HR to help you read faster, not to decide for you. It never rejects anyone on its own, every
            number comes with the reasons behind it, and you can always see exactly what the job asked for.
          </p>
          <Link href="/trust" className="inline-block text-sm font-semibold text-brand underline underline-offset-4">
            How scoring works →
          </Link>
        </div>
      </section>

      <section className="relative overflow-hidden rounded-3xl bg-brand px-8 py-14 sm:px-14">
        <div aria-hidden className="absolute -top-20 -right-16 h-56 w-56 rounded-full border-[28px] border-white/10" />
        <div className="relative flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-3">
            <h2 className="text-5xl text-white">Bring your first job.</h2>
            <p className="max-w-md text-white/80">Create your company, post a job and share the link. Invite your team when you&apos;re ready.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/signup" className="btn-accent px-6 py-3">
              Set up your company <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
            <Link href="/login" className="inline-flex items-center rounded-full border border-white/40 px-6 py-3 font-semibold text-white transition hover:bg-white/10">
              Sign in
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

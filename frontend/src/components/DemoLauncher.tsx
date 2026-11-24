"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import clsx from "clsx";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { homeFor, setSession } from "@/lib/auth";

export const DEMO_ENABLED = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

const MAIN = { email: "admin@aihr.demo", label: "Open the sample company", note: "No sign-up. You'll be the HR manager of a sample company." };

// Plain-language entry points; each signs in as one of the seeded demo accounts.
const OTHERS = [
  { email: "employee@aihr.demo", label: "I work there", desc: "Book time off, see payslips, ask HR questions" },
  { email: "candidate@aihr.demo", label: "I'm looking for a job", desc: "Upload a resume and track applications" },
];

/** Signs in to a seeded demo account and opens its home page. */
function useDemoLaunch() {
  const router = useRouter();
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");
  async function launch(email: string) {
    setPending(email);
    setError("");
    try {
      const { user } = await api.login(email, "demo12345");
      setSession({ user });
      router.push(homeFor(user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't open the demo");
      setPending(null);
    }
  }
  return { pending, error, launch };
}

/**
 * "Open the sample company" button. Without demo mode it links to sign-up instead.
 */
export function DemoButton({ className, children }: { className: string; children: ReactNode }) {
  const { pending, error, launch } = useDemoLaunch();
  if (!DEMO_ENABLED) {
    return <Link href="/signup" className={className}>{children}</Link>;
  }
  return (
    <>
      <button type="button" onClick={() => launch(MAIN.email)} disabled={pending !== null} className={className}>
        {pending ? "Opening…" : children}
      </button>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
    </>
  );
}

/** One-click sign-in to the seeded demo workspace. Renders nothing unless demo mode is on. */
export function DemoLauncher({ compact = false, inverted = false }: { compact?: boolean; inverted?: boolean }) {
  const { pending, error, launch } = useDemoLaunch();

  if (!DEMO_ENABLED) return null;

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <button
          type="button"
          onClick={() => launch(MAIN.email)}
          disabled={pending !== null}
          className={clsx(inverted ? "btn-accent w-full" : "btn-primary w-full", compact ? "px-7 py-4 text-lg" : "py-3.5 text-base sm:w-auto sm:px-8")}
        >
          {pending === MAIN.email ? "Opening…" : MAIN.label}
          <ArrowRight className="h-5 w-5" aria-hidden />
        </button>
        <p className={inverted ? "text-sm text-white/70" : "hint"}>{MAIN.note}</p>
      </div>

      {!compact && (
        <div className="space-y-2 pt-2">
          <p className={inverted ? "text-sm font-medium text-canvas" : "text-sm font-medium text-subtle"}>Or see it as…</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {OTHERS.map(({ email, label, desc }) => (
              <button
                key={email}
                type="button"
                onClick={() => launch(email)}
                disabled={pending !== null}
                className={
                  inverted
                    ? "rounded-xl border border-white/15 bg-white/5 px-4 py-3 text-left transition hover:bg-white/10 disabled:opacity-60"
                    : "rounded-xl border border-line bg-surface px-4 py-3 text-left transition hover:border-line-strong disabled:opacity-60"
                }
              >
                <span className={inverted ? "block font-semibold text-canvas" : "block font-semibold text-ink"}>
                  {pending === email ? "Opening…" : label}
                </span>
                <span className={inverted ? "block text-sm text-white/70" : "block text-sm text-muted"}>{desc}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

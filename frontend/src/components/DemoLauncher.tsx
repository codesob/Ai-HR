"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Briefcase, ShieldCheck, UserRound, UsersRound } from "lucide-react";
import { api } from "@/lib/api";
import { homeFor, setSession } from "@/lib/auth";

export const DEMO_ENABLED = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

const ROLES = [
  { email: "admin@aihr.demo", label: "HR admin", desc: "Analytics, team and approvals", icon: ShieldCheck },
  { email: "recruiter@aihr.demo", label: "Recruiter", desc: "Jobs and ranked candidates", icon: Briefcase },
  { email: "employee@aihr.demo", label: "Employee", desc: "Leave, payslips, HR assistant", icon: UsersRound },
  { email: "candidate@aihr.demo", label: "Candidate", desc: "Apply and track applications", icon: UserRound },
];

/** One-click sign-in to the seeded demo workspace. Renders nothing unless demo mode is on. */
export function DemoLauncher({ compact = false }: { compact?: boolean }) {
  const router = useRouter();
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");

  if (!DEMO_ENABLED) return null;

  async function launch(email: string) {
    setPending(email);
    setError("");
    try {
      const { access_token, user } = await api.login(email, "demo12345");
      setSession({ token: access_token, user });
      router.push(homeFor(user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't open the demo");
      setPending(null);
    }
  }

  return (
    <div className="space-y-3">
      {!compact && <p className="text-sm text-muted">Explore Halcyon Robotics, a sample company, as:</p>}
      <div className={compact ? "grid gap-2 sm:grid-cols-2" : "grid gap-3 sm:grid-cols-2 lg:grid-cols-4"}>
        {ROLES.map(({ email, label, desc, icon: Icon }) => (
          <button
            key={email}
            type="button"
            onClick={() => launch(email)}
            disabled={pending !== null}
            className="group flex items-start gap-3 rounded-2xl border border-line-strong bg-surface p-4 text-left transition hover:border-brand/50 hover:bg-surface-2 disabled:opacity-60"
          >
            <Icon className="mt-0.5 h-5 w-5 shrink-0 text-brand" aria-hidden />
            <span>
              <span className="block font-semibold text-ink">
                {pending === email ? "Opening…" : label}
              </span>
              <span className="block text-xs text-muted">{desc}</span>
            </span>
          </button>
        ))}
      </div>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

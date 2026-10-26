"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { LoginForm } from "@/components/LoginForm";
import { homeFor, type Role, type SessionUser } from "@/lib/auth";
import { useSession } from "@/lib/useSession";

export function AuthGate({
  roles,
  title,
  demoEmail,
  children,
}: {
  roles?: Role[];
  title: string;
  demoEmail?: string;
  children: (user: SessionUser) => ReactNode;
}) {
  const { session, hydrated } = useSession();

  if (!hydrated) return <p className="text-slate-400">Loading…</p>;

  if (!session) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">{title}</h1>
        <LoginForm demoEmail={demoEmail} />
        <p className="text-sm text-slate-400">
          New company?{" "}
          <Link href="/signup" className="text-indigo-300 hover:underline">
            Create a workspace
          </Link>
        </p>
      </div>
    );
  }

  if (roles && !roles.includes(session.user.role)) {
    return (
      <div className="card max-w-lg space-y-3">
        <h1 className="text-xl font-semibold">{title}</h1>
        <p className="text-slate-400">Your account ({session.user.role}) doesn&apos;t have access to this page.</p>
        <Link href={homeFor(session.user.role)} className="btn-secondary">
          Go to your dashboard
        </Link>
      </div>
    );
  }

  return <>{children(session.user)}</>;
}

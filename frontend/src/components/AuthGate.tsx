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

  if (!hydrated) return <p className="text-muted">Loading…</p>;

  if (!session) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <LoginForm demoEmail={demoEmail} />
        <p className="text-sm text-muted">
          New company?{" "}
          <Link href="/signup" className="text-brand hover:underline">
            Create a workspace
          </Link>
        </p>
      </div>
    );
  }

  if (roles && !roles.includes(session.user.role)) {
    return (
      <div className="card max-w-lg space-y-3">
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        <p className="text-muted">Your account ({session.user.role}) doesn&apos;t have access to this page.</p>
        <Link href={homeFor(session.user.role)} className="btn-secondary">
          Go to your dashboard
        </Link>
      </div>
    );
  }

  return <>{children(session.user)}</>;
}

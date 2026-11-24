"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { DEMO_ENABLED, DemoButton } from "@/components/DemoLauncher";
import { LoginForm } from "@/components/LoginForm";
import { getSession, homeFor } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  return (
    <div className="mx-auto max-w-md space-y-6 py-6">
      <div className="space-y-1">
        <h1 className="text-4xl">Welcome back.</h1>
        <p className="text-muted">Sign in to your workspace.</p>
      </div>
      <LoginForm
        demoEmail="admin@aihr.demo"
        onSuccess={() => {
          const session = getSession();
          router.push(session ? homeFor(session.user.role) : "/");
        }}
      />
      {DEMO_ENABLED && (
        <section className="flex flex-wrap items-center justify-between gap-3 rounded-card bg-brand-soft px-5 py-4">
          <p className="note">just looking?</p>
          <DemoButton className="btn-secondary py-2 text-sm">
            Open the sample company <ArrowRight className="h-4 w-4" aria-hidden />
          </DemoButton>
        </section>
      )}
      <p className="text-sm text-muted">
        New company?{" "}
        <Link href="/signup" className="font-semibold text-brand underline underline-offset-4">
          Create a workspace
        </Link>
      </p>
    </div>
  );
}

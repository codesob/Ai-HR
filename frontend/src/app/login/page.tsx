"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { DEMO_ENABLED, DemoLauncher } from "@/components/DemoLauncher";
import { LoginForm } from "@/components/LoginForm";
import { getSession, homeFor } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  return (
    <div className="mx-auto max-w-md space-y-6 py-6">
      <h1 className="text-2xl font-semibold tracking-tight">Sign in to AI-HR</h1>
      <LoginForm
        demoEmail="admin@aihr.demo"
        onSuccess={() => {
          const session = getSession();
          router.push(session ? homeFor(session.user.role) : "/");
        }}
      />
      {DEMO_ENABLED && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-ink-soft">Or jump straight into the demo</h2>
          <DemoLauncher compact />
        </section>
      )}
      <p className="text-sm text-muted">
        New company?{" "}
        <Link href="/signup" className="text-brand hover:underline">
          Create a workspace
        </Link>
      </p>
    </div>
  );
}

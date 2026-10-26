"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LoginForm } from "@/components/LoginForm";
import { getSession, homeFor } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  return (
    <div className="mx-auto max-w-md space-y-6">
      <h1 className="text-2xl font-bold">Sign in to AI-HR</h1>
      <LoginForm
        demoEmail="admin@aihr.demo"
        onSuccess={() => {
          const session = getSession();
          router.push(session ? homeFor(session.user.role) : "/");
        }}
      />
      <p className="text-sm text-slate-400">
        New company?{" "}
        <Link href="/signup" className="text-indigo-300 hover:underline">
          Create a workspace
        </Link>
      </p>
    </div>
  );
}

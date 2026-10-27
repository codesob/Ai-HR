"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Alert } from "@/components/ui";
import { api } from "@/lib/api";
import { homeFor, setSession } from "@/lib/auth";

function ResetPassword() {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) return setError("The two passwords don't match.");
    setLoading(true);
    setError("");
    try {
      const { user } = await api.resetPassword(token, password);
      setSession({ user });
      router.push(homeFor(user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't reset your password.");
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="mx-auto max-w-md space-y-4 py-6">
        <h1 className="text-3xl">This link is incomplete</h1>
        <p className="text-muted">Open the link from your email again, or ask for a new one.</p>
        <Link href="/forgot-password" className="btn-primary">Send a new link</Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md space-y-6 py-6">
      <h1 className="text-3xl">Choose a new password</h1>
      <form onSubmit={submit} className="card space-y-4">
        {error && (
          <Alert>
            {error}{" "}
            {error.includes("expired") && <Link href="/forgot-password" className="font-semibold underline">Send a new link</Link>}
          </Alert>
        )}
        <label className="block">
          <span className="label">New password (10+ characters)</span>
          <input className="input" type="password" required minLength={10} autoComplete="new-password"
            value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <label className="block">
          <span className="label">Type it again</span>
          <input className="input" type="password" required minLength={10} autoComplete="new-password"
            value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </label>
        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? "Saving…" : "Save and sign in"}
        </button>
        <p className="text-sm text-muted">For your safety, this signs you out on every other device.</p>
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading…</p>}>
      <ResetPassword />
    </Suspense>
  );
}

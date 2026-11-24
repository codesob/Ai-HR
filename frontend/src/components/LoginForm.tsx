"use client";

import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { setSession } from "@/lib/auth";

const DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

export function LoginForm({ onSuccess, demoEmail }: { onSuccess?: () => void; demoEmail?: string }) {
  const [email, setEmail] = useState(DEMO && demoEmail ? demoEmail : "");
  const [password, setPassword] = useState(DEMO && demoEmail ? "demo12345" : "");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { user } = await api.login(email, password);
      setSession({ user });
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleLogin} className="card space-y-4">
      {DEMO && demoEmail && <p className="text-xs text-muted">Demo account: {demoEmail} / demo12345</p>}
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <label className="block">
        <span className="label">Email</span>
        <input className="input" type="email" autoComplete="email" required value={email}
          onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label className="block">
        <span className="flex items-baseline justify-between">
          <span className="label">Password</span>
          <Link href="/forgot-password" className="text-sm font-semibold text-brand-ink hover:underline">Forgot password?</Link>
        </span>
        <input className="input" type="password" autoComplete="current-password" required value={password}
          onChange={(e) => setPassword(e.target.value)} />
      </label>
      <button type="submit" className="btn-primary w-full" disabled={loading}>
        {loading ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}

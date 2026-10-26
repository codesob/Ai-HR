"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { api } from "@/lib/api";
import { homeFor, setSession } from "@/lib/auth";

function AcceptInvite() {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { access_token, user } = await api.acceptInvite({ token, full_name: fullName, password });
      setSession({ token: access_token, user });
      router.push(homeFor(user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not accept invitation");
    } finally {
      setLoading(false);
    }
  }

  if (!token) return <p className="text-slate-400">This invitation link is missing its token.</p>;

  return (
    <form onSubmit={submit} className="card mx-auto max-w-md space-y-4">
      <h1 className="text-xl font-semibold">Join your team on AI-HR</h1>
      {error && (
        <p role="alert" className="text-sm text-red-400">
          {error}
        </p>
      )}
      <label className="block space-y-1 text-sm">
        <span className="text-slate-300">Your name</span>
        <input className="input" required autoComplete="name" value={fullName}
          onChange={(e) => setFullName(e.target.value)} />
      </label>
      <label className="block space-y-1 text-sm">
        <span className="text-slate-300">Choose a password (10+ characters)</span>
        <input className="input" type="password" required minLength={10} autoComplete="new-password"
          value={password} onChange={(e) => setPassword(e.target.value)} />
      </label>
      <button type="submit" className="btn-primary w-full" disabled={loading}>
        {loading ? "Joining…" : "Accept invitation"}
      </button>
    </form>
  );
}

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={<p className="text-slate-400">Loading…</p>}>
      <AcceptInvite />
    </Suspense>
  );
}

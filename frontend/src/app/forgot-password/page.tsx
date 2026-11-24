"use client";

import Link from "next/link";
import { useState } from "react";
import { MailCheck } from "lucide-react";
import { Alert } from "@/components/ui";
import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6 py-6">
      <h1 className="text-3xl">Reset your password</h1>
      {sent ? (
        <div className="card space-y-3">
          <MailCheck className="h-8 w-8 text-success" aria-hidden />
          <p className="text-lg font-semibold">Check your email</p>
          <p className="text-muted">
            If <b className="text-ink">{email}</b> has an account, we&apos;ve sent a link to choose a new password.
            It works for one hour.
          </p>
        </div>
      ) : (
        <form onSubmit={submit} className="card space-y-4">
          <p className="text-muted">Enter the email you sign in with and we&apos;ll send you a link to choose a new password.</p>
          {error && <Alert>{error}</Alert>}
          <label className="block">
            <span className="label">Email</span>
            <input className="input" type="email" autoComplete="email" required value={email}
              onChange={(e) => setEmail(e.target.value)} />
          </label>
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
      <p className="text-sm text-muted">
        Remembered it? <Link href="/login" className="font-semibold text-brand-ink hover:underline">Back to sign in</Link>
      </p>
    </div>
  );
}

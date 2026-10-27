"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { setSession } from "@/lib/auth";

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState({ company_name: "", full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const field = (key: keyof typeof form) => ({
    value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value }),
  });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { user } = await api.signup(form);
      setSession({ user });
      router.push("/team");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-up failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6 py-6">
      <div>
        <h1 className="text-2xl">Create your company workspace</h1>
        <p className="mt-1 text-muted">You&apos;ll be the workspace admin and can invite your team next.</p>
      </div>
      <form onSubmit={submit} className="card space-y-4">
        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
        <label className="block">
          <span className="label">Company name</span>
          <input className="input" required minLength={2} autoComplete="organization" {...field("company_name")} />
        </label>
        <label className="block">
          <span className="label">Your name</span>
          <input className="input" required autoComplete="name" {...field("full_name")} />
        </label>
        <label className="block">
          <span className="label">Work email</span>
          <input className="input" type="email" required autoComplete="email" {...field("email")} />
        </label>
        <label className="block">
          <span className="label">Password (10+ characters)</span>
          <input className="input" type="password" required minLength={10} autoComplete="new-password"
            {...field("password")} />
        </label>
        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? "Creating workspace…" : "Create workspace"}
        </button>
      </form>
      <p className="text-sm text-muted">
        Already have an account?{" "}
        <Link href="/login" className="text-brand-ink hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}

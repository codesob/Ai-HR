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
      const { access_token, user } = await api.signup(form);
      setSession({ token: access_token, user });
      router.push("/team");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-up failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Create your company workspace</h1>
        <p className="mt-1 text-slate-400">You&apos;ll be the workspace admin and can invite your team next.</p>
      </div>
      <form onSubmit={submit} className="card space-y-4">
        {error && (
          <p role="alert" className="text-sm text-red-400">
            {error}
          </p>
        )}
        <label className="block space-y-1 text-sm">
          <span className="text-slate-300">Company name</span>
          <input className="input" required minLength={2} autoComplete="organization" {...field("company_name")} />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-slate-300">Your name</span>
          <input className="input" required autoComplete="name" {...field("full_name")} />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-slate-300">Work email</span>
          <input className="input" type="email" required autoComplete="email" {...field("email")} />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-slate-300">Password (10+ characters)</span>
          <input className="input" type="password" required minLength={10} autoComplete="new-password"
            {...field("password")} />
        </label>
        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? "Creating workspace…" : "Create workspace"}
        </button>
      </form>
      <p className="text-sm text-slate-400">
        Already have an account?{" "}
        <Link href="/login" className="text-indigo-300 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}

"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { setToken } from "@/lib/auth";

export function LoginForm({
  onSuccess,
  defaultEmail = "recruiter@aihr.demo",
}: {
  onSuccess?: () => void;
  defaultEmail?: string;
}) {
  const [email, setEmail] = useState(defaultEmail);
  const [password, setPassword] = useState("demo12345");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleLogin} className="card max-w-md space-y-4">
      <h3 className="font-semibold">Sign in</h3>
      {error && <p className="text-sm text-red-400">{error}</p>}
      <input
        className="input"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
      />
      <input
        className="input"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
      />
      <button type="submit" className="btn-primary w-full" disabled={loading}>
        {loading ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}

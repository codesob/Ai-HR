"use client";

import { useCallback, useEffect, useState } from "react";
import { Laptop, Smartphone } from "lucide-react";
import { AuthGate } from "@/components/AuthGate";
import { PageHeader } from "@/components/PageHeader";
import { Alert } from "@/components/ui";
import { api, type DeviceSession } from "@/lib/api";
import { setSession, type SessionUser } from "@/lib/auth";

type Notice = { tone: "success" | "danger"; text: string } | null;

function describeDevice(ua: string): { label: string; mobile: boolean } {
  const mobile = /Mobi|Android|iPhone|iPad/i.test(ua);
  const browser = /Edg\//.test(ua) ? "Edge" : /Chrome\//.test(ua) ? "Chrome" : /Firefox\//.test(ua) ? "Firefox"
    : /Safari\//.test(ua) ? "Safari" : "Browser";
  const os = /Windows/.test(ua) ? "Windows" : /Mac OS X/.test(ua) && !mobile ? "Mac" : /Android/.test(ua) ? "Android"
    : /iPhone|iPad/.test(ua) ? "iPhone / iPad" : /Linux/.test(ua) ? "Linux" : "";
  return { label: ua ? `${browser}${os ? ` on ${os}` : ""}` : "Unknown device", mobile };
}

function when(iso: string) {
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function Profile({ user }: { user: SessionUser }) {
  const [name, setName] = useState(user.full_name);
  const [notice, setNotice] = useState<Notice>(null);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      setSession({ user: await api.updateProfile(name) });
      setNotice({ tone: "success", text: "Saved." });
    } catch (err) {
      setNotice({ tone: "danger", text: err instanceof Error ? err.message : "Couldn't save." });
    }
  }

  return (
    <form onSubmit={save} className="card space-y-4">
      <h2 className="text-xl">Your details</h2>
      {notice && <Alert tone={notice.tone}>{notice.text}</Alert>}
      <label className="block">
        <span className="label">Name</span>
        <input className="input" required value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <div>
        <span className="label">Email</span>
        <p className="flex flex-wrap items-center gap-2">
          {user.email}
          {user.email_verified_at
            ? <span className="badge bg-success-soft text-success">Confirmed</span>
            : <span className="badge bg-warning-soft text-warning">Not confirmed yet</span>}
        </p>
      </div>
      <button type="submit" className="btn-primary" disabled={name.trim() === user.full_name}>Save</button>
    </form>
  );
}

function Password() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [notice, setNotice] = useState<Notice>(null);
  const [saving, setSaving] = useState(false);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await api.changePassword(current, next);
      setCurrent("");
      setNext("");
      setNotice({ tone: "success", text: "Password changed. Your other devices have been signed out." });
    } catch (err) {
      setNotice({ tone: "danger", text: err instanceof Error ? err.message : "Couldn't change your password." });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="card space-y-4">
      <h2 className="text-xl">Password</h2>
      {notice && <Alert tone={notice.tone}>{notice.text}</Alert>}
      <label className="block">
        <span className="label">Current password</span>
        <input className="input" type="password" required autoComplete="current-password" value={current}
          onChange={(e) => setCurrent(e.target.value)} />
      </label>
      <label className="block">
        <span className="label">New password (10+ characters)</span>
        <input className="input" type="password" required minLength={10} autoComplete="new-password" value={next}
          onChange={(e) => setNext(e.target.value)} />
      </label>
      <button type="submit" className="btn-primary" disabled={saving}>{saving ? "Saving…" : "Change password"}</button>
    </form>
  );
}

function Devices() {
  const [sessions, setSessions] = useState<DeviceSession[] | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => api.sessions().then(setSessions).catch((e) => setError(e.message)), []);
  useEffect(() => {
    void load();
  }, [load]);

  async function end(id?: number) {
    try {
      await (id === undefined ? api.endOtherSessions() : api.endSession(id));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't sign that device out.");
    }
  }

  const others = sessions?.filter((s) => !s.current).length ?? 0;

  return (
    <section className="card space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl">Where you&apos;re signed in</h2>
          <p className="text-muted">Don&apos;t recognise a device? Sign it out and change your password.</p>
        </div>
        {others > 0 && (
          <button type="button" className="btn-secondary" onClick={() => end()}>Sign out all other devices</button>
        )}
      </div>
      {error && <Alert>{error}</Alert>}
      <ul className="divide-y divide-line">
        {sessions?.map((s) => {
          const d = describeDevice(s.user_agent);
          const Icon = d.mobile ? Smartphone : Laptop;
          return (
            <li key={s.id} className="flex items-center gap-4 py-3">
              <Icon className="h-6 w-6 shrink-0 text-subtle" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="font-semibold">
                  {d.label} {s.current && <span className="badge ml-1 bg-success-soft text-success">This device</span>}
                </p>
                <p className="text-sm text-muted">Signed in {when(s.created_at)} · last active {when(s.last_used_at)}</p>
              </div>
              {!s.current && (
                <button type="button" className="btn-ghost" onClick={() => end(s.id)}>Sign out</button>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default function SettingsPage() {
  return (
    <AuthGate title="Settings">
      {(user) => (
        <div className="space-y-8">
          <PageHeader title="Settings" subtitle="Your name, password and the devices you're signed in on." />
          {user.email.endsWith("@aihr.demo") ? (
            <div className="card space-y-2">
              <h2 className="text-xl">Settings are locked in the demo</h2>
              <p className="text-muted">
                Everyone trying the demo shares this account, so its name, password and devices can&apos;t be changed.
                Create your own workspace to get the full settings page.
              </p>
            </div>
          ) : (
            <>
              <div className="grid gap-6 lg:grid-cols-2">
                <Profile user={user} />
                <Password />
              </div>
              <Devices />
            </>
          )}
        </div>
      )}
    </AuthGate>
  );
}

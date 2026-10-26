"use client";

import { useCallback, useEffect, useState } from "react";
import { AuthGate } from "@/components/AuthGate";
import { PageHeader } from "@/components/PageHeader";
import { api, type Organization } from "@/lib/api";
import type { SessionUser } from "@/lib/auth";

const ROLES = ["recruiter", "employee", "admin"] as const;

function Team({ me }: { me: SessionUser }) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [users, setUsers] = useState<(SessionUser & { is_active?: boolean })[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<string>("recruiter");
  const [inviteUrl, setInviteUrl] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.users().then(setUsers).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    api.organization().then(setOrg).catch(() => undefined);
    load();
  }, [load]);

  async function invite(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const res = await api.invite(email, role);
      setInviteUrl(res.invite_url);
      setEmail("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invite failed");
    }
  }

  async function toggleActive(u: SessionUser & { is_active?: boolean }) {
    try {
      await api.updateUser(u.id, { is_active: !(u.is_active ?? true) });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  const careersUrl = org && typeof window !== "undefined" ? `${window.location.origin}/careers/${org.slug}` : "";

  return (
    <div className="space-y-8">
      <PageHeader title={org?.name ?? "Team"} subtitle="Invite your team and share your careers page" />
      {error && <p role="alert" className="text-sm text-red-400">{error}</p>}

      {careersUrl && (
        <div className="card">
          <h2 className="font-semibold">Your public careers page</h2>
          <p className="mt-2 break-all text-sm text-indigo-300">{careersUrl}</p>
        </div>
      )}

      <form onSubmit={invite} className="card space-y-3">
        <h2 className="font-semibold">Invite a teammate</h2>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input className="input" type="email" placeholder="name@company.com" required value={email}
            onChange={(e) => setEmail(e.target.value)} />
          <select className="input sm:max-w-44" value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <button className="btn-primary shrink-0" type="submit">Send invite</button>
        </div>
        {inviteUrl && (
          <p className="text-sm text-slate-300">
            Invitation created. If email isn&apos;t configured, share this link (valid 72h):
            <span className="mt-1 block break-all text-indigo-300">{inviteUrl}</span>
          </p>
        )}
      </form>

      <div className="card">
        <h2 className="mb-4 font-semibold">Members</h2>
        <ul className="divide-y divide-slate-800">
          {users.map((u) => (
            <li key={u.id} className="flex items-center justify-between gap-4 py-3 text-sm">
              <div>
                <p>{u.full_name} <span className="text-slate-500">· {u.email}</span></p>
                <p className="text-xs capitalize text-slate-400">{u.role}{u.is_active === false && " · deactivated"}</p>
              </div>
              {u.id !== me.id && (
                <button type="button" className="btn-secondary px-3 py-1.5 text-xs" onClick={() => toggleActive(u)}>
                  {u.is_active === false ? "Reactivate" : "Deactivate"}
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function TeamPage() {
  return (
    <AuthGate title="Team" roles={["admin"]} demoEmail="admin@aihr.demo">
      {(user) => <Team me={user} />}
    </AuthGate>
  );
}

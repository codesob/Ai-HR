"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";
import { ActivityLog } from "@/components/ActivityLog";
import { AuthGate } from "@/components/AuthGate";
import { PayrollPanel } from "@/components/PayrollPanel";
import { PageHeader } from "@/components/PageHeader";
import { Alert, Avatar } from "@/components/ui";
import { api, type Organization } from "@/lib/api";
import type { SessionUser } from "@/lib/auth";

const ROLES = ["recruiter", "employee", "admin"] as const;
const ROLE_ORDER = ["admin", "recruiter", "employee"];
const ROLE_LABELS: Record<string, string> = { admin: "Admin", recruiter: "Recruiter", employee: "Employee", candidate: "Candidate" };

function Team({ me }: { me: SessionUser }) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [users, setUsers] = useState<(SessionUser & { is_active?: boolean })[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<string>("recruiter");
  const [inviteUrl, setInviteUrl] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

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
  // Candidates sign up through the careers page; they belong in Recruiting, not the staff list.
  const staff = users
    .filter((u) => u.role !== "candidate")
    .sort((a, b) => ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role) || a.full_name.localeCompare(b.full_name));
  const applicants = users.length - staff.length;

  async function copyCareersUrl() {
    try {
      await navigator.clipboard.writeText(careersUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Couldn't copy. Select the link and copy it manually.");
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader title={org?.name ?? "Team"} subtitle="Your team, your careers page and payroll" />
      {error && <Alert>{error}</Alert>}

      {careersUrl && (
        <div className="card flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <h2 className="font-semibold">Your public careers page</h2>
            <a href={careersUrl} target="_blank" rel="noreferrer" className="mt-1 block truncate text-sm text-brand hover:underline">
              {careersUrl}
            </a>
          </div>
          <button type="button" className="btn-secondary shrink-0" onClick={copyCareersUrl}>
            {copied ? <><Check className="h-4 w-4 text-success" aria-hidden /> Copied</> : <><Copy className="h-4 w-4" aria-hidden /> Copy link</>}
          </button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        <form onSubmit={invite} className="card h-fit space-y-4">
          <h2 className="font-semibold">Invite a teammate</h2>
          <label className="block">
            <span className="label">Work email</span>
            <input className="input" type="email" placeholder="name@company.com" required value={email}
              onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="block">
            <span className="label">Role</span>
            <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
              {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
            </select>
          </label>
          <button className="btn-primary w-full" type="submit">Send invite</button>
          {inviteUrl && (
            <Alert tone="success">
              Invitation created. If email isn&apos;t set up, share this link (valid 72 hours):
              <span className="mt-1 block break-all font-medium">{inviteUrl}</span>
            </Alert>
          )}
        </form>

        <div className="card">
          <div className="mb-2 flex items-baseline justify-between">
            <h2 className="font-semibold">Team</h2>
            <span className="text-sm text-subtle">{staff.length} people</span>
          </div>
          <ul className="divide-y divide-line">
            {staff.map((u) => (
              <li key={u.id} className="flex items-center gap-3 py-3 text-sm">
                <Avatar name={u.full_name} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-ink">
                    {u.full_name}
                    {u.id === me.id && <span className="font-normal text-subtle"> (you)</span>}
                  </p>
                  <p className="truncate text-xs text-muted">{u.email}</p>
                </div>
                <span className="badge bg-surface-2 text-ink-soft">{ROLE_LABELS[u.role] ?? u.role}</span>
                {u.is_active === false && <span className="badge bg-danger-soft text-danger">Deactivated</span>}
                {u.id !== me.id && (
                  <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={() => toggleActive(u)}>
                    {u.is_active === false ? "Reactivate" : "Deactivate"}
                  </button>
                )}
              </li>
            ))}
          </ul>
          {applicants > 0 && (
            <p className="mt-3 border-t border-line pt-3 text-sm text-muted">
              Plus {applicants} candidate account{applicants === 1 ? "" : "s"} from your careers page.{" "}
              <Link href="/recruiter" className="text-brand hover:underline">See them in Recruiting</Link>
            </p>
          )}
        </div>
      </div>

      <PayrollPanel />
      <ActivityLog />
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

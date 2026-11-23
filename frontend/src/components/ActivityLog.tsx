"use client";

import { useEffect, useState } from "react";
import { api, type AuditEntry } from "@/lib/api";

// Most specific first; the first pattern that matches the method and path describes the event.
const DESCRIPTIONS: [string, RegExp, string][] = [
  ["PATCH", /\/applications\/\d+\/status$/, "moved a candidate to a new step"],
  ["POST", /\/applications\/apply\//, "applied to a job"],
  ["POST", /\/jobs\/generate$/, "drafted a job ad"],
  ["POST", /\/jobs$/, "posted a job"],
  ["PATCH", /\/jobs\/\d+$/, "edited a job"],
  ["POST", /\/interviews$/, "scheduled an interview"],
  ["POST", /\/interviews\/\d+\/room\/join$/, "joined an interview call"],
  ["POST", /\/interviews\/\d+\/room\/end$/, "finished an interview"],
  ["POST", /\/interviews\/\d+\/room\/consent$/, "answered whether the interview may be recorded"],
  ["POST", /\/interviews\/\d+\/room\/recording$/, "started or stopped recording an interview"],
  ["POST", /\/interviews\/\d+\/room\/audio$/, "saved part of an interview recording"],
  ["POST", /\/interviews\/\d+\/prep$/, "prepared interview questions"],
  ["PUT", /\/interviews\/\d+\/scorecard$/, "filled in an interview scorecard"],
  ["POST", /\/leave\/\d+\/review$/, "answered a time-off request"],
  ["POST", /\/leave$/, "asked for time off"],
  ["POST", /\/payroll\/run-all$/, "paid everyone (payroll)"],
  ["PUT", /\/payroll\/profile$/, "changed a salary"],
  ["POST", /\/users\/invite$/, "invited a teammate"],
  ["PATCH", /\/users\/\d+$/, "changed a teammate's access"],
  ["POST", /\/resumes\/upload$/, "uploaded a resume"],
  ["PATCH", /\/onboarding\/\d+\/tasks\//, "ticked off an onboarding task"],
  ["POST", /\/onboarding$/, "started onboarding a new hire"],
  ["POST", /\/agent\/run$/, "had the HR agent do the day's work"],
  ["POST", /\/agent\/chat$/, "asked HR"],
  ["POST", /\/agent\/actions\/\d+\/approve$/, "approved something the HR agent proposed"],
  ["POST", /\/agent\/actions\/\d+\/reject$/, "skipped something the HR agent proposed"],
  ["POST", /\/handbook$/, "added a handbook document"],
  ["DELETE", /\/handbook\/\d+$/, "removed a handbook document"],
  ["POST", /\/auth\/login$/, "signed in"],
  ["POST", /\/auth\/logout$/, "signed out"],
  ["POST", /\/auth\/signup$/, "created the workspace"],
  ["POST", /\/auth\/accept-invite$/, "joined the team"],
  ["POST", /\/auth\/password\/reset$/, "reset their password"],
  ["POST", /\/account\/password$/, "changed their password"],
  ["POST", /\/chat$/, "asked HR a question"],
];

function ago(iso: string): string {
  const mins = Math.round((Date.now() - Date.parse(iso)) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function describe(e: AuditEntry): string {
  const match = DESCRIPTIONS.find(([method, pattern]) => method === e.action && pattern.test(e.resource));
  return match ? match[2] : `${e.action} ${e.resource.replace(/^\/api\/v1/, "")}`;
}

type Row = { entry: AuditEntry; who: string; what: string; count: number };

/** Merges back-to-back entries by the same person doing the same thing ("moved a candidate … ×12"). */
function group(entries: AuditEntry[], names: Record<string, string>): Row[] {
  const rows: Row[] = [];
  for (const e of entries) {
    const who = (e.actor && names[e.actor]) || e.actor || "Someone";
    const what = describe(e);
    const failed = e.status_code !== null && e.status_code >= 400;
    const last = rows[rows.length - 1];
    if (last && !failed && last.who === who && last.what === what) last.count += 1;
    else rows.push({ entry: e, who, what, count: 1 });
  }
  return rows;
}

export function ActivityLog() {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [names, setNames] = useState<Record<string, string>>({});
  const [error, setError] = useState("");

  useEffect(() => {
    api.auditLog().then(setEntries).catch((e) => setError(e.message));
    api.users().then((us) => setNames(Object.fromEntries(us.map((u) => [u.email, u.full_name])))).catch(() => undefined);
  }, []);

  return (
    <div className="card space-y-4">
      <div>
        <h2 className="text-xl">Recent changes</h2>
        <p className="text-muted">Who did what in your company, newest first.</p>
      </div>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      {entries?.length === 0 && <p className="text-sm text-muted">No activity yet.</p>}
      <ul className="divide-y divide-line">
        {entries && group(entries, names).map(({ entry: e, who, what, count }) => (
          <li key={e.id} className="flex flex-wrap items-baseline justify-between gap-2 py-3">
            <span>
              <span className="font-semibold text-ink">{who}</span> <span className="text-muted">{what}</span>
              {count > 1 && <span className="badge ml-2 bg-surface-2 text-muted">{count} times</span>}
              {e.status_code !== null && e.status_code >= 400 && (
                <span className="badge ml-2 bg-danger-soft text-danger">failed ({e.status_code})</span>
              )}
            </span>
            <time className="text-sm text-subtle" dateTime={e.created_at} title={new Date(e.created_at).toLocaleString()}>
              {ago(e.created_at)}
            </time>
          </li>
        ))}
      </ul>
    </div>
  );
}

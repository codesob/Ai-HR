"use client";

import { useEffect, useState } from "react";
import { api, type AuditEntry } from "@/lib/api";

// Most specific first; the first pattern that matches the method and path describes the event.
const DESCRIPTIONS: [string, RegExp, string][] = [
  ["PATCH", /\/applications\/\d+\/status$/, "moved a candidate in the pipeline"],
  ["POST", /\/applications\/apply\//, "applied to a job"],
  ["POST", /\/jobs\/generate$/, "generated a job description"],
  ["POST", /\/jobs$/, "published a job"],
  ["PATCH", /\/jobs\/\d+$/, "edited a job"],
  ["POST", /\/interviews$/, "scheduled an interview"],
  ["POST", /\/leave\/\d+\/review$/, "reviewed a leave request"],
  ["POST", /\/leave$/, "requested leave"],
  ["POST", /\/payroll\/run-all$/, "ran payroll"],
  ["PUT", /\/payroll\/profile$/, "changed a salary"],
  ["POST", /\/users\/invite$/, "invited a teammate"],
  ["PATCH", /\/users\/\d+$/, "changed a teammate's access"],
  ["POST", /\/resumes\/upload$/, "uploaded a resume"],
  ["POST", /\/onboarding/, "updated onboarding"],
  ["POST", /\/chat$/, "asked the HR assistant"],
];

function describe(e: AuditEntry): string {
  const match = DESCRIPTIONS.find(([method, pattern]) => method === e.action && pattern.test(e.resource));
  return match ? match[2] : `${e.action} ${e.resource.replace(/^\/api\/v1/, "")}`;
}

export function ActivityLog() {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.auditLog().then(setEntries).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="card space-y-4">
      <div>
        <h2 className="font-semibold">Activity log</h2>
        <p className="text-sm text-muted">Every change made in your workspace, newest first.</p>
      </div>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      {entries?.length === 0 && <p className="text-sm text-muted">No activity yet.</p>}
      <ul className="divide-y divide-line text-sm">
        {entries?.map((e) => (
          <li key={e.id} className="flex flex-wrap items-baseline justify-between gap-2 py-2">
            <span>
              <span className="text-ink">{e.actor}</span> <span className="text-muted">{describe(e)}</span>
              {e.status_code !== null && e.status_code >= 400 && (
                <span className="badge ml-2 bg-danger-soft text-danger">failed ({e.status_code})</span>
              )}
            </span>
            <time className="text-xs text-subtle" dateTime={e.created_at}>
              {new Date(e.created_at).toLocaleString()}
            </time>
          </li>
        ))}
      </ul>
    </div>
  );
}

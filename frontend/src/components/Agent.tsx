"use client";

import { useState } from "react";
import clsx from "clsx";
import { Check, CircleAlert, Clock } from "lucide-react";
import type { AgentAction, AgentStep } from "@/lib/api";

type R = Record<string, unknown>;
const str = (v: unknown) => (v == null ? "" : String(v));

function fmtWhen(iso: unknown) {
  const d = new Date(str(iso));
  return Number.isNaN(d.getTime()) ? str(iso) : d.toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

/** One agent step in plain words. */
export function describeStep(step: AgentStep): { text: string; state: "done" | "waiting" | "error" } {
  const a = step.args as R;
  const r = step.result;
  if (r.error) return { text: r.error, state: "error" };
  if (r.waiting_for_approval) return { text: r.summary ?? "Waiting for your OK", state: "waiting" };
  const out = (r.result ?? {}) as R;
  const text = (() => {
    switch (step.tool) {
      case "get_workload": return "Checked what's waiting";
      case "list_applicants": return `Read the applicants for ${str((out.job as R | undefined)?.title) || "a job"}`;
      case "list_time_off_requests": return "Looked at the time-off requests";
      case "list_team": return "Looked at the team";
      case "search_policies": return `Looked up “${str(a.query)}” in the policies`;
      case "move_candidate": return `Moved ${str(out.name)} to ${str(out.stage)}`;
      case "schedule_interview": return `Booked an interview with ${str(out.candidate)} for ${fmtWhen(out.at)}`;
      case "decide_leave": return `${out.status === "approved" ? "Approved" : "Declined"} ${str(out.employee)}'s time off`;
      case "run_payroll": return `Paid ${str(out.processed)} people`;
      case "send_message": return `Emailed ${str(out.to)}`;
      case "send_task": return "Sent a take-home task";
      case "send_video_screen": return "Sent video screening questions";
      case "list_screening_to_review": return "Checked tasks and video answers waiting for review";
      case "decide_screening": return `${str(out.decision) === "pass" ? "Passed" : "Failed"} ${str(out.applicant)}`;
      case "read_resume": return `Read ${str(out.name)}'s resume`;
      case "list_onboarding": return "Checked new hires' checklists";
      case "start_onboarding": return out.already_open ? `${str(out.name)} is already onboarding` : `Started onboarding for ${str(out.name)}`;
      case "complete_onboarding_task": return `Ticked off “${str(out.task)}” for ${str(out.name)}`;
      case "my_time_off": return "Checked your time off";
      case "request_time_off": return `Booked ${str(out.days)} days off. HR will confirm`;
      case "my_payslips": return "Checked your payslips";
      case "my_applications": return "Checked your applications";
      default: return step.tool.replace(/_/g, " ");
    }
  })();
  return { text, state: "done" };
}

export function StepList({ steps, className }: { steps: AgentStep[]; className?: string }) {
  if (steps.length === 0) return null;
  return (
    <ul className={clsx("space-y-1.5 text-sm", className)}>
      {steps.map((s, i) => {
        const d = describeStep(s);
        return (
          <li key={i} className="flex gap-2">
            {d.state === "done" && <Check className="mt-0.5 h-4 w-4 shrink-0 text-brand" aria-label="Done" />}
            {d.state === "waiting" && <Clock className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-label="Waiting for approval" />}
            {d.state === "error" && <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-muted" aria-label="Couldn't do it" />}
            <span className={d.state === "error" ? "text-muted" : "text-ink-soft"}>
              {d.text}
              {d.state === "waiting" && <span className="text-muted"> · waiting for your OK</span>}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/** A change the agent wants to make, with Approve / Skip. */
export function ApprovalCard({ action, onDecide }: {
  action: AgentAction;
  onDecide: (id: number, approve: boolean) => Promise<void>;
}) {
  const [busy, setBusy] = useState<"approve" | "skip" | null>(null);
  async function decide(approve: boolean) {
    setBusy(approve ? "approve" : "skip");
    try {
      await onDecide(action.id, approve);
    } finally {
      setBusy(null);
    }
  }
  return (
    <li className="card flex flex-wrap items-center justify-between gap-4 p-4">
      <div className="min-w-0 space-y-1">
        <p className="font-semibold">{action.summary}</p>
        {action.reason && <p className="text-sm text-muted">Why: {action.reason}</p>}
      </div>
      <div className="flex shrink-0 gap-2">
        <button type="button" className="btn-secondary px-4 py-1.5 text-sm" onClick={() => decide(false)} disabled={busy !== null}>
          {busy === "skip" ? "Skipping…" : "Skip"}
        </button>
        <button type="button" className="btn-primary px-4 py-1.5 text-sm" onClick={() => decide(true)} disabled={busy !== null}>
          {busy === "approve" ? "Doing it…" : "Approve"}
        </button>
      </div>
    </li>
  );
}

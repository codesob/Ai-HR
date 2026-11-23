"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { ClipboardList, Play, Video, X } from "lucide-react";
import { Alert, Label } from "@/components/ui";
import { api, type Assessment, type Screening, type VideoScreen } from "@/lib/api";

const fmt = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });

const STATUS: Record<string, { label: string; tone: string }> = {
  sent: { label: "Waiting for their answer", tone: "bg-surface-2 text-muted" },
  invited: { label: "Waiting for their recording", tone: "bg-surface-2 text-muted" },
  submitted: { label: "Ready for your decision", tone: "bg-accent-soft text-warning" },
  completed: { label: "Ready for your decision", tone: "bg-accent-soft text-warning" },
  passed: { label: "Passed", tone: "bg-brand text-white" },
  failed: { label: "Didn't pass", tone: "bg-surface-2 text-muted" },
};

/** The AI's recommendation and the human pass/fail; the AI only advises. */
function Review({ item, onDecide }: { item: Assessment | VideoScreen; onDecide: (passed: boolean) => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const ready = item.status === "submitted" || item.status === "completed";
  return (
    <div className="space-y-3">
      {(ready || item.ai_recommendation) && (
        <div className="space-y-1.5 rounded-xl bg-surface-2 p-3 text-sm">
          <p className="flex items-center gap-1.5 font-semibold">
            AI review{item.ai_recommendation ? `: suggests ${item.ai_recommendation === "pass" ? "pass" : "fail"}` : ""}
            {item.ai_score != null && <span className="ml-auto font-display text-lg tabular-nums">{item.ai_score}</span>}
          </p>
          <p className="text-ink-soft">{item.ai_feedback || "Not reviewed yet. It usually takes a few seconds; refresh to check."}</p>
        </div>
      )}
      {ready && (
        <div className="space-y-2">
          <p className="text-xs text-muted">The AI only advises. Your decision is the one that counts, and the applicant is emailed.</p>
          <div className="grid grid-cols-2 gap-2">
            <button type="button" className="btn-secondary py-2 text-sm" disabled={busy}
              onClick={async () => { setBusy(true); await onDecide(false); setBusy(false); }}>Didn&apos;t pass</button>
            <button type="button" className="btn-primary py-2 text-sm" disabled={busy}
              onClick={async () => { setBusy(true); await onDecide(true); setBusy(false); }}>Pass</button>
          </div>
        </div>
      )}
    </div>
  );
}

function Recording({ screen, index }: { screen: VideoScreen; index: number }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);
  const answer = screen.answers.find((a) => a.index === index);
  return (
    <li className="space-y-2 rounded-xl border border-line p-3">
      <p className="text-sm font-semibold">{index + 1}. {screen.questions[index]}</p>
      {!answer ? (
        <p className="text-sm text-muted">Not answered yet.</p>
      ) : url ? (
        <video src={url} controls className="w-full rounded-lg bg-ink" />
      ) : (
        <button type="button" className="btn-secondary py-1.5 text-sm"
          onClick={() => api.videoAnswer(screen.id, index).then((b) => setUrl(URL.createObjectURL(b))).catch((e) => setError(e.message))}>
          <Play className="h-4 w-4" aria-hidden /> Watch
        </button>
      )}
      {error && <p className="text-sm text-danger">{error}</p>}
      {answer?.transcript && <p className="text-sm text-ink-soft"><span className="text-muted">Transcript: </span>{answer.transcript}</p>}
      {answer?.english && <p className="text-sm text-ink-soft"><span className="text-muted">In English: </span>{answer.english}</p>}
      {answer && answer.transcript === "" && <p className="text-sm text-muted">No clear speech in this recording.</p>}
    </li>
  );
}

function TaskForm({ applicationId, jobTitle, onSent, onCancel }: {
  applicationId: number; jobTitle: string; onSent: () => void; onCancel: () => void;
}) {
  const [title, setTitle] = useState(`${jobTitle} take-home task`);
  const [instructions, setInstructions] = useState("");
  const [days, setDays] = useState(5);
  const [error, setError] = useState("");
  return (
    <form className="space-y-3 rounded-xl bg-surface-2 p-3" onSubmit={async (e) => {
      e.preventDefault();
      try {
        await api.sendTask(applicationId, { title, instructions, due_days: days });
        onSent();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Couldn't send it.");
      }
    }}>
      {error && <Alert>{error}</Alert>}
      <label className="block"><span className="label">Title</span>
        <input className="input py-2" required minLength={3} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
      <label className="block"><span className="label">What should they do?</span>
        <textarea className="input" rows={5} required minLength={10} value={instructions}
          placeholder="Keep it to 2-4 hours of work and tied to the job's skills."
          onChange={(e) => setInstructions(e.target.value)} /></label>
      <div className="flex items-end gap-2">
        <label className="block"><span className="label">Days to finish</span>
          <input className="input w-24 py-2" type="number" min={1} max={30} value={days} onChange={(e) => setDays(Number(e.target.value))} /></label>
        <button type="submit" className="btn-primary ml-auto py-2 text-sm">Send task</button>
        <button type="button" className="btn-ghost px-2" onClick={onCancel} aria-label="Cancel"><X className="h-4 w-4" aria-hidden /></button>
      </div>
    </form>
  );
}

/** Take-home task and video screen for one applicant, inside the hiring screen. */
export function ScreeningPanel({ applicationId, jobTitle, closed, onChange }: {
  applicationId: number; jobTitle: string; closed: boolean; onChange: () => void;
}) {
  const [data, setData] = useState<Screening | null>(null);
  const [form, setForm] = useState<"task" | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => api.screeningFor(applicationId).then(setData).catch((e) => setError(e.message)), [applicationId]);
  useEffect(() => { void load(); }, [load]);

  async function act(fn: () => Promise<unknown>) {
    setError("");
    try {
      await fn();
      await load();
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That didn't work.");
    }
  }

  const task = data?.assessments.at(-1);
  const screen = data?.video_screens.at(-1);

  return (
    <div className="space-y-4 border-t border-line pt-4">
      <Label>Task and recorded answers</Label>
      {error && <Alert>{error}</Alert>}

      {task && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <ClipboardList className="h-4 w-4 text-brand" aria-hidden />
            <p className="font-semibold">{task.title}</p>
            <span className={clsx("badge", STATUS[task.status].tone)}>{STATUS[task.status].label}</span>
            <span className="text-xs text-muted">due {fmt(task.due_at)}</span>
          </div>
          {task.submission && (
            <pre className="max-h-56 overflow-auto rounded-xl border border-line bg-surface p-3 text-xs whitespace-pre-wrap">{task.submission}</pre>
          )}
          <Review item={task} onDecide={(passed) => act(() => api.decideTask(task.id, passed))} />
        </div>
      )}

      {screen && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Video className="h-4 w-4 text-brand" aria-hidden />
            <p className="font-semibold">Recorded answers</p>
            <span className={clsx("badge", STATUS[screen.status].tone)}>{STATUS[screen.status].label}</span>
            <span className="text-xs text-muted">{screen.answers.length}/{screen.questions.length} answered · due {fmt(screen.due_at)}</span>
          </div>
          <ul className="space-y-2">{screen.questions.map((_, i) => <Recording key={i} screen={screen} index={i} />)}</ul>
          <Review item={screen} onDecide={(passed) => act(() => api.decideVideo(screen.id, passed))} />
        </div>
      )}

      {!closed && form === "task" && (
        <TaskForm applicationId={applicationId} jobTitle={jobTitle} onCancel={() => setForm(null)}
          onSent={() => { setForm(null); void load(); onChange(); }} />
      )}
      {!closed && form === null && (
        <div className="flex flex-wrap gap-2">
          {(!task || task.status === "failed" || task.status === "passed") && (
            <button type="button" className="btn-secondary py-2 text-sm" onClick={() => setForm("task")}>
              <ClipboardList className="h-4 w-4" aria-hidden /> Send a task
            </button>
          )}
          {(!screen || screen.status === "failed" || screen.status === "passed") && (
            <button type="button" className="btn-secondary py-2 text-sm"
              onClick={() => act(() => api.sendVideoScreen(applicationId, { questions: [], due_days: 5 }))}>
              <Video className="h-4 w-4" aria-hidden /> Ask for recorded answers
            </button>
          )}
        </div>
      )}
      {!task && !screen && <p className="text-xs text-muted">Recorded answers: the applicant records short replies to three questions in their own time, in English or Nepali. Not a live call; book an interview for that.</p>}
    </div>
  );
}

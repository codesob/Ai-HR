"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CalendarDays, X } from "lucide-react";
import { Alert, Label } from "@/components/ui";
import { api, type Interview } from "@/lib/api";
import { useSession } from "@/lib/useSession";

const when = (iso: string) => new Date(iso).toLocaleString(undefined, {
  weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
});

function tomorrowAt10() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(10, 0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Live interviews for one applicant, inside the hiring screen: book one, open the room, read the notes. */
export function InterviewPanel({ applicationId, closed, onChange }: {
  applicationId: number; closed: boolean; onChange: () => void;
}) {
  const { session } = useSession();
  const [list, setList] = useState<Interview[]>([]);
  const [form, setForm] = useState(false);
  const [at, setAt] = useState(tomorrowAt10);
  const [minutes, setMinutes] = useState(45);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(() => api.interviews(applicationId).then(setList).catch((e) => setError(e.message)), [applicationId]);
  useEffect(() => { void load(); }, [load]);

  return (
    <div className="space-y-3 border-t border-line pt-4">
      <Label>Interview</Label>
      {error && <Alert>{error}</Alert>}
      {list.length > 0 && (
        <ul className="space-y-2">
          {list.map((i) => (
            <li key={i.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-line p-3">
              <CalendarDays className="h-4 w-4 text-brand" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{when(i.scheduled_at)}</p>
                <p className="truncate text-xs text-muted">{i.duration_minutes} min · {i.interviewer_email}</p>
              </div>
              <Link href={`/interview/${i.id}`} className={i.status === "scheduled" ? "btn-primary py-1.5 text-sm" : "btn-secondary py-1.5 text-sm"}>
                {i.status === "scheduled" ? "Open room" : "Notes and scorecard"}
              </Link>
            </li>
          ))}
        </ul>
      )}
      {!closed && (form ? (
        <form className="space-y-3 rounded-xl bg-surface-2 p-3" onSubmit={async (e) => {
          e.preventDefault();
          setError("");
          try {
            await api.scheduleInterview({
              application_id: applicationId, scheduled_at: new Date(at).toISOString(), duration_minutes: minutes,
              interviewer_email: email || session?.user.email,
            });
            setForm(false);
            await load();
            onChange();
          } catch (err) {
            setError(err instanceof Error ? err.message : "Couldn't book it.");
          }
        }}>
          <div className="grid gap-2 sm:grid-cols-[1fr_6rem]">
            <label className="block"><span className="label">When</span>
              <input className="input py-2" type="datetime-local" required value={at} onChange={(e) => setAt(e.target.value)} /></label>
            <label className="block"><span className="label">Minutes</span>
              <input className="input py-2" type="number" min={15} max={180} step={15} value={minutes}
                onChange={(e) => setMinutes(Number(e.target.value))} /></label>
          </div>
          <label className="block"><span className="label">Interviewer</span>
            <input className="input py-2" type="email" value={email} placeholder={session?.user.email ?? "you@company.com"}
              onChange={(e) => setEmail(e.target.value)} /></label>
          <div className="flex items-center gap-2">
            <button type="submit" className="btn-primary py-2 text-sm">Book and email both</button>
            <button type="button" className="btn-ghost ml-auto px-2" onClick={() => setForm(false)} aria-label="Cancel"><X className="h-4 w-4" aria-hidden /></button>
          </div>
          <p className="hint">The call happens in the browser. The applicant decides whether it may be recorded for a transcript.</p>
        </form>
      ) : (
        <button type="button" className="btn-secondary py-2 text-sm" onClick={() => setForm(true)}>
          <CalendarDays className="h-4 w-4" aria-hidden /> {list.length ? "Book another interview" : "Book an interview"}
        </button>
      ))}
    </div>
  );
}

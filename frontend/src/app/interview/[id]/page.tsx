"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Check } from "lucide-react";
import { AuthGate } from "@/components/AuthGate";
import { InterviewNotes } from "@/components/InterviewNotes";
import { InterviewRoom } from "@/components/InterviewRoom";
import { Alert } from "@/components/ui";
import { api, type InterviewDetail, type MyInterview, type Room } from "@/lib/api";
import type { SessionUser } from "@/lib/auth";

const when = (iso: string) => new Date(iso).toLocaleString(undefined, {
  weekday: "long", month: "long", day: "numeric", hour: "numeric", minute: "2-digit",
});

/** Camera preview and, for the applicant, the recording choice, before entering the call. */
function Lobby({ candidate, onJoin }: { candidate: boolean; onJoin: (stream: MediaStream, consent: boolean) => Promise<void> }) {
  const preview = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [consent, setConsent] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    let s: MediaStream | null = null;
    navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 }, audio: { echoCancellation: true, noiseSuppression: true } })
      .then((m) => { s = m; setStream(m); if (preview.current) preview.current.srcObject = m; })
      .catch(() => setError("We couldn't use your camera or microphone. Allow access in your browser, then reload."));
    return () => { /* the stream is handed to the call; stopped when the page closes */ void s; };
  }, []);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
      <div className="overflow-hidden rounded-2xl bg-ink">
        <video ref={preview} autoPlay muted playsInline className="aspect-video w-full object-cover" />
      </div>
      <div className="space-y-4">
        {error && <Alert>{error}</Alert>}
        {candidate && (
          <fieldset className="card space-y-3 p-4">
            <legend className="sr-only">Recording</legend>
            <p className="font-semibold">May we record this call?</p>
            <p className="text-sm text-ink-soft">
              The recording is turned into a written transcript so the interviewer can focus on you instead of taking notes.
              Only the hiring team sees it. It&apos;s your choice, and saying no doesn&apos;t affect the decision.
              You can change your mind during the call.
            </p>
            {[[true, "Yes, you can record"], [false, "No, don't record"]].map(([value, label]) => (
              <label key={String(value)} className="flex cursor-pointer items-center gap-2 text-sm">
                <input type="radio" name="consent" checked={consent === value} onChange={() => setConsent(value as boolean)} />
                {label as string}
              </label>
            ))}
          </fieldset>
        )}
        <button type="button" className="btn-primary w-full" disabled={!stream || joining || (candidate && consent === null)}
          onClick={async () => {
            setJoining(true);
            try {
              await onJoin(stream!, consent ?? false);
            } catch (e) {
              setError(e instanceof Error ? e.message : "Couldn't join.");
              setJoining(false);
            }
          }}>
          {joining ? "Joining…" : "Join interview"}
        </button>
        <p className="hint">Works best in Chrome, Edge or Firefox, with headphones.</p>
      </div>
    </div>
  );
}

function PrepQuestions({ iv, onChange }: { iv: InterviewDetail; onChange: (iv: InterviewDetail) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const draftKey = `interview-notes-${iv.id}`;
  const [notes, setNotes] = useState(() => { try { return localStorage.getItem(draftKey) ?? ""; } catch { return ""; } });
  return (
    <aside className="space-y-4">
      <div className="card space-y-3 p-4">
        <p className="font-semibold">Questions to ask</p>
        {error && <Alert>{error}</Alert>}
        {iv.prep_questions.length ? (
          <ol className="list-decimal space-y-2.5 pl-5 text-sm">
            {iv.prep_questions.map((q, i) => (
              <li key={i}><p className="font-semibold">{q.question}</p><p className="text-muted">{q.why}</p></li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-muted">Suggested from their resume, the job, and their task and recorded answers.</p>
        )}
        <button type="button" className="btn-secondary w-full py-2 text-sm" disabled={busy} onClick={async () => {
          setBusy(true);
          setError("");
          try { onChange(await api.prepareQuestions(iv.id)); } catch (e) { setError(e instanceof Error ? e.message : "Try again."); }
          setBusy(false);
        }}>
          {busy ? "Preparing…" : iv.prep_questions.length ? "Suggest different questions" : "Suggest questions"}
        </button>
      </div>
      <label className="card block space-y-2 p-4">
        <span className="font-semibold">Your notes</span>
        <textarea className="input text-sm" rows={6} value={notes} placeholder="Private. They carry over to your scorecard."
          onChange={(e) => { setNotes(e.target.value); try { localStorage.setItem(draftKey, e.target.value); } catch { /* fine */ } }} />
      </label>
    </aside>
  );
}

function Interviewer({ id }: { id: number }) {
  const [iv, setIv] = useState<InterviewDetail | null>(null);
  const [call, setCall] = useState<{ room: Room; stream: MediaStream } | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => api.interview(id).then(setIv).catch((e) => setError(e.message)), [id]);
  useEffect(() => { void load(); }, [load]);

  if (error) return <Alert>{error}</Alert>;
  if (!iv) return <p className="text-muted">Loading…</p>;

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm text-muted"><Link href="/recruiter" className="hover:underline">Hiring</Link> › {iv.job_title}</p>
        <h1 className="text-3xl">Interview with {iv.candidate_name}</h1>
        <p className="text-muted">{when(iv.scheduled_at)} · {iv.duration_minutes} min</p>
      </header>
      {iv.status === "scheduled" ? (
        <div className="grid gap-6 xl:grid-cols-[1fr_22rem]">
          {call
            ? <InterviewRoom room={call.room} local={call.stream} onEnded={() => {
                call.stream.getTracks().forEach((t) => t.stop());
                setCall(null);
                void load();
              }} />
            : <Lobby candidate={false} onJoin={async (stream) => setCall({ room: await api.joinRoom(id), stream })} />}
          <PrepQuestions iv={iv} onChange={setIv} />
        </div>
      ) : (
        <InterviewNotes initial={iv} />
      )}
    </div>
  );
}

function Applicant({ id }: { id: number }) {
  const [info, setInfo] = useState<MyInterview | null | undefined>(undefined);
  const [call, setCall] = useState<{ room: Room; stream: MediaStream } | null>(null);
  const [ended, setEnded] = useState(false);
  useEffect(() => {
    api.myInterviews().then((all) => setInfo(all.find((i) => i.id === id) ?? null)).catch(() => setInfo(null));
  }, [id]);

  if (info === undefined) return <p className="text-muted">Loading…</p>;
  if (info === null) return <Alert>We couldn&apos;t find this interview in your account.</Alert>;

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm text-muted">Your interview</p>
        <h1 className="text-3xl">{info.job_title}</h1>
        <p className="text-muted">{when(info.scheduled_at)} · {info.duration_minutes} min</p>
      </header>
      {ended || info.status !== "scheduled" ? (
        <div className="card max-w-xl space-y-2">
          <p className="flex items-center gap-2 font-display text-xl"><Check className="h-5 w-5 text-brand" aria-hidden />Thanks for your time</p>
          <p className="text-ink-soft">The interview is over. The team will email you about the next step.</p>
          <Link href="/candidate" className="btn-secondary mt-2">Back to my applications</Link>
        </div>
      ) : call ? (
        <InterviewRoom room={call.room} local={call.stream} onEnded={() => {
          call.stream.getTracks().forEach((t) => t.stop());
          setCall(null);
          setEnded(true);
        }} />
      ) : (
        <Lobby candidate onJoin={async (stream, consent) => {
          await api.setRecordingConsent(id, consent);
          const room = await api.joinRoom(id);
          setCall({ room, stream });
        }} />
      )}
    </div>
  );
}

function Page({ user }: { user: SessionUser }) {
  const id = Number(useParams<{ id: string }>().id);
  return user.role === "candidate" ? <Applicant id={id} /> : <Interviewer id={id} />;
}

export default function InterviewPage() {
  return (
    <AuthGate title="Interview" roles={["admin", "recruiter", "candidate"]}>
      {(user) => <Page user={user} />}
    </AuthGate>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Circle, Square, Video } from "lucide-react";
import { Alert } from "@/components/ui";
import { api, type MyScreening } from "@/lib/api";

const MAX_SECONDS = 120;
const due = (iso: string) => new Date(iso).toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

function pickType() {
  const types = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm", "video/mp4"];
  return types.find((t) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) ?? "";
}

/** Record one answer in the browser: camera preview, record (max 2 min), watch it back, send or redo. */
function Recorder({ onSend }: { onSend: (blob: Blob) => Promise<void> }) {
  const live = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const [state, setState] = useState<"idle" | "ready" | "recording" | "review" | "sending">("idle");
  const [take, setTake] = useState<{ blob: Blob; url: string } | null>(null);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState("");

  const stopCamera = useCallback(() => {
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
  }, []);
  useEffect(() => () => stopCamera(), [stopCamera]);
  useEffect(() => {
    if (state !== "recording") return;
    const id = setInterval(() => setSeconds((s) => {
      if (s + 1 >= MAX_SECONDS) recorder.current?.stop();
      return s + 1;
    }), 1000);
    return () => clearInterval(id);
  }, [state]);

  async function openCamera() {
    setError("");
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 360 }, audio: true });
      if (live.current) live.current.srcObject = stream.current;
      setState("ready");
    } catch {
      setError("We couldn't use your camera or microphone. Allow access in your browser and try again.");
    }
  }

  function record() {
    if (!stream.current) return;
    const chunks: BlobPart[] = [];
    const type = pickType();
    const rec = new MediaRecorder(stream.current, { ...(type ? { mimeType: type } : {}), videoBitsPerSecond: 600_000 });
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = () => {
      const blob = new Blob(chunks, { type: (type || "video/webm").split(";")[0] });
      setTake({ blob, url: URL.createObjectURL(blob) });
      setState("review");
    };
    recorder.current = rec;
    setSeconds(0);
    rec.start(1000);
    setState("recording");
  }

  async function send() {
    if (!take) return;
    setState("sending");
    try {
      await onSend(take.blob);
      URL.revokeObjectURL(take.url);
      stopCamera();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't send it. Try again.");
      setState("review");
    }
  }

  return (
    <div className="space-y-3">
      {error && <Alert>{error}</Alert>}
      <div className="overflow-hidden rounded-xl bg-ink">
        {state === "review" || state === "sending"
          ? <video src={take?.url} controls className="aspect-video w-full" />
          : <video ref={live} autoPlay muted playsInline className="aspect-video w-full" />}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {state === "idle" && <button type="button" className="btn-primary py-2 text-sm" onClick={openCamera}><Video className="h-4 w-4" aria-hidden /> Turn on camera</button>}
        {state === "ready" && <button type="button" className="btn-primary py-2 text-sm" onClick={record}><Circle className="h-4 w-4 fill-current" aria-hidden /> Start recording</button>}
        {state === "recording" && (
          <>
            <button type="button" className="btn-dark py-2 text-sm" onClick={() => recorder.current?.stop()}><Square className="h-4 w-4 fill-current" aria-hidden /> Stop</button>
            <span className="font-display text-lg tabular-nums text-danger">{Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")}</span>
            <span className="text-xs text-muted">up to 2 minutes</span>
          </>
        )}
        {(state === "review" || state === "sending") && (
          <>
            <button type="button" className="btn-primary py-2 text-sm" onClick={send} disabled={state === "sending"}>
              {state === "sending" ? "Sending…" : "Use this answer"}
            </button>
            <button type="button" className="btn-secondary py-2 text-sm" disabled={state === "sending"}
              onClick={() => { setTake(null); setState("ready"); if (live.current && stream.current) live.current.srcObject = stream.current; }}>
              Record again
            </button>
          </>
        )}
      </div>
    </div>
  );
}

/** Tasks and video questions the hiring team sent this applicant. */
export function ApplicantScreening() {
  const [data, setData] = useState<MyScreening | null>(null);
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [recording, setRecording] = useState<{ screen: number; index: number } | null>(null);
  // Telling the transcriber the language matters a lot for Nepali.
  const [language, setLanguage] = useState<"en" | "ne">("en");
  const [error, setError] = useState("");
  const load = useCallback(() => api.myScreening().then(setData).catch((e) => setError(e.message)), []);
  useEffect(() => { void load(); }, [load]);

  if (!data || (data.assessments.length === 0 && data.video_screens.length === 0)) return null;

  return (
    <section className="space-y-4">
      <h2 className="text-2xl">Things to do</h2>
      {error && <Alert>{error}</Alert>}

      {data.assessments.map((t) => (
        <div key={t.id} className="card space-y-3">
          <div>
            <p className="text-xs text-muted">{t.job_title} · task</p>
            <h3 className="font-display text-xl">{t.title}</h3>
            {t.status === "sent" && <p className="text-sm text-warning">Due {due(t.due_at)}</p>}
          </div>
          <p className="whitespace-pre-wrap text-ink-soft">{t.instructions}</p>
          {t.status === "sent" ? (
            <form className="space-y-2" onSubmit={async (e) => {
              e.preventDefault();
              try {
                await api.submitTask(t.id, drafts[t.id] ?? "");
                await load();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Couldn't submit.");
              }
            }}>
              <label className="block">
                <span className="label">Your answer</span>
                <textarea className="input" rows={8} required value={drafts[t.id] ?? ""}
                  placeholder="Write your answer, paste code, or add links (GitHub, Google Drive, Figma)."
                  onChange={(e) => setDrafts({ ...drafts, [t.id]: e.target.value })} />
              </label>
              <button type="submit" className="btn-primary">Submit</button>
              <p className="hint">You can submit once.</p>
            </form>
          ) : (
            <p className="flex items-center gap-2 text-sm font-semibold text-brand"><Check className="h-4 w-4" aria-hidden />
              {t.status === "submitted" ? "Submitted. The team is reviewing it." : "Reviewed. We've emailed you."}</p>
          )}
        </div>
      ))}

      {data.video_screens.map((s) => {
        const left = s.questions.map((_, i) => i).filter((i) => !s.answered.includes(i));
        return (
          <div key={s.id} className="card space-y-4">
            <div>
              <p className="text-xs text-muted">{s.job_title} · video questions</p>
              <h3 className="font-display text-xl">Record short answers</h3>
              {s.status === "invited" && (
                <p className="text-sm text-muted">About a minute each. Due {due(s.due_at)}. You can redo any answer before you finish.</p>
              )}
            </div>
            {s.status === "invited" && (
              <fieldset className="flex flex-wrap items-center gap-2">
                <legend className="sr-only">Language</legend>
                <span className="text-sm font-semibold">I&apos;ll answer in</span>
                {([["en", "English"], ["ne", "नेपाली (Nepali)"]] as const).map(([value, label]) => (
                  <label key={value} className={language === value
                    ? "cursor-pointer rounded-full bg-brand px-3 py-1 text-sm font-semibold text-white"
                    : "cursor-pointer rounded-full border border-line-strong px-3 py-1 text-sm"}>
                    <input type="radio" name={`lang-${s.id}`} value={value} className="sr-only"
                      checked={language === value} onChange={() => setLanguage(value)} />
                    {label}
                  </label>
                ))}
              </fieldset>
            )}
            <ol className="space-y-3">
              {s.questions.map((q, i) => {
                const done = s.answered.includes(i);
                const open = recording?.screen === s.id && recording.index === i;
                return (
                  <li key={i} className="space-y-3 rounded-xl border border-line p-4">
                    <div className="flex items-start gap-3">
                      <span className={done ? "flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand text-white" : "flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-2 text-xs font-semibold"}>
                        {done ? <Check className="h-3.5 w-3.5" aria-hidden /> : i + 1}
                      </span>
                      <p className="flex-1 font-semibold">{q}</p>
                      {s.status === "invited" && !open && (
                        <button type="button" className="btn-secondary px-3 py-1.5 text-sm" onClick={() => setRecording({ screen: s.id, index: i })}>
                          {done ? "Redo" : "Answer"}
                        </button>
                      )}
                    </div>
                    {open && (
                      <Recorder onSend={async (blob) => {
                        await api.uploadAnswer(s.id, i, blob, language);
                        setRecording(null);
                        await load();
                      }} />
                    )}
                  </li>
                );
              })}
            </ol>
            {s.status === "invited" ? (
              <button type="button" className="btn-primary" disabled={left.length > 0} onClick={async () => {
                try {
                  await api.finishVideoScreen(s.id);
                  await load();
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Couldn't send your answers.");
                }
              }}>
                {left.length ? `${left.length} question${left.length === 1 ? "" : "s"} left` : "Send my answers"}
              </button>
            ) : (
              <p className="flex items-center gap-2 text-sm font-semibold text-brand"><Check className="h-4 w-4" aria-hidden />
                {s.status === "completed" ? "Sent. The team is watching your answers." : "Reviewed. We've emailed you."}</p>
            )}
          </div>
        );
      })}
    </section>
  );
}

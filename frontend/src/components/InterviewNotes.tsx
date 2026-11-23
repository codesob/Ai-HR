"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { Check, ChevronDown } from "lucide-react";
import { Alert, Label } from "@/components/ui";
import { api, type InterviewDetail } from "@/lib/api";

const clock = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

const LEVEL = {
  strong: { label: "Clear evidence", tone: "bg-brand text-white" },
  some: { label: "Some evidence", tone: "bg-accent-soft text-warning" },
  none: { label: "Not shown", tone: "bg-surface-2 text-muted" },
} as const;

const SUGGESTS = { advance: "move forward", unsure: "unsure", decline: "not move forward" } as const;

function List({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="space-y-1.5">
      <Label>{title}</Label>
      <ul className="list-disc space-y-1 pl-5 text-ink-soft">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  );
}

function Scorecard({ iv, onSaved }: { iv: InterviewDetail; onSaved: (iv: InterviewDetail) => void }) {
  const draftKey = `interview-notes-${iv.id}`;
  const [rating, setRating] = useState(iv.scorecard?.rating ?? 0);
  const [rec, setRec] = useState(iv.scorecard?.recommendation ?? "");
  const [notes, setNotes] = useState(() => {
    if (iv.scorecard) return iv.scorecard.notes;
    try { return localStorage.getItem(draftKey) ?? ""; } catch { return ""; }
  });
  const [saved, setSaved] = useState(Boolean(iv.scorecard));
  const [error, setError] = useState("");

  return (
    <form className="card space-y-4" onSubmit={async (e) => {
      e.preventDefault();
      setError("");
      try {
        onSaved(await api.saveScorecard(iv.id, { rating, recommendation: rec, notes }));
        setSaved(true);
        try { localStorage.removeItem(draftKey); } catch { /* not needed */ }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Couldn't save.");
      }
    }}>
      <h3 className="text-lg font-semibold">Your scorecard</h3>
      {error && <Alert>{error}</Alert>}
      <fieldset className="space-y-1.5">
        <legend className="label">Overall</legend>
        <div className="flex gap-1.5">
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} type="button" aria-pressed={rating === n} onClick={() => { setRating(n); setSaved(false); }}
              className={clsx("h-10 w-10 rounded-lg border font-display text-lg",
                rating === n ? "border-brand bg-brand text-white" : "border-line-strong hover:bg-surface-2")}>{n}</button>
          ))}
        </div>
        <p className="hint">1 = clearly not a fit · 3 = mixed · 5 = excellent</p>
      </fieldset>
      <fieldset className="space-y-1.5">
        <legend className="label">Your recommendation</legend>
        <div className="flex flex-wrap gap-2">
          {(["advance", "unsure", "decline"] as const).map((v) => (
            <label key={v} className={clsx("cursor-pointer rounded-full px-3 py-1.5 text-sm",
              rec === v ? "bg-brand font-semibold text-white" : "border border-line-strong")}>
              <input type="radio" name="rec" className="sr-only" checked={rec === v} onChange={() => { setRec(v); setSaved(false); }} />
              {v === "advance" ? "Move forward" : v === "unsure" ? "Not sure" : "Don't move forward"}
            </label>
          ))}
        </div>
      </fieldset>
      <label className="block"><span className="label">Notes</span>
        <textarea className="input" rows={5} value={notes} placeholder="What stood out, with examples."
          onChange={(e) => { setNotes(e.target.value); setSaved(false); }} /></label>
      <div className="flex items-center gap-3">
        <button type="submit" className="btn-primary" disabled={!rating || !rec}>Save scorecard</button>
        {saved && iv.scorecard && <span className="flex items-center gap-1 text-sm text-brand"><Check className="h-4 w-4" aria-hidden />Saved by {iv.scorecard.by}</span>}
      </div>
    </form>
  );
}

/** After the call: AI notes from the transcript, the interviewer's scorecard, the decision, and the transcript. */
export function InterviewNotes({ initial }: { initial: InterviewDetail }) {
  const [iv, setIv] = useState(initial);
  // Shows the English version by default when there is one, until the reader picks.
  const [picked, setPicked] = useState<boolean | null>(null);
  const [showTranscript, setShowTranscript] = useState(false);
  const [decided, setDecided] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (iv.summary_status !== "processing") return;
    const t = setInterval(() => api.interview(iv.id).then(setIv).catch(() => undefined), 5000);
    return () => clearInterval(t);
  }, [iv.id, iv.summary_status]);
  const english = picked ?? Boolean(iv.transcript_english);

  const s = iv.summary;
  const englishLines = iv.transcript_english?.split("\n") ?? [];

  async function decide(status: "offer" | "rejected") {
    setError("");
    try {
      await api.setApplicationStatus(iv.application_id, status);
      setDecided(status === "offer" ? "Moved to offer. They've been emailed." : "Rejected. They've been emailed.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "That didn't work.");
    }
  }

  return (
    <div className="space-y-6">
      {iv.summary_status === "processing" && (
        <Alert tone="warning">Transcribing the call and writing notes. This usually takes a minute or two; the page updates by itself.</Alert>
      )}
      {iv.summary_status === "failed" && (
        <Alert>The notes couldn&apos;t be made from this recording. Fill in the scorecard from your own notes.</Alert>
      )}
      {iv.summary_status === "" && iv.status === "completed" && (
        <p className="text-muted">This interview wasn&apos;t recorded, so there&apos;s no transcript. Fill in the scorecard from your own notes.</p>
      )}

      {s && (
        <section className="card space-y-5">
          <div className="flex flex-wrap items-baseline gap-2">
            <h3 className="text-lg font-semibold">AI notes from the call</h3>
            <span className="text-sm text-muted">suggests: {SUGGESTS[s.recommendation]}</span>
          </div>
          <p className="text-ink-soft">{s.overview}</p>
          {s.skills.length > 0 && (
            <div className="space-y-2">
              <Label>What they showed for each skill</Label>
              <ul className="divide-y divide-line">
                {s.skills.map((k) => (
                  <li key={k.skill} className="grid gap-1 py-2.5 sm:grid-cols-[10rem_1fr] sm:gap-4">
                    <div>
                      <p className="font-semibold">{k.skill}</p>
                      <span className={clsx("badge mt-1", LEVEL[k.level].tone)}>{LEVEL[k.level].label}</span>
                    </div>
                    <p className="text-sm text-ink-soft">{k.evidence}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="grid gap-5 sm:grid-cols-2">
            <List title="Strengths" items={s.strengths} />
            <List title="Concerns" items={s.concerns} />
          </div>
          <List title="Follow up on" items={s.follow_ups} />
          <p className="text-xs text-muted">Based only on what was said, never on voice, face or accent. Check the transcript before relying on it.</p>
        </section>
      )}

      <Scorecard iv={iv} onSaved={setIv} />

      <section className="card space-y-3">
        <h3 className="text-lg font-semibold">Your decision</h3>
        <p className="text-sm text-muted">The applicant is emailed either way.</p>
        {error && <Alert>{error}</Alert>}
        {decided ? (
          <p className="flex items-center gap-2 font-semibold text-brand"><Check className="h-4 w-4" aria-hidden />{decided}</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => decide("rejected")}>Reject</button>
            <button type="button" className="btn-primary" onClick={() => decide("offer")}>Make an offer</button>
          </div>
        )}
      </section>

      {iv.transcript.length > 0 && (
        <section className="card space-y-3">
          <button type="button" className="flex w-full items-center justify-between text-left" aria-expanded={showTranscript}
            onClick={() => setShowTranscript((v) => !v)}>
            <span className="text-lg font-semibold">Transcript</span>
            <ChevronDown className={clsx("h-4 w-4 transition", showTranscript && "rotate-180")} aria-hidden />
          </button>
          {showTranscript && (
            <>
              {iv.transcript_english && (
                <div className="flex gap-2 text-sm">
                  <button type="button" className={english ? "font-semibold text-brand" : "text-muted"} onClick={() => setPicked(true)}>In English</button>
                  <span className="text-muted">·</span>
                  <button type="button" className={!english ? "font-semibold text-brand" : "text-muted"} onClick={() => setPicked(false)}>As spoken</button>
                </div>
              )}
              <ol className="max-h-[28rem] space-y-2 overflow-auto text-sm">
                {english
                  ? englishLines.map((line, i) => <li key={i} className="text-ink-soft">{line}</li>)
                  : iv.transcript.map((line, i) => (
                    <li key={i} className="grid grid-cols-[3rem_6rem_1fr] gap-2">
                      <span className="tabular-nums text-muted">{clock(line.at)}</span>
                      <span className={line.speaker === "candidate" ? "font-semibold text-brand" : "font-semibold"}>
                        {line.speaker === "candidate" ? "Applicant" : "Interviewer"}
                      </span>
                      <span className="text-ink-soft">{line.text}</span>
                    </li>
                  ))}
              </ol>
              <p className="hint">Made by speech recognition, so some words may be wrong.</p>
            </>
          )}
        </section>
      )}
    </div>
  );
}

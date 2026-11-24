"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { Circle, Mic, MicOff, PhoneOff, Video, VideoOff } from "lucide-react";
import { Alert } from "@/components/ui";
import { api, type Room, type Signal } from "@/lib/api";

// Recording is cut into parts so a dropped connection loses minutes, not the whole call.
const PART_SECONDS = 300;

function audioType() {
  const types = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"];
  return types.find((t) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) ?? "";
}

const clock = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

type Track = "interviewer" | "candidate";

/**
 * A two-person video call in the browser (peer-to-peer WebRTC; the server only relays setup messages).
 * The interviewer's browser records each side's audio separately, only while the applicant allows it,
 * so the transcript knows who said what.
 */
export function InterviewRoom({ room, local, onEnded }: {
  room: Room; local: MediaStream; onEnded: () => void;
}) {
  const id = room.id;
  const interviewer = room.role === "interviewer";
  const localVideo = useRef<HTMLVideoElement>(null);
  const remoteVideo = useRef<HTMLVideoElement>(null);
  const pc = useRef<RTCPeerConnection | null>(null);
  const pendingIce = useRef<(RTCIceCandidateInit & { gen?: number })[]>([]);
  // Each connection attempt has a number; messages from an older attempt (a rejoin, a repeated hello) are ignored.
  const gen = useRef(0);
  const remoteStream = useRef<MediaStream | null>(null);
  const [connected, setConnected] = useState(false);
  const [micOn, setMicOn] = useState(true);
  const [camOn, setCamOn] = useState(true);
  const [consent, setConsent] = useState<boolean | null>(room.recording_consent);
  const [recordingOn, setRecordingOn] = useState(room.recording_on);
  const [language, setLanguage] = useState<"en" | "ne" | "">("en");
  const [elapsed, setElapsed] = useState(0);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [ending, setEnding] = useState(false);

  // Recording (interviewer only).
  const recorders = useRef<MediaRecorder[]>([]);
  const uploads = useRef<Promise<unknown>[]>([]);
  const part = useRef(0);
  const recordStart = useRef(0);
  const rotateTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const discard = useRef(false);

  useEffect(() => {
    if (localVideo.current) localVideo.current.srcObject = local;
  }, [local]);

  useEffect(() => {
    if (!recordingOn) return;
    const t = setInterval(() => setElapsed((Date.now() - recordStart.current) / 1000), 1000);
    return () => clearInterval(t);
  }, [recordingOn]);

  const newPeer = useCallback((attempt: number) => {
    pc.current?.close();
    gen.current = attempt;
    pendingIce.current = pendingIce.current.filter((c) => c.gen === attempt);
    const peer = new RTCPeerConnection({ iceServers: room.ice_servers });
    local.getTracks().forEach((t) => peer.addTrack(t, local));
    peer.onicecandidate = (e) => { if (e.candidate) void api.sendSignal(id, "ice", { ...e.candidate.toJSON(), gen: attempt }).catch(() => undefined); };
    peer.ontrack = (e) => {
      remoteStream.current = e.streams[0];
      if (remoteVideo.current) remoteVideo.current.srcObject = e.streams[0];
    };
    peer.onconnectionstatechange = () => {
      const s = peer.connectionState;
      setConnected(s === "connected");
      if (s === "failed") setNotice("The call couldn't connect. If it keeps failing, use the backup room link below.");
    };
    pc.current = peer;
    return peer;
  }, [id, local, room.ice_servers]);

  const flushIce = useCallback(async () => {
    const peer = pc.current;
    if (!peer?.remoteDescription) return;
    const ready = pendingIce.current.filter((c) => c.gen === gen.current);
    pendingIce.current = pendingIce.current.filter((c) => (c.gen ?? 0) > gen.current);
    for (const c of ready) {
      const { candidate, sdpMid, sdpMLineIndex, usernameFragment } = c;
      await peer.addIceCandidate({ candidate, sdpMid, sdpMLineIndex, usernameFragment }).catch(() => undefined);
    }
  }, []);

  // ---------- recording ----------

  const startPart = useCallback(() => {
    const type = audioType();
    const offset = (Date.now() - recordStart.current) / 1000;
    const index = part.current++;
    const sources: [Track, MediaStream | null][] = [
      ["interviewer", local],
      ["candidate", remoteStream.current],
    ];
    recorders.current = sources.flatMap(([track, stream]) => {
      const audio = stream?.getAudioTracks() ?? [];
      if (!audio.length) return [];
      const rec = new MediaRecorder(new MediaStream(audio), { ...(type ? { mimeType: type } : {}), audioBitsPerSecond: 32_000 });
      const chunks: BlobPart[] = [];
      rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      rec.onstop = () => {
        if (discard.current || !chunks.length) return;
        const blob = new Blob(chunks, { type: (type || "audio/webm").split(";")[0] });
        uploads.current.push(api.uploadInterviewAudio(id, index, track, offset, language, blob)
          .catch((e) => setError(`Part of the recording didn't upload: ${e instanceof Error ? e.message : e}`)));
      };
      rec.start();
      return [rec];
    });
  }, [id, language, local]);

  const stopRecorders = useCallback(() => {
    if (rotateTimer.current) clearInterval(rotateTimer.current);
    rotateTimer.current = null;
    recorders.current.forEach((r) => r.state !== "inactive" && r.stop());
    recorders.current = [];
  }, []);

  async function startRecording() {
    setError("");
    try {
      await api.setRecording(id, true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't start recording.");
      return;
    }
    discard.current = false;
    if (!recordStart.current) recordStart.current = Date.now();
    startPart();
    rotateTimer.current = setInterval(() => { recorders.current.forEach((r) => r.stop()); startPart(); }, PART_SECONDS * 1000);
    setRecordingOn(true);
  }

  async function stopRecording() {
    stopRecorders();
    setRecordingOn(false);
    await api.setRecording(id, false).catch(() => undefined);
  }

  // ---------- signalling ----------

  const handle = useCallback(async (m: Signal) => {
    if (m.kind === "hello") {
      // The interviewer always makes the offer, so whoever arrives second, the call starts the same way.
      if (interviewer) {
        const attempt = Date.now(); // keeps increasing across page reloads
        const peer = newPeer(attempt);
        await peer.setLocalDescription(await peer.createOffer());
        await api.sendSignal(id, "offer", { ...peer.localDescription!.toJSON(), gen: attempt });
      } else {
        await api.sendSignal(id, "hello");
      }
    } else if (m.kind === "offer" && !interviewer) {
      const attempt = Number(m.data.gen) || 0;
      if (attempt < gen.current) return;
      const peer = newPeer(attempt);
      await peer.setRemoteDescription({ type: "offer", sdp: String(m.data.sdp) });
      await flushIce();
      await peer.setLocalDescription(await peer.createAnswer());
      await api.sendSignal(id, "answer", { ...peer.localDescription!.toJSON(), gen: attempt });
    } else if (m.kind === "answer" && interviewer && pc.current) {
      if (Number(m.data.gen) !== gen.current || pc.current.signalingState !== "have-local-offer") return;
      await pc.current.setRemoteDescription({ type: "answer", sdp: String(m.data.sdp) });
      await flushIce();
    } else if (m.kind === "ice") {
      const c = m.data as RTCIceCandidateInit & { gen?: number };
      if ((c.gen ?? 0) < gen.current) return;
      pendingIce.current.push(c);
      await flushIce();
    } else if (m.kind === "consent") {
      const allowed = Boolean(m.data.allowed);
      setConsent(allowed);
      if (!allowed && recorders.current.length) {
        // Withdrawn: drop the part in progress and stop.
        discard.current = true;
        stopRecorders();
        setRecordingOn(false);
        setNotice("The applicant stopped the recording. Carry on without it.");
      } else if (allowed) {
        setNotice("The applicant agreed to recording.");
      }
    } else if (m.kind === "recording") {
      setRecordingOn(Boolean(m.data.on));
    } else if (m.kind === "bye") {
      if (interviewer) {
        setConnected(false);
        setNotice("The applicant left the call. They can rejoin from the same link.");
      } else {
        onEnded();
      }
    }
  }, [flushIce, id, interviewer, newPeer, onEnded, stopRecorders]);

  // One long-poll loop for the whole visit; it always calls the latest handler and never re-reads old messages.
  const handleRef = useRef(handle);
  useEffect(() => { handleRef.current = handle; }, [handle]);
  useEffect(() => {
    const abort = new AbortController();
    let cursor = room.cursor;
    let stopped = false;
    void (async () => {
      while (!stopped) {
        try {
          const got = await api.waitSignals(id, cursor, abort.signal);
          cursor = got.cursor;
          for (const m of got.messages) await handleRef.current(m).catch(() => undefined);
        } catch {
          if (stopped) return;
          await new Promise((r) => setTimeout(r, 2000));
        }
      }
    })();
    return () => { stopped = true; abort.abort(); };
  }, [id, room.cursor]);

  useEffect(() => () => {
    stopRecorders();
    pc.current?.close();
  }, [stopRecorders]);

  // ---------- controls ----------

  function toggle(kind: "audio" | "video") {
    const tracks = kind === "audio" ? local.getAudioTracks() : local.getVideoTracks();
    const on = !(kind === "audio" ? micOn : camOn);
    tracks.forEach((t) => { t.enabled = on; });
    (kind === "audio" ? setMicOn : setCamOn)(on);
  }

  async function leave() {
    setEnding(true);
    if (interviewer) {
      stopRecorders();
      // Wait for the last part to finish uploading before the transcript is made.
      await new Promise((r) => setTimeout(r, 300));
      await Promise.allSettled(uploads.current);
      try {
        await api.endInterview(id);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Couldn't end the interview.");
        setEnding(false);
        return;
      }
    } else {
      await api.sendSignal(id, "bye").catch(() => undefined);
    }
    pc.current?.close();
    onEnded();
  }

  async function changeConsent(allowed: boolean) {
    await api.setRecordingConsent(id, allowed).catch((e) => setError(e.message));
    setConsent(allowed);
    if (!allowed) setRecordingOn(false);
  }

  return (
    <div className="space-y-3">
      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="warning">{notice}</Alert>}

      <div className="relative overflow-hidden rounded-2xl bg-ink">
        <video ref={remoteVideo} autoPlay playsInline className="aspect-video w-full object-cover" />
        {!connected && (
          <p className="absolute inset-0 flex items-center justify-center p-6 text-center text-white/80">
            {interviewer ? `Waiting for ${room.candidate_name} to join…` : "Waiting for the interviewer to join…"}
          </p>
        )}
        <video ref={localVideo} autoPlay muted playsInline
          className="absolute right-3 bottom-3 aspect-video w-32 rounded-lg border-2 border-white/70 object-cover sm:w-44" />
        {recordingOn && (
          <span className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-danger px-3 py-1 text-xs font-semibold text-white">
            <Circle className="h-2.5 w-2.5 fill-current" aria-hidden /> Recording{interviewer ? ` ${clock(elapsed)}` : ""}
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={clsx(micOn ? "btn-secondary" : "btn-dark", "py-2 text-sm")} onClick={() => toggle("audio")}
          aria-pressed={!micOn}>
          {micOn ? <Mic className="h-4 w-4" aria-hidden /> : <MicOff className="h-4 w-4" aria-hidden />} {micOn ? "Mute" : "Unmute"}
        </button>
        <button type="button" className={clsx(camOn ? "btn-secondary" : "btn-dark", "py-2 text-sm")} onClick={() => toggle("video")}
          aria-pressed={!camOn}>
          {camOn ? <Video className="h-4 w-4" aria-hidden /> : <VideoOff className="h-4 w-4" aria-hidden />} {camOn ? "Camera off" : "Camera on"}
        </button>
        <button type="button" className="btn-dark ml-auto bg-danger py-2 text-sm" onClick={leave} disabled={ending}>
          <PhoneOff className="h-4 w-4" aria-hidden /> {ending ? "Ending…" : interviewer ? "End interview" : "Leave"}
        </button>
      </div>

      {interviewer ? (
        <div className="card space-y-3 p-4">
          <p className="font-semibold">Recording and transcript</p>
          {consent ? (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <label className="text-sm">Call language
                  <select className="input ml-2 inline-block w-auto py-1.5 text-sm" value={language} disabled={recordingOn}
                    onChange={(e) => setLanguage(e.target.value as "en" | "ne" | "")}>
                    <option value="en">English</option>
                    <option value="ne">नेपाली (Nepali)</option>
                    <option value="">Mixed</option>
                  </select>
                </label>
                {recordingOn
                  ? <button type="button" className="btn-secondary ml-auto py-2 text-sm" onClick={stopRecording}>Stop recording</button>
                  : <button type="button" className="btn-primary ml-auto py-2 text-sm" onClick={startRecording} disabled={!connected}>
                      <Circle className="h-3.5 w-3.5 fill-current" aria-hidden /> Start recording
                    </button>}
              </div>
              <p className="hint">The applicant agreed and sees when you&apos;re recording. They can stop it at any time.
                Each side&apos;s voice is recorded separately so the transcript shows who said what.</p>
            </>
          ) : (
            <p className="text-sm text-muted">
              {consent === false
                ? "The applicant chose not to be recorded. Take your own notes; you can fill in the scorecard after the call."
                : "The applicant hasn't decided about recording yet. They're asked when they join."}
            </p>
          )}
        </div>
      ) : (
        <div className="card flex flex-wrap items-center gap-3 p-4 text-sm">
          <p className="flex-1 text-ink-soft">
            {consent
              ? "You allowed this call to be recorded and transcribed for the hiring team's notes."
              : "This call isn't being recorded."}
          </p>
          {consent
            ? <button type="button" className="btn-secondary py-2 text-sm" onClick={() => changeConsent(false)}>Stop recording me</button>
            : <button type="button" className="btn-secondary py-2 text-sm" onClick={() => changeConsent(true)}>Allow recording</button>}
        </div>
      )}

      {room.backup_link && (
        <p className="text-xs text-muted">Trouble connecting? Use the backup room:{" "}
          <a href={room.backup_link} target="_blank" rel="noreferrer" className="text-brand-ink underline">{room.backup_link}</a></p>
      )}
    </div>
  );
}

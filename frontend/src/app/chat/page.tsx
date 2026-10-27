"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { ArrowUp, FileText, Sparkles } from "lucide-react";
import { AuthGate } from "@/components/AuthGate";
import { api } from "@/lib/api";

type Message = { role: "user" | "assistant"; content: string; sources?: string[]; failed?: boolean };

const SUGGESTIONS = [
  "How many annual leave days do I get?",
  "What is the remote work policy?",
  "When is payroll processed?",
  "What is the interview process?",
];

function sourceName(s: string) {
  return s.split(/[\\/]/).pop()?.replace(/\.(md|txt|pdf)$/i, "").replace(/[-_]/g, " ") ?? s;
}

function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  async function send(text: string) {
    if (!text.trim() || loading) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.chat(text, sessionId);
      setSessionId(res.session_id);
      setMessages((m) => [...m, { role: "assistant", content: res.reply, sources: res.sources }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", failed: true, content: err instanceof Error ? err.message : "The HR assistant is unavailable." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-8rem)] max-w-3xl flex-col">
      <header className="space-y-1 pb-6">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">HR assistant</h1>
        <p className="text-muted">Answers from your company&apos;s HR policies, with the source for every answer.</p>
      </header>

      <div className="flex-1 space-y-5 pb-6" aria-live="polite">
        {messages.length === 0 && (
          <div className="grid gap-3 pt-4 sm:grid-cols-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} type="button" onClick={() => send(s)}
                className="card p-4 text-left text-sm text-ink-soft transition hover:border-brand/40 hover:text-ink">
                {s}
              </button>
            ))}
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <p className="max-w-[85%] rounded-2xl rounded-br-md bg-brand px-4 py-2.5 text-sm text-white">{m.content}</p>
            </div>
          ) : (
            <div key={i} className="flex gap-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-soft">
                <Sparkles className="h-4 w-4 text-brand" aria-hidden />
              </span>
              <div className="min-w-0 max-w-[85%] space-y-2">
                <p className={clsx(
                  "whitespace-pre-wrap rounded-2xl rounded-tl-md border px-4 py-2.5 text-sm",
                  m.failed ? "border-danger/30 bg-danger-soft text-danger" : "border-line bg-surface text-ink-soft",
                )}>
                  {m.content}
                </p>
                {m.sources && m.sources.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-xs text-subtle">Sources</span>
                    {m.sources.map((s) => (
                      <span key={s} className="badge border border-line bg-surface-2 capitalize text-ink-soft">
                        <FileText className="h-3 w-3" aria-hidden />
                        {sourceName(s)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ),
        )}

        {loading && (
          <div className="flex gap-3" aria-label="Assistant is typing">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-soft">
              <Sparkles className="h-4 w-4 text-brand" aria-hidden />
            </span>
            <span className="flex items-center gap-1 rounded-2xl border border-line bg-surface px-4">
              {[0, 150, 300].map((d) => (
                <span key={d} className="h-1.5 w-1.5 animate-bounce rounded-full bg-subtle" style={{ animationDelay: `${d}ms` }} />
              ))}
            </span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        className="sticky bottom-4 flex items-center gap-2 rounded-2xl border border-line-strong bg-surface p-2 shadow-[var(--shadow-card)]"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <label htmlFor="chat-input" className="sr-only">Your question</label>
        <input id="chat-input" className="flex-1 bg-transparent px-3 py-2 text-sm text-ink placeholder:text-subtle focus:outline-hidden"
          value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about leave, benefits, payroll…" />
        <button type="submit" className="btn-primary h-10 w-10 p-0" disabled={loading || !input.trim()} aria-label="Send">
          <ArrowUp className="h-4 w-4" aria-hidden />
        </button>
      </form>
    </div>
  );
}

export default function ChatPage() {
  return (
    <AuthGate title="HR assistant">
      {() => <Chat />}
    </AuthGate>
  );
}

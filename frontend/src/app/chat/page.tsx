"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { ArrowUp } from "lucide-react";
import { StepList } from "@/components/Agent";
import { AuthGate } from "@/components/AuthGate";
import { api, type AgentStep } from "@/lib/api";
import type { SessionUser } from "@/lib/auth";

type Message = { role: "user" | "assistant"; content: string; steps?: AgentStep[]; failed?: boolean };

const SUGGESTIONS: Record<string, string[]> = {
  staff: [
    "What needs doing today?",
    "Who are the best applicants for Senior ML Engineer?",
    "Book an interview with the top applicant for next Tuesday at 2pm",
    "Is last month's payroll done?",
  ],
  employee: [
    "How many days off do I have left?",
    "Book December 22 to 26 off",
    "What did I get paid last month?",
    "What's the remote work policy?",
  ],
  candidate: [
    "Where are my applications at?",
    "What is the interview process?",
    "When do health benefits start?",
    "What's the remote work policy?",
  ],
};

function Chat({ user }: { user: SessionUser }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const kind = user.role === "admin" || user.role === "recruiter" ? "staff" : user.role;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  async function send(text: string) {
    if (!text.trim() || loading) return;
    const history = messages.filter((m) => !m.failed).map(({ role, content }) => ({ role, content }));
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setLoading(true);
    try {
      const run = await api.agentChat(text, history);
      setMessages((m) => [...m, { role: "assistant", content: run.reply, steps: run.steps, failed: run.status === "failed" }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", failed: true, content: err instanceof Error ? err.message : "HR isn't reachable right now." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-8rem)] max-w-3xl flex-col">
      <header className="space-y-1 pb-6">
        <h1 className="text-3xl sm:text-4xl">Ask HR</h1>
        <p className="text-lg text-muted">
          {kind === "staff"
            ? "Tell HR what to do, or ask about anything in the workspace. Big changes come back to you for an OK."
            : "Ask anything about leave, pay or company rules, or just ask for what you need. It can book your time off."}
        </p>
      </header>

      <div className="flex-1 space-y-5 pb-6" aria-live="polite">
        {messages.length === 0 && (
          <div className="grid gap-3 pt-4 sm:grid-cols-2">
            {SUGGESTIONS[kind].map((s) => (
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
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-semibold text-brand">HR</span>
              <div className={clsx(
                "min-w-0 max-w-[85%] space-y-3 rounded-2xl rounded-tl-md border px-4 py-3 text-sm",
                m.failed ? "border-danger/30 bg-danger-soft text-danger" : "border-line bg-surface text-ink-soft",
              )}>
                <p className="whitespace-pre-wrap">{m.content}</p>
                {m.steps && m.steps.length > 0 && <StepList steps={m.steps} className="border-t border-line pt-3 text-xs" />}
              </div>
            </div>
          ),
        )}

        {loading && (
          <div className="flex gap-3" aria-label="HR is working">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-soft text-xs font-semibold text-brand">HR</span>
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
        className="sticky bottom-4 flex items-center gap-2 rounded-full border border-line-strong bg-surface p-1.5 shadow-(--shadow-card)"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <label htmlFor="chat-input" className="sr-only">Your message</label>
        <input id="chat-input" className="flex-1 bg-transparent px-4 py-2 text-sm text-ink placeholder:text-subtle focus:outline-hidden"
          value={input} onChange={(e) => setInput(e.target.value)}
          placeholder={kind === "staff" ? "Tell HR what to do…" : "Ask or ask for something…"} />
        <button type="submit" className="btn-primary h-10 w-10 p-0" disabled={loading || !input.trim()} aria-label="Send">
          <ArrowUp className="h-4 w-4" aria-hidden />
        </button>
      </form>
    </div>
  );
}

export default function ChatPage() {
  return (
    <AuthGate title="Ask HR">
      {(user) => <Chat user={user} />}
    </AuthGate>
  );
}

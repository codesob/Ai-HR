"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type Message = { role: "user" | "assistant"; content: string };

const SUGGESTIONS = [
  "How many annual leave days do I get?",
  "What is the remote work policy?",
  "When is payroll processed?",
  "What is the interview process?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);

  async function send(text: string) {
    if (!text.trim()) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.chat(text, sessionId);
      setSessionId(res.session_id);
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Unable to reach HR assistant. Is the API running?" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">HR Copilot (RAG)</h1>
        <p className="text-slate-400">
          Ask about leave, payroll, benefits, and recruiting policies — powered by vector search
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            className="rounded-full border border-slate-600 px-3 py-1 text-xs hover:bg-slate-800"
            onClick={() => send(s)}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="card min-h-[400px] flex flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto">
          {messages.length === 0 && (
            <p className="text-center text-slate-500">Start a conversation with the HR knowledge base</p>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`rounded-lg px-4 py-2 text-sm ${
                m.role === "user"
                  ? "ml-8 bg-indigo-600/30"
                  : "mr-8 bg-slate-800 text-slate-300"
              }`}
            >
              {m.content}
            </div>
          ))}
          {loading && <p className="text-sm text-slate-500">Thinking…</p>}
        </div>
        <form
          className="mt-4 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <input
            className="input flex-1"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about leave, benefits, policies…"
          />
          <button type="submit" className="btn-primary" disabled={loading}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

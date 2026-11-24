"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FileText, Trash2, Upload } from "lucide-react";
import { Alert } from "@/components/ui";
import { api, type PolicyDocument } from "@/lib/api";

/** The company's own HR handbook. Ask HR and the agent answer from these files. */
export function HandbookPanel() {
  const [docs, setDocs] = useState<PolicyDocument[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  const load = useCallback(() => api.handbook().then(setDocs).catch((e) => setError(e.message)), []);
  useEffect(() => {
    void load();
  }, [load]);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true);
    setError("");
    try {
      for (const file of Array.from(files)) await api.uploadHandbook(file);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't upload that file.");
    } finally {
      setUploading(false);
      if (input.current) input.current.value = "";
    }
  }

  async function remove(doc: PolicyDocument) {
    if (!confirm(`Remove “${doc.title}”? Ask HR will stop using it.`)) return;
    try {
      await api.deleteHandbook(doc.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't remove it.");
    }
  }

  return (
    <section className="card space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-2xl">Company handbook</h2>
          <p className="text-muted">
            Upload your HR policies. Ask HR and the agent answer from these and say which document they used.
            {docs?.length === 0 && " Until you add one, they use a set of sample policies."}
          </p>
        </div>
        <label className="btn-secondary cursor-pointer py-2 text-sm">
          <Upload className="h-4 w-4" aria-hidden />
          {uploading ? "Reading…" : "Upload files"}
          <input ref={input} type="file" multiple accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp" className="sr-only" disabled={uploading}
            onChange={(e) => upload(e.target.files)} />
        </label>
      </div>
      {error && <Alert>{error}</Alert>}
      {docs && docs.length > 0 && (
        <ul className="divide-y divide-line">
          {docs.map((d) => (
            <li key={d.id} className="flex items-center gap-3 py-3">
              <FileText className="h-5 w-5 shrink-0 text-brand" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold capitalize">{d.title}</p>
                <p className="text-xs text-muted">
                  {d.filename} · {d.chunks} passages · added {new Date(d.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                </p>
              </div>
              <button type="button" className="btn-ghost px-2" onClick={() => remove(d)} aria-label={`Remove ${d.title}`}>
                <Trash2 className="h-4 w-4" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="hint">PDF, Word, text or Markdown, up to 5 MB each. Scanned pages and photos are read too.</p>
    </section>
  );
}

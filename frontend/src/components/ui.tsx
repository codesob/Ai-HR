import type { ReactNode } from "react";
import clsx from "clsx";
import type { LucideIcon } from "lucide-react";

/** Circular 0–100 score; color follows the value but the number is always shown. */
export function ScoreRing({ value, size = 56 }: { value: number | null | undefined; size?: number }) {
  const pct = value == null ? null : Math.round(Math.max(0, Math.min(1, value)) * 100);
  const r = (size - 6) / 2;
  const c = 2 * Math.PI * r;
  const tone = pct == null ? "var(--color-line-strong)" : pct >= 75 ? "var(--color-success)" : pct >= 50 ? "var(--color-brand)" : "var(--color-warning)";
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={pct == null ? "Not scored" : `Match score ${pct} out of 100`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-surface-2)" strokeWidth={5} />
        {pct != null && (
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={tone} strokeWidth={5} strokeLinecap="round"
            strokeDasharray={c} strokeDashoffset={c * (1 - pct / 100)} />
        )}
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-ink">{pct ?? "–"}</span>
    </div>
  );
}

export function MiniBar({ label, value }: { label: string; value: number | undefined }) {
  const pct = value == null ? 0 : Math.round(value * 100);
  return (
    <div className="min-w-0 flex-1 space-y-1">
      <div className="flex justify-between gap-2 text-xs">
        <span className="truncate text-muted">{label}</span>
        <span className="font-medium text-ink-soft">{value == null ? "–" : `${pct}%`}</span>
      </div>
      <div className="h-1 rounded-full bg-surface-2">
        <div className="h-1 rounded-full bg-brand" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function Avatar({ name }: { name: string | null | undefined }) {
  const initials = (name ?? "?").split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  return (
    <span aria-hidden className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-soft text-sm font-semibold text-brand-ink">
      {initials}
    </span>
  );
}

export function EmptyState({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-[var(--radius-card)] border border-dashed border-line-strong px-6 py-12 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-2">
        <Icon className="h-5 w-5 text-subtle" aria-hidden />
      </span>
      <p className="font-medium text-ink">{title}</p>
      {children && <div className="max-w-sm text-sm text-muted">{children}</div>}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="card p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-ink">{value}</p>
      {hint && <p className="mt-1 text-xs text-subtle">{hint}</p>}
    </div>
  );
}

const STAGE_TONES: Record<string, string> = {
  applied: "bg-surface-2 text-ink-soft",
  screening: "bg-brand-soft text-brand-ink",
  assessment: "bg-brand-soft text-brand-ink",
  interview: "bg-brand-soft text-brand-ink",
  offer: "bg-warning-soft text-warning",
  hired: "bg-success-soft text-success",
  rejected: "bg-danger-soft text-danger",
  pending: "bg-warning-soft text-warning",
  approved: "bg-success-soft text-success",
  scheduled: "bg-brand-soft text-brand-ink",
  completed: "bg-success-soft text-success",
};

export function StatusBadge({ status }: { status: string }) {
  return <span className={clsx("badge capitalize", STAGE_TONES[status] ?? "bg-surface-2 text-ink-soft")}>{status}</span>;
}

export function Alert({ children, tone = "danger" }: { children: ReactNode; tone?: "danger" | "success" | "warning" }) {
  const tones = { danger: "bg-danger-soft text-danger", success: "bg-success-soft text-success", warning: "bg-warning-soft text-warning" };
  return (
    <p role={tone === "danger" ? "alert" : "status"} className={clsx("rounded-xl px-4 py-3 text-sm", tones[tone])}>
      {children}
    </p>
  );
}

"use client";

import { useMemo, useSyncExternalStore } from "react";
import { getSession, onSessionChange } from "@/lib/auth";

const read = () => (typeof window === "undefined" ? null : window.localStorage.getItem("aihr_session"));

export function useSession() {
  // Snapshot is the raw string so React sees a stable value between changes.
  const raw = useSyncExternalStore(onSessionChange, read, () => null);
  const hydrated = useSyncExternalStore(onSessionChange, () => true, () => false);
  return { session: useMemo(() => (raw ? getSession() : null), [raw]), hydrated };
}

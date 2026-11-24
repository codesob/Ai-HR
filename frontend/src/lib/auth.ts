export type Role = "admin" | "recruiter" | "employee" | "candidate";

export interface SessionUser {
  id: number;
  organization_id: number;
  email: string;
  full_name: string;
  role: Role;
  email_verified_at?: string | null;
}

/**
 * The credentials live in httpOnly cookies the page can't read. This only caches who is signed in,
 * so the UI can render immediately; the server stays the source of truth (see SessionSync).
 */
interface Session {
  user: SessionUser;
}

const STORAGE_KEY = "aihr_session";
const EVENT = "aihr-session";

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as Session) : null;
    return parsed?.user ? { user: parsed.user } : null;
  } catch {
    return null;
  }
}

export function setSession(session: Session) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ user: session.user }));
  window.dispatchEvent(new Event(EVENT));
}

export function clearSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event(EVENT));
}

export function onSessionChange(callback: () => void): () => void {
  window.addEventListener(EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

export function homeFor(role: Role): string {
  switch (role) {
    case "admin":
      return "/admin";
    case "recruiter":
      return "/recruiter";
    case "employee":
      return "/employee";
    default:
      return "/candidate";
  }
}

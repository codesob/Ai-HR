export type Role = "admin" | "recruiter" | "employee" | "candidate";

export interface SessionUser {
  id: number;
  organization_id: number;
  email: string;
  full_name: string;
  role: Role;
}

interface Session {
  token: string;
  user: SessionUser;
}

const STORAGE_KEY = "aihr_session";
const EVENT = "aihr-session";

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  return getSession()?.token ?? null;
}

export function setSession(session: Session) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
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

export function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
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

import { getAuthHeaders, getToken } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const FALLBACK_API_URL = "http://localhost:8080";
const PREFIX = "/api/v1";

async function fetchWithFallback(path: string, options: RequestInit = {}): Promise<Response> {
  const urls = [API_URL];
  if (API_URL !== FALLBACK_API_URL) urls.push(FALLBACK_API_URL);

  let lastError: string | Error = new Error("Network request failed");
  for (const baseUrl of urls) {
    try {
      return await fetch(`${baseUrl}${PREFIX}${path}`, options);
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
    }
  }

  throw lastError;
}

export function setToken(token: string) {
  localStorage.setItem("aihr_token", token);
}

export function clearToken() {
  localStorage.removeItem("aihr_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = false
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (auth) {
    Object.assign(headers, getAuthHeaders());
  }
  const res = await fetchWithFallback(`${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json().catch(() => {
    throw new Error("Failed to parse server response");
  });
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name: "User" }),
    }),
  register: (email: string, password: string, full_name: string, role: string) =>
    request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name, role }),
    }),
  jobs: () => request<Job[]>("/jobs"),
  createJob: (job: Partial<Job>) =>
    request<Job>("/jobs", { method: "POST", body: JSON.stringify(job) }, true),
  generateJD: (payload: object) =>
    request<Record<string, unknown>>("/jobs/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }, true),
  applications: (jobId?: number) =>
    request<Application[]>(`/applications${jobId ? `?job_id=${jobId}` : ""}`, {}, true),
  ranked: (jobId: number) =>
    request<Record<string, unknown>[]>(`/applications/ranked/${jobId}`),
  apply: (jobId: number) =>
    request(`/applications/apply/${jobId}`, { method: "POST" }, true),
  analytics: () => request<Analytics>("/analytics/hiring", {}, true),
  chat: (message: string, session_id?: string) =>
    request<{ reply: string; sources: string[]; session_id: string }>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id }),
    }),
  interviews: () => request<Interview[]>("/interviews"),
  scheduleInterview: (payload: object) =>
    request("/interviews", { method: "POST", body: JSON.stringify(payload) }, true),
  onboarding: () => request("/onboarding"),
  startOnboarding: (payload: object) =>
    request("/onboarding", { method: "POST", body: JSON.stringify(payload) }, true),
  parseResumeText: (text: string) =>
    request<Record<string, unknown>>("/resumes/parse-text", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  uploadResume: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetchWithFallback(`/resumes/upload`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: form,
    });
    if (!res.ok) throw new Error("Upload failed");
    return res.json();
  },
};

export interface Job {
  id: number;
  title: string;
  department: string;
  description: string;
  requirements: string;
  required_skills: string[];
  min_experience_years: number;
  salary_min: number | null;
  salary_max: number | null;
  status: string;
}

export interface Application {
  id: number;
  job_id: number;
  candidate_id: number;
  status: string;
  match_score: number | null;
  rank_score: number | null;
  match_explanation: Record<string, unknown> | null;
  candidate_name?: string;
  job_title?: string;
}

export interface Analytics {
  total_jobs: number;
  open_jobs: number;
  total_applications: number;
  avg_time_to_hire_days: number | null;
  avg_match_score: number | null;
  funnel: Record<string, number>;
  source_effectiveness: Record<string, number>;
}

export interface Interview {
  id: number;
  application_id: number;
  scheduled_at: string;
  duration_minutes: number;
  meeting_link: string | null;
  interviewer_email: string;
  status: string;
}

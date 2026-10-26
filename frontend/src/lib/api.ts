import { clearSession, getAuthHeaders, type SessionUser } from "@/lib/auth";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const PREFIX = "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d: { loc?: string[]; msg?: string }) => `${d.loc?.slice(-1)[0] ?? "field"}: ${d.msg}`)
      .join("; ");
  }
  return fallback;
}

async function request<T>(path: string, options: RequestInit = {}, auth = true): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
  if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (auth) Object.assign(headers, getAuthHeaders());

  let res: Response;
  try {
    res = await fetch(`${API_URL}${PREFIX}${path}`, { ...options, headers });
  } catch {
    throw new ApiError("Can't reach the server. Check your connection and try again.", 0);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && auth) clearSession();
    throw new ApiError(errorMessage(body, res.statusText || "Request failed"), res.status);
  }
  return body as T;
}

const json = (method: string, data?: unknown): RequestInit => ({
  method,
  body: data === undefined ? undefined : JSON.stringify(data),
});

export interface AuthResponse {
  access_token: string;
  user: SessionUser;
}

export const api = {
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", json("POST", { email, password }), false),
  signup: (payload: { company_name: string; full_name: string; email: string; password: string }) =>
    request<AuthResponse>("/auth/signup", json("POST", payload), false),
  registerCandidate: (payload: { org_slug: string; full_name: string; email: string; password: string }) =>
    request<AuthResponse>("/auth/register", json("POST", payload), false),
  acceptInvite: (payload: { token: string; full_name: string; password: string }) =>
    request<AuthResponse>("/auth/accept-invite", json("POST", payload), false),
  organization: () => request<Organization>("/auth/organization"),

  users: () => request<SessionUser[]>("/users"),
  invite: (email: string, role: string) =>
    request<{ email: string; role: string; invite_url: string }>("/users/invite", json("POST", { email, role })),
  updateUser: (id: number, data: { role?: string; is_active?: boolean }) =>
    request<SessionUser>(`/users/${id}`, json("PATCH", data)),

  jobs: () => request<Job[]>("/jobs"),
  publicJobs: (slug: string) => request<Job[]>(`/jobs/public/${encodeURIComponent(slug)}`, {}, false),
  createJob: (job: Partial<Job>) => request<Job>("/jobs", json("POST", job)),
  updateJob: (id: number, job: Partial<Job>) => request<Job>(`/jobs/${id}`, json("PATCH", job)),
  generateJD: (payload: object) => request<Record<string, unknown>>("/jobs/generate", json("POST", payload)),

  applications: (jobId?: number) => request<Application[]>(`/applications${jobId ? `?job_id=${jobId}` : ""}`),
  myApplications: () => request<Application[]>("/applications/mine"),
  ranked: (jobId: number) => request<RankedCandidate[]>(`/applications/ranked/${jobId}`),
  apply: (jobId: number) => request<Application>(`/applications/apply/${jobId}`, { method: "POST" }),
  setApplicationStatus: (id: number, status: string) =>
    request<Application>(`/applications/${id}/status`, json("PATCH", { status })),

  analytics: () => request<Analytics>("/analytics/hiring"),
  chat: (message: string, session_id?: string) =>
    request<{ reply: string; sources: string[]; session_id: string }>("/chat", json("POST", { message, session_id })),

  interviews: () => request<Interview[]>("/interviews"),
  scheduleInterview: (payload: object) => request<Interview>("/interviews", json("POST", payload)),

  myLeave: () => request<LeaveRequest[]>("/leave/mine"),
  requestLeave: (payload: { leave_type: string; start_date: string; end_date: string; reason: string }) =>
    request<LeaveRequest>("/leave", json("POST", payload)),
  pendingLeave: () => request<LeaveRequest[]>("/leave?status=pending"),
  reviewLeave: (id: number, status: "approved" | "rejected") =>
    request<LeaveRequest>(`/leave/${id}/review`, json("POST", { status })),
  myPayslips: () => request<Payslip[]>("/payroll/payslips/mine"),

  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Record<string, unknown>>("/resumes/upload", { method: "POST", body: form });
  },
};

export interface Organization {
  id: number;
  name: string;
  slug: string;
  plan: string;
}

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

export interface MatchExplanation {
  explanation?: string;
  matched_skills?: string[];
  missing_skills?: string[];
}

export interface Application {
  id: number;
  job_id: number;
  candidate_id: number;
  status: string;
  match_score: number | null;
  rank_score: number | null;
  match_explanation: MatchExplanation | null;
  candidate_name?: string;
  job_title?: string;
  created_at: string;
}

export interface RankedCandidate {
  application_id: number;
  candidate_id: number;
  candidate_name: string | null;
  status: string;
  match_score: number | null;
  rank_score: number;
  match_explanation: MatchExplanation | null;
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

export interface LeaveRequest {
  id: number;
  user_id: number;
  leave_type: string;
  start_date: string;
  end_date: string;
  status: string;
  reason: string;
}

export interface Payslip {
  id: number;
  period_start: string;
  period_end: string;
  gross_amount: number;
  tax_deduction: number;
  net_amount: number;
}

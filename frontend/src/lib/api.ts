import { clearSession, type SessionUser } from "@/lib/auth";

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

async function send(path: string, options: RequestInit): Promise<Response> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
  if (options.body !== undefined && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  try {
    // Credentials are httpOnly cookies set by the API; the browser attaches them.
    return await fetch(`${API_URL}${PREFIX}${path}`, { ...options, headers, credentials: "include" });
  } catch {
    throw new ApiError("Can't reach the server. Check your connection and try again.", 0);
  }
}

// One refresh at a time, shared by every request that hit an expired access token.
let refreshing: Promise<boolean> | null = null;
function refreshSession(): Promise<boolean> {
  refreshing ??= send("/auth/refresh", { method: "POST" })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

async function request<T>(path: string, options: RequestInit = {}, auth = true): Promise<T> {
  let res = await send(path, options);
  if (res.status === 401 && auth) {
    if (await refreshSession()) res = await send(path, options);
    if (res.status === 401) clearSession();
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(errorMessage(body, res.statusText || "Request failed"), res.status);
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
  me: () => request<SessionUser>("/auth/me"),
  logout: () => request<void>("/auth/logout", { method: "POST" }, false),
  forgotPassword: (email: string) =>
    request<{ detail: string }>("/auth/password/forgot", json("POST", { email }), false),
  resetPassword: (token: string, password: string) =>
    request<AuthResponse>("/auth/password/reset", json("POST", { token, password }), false),
  verifyEmail: (token: string) => request<SessionUser>("/auth/email/verify", json("POST", { token }), false),
  resendVerification: () => request<{ detail: string }>("/auth/email/resend", { method: "POST" }),
  updateProfile: (full_name: string) => request<SessionUser>("/account/profile", json("PATCH", { full_name })),
  changePassword: (current_password: string, new_password: string) =>
    request<void>("/account/password", json("POST", { current_password, new_password })),
  sessions: () => request<DeviceSession[]>("/account/sessions"),
  endSession: (id: number) => request<void>(`/account/sessions/${id}`, { method: "DELETE" }),
  endOtherSessions: () => request<void>("/account/sessions/revoke-others", { method: "POST" }),

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
  apply: (jobId: number, source?: string) =>
    request<Application>(`/applications/apply/${jobId}${source ? `?source=${encodeURIComponent(source)}` : ""}`, { method: "POST" }),
  setApplicationStatus: (id: number, status: string) =>
    request<Application>(`/applications/${id}/status`, json("PATCH", { status })),

  analytics: () => request<Analytics>("/analytics/hiring"),
  chat: (message: string, session_id?: string) =>
    request<{ reply: string; sources: string[]; session_id: string }>("/chat", json("POST", { message, session_id })),

  agentStatus: () => request<{ configured: boolean }>("/agent/status"),
  agentChat: (message: string, history: AgentTurn[] = []) =>
    request<AgentRun>("/agent/chat", json("POST", { message, history })),
  agentRun: (instruction?: string) => request<AgentRun>("/agent/run", json("POST", { instruction: instruction ?? null })),
  agentRuns: () => request<AgentRun[]>("/agent/runs"),
  agentActions: (status = "proposed") => request<AgentAction[]>(`/agent/actions?status=${status}`),
  approveAction: (id: number) => request<AgentAction>(`/agent/actions/${id}/approve`, { method: "POST" }),
  rejectAction: (id: number) => request<AgentAction>(`/agent/actions/${id}/reject`, { method: "POST" }),

  interviews: (applicationId?: number) =>
    request<Interview[]>(`/interviews${applicationId ? `?application_id=${applicationId}` : ""}`),
  scheduleInterview: (payload: object) => request<Interview>("/interviews", json("POST", payload)),
  interview: (id: number) => request<InterviewDetail>(`/interviews/${id}`),
  myInterviews: () => request<MyInterview[]>("/interviews/mine"),
  prepareQuestions: (id: number) => request<InterviewDetail>(`/interviews/${id}/prep`, { method: "POST" }),
  saveScorecard: (id: number, card: { rating: number; recommendation: string; notes: string }) =>
    request<InterviewDetail>(`/interviews/${id}/scorecard`, json("PUT", card)),
  joinRoom: (id: number) => request<Room>(`/interviews/${id}/room/join`, { method: "POST" }),
  sendSignal: (id: number, kind: string, data: object = {}) =>
    request<void>(`/interviews/${id}/room/signal`, json("POST", { kind, data })),
  waitSignals: (id: number, after: number, signal?: AbortSignal) =>
    request<{ messages: Signal[]; cursor: number }>(`/interviews/${id}/room/signal?after=${after}`, { signal }),
  setRecordingConsent: (id: number, allowed: boolean) =>
    request<void>(`/interviews/${id}/room/consent`, json("POST", { allowed })),
  setRecording: (id: number, on: boolean) => request<void>(`/interviews/${id}/room/recording`, json("POST", { on })),
  uploadInterviewAudio: (id: number, part: number, track: "interviewer" | "candidate", offset: number,
    language: "en" | "ne" | "", audio: Blob) => {
    const form = new FormData();
    form.append("part", String(part));
    form.append("track", track);
    form.append("offset", offset.toFixed(1));
    form.append("language", language);
    form.append("file", new File([audio], `part-${part}-${track}.webm`, { type: audio.type || "audio/webm" }));
    return request<void>(`/interviews/${id}/room/audio`, { method: "POST", body: form });
  },
  endInterview: (id: number) => request<InterviewDetail>(`/interviews/${id}/room/end`, { method: "POST" }),

  myLeave: () => request<LeaveRequest[]>("/leave/mine"),
  requestLeave: (payload: { leave_type: string; start_date: string; end_date: string; reason: string }) =>
    request<LeaveRequest>("/leave", json("POST", payload)),
  pendingLeave: () => request<LeaveRequest[]>("/leave?status=pending"),
  reviewLeave: (id: number, status: "approved" | "rejected") =>
    request<LeaveRequest>(`/leave/${id}/review`, json("POST", { status })),
  myPayslips: () => request<Payslip[]>("/payroll/payslips/mine"),
  salaryProfiles: () => request<SalaryRow[]>("/payroll/profiles"),
  setSalary: (profile: SalaryInput) => request<{ status: string }>("/payroll/profile", json("PUT", profile)),
  payrollPeriod: () => request<PayrollPeriod>("/payroll/period"),
  runPayroll: (period_start: string, period_end: string, festival_allowance = false) =>
    request<{ processed: number; skipped: number; total_net: number; bs_month: string; fiscal_year: string }>(
      "/payroll/run-all",
      json("POST", { period_start, period_end, festival_allowance }),
    ),
  remittance: (bs_year: number, bs_month: number) =>
    request<Remittance>(`/payroll/remittance?bs_year=${bs_year}&bs_month=${bs_month}`),
  /** One row per person for keying into the SSF and IRD portals (cookie-authenticated, so fetched as a blob). */
  remittanceCsv: async (bs_year: number, bs_month: number) => {
    const res = await fetch(`${API_URL}${PREFIX}/payroll/remittance?bs_year=${bs_year}&bs_month=${bs_month}&format=csv`, {
      credentials: "include",
    });
    if (!res.ok) throw new Error("Couldn't download the remittance sheet");
    return res.blob();
  },

  auditLog: () => request<AuditEntry[]>("/users/audit"),

  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Record<string, unknown>>("/resumes/upload", { method: "POST", body: form });
  },

  onboarding: () => request<Onboarding[]>("/onboarding"),
  startOnboarding: (payload: { employee_name: string; employee_email: string; role: string }) =>
    request<Onboarding>("/onboarding", json("POST", payload)),
  setOnboardingTask: (id: number, taskId: string, completed: boolean) =>
    request<Onboarding>(`/onboarding/${id}/tasks/${taskId}`, json("PATCH", { completed })),

  handbook: () => request<PolicyDocument[]>("/handbook"),
  uploadHandbook: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<PolicyDocument>("/handbook", { method: "POST", body: form });
  },
  deleteHandbook: (id: number) => request<void>(`/handbook/${id}`, { method: "DELETE" }),

  screeningFor: (applicationId: number) => request<Screening>(`/screening/applications/${applicationId}`),
  sendTask: (applicationId: number, payload: { title: string; instructions: string; due_days: number }) =>
    request<Assessment>(`/screening/applications/${applicationId}/assessment`, json("POST", payload)),
  sendVideoScreen: (applicationId: number, payload: { questions: string[]; due_days: number }) =>
    request<VideoScreen>(`/screening/applications/${applicationId}/video`, json("POST", payload)),
  decideTask: (id: number, passed: boolean) => request<Assessment>(`/screening/assessments/${id}/decision`, json("POST", { passed })),
  decideVideo: (id: number, passed: boolean) => request<VideoScreen>(`/screening/video/${id}/decision`, json("POST", { passed })),
  /** The recording as a blob (cookie-authenticated, so it can't be a plain <video src>). */
  videoAnswer: async (id: number, index: number) => {
    const res = await fetch(`${API_URL}${PREFIX}/screening/video/${id}/answers/${index}`, { credentials: "include" });
    if (!res.ok) throw new Error("Couldn't load the recording");
    return res.blob();
  },
  myScreening: () => request<MyScreening>("/screening/mine"),
  submitTask: (id: number, text: string) => request<void>(`/screening/assessments/${id}/submit`, json("POST", { text })),
  uploadAnswer: (id: number, index: number, video: Blob, language: "en" | "ne" | "" = "") => {
    const form = new FormData();
    form.append("language", language);
    form.append("file", new File([video], `answer-${index}.webm`, { type: video.type || "video/webm" }));
    return request<void>(`/screening/video/${id}/answers/${index}`, { method: "POST", body: form });
  },
  finishVideoScreen: (id: number) => request<void>(`/screening/video/${id}/complete`, { method: "POST" }),
};

export interface DeviceSession {
  id: number;
  user_agent: string;
  ip: string;
  created_at: string;
  last_used_at: string;
  current: boolean;
}

/** Yearly pay in NPR plus what Nepal's SSF and income tax rules need to know about the person. */
export interface SalaryInput {
  user_id: number;
  annual_base: number;
  basic_monthly: number | null;
  ssf_enrolled: boolean;
  married: boolean;
  female: boolean;
  remote_category: "A" | "B" | "C" | "D" | "E" | null;
  cit_monthly: number;
  life_insurance_annual: number;
  health_insurance_annual: number;
  pan: string | null;
  ssf_number: string | null;
  joined_on: string | null;
}

export type SalaryRow = { full_name: string; role: string; currency: string | null } & {
  [K in keyof SalaryInput]: K extends "user_id" ? number : SalaryInput[K] | null;
} & {
  last_period_end: string | null;
  last_net_amount: number | null;
  last_bs_month: string | null;
};

export interface PayrollPeriod {
  bs_year: number;
  bs_month: number;
  label: string;
  fiscal_year: string;
  period_start: string;
  period_end: string;
  days: number;
}

export interface Remittance {
  bs_month: string;
  fiscal_year: string;
  people: { user_id: number; full_name: string; ssf_total: number; tds: number; net: number }[];
  ssf: { employee: number; employer: number; total: number; due: string };
  ird: { sst_11211: number; income_tax: number; total: number; due: string };
  missing_pan: string[];
  missing_ssf_number: string[];
}

export interface AuditEntry {
  id: number;
  actor: string;
  action: string;
  resource: string;
  status_code: number | null;
  created_at: string;
}

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
  semantic_similarity?: number;
  skill_gap_score?: number;
  experience_fit?: number;
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
  source?: string;
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

export interface TranscriptLine {
  at: number;
  speaker: "interviewer" | "candidate";
  text: string;
}

export interface InterviewSummary {
  overview: string;
  skills: { skill: string; evidence: string; level: "strong" | "some" | "none" }[];
  strengths: string[];
  concerns: string[];
  follow_ups: string[];
  recommendation: "advance" | "unsure" | "decline";
}

export interface InterviewDetail extends Interview {
  candidate_name: string | null;
  job_title: string | null;
  prep_questions: { question: string; why: string }[];
  recording_consent: boolean | null;
  recording_on: boolean;
  recorded_parts: number;
  transcript: TranscriptLine[];
  transcript_english: string | null;
  summary: InterviewSummary | null;
  summary_status: "" | "processing" | "ready" | "failed";
  scorecard: { rating: number; recommendation: string; notes: string; by: string; at: string } | null;
  started_at: string | null;
  ended_at: string | null;
}

export interface MyInterview {
  id: number;
  job_title: string;
  scheduled_at: string;
  duration_minutes: number;
  status: string;
}

export interface Room {
  id: number;
  role: "interviewer" | "candidate";
  job_title: string;
  candidate_name: string;
  scheduled_at: string;
  duration_minutes: number;
  status: string;
  backup_link: string | null;
  recording_consent: boolean | null;
  recording_on: boolean;
  ice_servers: RTCIceServer[];
  cursor: number;
  prep_questions: { question: string; why: string }[];
}

export interface Signal {
  id: number;
  kind: "hello" | "offer" | "answer" | "ice" | "bye" | "consent" | "recording";
  data: Record<string, unknown>;
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

export interface PayslipBreakdown {
  fiscal_year: string;
  bs_month: string;
  basic: number;
  allowances: number;
  festival_allowance: number;
  ssf_employee: number;
  ssf_employer: number;
  cit: number;
  tds: number;
  sst: number;
  projection: { months_left: number; taxable: number; annual_tax: number; retirement_deduction: number };
  warnings: string[];
  unverified: string[];
}

export interface Payslip {
  id: number;
  period_start: string;
  period_end: string;
  gross_amount: number;
  tax_deduction: number;
  net_amount: number;
  ssf_employee: number;
  breakdown: Partial<PayslipBreakdown>;
}

export interface AgentTurn {
  role: "user" | "assistant";
  content: string;
}

export interface AgentStep {
  tool: string;
  args: Record<string, unknown>;
  result: { ok?: boolean; error?: string; waiting_for_approval?: boolean; summary?: string; result?: unknown };
}

export interface AgentAction {
  id: number;
  tool: string;
  summary: string;
  reason: string;
  status: "proposed" | "executed" | "rejected" | "failed";
  result: { result?: unknown; error?: string };
  created_at: string;
  decided_at: string | null;
}

export interface AgentRun {
  id: number;
  trigger: string;
  instruction: string;
  status: "running" | "done" | "failed";
  reply: string;
  steps: AgentStep[];
  created_at: string;
  proposed: AgentAction[];
}

export interface OnboardingStep {
  id: string;
  title: string;
  category: string;
  completed: boolean;
}

export interface Onboarding {
  id: number;
  employee_name: string;
  employee_email: string;
  role: string;
  tasks: OnboardingStep[];
  status: "in_progress" | "completed";
}

export interface PolicyDocument {
  id: number;
  title: string;
  filename: string;
  chunks: number;
  characters: number;
  created_at: string;
}

interface Reviewed {
  ai_score: number | null;
  ai_recommendation: "pass" | "fail" | "";
  ai_feedback: string;
  reviewed_at: string | null;
}

export interface Assessment extends Reviewed {
  id: number;
  application_id: number;
  title: string;
  instructions: string;
  due_at: string;
  status: "sent" | "submitted" | "passed" | "failed";
  submission: string;
  submitted_at: string | null;
}

export interface VideoScreen extends Reviewed {
  id: number;
  application_id: number;
  questions: string[];
  answers: { index: number; transcript: string | null; english?: string | null }[];
  due_at: string;
  status: "invited" | "completed" | "passed" | "failed";
  completed_at: string | null;
}

export interface Screening {
  assessments: Assessment[];
  video_screens: VideoScreen[];
}

export interface MyScreening {
  assessments: { id: number; job_title: string; title: string; instructions: string; due_at: string; status: "sent" | "submitted" | "reviewed"; submission: string }[];
  video_screens: { id: number; job_title: string; questions: string[]; answered: number[]; due_at: string; status: "invited" | "completed" | "reviewed" }[];
}

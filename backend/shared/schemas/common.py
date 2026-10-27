from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from shared.models.entities import UserRole


class UserOut(BaseModel):
    id: int
    organization_id: int
    email: str
    full_name: str
    role: str
    is_active: bool = True
    email_verified_at: datetime | None = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class OrgSignup(BaseModel):
    company_name: str = Field(min_length=2, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class CandidateRegister(BaseModel):
    org_slug: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class AcceptInviteRequest(BaseModel):
    token: str = Field(min_length=10, max_length=256)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=10, max_length=128)


class InviteCreate(BaseModel):
    email: EmailStr
    role: UserRole


class InvitationOut(BaseModel):
    id: int
    email: str
    role: UserRole
    expires_at: datetime
    invite_url: str | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None


class OrganizationOut(BaseModel):
    id: int
    name: str
    slug: str
    plan: str

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    department: str = "Engineering"
    description: str = Field(min_length=10, max_length=20000)
    requirements: str = ""
    required_skills: list[str] = []
    min_experience_years: float = 0
    salary_min: int | None = None
    salary_max: int | None = None


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    department: str | None = None
    description: str | None = Field(default=None, min_length=10, max_length=20000)
    requirements: str | None = None
    required_skills: list[str] | None = None
    min_experience_years: float | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    status: str | None = Field(default=None, pattern="^(open|closed|draft)$")


class JobOut(BaseModel):
    id: int
    title: str
    department: str
    description: str
    requirements: str
    required_skills: list[str]
    min_experience_years: float
    salary_min: int | None
    salary_max: int | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ParsedResume(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    skills: list[str] = []
    experience_years: float = 0
    education: str | None = None
    certifications: list[str] = []
    work_experience: list[dict[str, Any]] = []
    projects: list[str] = []
    summary: str | None = None
    # Read by the vision model from a photo or scan: names and numbers may be misread.
    read_from_scan: bool = False


class MatchExplanation(BaseModel):
    match_score: float
    skill_gap_score: float
    experience_fit: float
    confidence_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    semantic_similarity: float
    explanation: str


class ApplicationOut(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    status: str
    match_score: float | None
    rank_score: float | None
    match_explanation: dict[str, Any] | None
    source: str = "careers_page"
    created_at: datetime
    candidate_name: str | None = None
    job_title: str | None = None

    model_config = {"from_attributes": True}


class ApplicationStatusUpdate(BaseModel):
    status: str = Field(pattern="^(applied|screening|assessment|interview|offer|hired|rejected)$")


class ResumeText(BaseModel):
    text: str = Field(min_length=1, max_length=50000)


class InterviewCreate(BaseModel):
    application_id: int
    scheduled_at: datetime
    duration_minutes: int = 60
    interviewer_email: EmailStr
    meeting_link: str | None = None


class InterviewOut(BaseModel):
    id: int
    application_id: int
    scheduled_at: datetime
    duration_minutes: int
    meeting_link: str | None
    interviewer_email: str
    status: str

    model_config = {"from_attributes": True}


class ChatMessage(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=64)


class ChatResponse(BaseModel):
    reply: str
    sources: list[str] = []
    session_id: str


class AnalyticsSummary(BaseModel):
    total_jobs: int
    open_jobs: int
    total_applications: int
    avg_time_to_hire_days: float | None
    avg_match_score: float | None
    funnel: dict[str, int]
    source_effectiveness: dict[str, int]


class OnboardingCreate(BaseModel):
    employee_name: str
    employee_email: EmailStr
    role: str


class OnboardingOut(BaseModel):
    id: int
    employee_name: str
    employee_email: str
    role: str
    tasks: list[dict[str, Any]]
    status: str

    model_config = {"from_attributes": True}


class JDGenerateRequest(BaseModel):
    title: str
    department: str
    seniority: str = "mid"
    key_skills: list[str] = []


class JDGenerateResponse(BaseModel):
    title: str
    description: str
    responsibilities: list[str]
    requirements: list[str]
    skills: list[str]
    salary_band: str
    bias_warnings: list[str] = []


class NotificationCreate(BaseModel):
    recipient: EmailStr
    channel: str = "in_app"
    subject: str
    body: str
    event_type: str = "manual"
    payload: dict[str, Any] = {}


class NotificationOut(BaseModel):
    id: int
    recipient: str
    channel: str
    subject: str
    body: str
    status: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=128)
    password: str = Field(min_length=10, max_length=128)


class TokenRequest(BaseModel):
    token: str = Field(min_length=10, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)


class SessionOut(BaseModel):
    id: int
    user_agent: str
    ip: str
    created_at: datetime
    last_used_at: datetime
    current: bool = False

    model_config = {"from_attributes": True}

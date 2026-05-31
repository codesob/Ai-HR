from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: str = "candidate"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    title: str
    department: str = "Engineering"
    description: str
    requirements: str = ""
    required_skills: list[str] = []
    min_experience_years: float = 0
    salary_min: int | None = None
    salary_max: int | None = None


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
    created_at: datetime
    candidate_name: str | None = None
    job_title: str | None = None

    model_config = {"from_attributes": True}


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
    message: str
    session_id: str | None = None


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
    diversity_placeholder: dict[str, float]
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

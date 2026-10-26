import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.session import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"
    EMPLOYEE = "employee"


class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    SCREENING = "screening"
    ASSESSMENT = "assessment"
    INTERVIEW = "interview"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"


def _org_fk() -> Mapped[int]:
    return mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)


class Organization(Base):
    """Tenant root. Every tenant-owned row carries an organization_id."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(32), default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = _org_fk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CANDIDATE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(lazy="joined")
    applications: Mapped[list["Application"]] = relationship(back_populates="candidate")


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = _org_fk()
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    invited_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = _org_fk()
    title: Mapped[str] = mapped_column(String(255))
    department: Mapped[str] = mapped_column(String(128), default="Engineering")
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    min_experience_years: Mapped[float] = mapped_column(Float, default=0)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    applications: Mapped[list["Application"]] = relationship(back_populates="job")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = _org_fk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    experience_years: Mapped[float] = mapped_column(Float, default=0)
    education: Mapped[str | None] = mapped_column(String(512), nullable=True)
    resume_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_application_job_candidate"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = _org_fk()
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), default=ApplicationStatus.APPLIED
    )
    source: Mapped[str] = mapped_column(String(64), default="careers_page")
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="applications")
    candidate: Mapped["User"] = relationship(back_populates="applications")


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = _org_fk()
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    meeting_link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    interviewer_email: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="scheduled")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = _org_fk()
    employee_name: Mapped[str] = mapped_column(String(255))
    employee_email: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(255))
    tasks: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="in_progress")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=True
    )
    actor: Mapped[str] = mapped_column(String(255), default="anonymous")
    action: Mapped[str] = mapped_column(String(64))
    resource: Mapped[str] = mapped_column(String(512))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = _org_fk()
    recipient: Mapped[str] = mapped_column(String(255), index=True)
    channel: Mapped[str] = mapped_column(String(32), default="in_app")
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    event_type: Mapped[str] = mapped_column(String(128), default="manual")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


from shared.models.leave import LeaveBalance, LeaveRequest  # noqa: E402,F401
from shared.models.payroll import Payslip, SalaryProfile  # noqa: E402,F401

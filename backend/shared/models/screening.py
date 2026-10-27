from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import Base


class Assessment(Base):
    """A take-home task sent to an applicant. The AI reviews the answer; a person makes the call."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    instructions: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # sent → submitted → passed | failed
    status: Mapped[str] = mapped_column(String(16), default="sent")
    submission: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_recommendation: Mapped[str] = mapped_column(String(8), default="")  # pass, fail, or "" if not reviewed
    ai_feedback: Mapped[str] = mapped_column(Text, default="")
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VideoScreen(Base):
    """One-way video screening: the applicant records an answer per question; it's transcribed, the AI reviews
    the answers, and a person watches and decides."""

    __tablename__ = "video_screens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    # One entry per answered question: {"index", "file", "content_type", "transcript"}
    answers: Mapped[list] = mapped_column(JSON, default=list)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # invited → completed → passed | failed
    status: Mapped[str] = mapped_column(String(16), default="invited")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_recommendation: Mapped[str] = mapped_column(String(8), default="")
    ai_feedback: Mapped[str] = mapped_column(Text, default="")
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

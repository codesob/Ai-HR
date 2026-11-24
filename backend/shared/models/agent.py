from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import Base


class AgentRun(Base):
    """One pass of the HR agent: what it was asked, every step it took, and how it ended."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    # Who the agent acted for; None for scheduled runs.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    trigger: Mapped[str] = mapped_column(String(32))  # "chat", "run", "schedule"
    instruction: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running, done, failed
    reply: Mapped[str] = mapped_column(Text, default="")
    steps: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentAction(Base):
    """A change the agent wants to make that needs a person's OK first (reject, offer, payroll …)."""

    __tablename__ = "agent_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    tool: Mapped[str] = mapped_column(String(64))
    args: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[str] = mapped_column(String(512))
    reason: Mapped[str] = mapped_column(Text, default="")
    # proposed → executed | rejected | failed
    status: Mapped[str] = mapped_column(String(16), default="proposed", index=True)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

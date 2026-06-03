"""SQLAlchemy ORM models for saved progress."""
from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Matter(Base):
    """A saved roadmap session for one user's case (no PII required)."""

    __tablename__ = "matters"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(120), default="My Illinois divorce")
    flow_id: Mapped[str] = mapped_column(String(64), default="il_divorce")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    steps: Mapped[List["StepProgress"]] = relationship(
        back_populates="matter",
        cascade="all, delete-orphan",
    )


class StepProgress(Base):
    """Per-step completion state + optional user note for a matter."""

    __tablename__ = "step_progress"
    __table_args__ = (UniqueConstraint("matter_id", "step_id", name="uq_matter_step"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    matter_id: Mapped[int] = mapped_column(ForeignKey("matters.id"))
    step_id: Mapped[str] = mapped_column(String(64))
    done: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    matter: Mapped["Matter"] = relationship(back_populates="steps")

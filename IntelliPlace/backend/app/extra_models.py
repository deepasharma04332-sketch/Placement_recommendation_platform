from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from .database import Base


def _now():
    return datetime.now(timezone.utc)


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    skills = Column(Text, default="[]")
    ats_score = Column(Float, default=0)
    ats_report = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=_now)


class TestAttempt(Base):
    __tablename__ = "test_attempts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    category = Column(String(50), nullable=False)
    score = Column(Float, nullable=False)
    correct = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)


class InterviewAttempt(Base):
    __tablename__ = "interview_attempts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    question_id = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    feedback = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_now)

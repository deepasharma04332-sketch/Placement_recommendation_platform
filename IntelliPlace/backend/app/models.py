from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), default="")
    college = Column(String(200), default="")
    degree = Column(String(100), default="")
    branch = Column(String(100), default="")
    graduation_year = Column(Integer, nullable=True)
    cgpa = Column(Float, default=0.0)
    backlogs = Column(Integer, default=0)
    skills = Column(Text, default="[]")          # JSON-encoded list of skill names
    career_interests = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    saved_jobs = relationship("SavedJob", cascade="all, delete-orphan")


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    job_id = Column(Integer, nullable=False)
    saved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

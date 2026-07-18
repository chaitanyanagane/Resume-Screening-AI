"""SQLAlchemy model for jobs."""

from sqlalchemy import Column, Integer, String, Text, Float, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    skills_required = Column(Text, nullable=False)          # JSON string
    experience_required = Column(Float, nullable=False)
    education_required = Column(Integer, nullable=False)
    location = Column(Text, nullable=True)
    status = Column(Text, nullable=False)
    recruiter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    department = Column(Text, nullable=True)
    employment_type = Column(Text, nullable=True)
    salary_range = Column(Text, nullable=True)
    preferred_skills = Column(Text, nullable=True)           # JSON string
    responsibilities = Column(Text, nullable=True)           # JSON string
    hiring_manager = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'closed')", name="ck_jobs_status"),
    )

    # Relationships
    recruiter = relationship("User")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    candidate_rankings = relationship("CandidateRanking", back_populates="job", cascade="all, delete-orphan")

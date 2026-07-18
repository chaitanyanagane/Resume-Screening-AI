"""SQLAlchemy models for candidate profiles and resume analyses."""

from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    resume_text = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)                     # JSON string
    education_level = Column(Integer, default=0)
    years_experience = Column(Float, default=0.0)
    inferred_gender = Column(Text, default="Unknown")
    email = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    resume_filename = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)

    # Relationships
    user = relationship("User", back_populates="candidate_profile")
    applications = relationship("Application", back_populates="candidate_profile", cascade="all, delete-orphan")
    resume_analyses = relationship("ResumeAnalysis", back_populates="candidate_profile", cascade="all, delete-orphan")


class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_profile_id = Column(Integer, ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    summary = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True)                  # JSON string
    weaknesses = Column(Text, nullable=True)                 # JSON string
    linkedin = Column(Text, nullable=True)
    github = Column(Text, nullable=True)
    projects = Column(Text, nullable=True)                   # JSON string
    certifications = Column(Text, nullable=True)             # JSON string
    languages = Column(Text, nullable=True)                  # JSON string
    resume_quality = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)

    candidate_profile = relationship("CandidateProfile", back_populates="resume_analyses")

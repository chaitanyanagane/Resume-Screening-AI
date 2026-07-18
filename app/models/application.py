"""SQLAlchemy models for applications and related AI analysis tables."""

from sqlalchemy import Column, Integer, String, Text, Float, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_profile_id = Column(Integer, ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    status = Column(Text, nullable=False)
    score = Column(Float, default=0.0)
    score_breakdown = Column(Text, nullable=True)            # JSON string
    explanation = Column(Text, nullable=True)                 # JSON string
    notes = Column(Text, nullable=True)
    interview_questions = Column(Text, nullable=True)         # JSON string
    created_at = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('applied', 'screening', 'technical_interview', 'manager_round', 'hr_interview', 'offer', 'selected', 'rejected')",
            name="ck_applications_status",
        ),
    )

    # Relationships
    job = relationship("Job", back_populates="applications")
    candidate_profile = relationship("CandidateProfile", back_populates="applications")
    skill_match = relationship("SkillMatch", back_populates="application", uselist=False, cascade="all, delete-orphan")
    ranking = relationship("CandidateRanking", back_populates="application", uselist=False, cascade="all, delete-orphan")
    interview_recommendation = relationship("InterviewRecommendation", back_populates="application", uselist=False, cascade="all, delete-orphan")
    ai_questions = relationship("AIInterviewQuestion", back_populates="application", uselist=False, cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="application", cascade="all, delete-orphan")
    recruiter_notes = relationship("RecruiterNote", back_populates="application", cascade="all, delete-orphan")


class SkillMatch(Base):
    __tablename__ = "skill_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    required_skills = Column(Text, nullable=True)             # JSON string
    present_skills = Column(Text, nullable=True)              # JSON string
    missing_skills = Column(Text, nullable=True)              # JSON string
    learning_recommendations = Column(Text, nullable=True)    # JSON string
    semantic_overlap_pct = Column(Float, default=0.0)

    application = relationship("Application", back_populates="skill_match")


class CandidateRanking(Base):
    __tablename__ = "candidate_rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), unique=True, nullable=False)
    rank_position = Column(Integer, nullable=True)
    ats_score = Column(Float, default=0.0)
    skill_match_pct = Column(Float, default=0.0)
    recommendation = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0)

    job = relationship("Job", back_populates="candidate_rankings")
    application = relationship("Application", back_populates="ranking")


class InterviewRecommendation(Base):
    __tablename__ = "interview_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), unique=True, nullable=False)
    status = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('Highly Recommended', 'Recommended', 'Consider', 'Not Recommended')",
            name="ck_interview_rec_status",
        ),
    )

    application = relationship("Application", back_populates="interview_recommendation")


class AIInterviewQuestion(Base):
    __tablename__ = "ai_interview_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    technical_questions = Column(Text, nullable=True)         # JSON string
    behavioral_questions = Column(Text, nullable=True)        # JSON string
    project_questions = Column(Text, nullable=True)           # JSON string
    coding_questions = Column(Text, nullable=True)            # JSON string

    application = relationship("Application", back_populates="ai_questions")

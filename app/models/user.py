"""SQLAlchemy models for users and refresh tokens."""

from sqlalchemy import Column, Integer, String, Text, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    phone = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('candidate', 'recruiter', 'admin')", name="ck_users_role"),
    )

    # Relationships
    candidate_profile = relationship("CandidateProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user")
    recruiter_notes = relationship("RecruiterNote", back_populates="recruiter", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="recruiter", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(Text, unique=True, nullable=False)
    expires_at = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")

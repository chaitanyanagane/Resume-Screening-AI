"""Re-export all ORM models so Alembic and the app can import from one place."""

from app.models.user import User, RefreshToken
from app.models.job import Job
from app.models.candidate import CandidateProfile, ResumeAnalysis
from app.models.application import (
    Application,
    SkillMatch,
    CandidateRanking,
    InterviewRecommendation,
    AIInterviewQuestion,
)
from app.models.interview import Interview
from app.models.note import RecruiterNote
from app.models.notification import Notification
from app.models.activity_log import ActivityLog

__all__ = [
    "User",
    "RefreshToken",
    "Job",
    "CandidateProfile",
    "ResumeAnalysis",
    "Application",
    "SkillMatch",
    "CandidateRanking",
    "InterviewRecommendation",
    "AIInterviewQuestion",
    "Interview",
    "RecruiterNote",
    "Notification",
    "ActivityLog",
]

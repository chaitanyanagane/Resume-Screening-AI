"""Pydantic schemas for interview endpoints."""

from pydantic import BaseModel
from typing import Optional


class InterviewCreateRequest(BaseModel):
    interviewer: str
    type: str
    scheduled_at: str
    meeting_link: Optional[str] = None


class InterviewFeedbackRequest(BaseModel):
    status: str
    feedback: str
    rating: int

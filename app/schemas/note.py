"""Pydantic schemas for recruiter note endpoints."""

from pydantic import BaseModel
from typing import List, Optional


class RecruiterNoteRequest(BaseModel):
    note_text: str
    is_pinned: Optional[int] = 0
    mentions: Optional[List[str]] = []

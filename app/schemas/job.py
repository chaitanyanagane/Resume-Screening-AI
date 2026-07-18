"""Pydantic schemas for job endpoints."""

from pydantic import BaseModel
from typing import List, Optional


class JobCreateRequest(BaseModel):
    title: str
    description: str
    skills_required: List[str]
    experience_required: float
    education_required: int
    location: Optional[str] = "Remote"
    department: Optional[str] = "Engineering"
    employment_type: Optional[str] = "Full-time"
    salary_range: Optional[str] = None
    preferred_skills: Optional[List[str]] = []
    responsibilities: Optional[List[str]] = []
    hiring_manager: Optional[str] = None


class JobResponse(BaseModel):
    id: int
    title: str
    description: str
    skills_required: List[str]
    experience_required: float
    education_required: int
    location: str
    status: str
    recruiter_id: int
    department: Optional[str] = None
    employment_type: Optional[str] = None
    salary_range: Optional[str] = None
    preferred_skills: Optional[List[str]] = []
    responsibilities: Optional[List[str]] = []
    hiring_manager: Optional[str] = None
    created_at: str

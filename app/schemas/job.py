"""Pydantic schemas for job endpoints."""

from pydantic import BaseModel, Field
from typing import List, Optional


class JobCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=50, max_length=10000)
    skills_required: List[str] = Field(..., min_length=1)
    experience_required: float = Field(..., ge=0, le=50)
    education_required: int = Field(..., ge=1, le=5, description="1=High School, 2=Associate, 3=Bachelor, 4=Master, 5=PhD")
    location: Optional[str] = Field("Remote", max_length=100)
    department: Optional[str] = Field("Engineering", max_length=100)
    employment_type: Optional[str] = Field("Full-time", max_length=50)
    salary_range: Optional[str] = Field(None, max_length=100)
    preferred_skills: Optional[List[str]] = Field(default_factory=list)
    responsibilities: Optional[List[str]] = Field(default_factory=list)
    hiring_manager: Optional[str] = Field(None, max_length=100)


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

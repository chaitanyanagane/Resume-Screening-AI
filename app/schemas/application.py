"""Pydantic schemas for application endpoints."""

from pydantic import BaseModel, Field
from typing import Optional


class ApplicationApplyRequest(BaseModel):
    job_id: int = Field(..., gt=0)


class ApplicationStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(applied|reviewing|interviewing|offered|rejected)$")
    notes: Optional[str] = Field(None, max_length=1000)


class ApplicationStageRequest(BaseModel):
    stage: str = Field(..., max_length=50)

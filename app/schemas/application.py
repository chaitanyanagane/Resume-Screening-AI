"""Pydantic schemas for application endpoints."""

from pydantic import BaseModel
from typing import Optional


class ApplicationApplyRequest(BaseModel):
    job_id: int


class ApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class ApplicationStageRequest(BaseModel):
    stage: str

"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import re


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Valid email address of the user")
    password: str = Field(
        ..., 
        min_length=6, 
        max_length=64, 
        description="Password must be at least 6 characters long"
    )
    name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, description="Contact phone number")
    role: str = Field(..., pattern=r"^(candidate|recruiter|admin)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    role: str
    name: str
    email: str
    refresh_token: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str

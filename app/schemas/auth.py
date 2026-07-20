"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import re


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Valid email address of the user")
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=64, 
        description="Password must contain at least one uppercase, one lowercase, one number and one special character"
    )
    name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$", description="E.164 phone number format")
    role: str = Field(..., pattern=r"^(candidate|recruiter|admin)$")

    @field_validator('password')
    def validate_password_complexity(cls, v):
        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$", v):
            raise ValueError('Password must contain at least one uppercase, one lowercase, one number and one special character')
        return v


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

"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr
from typing import Optional


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str
    email: str
    refresh_token: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    refresh_token: str

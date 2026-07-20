"""
Centralized application configuration using pydantic-settings.

All values are read from environment variables with sensible development
defaults so the app works out-of-the-box with ``uvicorn app.main:app``.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings – every field maps to an env var of the same name."""

    # ── Database ────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./hiresense.db"

    # ── Authentication ──────────────────────────────────────────────────
    JWT_SECRET: str = "hiresense_jwt_super_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── CORS ────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ── File Uploads ────────────────────────────────────────────────────
    # File Upload constraints
    max_file_size_bytes: int = 5 * 1024 * 1024  # 5MB limit
    CLOUDINARY_URL: Optional[str] = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# Singleton – import this everywhere
settings = Settings()

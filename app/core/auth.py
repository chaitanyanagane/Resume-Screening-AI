"""
Authentication utilities — JWT, bcrypt, role-based access control.

Refactored to use SQLAlchemy sessions instead of raw sqlite3.
All JWT logic, bcrypt hashing, and token management is preserved identically.
"""

import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.config import settings
from app.core.database import get_db

# ── JWT configuration (reads from centralised settings) ─────────────────
SECRET_KEY = settings.JWT_SECRET
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Password helpers ────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hashed password."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


# ── Access-token helpers ────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token using timezone-aware UTC datetime."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


# ── Current-user dependency ─────────────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """Dependency to retrieve currently authenticated user."""
    from app.models.user import User  # deferred to avoid circular imports

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    sub_val = payload.get("sub")
    email: str = payload.get("email")
    role: str = payload.get("role")

    if sub_val is None or email is None or role is None:
        raise credentials_exception

    try:
        user_id = int(sub_val)
    except ValueError:
        raise credentials_exception

    # Get user details from database via SQLAlchemy
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise credentials_exception

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "phone": user.phone,
    }


# ── Role checker ────────────────────────────────────────────────────────

class RoleChecker:
    """Dependency to enforce role-based access control (RBAC)."""

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your account role",
            )
        return current_user


# ── Refresh-token helpers ───────────────────────────────────────────────

def create_refresh_token_in_db(db: Session, data: dict) -> str:
    """Create and persist a refresh token using the provided session."""
    from app.models.user import RefreshToken  # deferred import

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    db_token = RefreshToken(
        user_id=int(data["sub"]),
        token=token,
        expires_at=expire.isoformat(),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(db_token)
    # Caller is responsible for committing (allows transactional grouping)
    return token


def verify_refresh_token(db: Session, token: str) -> Optional[dict]:
    """Decode and validate a refresh token against the database."""
    from app.models.user import RefreshToken  # deferred import

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None

        stored = db.query(RefreshToken).filter(RefreshToken.token == token).first()
        if not stored:
            return None

        return payload
    except jwt.PyJWTError:
        return None


def revoke_refresh_token(db: Session, token: str):
    """Delete a refresh token from the database."""
    from app.models.user import RefreshToken  # deferred import

    db.query(RefreshToken).filter(RefreshToken.token == token).delete()
    db.commit()


def revoke_all_user_refresh_tokens(db: Session, user_id: int):
    """Delete all refresh tokens for a user (logout from all devices)."""
    from app.models.user import RefreshToken  # deferred import

    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.commit()

import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
import os
from src.database import get_db_connection

# JWT config
SECRET_KEY = os.environ.get("JWT_SECRET", "hiresense_jwt_super_secret_key_change_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

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

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency to retrieve currently authenticated user."""
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
        
    # Get user details from database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, role, name, phone FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user is None:
        raise credentials_exception
        
    return dict(user)

class RoleChecker:
    """Dependency to enforce role-based access control (RBAC)."""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your account role"
            )
        return current_user


REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_refresh_token_in_conn(conn, data: dict) -> str:
    """Create and insert a refresh token using an existing connection."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO refresh_tokens (user_id, token, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (int(data["sub"]), token, expire.isoformat(), datetime.now(timezone.utc).isoformat())
    )
    return token

def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token."""
    conn = get_db_connection()
    token = create_refresh_token_in_conn(conn, data)
    conn.commit()
    conn.close()
    return token

def verify_refresh_token(token: str) -> Optional[dict]:
    """Decode and validate a refresh token against the database."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM refresh_tokens WHERE token = ?", (token,))
        stored = cursor.fetchone()
        conn.commit()
        conn.close()
        
        if not stored:
            return None
            
        return payload
    except jwt.PyJWTError:
        return None

def revoke_refresh_token(token: str):
    """Delete a refresh token from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM refresh_tokens WHERE token = ?", (token,))
    conn.commit()
    conn.close()

def revoke_all_user_refresh_tokens(user_id: int):
    """Delete all refresh tokens for a user (logout from all devices)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

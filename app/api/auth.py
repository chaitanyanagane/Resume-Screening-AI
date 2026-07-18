from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.user import User, ActivityLog
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, TokenRefreshRequest
from app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token_in_db,
    verify_refresh_token,
    revoke_refresh_token,
    revoke_all_user_refresh_tokens,
    get_current_user,
    RoleChecker,
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if req.role not in ['candidate', 'recruiter', 'admin']:
        raise HTTPException(status_code=400, detail="Invalid account role selection")
        
    if len(req.password) < 8 or not any(char.isdigit() for char in req.password) or not any(char.isalpha() for char in req.password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long and contain both letters and numbers.")
        
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email address already registered")
        
    hashed_pw = hash_password(req.password)
    now = datetime.now(timezone.utc).isoformat()
    
    new_user = User(
        email=req.email,
        password_hash=hashed_pw,
        role=req.role,
        name=req.name,
        phone=req.phone,
        created_at=now
    )
    
    try:
        db.add(new_user)
        db.flush()  # to get new_user.id
        
        log = ActivityLog(
            user_id=new_user.id,
            action="register",
            details=f"User registered as {req.role}",
            created_at=now
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error during registration")
        
    return {"message": "User registered successfully", "user_id": new_user.id}


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password credentials")
        
    access_token = create_access_token(data={
        "sub": str(user.id),
        "email": user.email,
        "role": user.role
    })
    
    refresh_token = create_refresh_token_in_db(db, data={
        "sub": str(user.id),
        "email": user.email,
        "role": user.role
    })
    
    now = datetime.now(timezone.utc).isoformat()
    log = ActivityLog(
        user_id=user.id,
        action="login",
        details="User logged in successfully",
        created_at=now
    )
    db.add(log)
    db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.name,
        "email": user.email,
        "refresh_token": refresh_token
    }


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "role": current_user["role"],
        "name": current_user["name"],
        "phone": current_user.get("phone")
    }


@router.post("/refresh")
def refresh_token(req: TokenRefreshRequest, db: Session = Depends(get_db)):
    payload = verify_refresh_token(db, req.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        
    # Generate new access token
    access_token = create_access_token(data={
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role")
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(req: TokenRefreshRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    revoke_refresh_token(db, req.refresh_token)
    return {"message": "Logged out successfully"}


@router.post("/logout/all")
def logout_all_devices(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    revoke_all_user_refresh_tokens(db, current_user["id"])
    return {"message": "Logged out from all devices successfully"}

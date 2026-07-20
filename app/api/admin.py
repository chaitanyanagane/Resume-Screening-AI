from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.activity_log import ActivityLog
from app.core.auth import RoleChecker

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users")
def get_admin_users(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(RoleChecker(['admin'])), 
    db: Session = Depends(get_db)
):
    users = db.query(User).order_by(User.id.desc()).offset(offset).limit(limit).all()
    
    res = []
    for u in users:
        res.append({
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "name": u.name,
            "phone": u.phone,
            "created_at": u.created_at
        })
    return res

@router.get("/logs")
def get_admin_logs(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(RoleChecker(['admin'])), 
    db: Session = Depends(get_db)
):
    logs = db.query(ActivityLog, User).outerjoin(User, ActivityLog.user_id == User.id).order_by(ActivityLog.id.desc()).offset(offset).limit(limit).all()
    
    res = []
    for log, user in logs:
        res.append({
            "id": log.id,
            "action": log.action,
            "details": log.details,
            "created_at": log.created_at,
            "user_email": user.email if user else None,
            "user_role": user.role if user else None
        })
    return res

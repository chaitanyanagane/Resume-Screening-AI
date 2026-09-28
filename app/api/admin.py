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


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: dict,
    current_user: dict = Depends(RoleChecker(['admin'])),
    db: Session = Depends(get_db)
):
    from fastapi import HTTPException
    from datetime import datetime, timezone
    
    new_role = payload.get("role")
    if new_role not in ["candidate", "recruiter", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role specified.")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    old_role = user.role
    user.role = new_role
    
    # Log admin action in activity_logs
    log = ActivityLog(
        user_id=current_user.get("user_id"),
        action="UPDATE_USER_ROLE",
        details=f"Admin updated user {user.email} (ID {user.id}) role from {old_role} to {new_role}.",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    db.add(log)
    db.commit()
    
    return {"message": "Role updated successfully", "user_id": user.id, "new_role": user.role}

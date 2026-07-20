from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.notification import Notification
from app.core.auth import RoleChecker

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("")
def list_notifications(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), 
    db: Session = Depends(get_db)
):
    notifications = db.query(Notification).filter(Notification.recruiter_id == current_user["id"]).order_by(Notification.id.desc()).offset(offset).limit(limit).all()
    
    res = []
    for n in notifications:
        res.append({
            "id": n.id,
            "recruiter_id": n.recruiter_id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "is_read": n.is_read,
            "created_at": n.created_at
        })
    return res

@router.put("/{notification_id}/read")
def mark_notification_read(notification_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notification_id, Notification.recruiter_id == current_user["id"]).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notif.is_read = 1
    db.commit()
    
    return {"message": "Notification marked as read"}

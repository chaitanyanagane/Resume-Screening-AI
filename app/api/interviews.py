from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.interview import Interview
from app.models.activity_log import ActivityLog
from app.models.notification import Notification
from app.schemas.interview import InterviewCreateRequest, InterviewFeedbackRequest
from app.core.auth import get_current_user, RoleChecker

router = APIRouter(tags=["interviews"])

@router.get("/applications/{app_id}/interviews")
def list_application_interviews(app_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    interviews = db.query(Interview).filter(Interview.application_id == app_id).order_by(Interview.id.desc()).all()
    
    res = []
    for i in interviews:
        res.append({
            "id": i.id,
            "application_id": i.application_id,
            "interviewer": i.interviewer,
            "type": i.type,
            "scheduled_at": i.scheduled_at,
            "meeting_link": i.meeting_link,
            "status": i.status,
            "feedback": i.feedback,
            "rating": i.rating,
            "created_at": i.created_at
        })
    return res


@router.post("/applications/{app_id}/interviews")
def schedule_interview(app_id: int, req: InterviewCreateRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).isoformat()
    
    interview = Interview(
        application_id=app_id,
        interviewer=req.interviewer,
        type=req.type,
        scheduled_at=req.scheduled_at,
        meeting_link=req.meeting_link,
        status="scheduled",
        created_at=now
    )
    
    try:
        db.add(interview)
        db.flush()
        
        log = ActivityLog(
            user_id=current_user["id"],
            action="schedule_interview",
            details=f"Scheduled {req.type} interview with {req.interviewer}",
            created_at=now
        )
        db.add(log)
        
        notification = Notification(
            recruiter_id=current_user["id"],
            title="Interview Scheduled",
            message=f"Scheduled {req.type} interview for application #{app_id}",
            type="interview_accepted",
            is_read=0,
            created_at=now
        )
        db.add(notification)
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error scheduling interview")
        
    return {"message": "Interview scheduled successfully", "interview_id": interview.id}


@router.put("/interviews/{interview_id}/feedback")
def submit_interview_feedback(interview_id: int, req: InterviewFeedbackRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
        
    interview.status = req.status
    interview.feedback = req.feedback
    interview.rating = req.rating
    
    now = datetime.now(timezone.utc).isoformat()
    log = ActivityLog(
        user_id=current_user["id"],
        action="interview_feedback",
        details=f"Recorded feedback for interview {interview_id}",
        created_at=now
    )
    
    db.add(log)
    db.commit()
    
    return {"message": "Interview feedback submitted successfully"}

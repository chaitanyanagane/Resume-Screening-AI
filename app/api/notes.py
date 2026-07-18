import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.note import RecruiterNote
from app.models.user import User
from app.models.activity_log import ActivityLog
from app.schemas.note import RecruiterNoteRequest
from app.core.auth import RoleChecker

router = APIRouter(tags=["notes"])

@router.get("/applications/{app_id}/notes/list")
def list_recruiter_notes(app_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    notes = db.query(RecruiterNote, User).join(User, RecruiterNote.recruiter_id == User.id).filter(RecruiterNote.application_id == app_id).order_by(RecruiterNote.is_pinned.desc(), RecruiterNote.id.desc()).all()
    
    res = []
    for n, u in notes:
        d = {
            "id": n.id,
            "application_id": n.application_id,
            "recruiter_id": n.recruiter_id,
            "note_text": n.note_text,
            "is_pinned": n.is_pinned,
            "created_at": n.created_at,
            "recruiter_name": u.name
        }
        try: d["mentions"] = json.loads(n.mentions) if n.mentions else []
        except Exception: d["mentions"] = []
        res.append(d)
        
    return res


@router.post("/applications/{app_id}/notes")
def add_recruiter_note(app_id: int, req: RecruiterNoteRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).isoformat()
    
    note = RecruiterNote(
        application_id=app_id,
        recruiter_id=current_user["id"],
        note_text=req.note_text,
        is_pinned=req.is_pinned,
        mentions=json.dumps(req.mentions) if req.mentions else "[]",
        created_at=now
    )
    
    try:
        db.add(note)
        db.flush()
        
        log = ActivityLog(
            user_id=current_user["id"],
            action="add_note",
            details=f"Added notes on application {app_id}",
            created_at=now
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error adding note")
        
    return {"message": "Recruiter note added successfully", "note_id": note.id}


@router.put("/notes/{note_id}/pin")
def pin_recruiter_note(note_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    note = db.query(RecruiterNote).filter(RecruiterNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    note.is_pinned = 1 if note.is_pinned == 0 else 0
    db.commit()
    
    return {"message": "Note pinning toggled", "is_pinned": note.is_pinned}


@router.delete("/notes/{note_id}")
def delete_recruiter_note(note_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    note = db.query(RecruiterNote).filter(RecruiterNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    if current_user["role"] == "recruiter" and note.recruiter_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Unauthorized delete operation")
        
    db.delete(note)
    
    now = datetime.now(timezone.utc).isoformat()
    log = ActivityLog(
        user_id=current_user["id"],
        action="delete_note",
        details=f"Deleted recruiter note {note_id}",
        created_at=now
    )
    db.add(log)
    db.commit()
    
    return {"message": "Recruiter note deleted successfully"}

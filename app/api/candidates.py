import os
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert

from app.core.database import get_db
from app.core.config import settings
from app.models.candidate import CandidateProfile
from app.models.activity_log import ActivityLog
from app.core.auth import get_current_user, RoleChecker
from app.ai.bias_auditor import infer_gender
from app.ai.resume_parser import extract_text, parse_resume

router = APIRouter(prefix="/candidates", tags=["candidates"])

@router.post("/profile/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(RoleChecker(['candidate'])),
    db: Session = Depends(get_db)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".txt"]:
        raise HTTPException(status_code=400, detail="Only PDF and TXT file formats are permitted in enterprise mode.")
        
    contents = await file.read()
    if len(contents) > settings.max_file_size_bytes:
        raise HTTPException(status_code=400, detail="File size exceeds the upload limit.")
        
    if ext == ".pdf" and not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF binary payload signature.")
        
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    with open(target_path, "wb") as f:
        f.write(contents)
        
    try:
        resume_text = extract_text(target_path)
        parsed = parse_resume(resume_text)
        inferred_gen = infer_gender(resume_text)
        
        now = datetime.now(timezone.utc).isoformat()
        
        profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user["id"]).first()
        
        if profile:
            profile.resume_text = resume_text
            profile.skills = json.dumps(parsed.get("skills", []))
            profile.education_level = parsed.get("education_level", 0)
            profile.years_experience = parsed.get("years_experience", 0.0)
            profile.inferred_gender = inferred_gen
            profile.email = parsed.get("email") or current_user.get("email")
            profile.phone = parsed.get("phone") or current_user.get("phone")
            profile.resume_filename = unique_filename
        else:
            profile = CandidateProfile(
                user_id=current_user["id"],
                resume_text=resume_text,
                skills=json.dumps(parsed.get("skills", [])),
                education_level=parsed.get("education_level", 0),
                years_experience=parsed.get("years_experience", 0.0),
                inferred_gender=inferred_gen,
                email=parsed.get("email") or current_user.get("email"),
                phone=parsed.get("phone") or current_user.get("phone"),
                resume_filename=unique_filename,
                created_at=now
            )
            db.add(profile)
            
        log = ActivityLog(
            user_id=current_user["id"],
            action="upload_resume",
            details=f"Uploaded resume: {file.filename} (stored as {unique_filename})",
            created_at=now
        )
        db.add(log)
        db.commit()
        
        return {
            "message": "Resume uploaded and profile parsed successfully",
            "skills": parsed.get("skills", []),
            "education_level": parsed.get("education_level", 0),
            "years_experience": parsed.get("years_experience", 0.0),
            "inferred_gender": inferred_gen,
            "email": parsed.get("email", ""),
            "phone": parsed.get("phone", "")
        }
    except Exception as e:
        db.rollback()
        if os.path.exists(target_path):
            os.unlink(target_path)
        raise HTTPException(status_code=500, detail=f"Failed to process and parse resume: {str(e)}")

@router.get("/profile")
def get_candidate_profile(current_user: dict = Depends(RoleChecker(['candidate'])), db: Session = Depends(get_db)):
    prof = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user["id"]).first()
    
    if not prof:
        return {"has_profile": False}
        
    d = {
        "id": prof.id,
        "user_id": prof.user_id,
        "resume_text": prof.resume_text,
        "education_level": prof.education_level,
        "years_experience": prof.years_experience,
        "inferred_gender": prof.inferred_gender,
        "email": prof.email,
        "phone": prof.phone,
        "resume_filename": prof.resume_filename,
        "created_at": prof.created_at,
        "has_profile": True
    }
    try:
        d["skills"] = json.loads(prof.skills) if prof.skills else []
    except Exception:
        d["skills"] = []
        
    return d

@router.get("/profile/resume/download/{filename}")
def download_resume_endpoint(filename: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    
    if current_user["role"] == "candidate":
        prof = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user["id"]).first()
        if not prof or prof.resume_filename != filename:
            raise HTTPException(status_code=403, detail="Access denied. You can only download your own resume.")
            
    safe_filename = os.path.basename(filename)
    file_path = os.path.realpath(os.path.join(settings.UPLOAD_DIR, safe_filename))
    if not file_path.startswith(os.path.realpath(settings.UPLOAD_DIR)):
        raise HTTPException(status_code=403, detail="Invalid file path.")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Requested resume file not found.")
        
    now = datetime.now(timezone.utc).isoformat()
    log = ActivityLog(
        user_id=current_user["id"],
        action="download_resume",
        details=f"Downloaded resume: {safe_filename}",
        created_at=now
    )
    db.add(log)
    db.commit()
    
    return FileResponse(file_path, media_type="application/octet-stream", filename=safe_filename)


import os
import uuid
import json
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

import cloudinary
import cloudinary.uploader

from app.core.database import get_db
from app.core.config import settings
from app.models.candidate import CandidateProfile
from app.models.activity_log import ActivityLog
from app.core.auth import get_current_user, RoleChecker
from app.ai.bias_auditor import infer_gender
from app.ai.resume_parser import extract_text_from_bytes, parse_resume
from app.core.security import limiter

router = APIRouter(prefix="/candidates", tags=["candidates"])

# Configure Cloudinary if URL is available
if settings.CLOUDINARY_URL:
    cloudinary.config(url=settings.CLOUDINARY_URL)


@router.post("/profile/upload")
@limiter.limit("5/minute")
async def upload_resume(
    request: Request,
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
        
    # Strict MIME type validation
    import magic
    mime_type = magic.from_buffer(contents, mime=True)
    if ext == ".pdf" and mime_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File content does not match PDF signature.")
    if ext == ".txt" and not mime_type.startswith("text/"):
        raise HTTPException(status_code=400, detail="File content does not match TXT signature.")
        
    # Attempt Cloudinary upload with retries
    secure_url = None
    if settings.CLOUDINARY_URL:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Upload to Cloudinary directly from memory
                response = cloudinary.uploader.upload(
                    contents,
                    resource_type="auto",
                    folder="hiresense_resumes",
                    filename_override=file.filename
                )
                secure_url = response.get("secure_url")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=502, detail=f"Cloudinary upload failed: {str(e)}")
                time.sleep(1) # wait before retrying
    else:
        # Fallback if Cloudinary is not configured during dev (though not recommended for prod)
        raise HTTPException(status_code=501, detail="Cloudinary is not configured. Please set CLOUDINARY_URL.")
        
    try:
        # Extract text directly from memory
        resume_text = extract_text_from_bytes(contents, ext)
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
            profile.resume_url = secure_url
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
                resume_url=secure_url,
                created_at=now
            )
            db.add(profile)
            
        log = ActivityLog(
            user_id=current_user["id"],
            action="upload_resume",
            details=f"Uploaded resume: {file.filename} to Cloudinary",
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
        "resume_url": prof.resume_url,
        "created_at": prof.created_at,
        "has_profile": True
    }
    try:
        d["skills"] = json.loads(prof.skills) if prof.skills else []
    except Exception:
        d["skills"] = []
        
    return d

@router.get("/profile/resume/download")
def download_resume_endpoint(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Replaced local file serving with redirect to Cloudinary URL
    if current_user["role"] == "candidate":
        prof = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user["id"]).first()
        if not prof or not prof.resume_url:
            raise HTTPException(status_code=404, detail="Requested resume not found.")
            
        now = datetime.now(timezone.utc).isoformat()
        log = ActivityLog(
            user_id=current_user["id"],
            action="download_resume",
            details="Downloaded resume via Cloudinary secure URL",
            created_at=now
        )
        db.add(log)
        db.commit()
        
        return RedirectResponse(url=prof.resume_url)
    
    raise HTTPException(status_code=403, detail="Access denied.")


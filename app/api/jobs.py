import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.job import Job
from app.models.activity_log import ActivityLog
from app.schemas.job import JobCreateRequest, JobResponse
from app.core.auth import get_current_user, RoleChecker

router = APIRouter(prefix="/jobs", tags=["jobs"])

def _parse_job_json_fields(job: Job) -> dict:
    d = {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "experience_required": job.experience_required,
        "education_required": job.education_required,
        "location": job.location,
        "status": job.status,
        "recruiter_id": job.recruiter_id,
        "department": job.department,
        "employment_type": job.employment_type,
        "salary_range": job.salary_range,
        "hiring_manager": job.hiring_manager,
        "created_at": job.created_at,
    }
    try: d["skills_required"] = json.loads(job.skills_required) if job.skills_required else []
    except Exception: d["skills_required"] = []
    
    try: d["preferred_skills"] = json.loads(job.preferred_skills) if job.preferred_skills else []
    except Exception: d["preferred_skills"] = []
    
    try: d["responsibilities"] = json.loads(job.responsibilities) if job.responsibilities else []
    except Exception: d["responsibilities"] = []
    
    return d

@router.get("", response_model=List[JobResponse])
def list_jobs(
    limit: int = 100, 
    offset: int = 0, 
    current_user: dict = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user["role"] == "admin":
        jobs = db.query(Job).order_by(Job.id.desc()).offset(offset).limit(limit).all()
    elif current_user["role"] == "recruiter":
        jobs = db.query(Job).filter(Job.recruiter_id == current_user["id"]).order_by(Job.id.desc()).offset(offset).limit(limit).all()
    else:
        jobs = db.query(Job).filter(Job.status == 'active').order_by(Job.id.desc()).offset(offset).limit(limit).all()
        
    return [_parse_job_json_fields(j) for j in jobs]

@router.post("", response_model=JobResponse)
def create_job(req: JobCreateRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).isoformat()
    
    new_job = Job(
        title=req.title,
        description=req.description,
        skills_required=json.dumps(req.skills_required),
        experience_required=req.experience_required,
        education_required=req.education_required,
        location=req.location,
        status="active",
        recruiter_id=current_user["id"],
        department=req.department,
        employment_type=req.employment_type,
        salary_range=req.salary_range,
        preferred_skills=json.dumps(req.preferred_skills) if req.preferred_skills else "[]",
        responsibilities=json.dumps(req.responsibilities) if req.responsibilities else "[]",
        hiring_manager=req.hiring_manager,
        created_at=now
    )
    
    try:
        db.add(new_job)
        db.flush()
        
        log = ActivityLog(
            user_id=current_user["id"],
            action="create_job",
            details=f"Created job post: {req.title}",
            created_at=now
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error during job creation")
        
    return _parse_job_json_fields(new_job)

@router.delete("/{job_id}")
def delete_job(job_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if current_user["role"] == "recruiter" and job.recruiter_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Unauthorized delete operation")
        
    now = datetime.now(timezone.utc).isoformat()
    log = ActivityLog(
        user_id=current_user["id"],
        action="delete_job",
        details=f"Deleted job post: {job.title}",
        created_at=now
    )
    
    db.delete(job)
    db.add(log)
    db.commit()
    
    return {"message": "Job deleted successfully"}

@router.put("/{job_id}", response_model=JobResponse)
def edit_job(job_id: int, req: JobCreateRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if current_user["role"] == "recruiter" and job.recruiter_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Unauthorized edit operation")
        
    job.title = req.title
    job.description = req.description
    job.skills_required = json.dumps(req.skills_required)
    job.experience_required = req.experience_required
    job.education_required = req.education_required
    job.location = req.location
    job.department = req.department
    job.employment_type = req.employment_type
    job.salary_range = req.salary_range
    job.preferred_skills = json.dumps(req.preferred_skills) if req.preferred_skills else "[]"
    job.responsibilities = json.dumps(req.responsibilities) if req.responsibilities else "[]"
    job.hiring_manager = req.hiring_manager
    
    now = datetime.now(timezone.utc).isoformat()
    log = ActivityLog(
        user_id=current_user["id"],
        action="edit_job",
        details=f"Edited job post: {req.title}",
        created_at=now
    )
    
    db.add(log)
    db.commit()
    db.refresh(job)
    
    return _parse_job_json_fields(job)

@router.post("/{job_id}/duplicate", response_model=JobResponse)
def duplicate_job(job_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if current_user["role"] == "recruiter" and job.recruiter_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Unauthorized duplicate operation")
        
    now = datetime.now(timezone.utc).isoformat()
    new_title = f"{job.title} (Copy)"
    
    new_job = Job(
        title=new_title,
        description=job.description,
        skills_required=job.skills_required,
        experience_required=job.experience_required,
        education_required=job.education_required,
        location=job.location,
        status="active",
        recruiter_id=current_user["id"],
        department=job.department,
        employment_type=job.employment_type,
        salary_range=job.salary_range,
        preferred_skills=job.preferred_skills,
        responsibilities=job.responsibilities,
        hiring_manager=job.hiring_manager,
        created_at=now
    )
    
    db.add(new_job)
    db.flush()
    
    log = ActivityLog(
        user_id=current_user["id"],
        action="duplicate_job",
        details=f"Duplicated job: {job.title} as {new_title}",
        created_at=now
    )
    db.add(log)
    db.commit()
    
    return _parse_job_json_fields(new_job)

def toggle_job_status(job_id: int, status: str, current_user: dict, db: Session):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if current_user["role"] == "recruiter" and job.recruiter_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Unauthorized operation")
        
    job.status = status
    
    now = datetime.now(timezone.utc).isoformat()
    action = "close_job" if status == "closed" else "reopen_job"
    details = f"Closed hiring for: {job.title}" if status == "closed" else f"Reopened hiring for: {job.title}"
    
    log = ActivityLog(
        user_id=current_user["id"],
        action=action,
        details=details,
        created_at=now
    )
    
    db.add(log)
    db.commit()
    db.refresh(job)
    
    return _parse_job_json_fields(job)

@router.put("/{job_id}/close", response_model=JobResponse)
def close_job(job_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    return toggle_job_status(job_id, "closed", current_user, db)

@router.put("/{job_id}/reopen", response_model=JobResponse)
def reopen_job(job_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    return toggle_job_status(job_id, "active", current_user, db)

@router.get("/{job_id}/rankings")
def get_job_rankings(job_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    from app.models.application import CandidateRanking, Application
    from app.models.candidate import CandidateProfile
    from app.models.user import User

    rankings = db.query(
        CandidateRanking, Application, CandidateProfile, User
    ).join(
        Application, CandidateRanking.application_id == Application.id
    ).join(
        CandidateProfile, Application.candidate_profile_id == CandidateProfile.id
    ).join(
        User, CandidateProfile.user_id == User.id
    ).filter(
        CandidateRanking.job_id == job_id
    ).order_by(
        CandidateRanking.ats_score.desc()
    ).all()
    
    res = []
    for r, app, prof, user in rankings:
        d = {
            "id": r.id,
            "job_id": r.job_id,
            "application_id": r.application_id,
            "rank_position": r.rank_position,
            "ats_score": r.ats_score,
            "skill_match_pct": r.skill_match_pct,
            "recommendation": r.recommendation,
            "confidence_score": r.confidence_score,
            "candidate_name": user.name,
            "application_status": app.status
        }
        res.append(d)
        
    return res


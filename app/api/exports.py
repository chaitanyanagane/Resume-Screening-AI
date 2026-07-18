from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.application import Application
from app.models.candidate import CandidateProfile
from app.models.user import User
from app.models.job import Job
from app.core.auth import RoleChecker
from app.api.applications import list_applications
from app.ai.exporter import export_applications_csv, generate_candidate_text_report

router = APIRouter(prefix="/applications", tags=["exports"])

@router.get("/export/excel")
def list_export_excel(job_id: Optional[int] = None, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    query = db.query(
        Application, CandidateProfile, User, Job
    ).join(
        CandidateProfile, Application.candidate_profile_id == CandidateProfile.id
    ).join(
        User, CandidateProfile.user_id == User.id
    ).join(
        Job, Application.job_id == Job.id
    )
    
    if job_id:
        query = query.filter(Application.job_id == job_id)
        
    query = query.order_by(Application.score.desc())
    records = query.all()
    
    output = "Application ID,Candidate Name,Candidate Email,Candidate Phone,Years Experience,Education Level,Gender,Job Title,Hiring Stage,ATS Score\n"
    edu_map = {0: "N/A", 1: "12th/HSC", 2: "Diploma", 3: "Bachelor", 4: "Master", 5: "PhD"}
    
    for a, cp, u, j in records:
        edu_str = edu_map.get(cp.education_level, "Unknown")
        job_title_escaped = f"\"{j.title}\"" if "," in str(j.title) else j.title
        output += f"{a.id},{u.name},{cp.email},{cp.phone},{cp.years_experience},{edu_str},{cp.inferred_gender},{job_title_escaped},{a.status},{a.score:.1f}\n"
        
    return Response(
        content=output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=hiresense_ats_export_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"}
    )

@router.get("/export/csv")
def get_applications_csv(job_id: Optional[int] = None, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    apps = list_applications(job_id=job_id, current_user=current_user, db=db)
    csv_data = export_applications_csv(apps)
    
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hiresense_candidates_export.csv"}
    )

@router.get("/{app_id}/export/report")
def get_candidate_report(app_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    candidate = db.query(CandidateProfile, User).join(User, CandidateProfile.user_id == User.id).filter(CandidateProfile.id == app.candidate_profile_id).first()
    
    cp, u = candidate
    cand_dict = {
        "id": cp.id,
        "user_id": cp.user_id,
        "resume_text": cp.resume_text,
        "skills": cp.skills,
        "education_level": cp.education_level,
        "years_experience": cp.years_experience,
        "inferred_gender": cp.inferred_gender,
        "email": cp.email,
        "phone": cp.phone,
        "name": u.name
    }
    
    app_dict = {
        "id": app.id,
        "job_id": app.job_id,
        "candidate_profile_id": app.candidate_profile_id,
        "status": app.status,
        "score": app.score,
        "score_breakdown": app.score_breakdown,
        "explanation": app.explanation,
        "notes": app.notes,
        "interview_questions": app.interview_questions
    }
    
    report_text = generate_candidate_text_report(cand_dict, app_dict)
    
    return Response(
        content=report_text,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=hiresense_report_{u.name.replace(' ', '_')}.txt"}
    )

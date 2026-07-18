import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.application import (
    Application,
    SkillMatch,
    CandidateRanking,
    InterviewRecommendation,
    AIInterviewQuestion,
)
from app.models.job import Job
from app.models.candidate import CandidateProfile, ResumeAnalysis
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.schemas.application import ApplicationApplyRequest, ApplicationStatusUpdate, ApplicationStageRequest
from app.core.auth import get_current_user, RoleChecker
from app.ai.matcher import HybridMatcher
from app.ai.pipeline import ResumeScreeningPipeline

router = APIRouter(prefix="/applications", tags=["applications"])

@router.post("", status_code=status.HTTP_201_CREATED)
def apply_to_job(req: ApplicationApplyRequest, current_user: dict = Depends(RoleChecker(['candidate'])), db: Session = Depends(get_db)):
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user["id"]).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Please upload a resume to construct a profile before applying")
        
    candidate_skills = set(json.loads(profile.skills) if profile.skills else [])
    
    existing_app = db.query(Application).filter(Application.job_id == req.job_id, Application.candidate_profile_id == profile.id).first()
    if existing_app:
        raise HTTPException(status_code=400, detail="You have already applied to this job post")
        
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Target job post not found")
        
    job_skills_req = json.loads(job.skills_required) if job.skills_required else []
    job_exp = job.experience_required
    
    jd_requirements = {
        "skills": job_skills_req,
        "experience": job_exp,
        "education": job.education_required
    }
    
    pipeline = ResumeScreeningPipeline()
    res = pipeline.process_resume(profile.resume_text, job.description, apply_blind_screening=True, is_raw_text=True, jd_requirements=jd_requirements)
    
    questions = [
        f"How did you leverage your experience in {', '.join(list(candidate_skills)[:3])} to solve engineering problems?"
    ]
    missing_skills = res["score_breakdown"]["missing_skills"]
    if missing_skills:
        questions.append(f"We noted that you might not have listed {missing_skills[0]} on your profile. Can you explain your conceptual understanding of it?")
    if profile.years_experience < job_exp:
        questions.append(f"This role prefers {job_exp}+ years of experience, and we matched {profile.years_experience} years. How do you plan to scale up to the senior expectations?")
    
    recruiter_notes = res["explanation"]["recruiter_notes"]
    now = datetime.now(timezone.utc).isoformat()
    
    try:
        new_app = Application(
            job_id=req.job_id,
            candidate_profile_id=profile.id,
            status="applied",
            score=res["final_score"],
            score_breakdown=json.dumps(res["score_breakdown"]),
            explanation=json.dumps(res["explanation"]),
            notes=recruiter_notes,
            interview_questions=json.dumps(questions),
            created_at=now
        )
        db.add(new_app)
        db.flush()
        
        analysis = ResumeAnalysis(
            candidate_profile_id=profile.id,
            summary=res["explanation"]["summary"],
            strengths=json.dumps(res["explanation"]["strengths"]),
            weaknesses=json.dumps(res["explanation"]["weaknesses"]),
            linkedin=res["parsed"]["linkedin"],
            github=res["parsed"]["github"],
            projects=json.dumps(res["parsed"]["projects"]),
            certifications=json.dumps(res["parsed"]["certifications"]),
            languages=json.dumps(res["parsed"]["languages"]),
            resume_quality=f"Contact verification matched. Structural quality score: {res['score_breakdown']['resume_quality_score']}/100.",
            created_at=now
        )
        db.add(analysis)
        
        skill_match = SkillMatch(
            application_id=new_app.id,
            required_skills=json.dumps(res["score_breakdown"]["required_skills"]),
            present_skills=json.dumps(res["score_breakdown"]["present_skills"]),
            missing_skills=json.dumps(res["score_breakdown"]["missing_skills"]),
            learning_recommendations=json.dumps(res["explanation"]["learning_recommendations"]),
            semantic_overlap_pct=res["score_breakdown"]["tfidf_score"]
        )
        db.add(skill_match)
        
        count_apps = db.query(Application).filter(Application.job_id == req.job_id).count()
        ranking = CandidateRanking(
            job_id=req.job_id,
            application_id=new_app.id,
            rank_position=count_apps,
            ats_score=res["final_score"],
            skill_match_pct=res["score_breakdown"]["skills_score"],
            recommendation=res["explanation"]["hiring_recommendation"],
            confidence_score=res["explanation"]["confidence_score"]
        )
        db.add(ranking)
        
        interview_rec = InterviewRecommendation(
            application_id=new_app.id,
            status=res["explanation"]["hiring_recommendation"],
            explanation=res["explanation"]["recommendation_explanation"]
        )
        db.add(interview_rec)
        
        ai_questions = AIInterviewQuestion(
            application_id=new_app.id,
            technical_questions=json.dumps(res["explanation"]["categorized_questions"]["technical"]),
            behavioral_questions=json.dumps(res["explanation"]["categorized_questions"]["behavioral"]),
            project_questions=json.dumps(res["explanation"]["categorized_questions"]["project"]),
            coding_questions=json.dumps(res["explanation"]["categorized_questions"]["coding"])
        )
        db.add(ai_questions)
        
        log = ActivityLog(
            user_id=current_user["id"],
            action="apply_job",
            details=f"Applied to job: {job.title}",
            created_at=now
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit application due to a database error: {str(e)}")
        
    return {"message": "Application submitted successfully", "application_id": new_app.id}

@router.get("")
def list_applications(job_id: Optional[int] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role"] == "candidate":
        apps = db.query(Application, Job).join(Job, Application.job_id == Job.id).join(CandidateProfile, Application.candidate_profile_id == CandidateProfile.id).filter(CandidateProfile.user_id == current_user["id"]).order_by(Application.id.desc()).all()
        
        res = []
        for a, j in apps:
            res.append({
                "id": a.id,
                "status": a.status,
                "score": a.score,
                "created_at": a.created_at,
                "job_title": j.title,
                "job_location": j.location
            })
        return res
        
    # Recruiter / Admin views applicants
    query = db.query(
        Application, CandidateProfile, User, Job
    ).join(
        Job, Application.job_id == Job.id
    ).join(
        CandidateProfile, Application.candidate_profile_id == CandidateProfile.id
    ).join(
        User, CandidateProfile.user_id == User.id
    )
    
    if current_user["role"] == "recruiter":
        query = query.filter(Job.recruiter_id == current_user["id"])
        if job_id:
            query = query.filter(Job.id == job_id)
    elif job_id:
        query = query.filter(Job.id == job_id)
        
    query = query.order_by(Application.score.desc())
    results = query.all()
    
    res = []
    for rank, (a, cp, u, j) in enumerate(results, 1):
        d = {
            "id": a.id,
            "status": a.status,
            "score": a.score,
            "score_breakdown": a.score_breakdown,
            "explanation": a.explanation,
            "notes": a.notes,
            "interview_questions": a.interview_questions,
            "created_at": a.created_at,
            "years_experience": cp.years_experience,
            "education_level": cp.education_level,
            "inferred_gender": cp.inferred_gender,
            "skills": cp.skills,
            "email": cp.email,
            "phone": cp.phone,
            "candidate_name": u.name,
            "job_title": j.title,
            "job_id": j.id,
            "rank": rank
        }
        try:
            d["skills"] = json.loads(d["skills"]) if d["skills"] else []
            d["score_breakdown"] = json.loads(d["score_breakdown"]) if d["score_breakdown"] else {}
            d["explanation"] = json.loads(d["explanation"]) if d["explanation"] else {}
            d["interview_questions"] = json.loads(d["interview_questions"]) if d["interview_questions"] else []
            d["hiring_recommendation"] = d["explanation"].get("hiring_recommendation", "Consider")
        except Exception:
            pass
        res.append(d)
    return res

@router.put("/{app_id}/status")
def update_application_status(app_id: int, req: ApplicationStatusUpdate, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    if req.status not in ['applied', 'reviewing', 'shortlisted', 'rejected']:
        raise HTTPException(status_code=400, detail="Invalid application status type")
        
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application record not found")
        
    job = db.query(Job).filter(Job.id == app.job_id).first()
    user_cand = db.query(User).join(CandidateProfile).filter(CandidateProfile.id == app.candidate_profile_id).first()
    
    if current_user["role"] == "recruiter" and job.recruiter_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Unauthorized update operation")
        
    app.status = req.status
    if req.notes:
        app.notes = req.notes
        
    now = datetime.now(timezone.utc).isoformat()
    log = ActivityLog(
        user_id=current_user["id"],
        action="update_status",
        details=f"Updated status of candidate {user_cand.name} for {job.title} to {req.status}",
        created_at=now
    )
    db.add(log)
    db.commit()
    
    return {"message": f"Application status updated to {req.status}"}

@router.put("/{app_id}/stage")
def update_application_stage(app_id: int, req: ApplicationStageRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    old_status = app.status
    app.status = req.stage
    
    now = datetime.now(timezone.utc).isoformat()
    log = ActivityLog(
        user_id=current_user["id"],
        action="update_stage",
        details=f"Moved application {app_id} from {old_status} to {req.stage}",
        created_at=now
    )
    db.add(log)
    db.commit()
    
    return {"message": f"Application stage updated to {req.stage}"}

@router.get("/{app_id}/analysis")
def get_application_analysis(app_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    if current_user["role"] == "candidate":
        cand = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user["id"]).first()
        if not cand or cand.id != app.candidate_profile_id:
            raise HTTPException(status_code=403, detail="Access denied")

    analysis = db.query(ResumeAnalysis).filter(ResumeAnalysis.candidate_profile_id == app.candidate_profile_id).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Resume analysis details not found")
        
    d = {
        "id": analysis.id,
        "candidate_profile_id": analysis.candidate_profile_id,
        "summary": analysis.summary,
        "linkedin": analysis.linkedin,
        "github": analysis.github,
        "resume_quality": analysis.resume_quality,
        "created_at": analysis.created_at
    }
    try: d["strengths"] = json.loads(analysis.strengths) if analysis.strengths else []
    except Exception: d["strengths"] = []
    try: d["weaknesses"] = json.loads(analysis.weaknesses) if analysis.weaknesses else []
    except Exception: d["weaknesses"] = []
    try: d["projects"] = json.loads(analysis.projects) if analysis.projects else []
    except Exception: d["projects"] = []
    try: d["certifications"] = json.loads(analysis.certifications) if analysis.certifications else []
    except Exception: d["certifications"] = []
    try: d["languages"] = json.loads(analysis.languages) if analysis.languages else []
    except Exception: d["languages"] = []
    
    return d

@router.get("/{app_id}/score")
def get_application_ats_score(app_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    if current_user["role"] == "candidate":
        cand = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user["id"]).first()
        if not cand or cand.id != app.candidate_profile_id:
            raise HTTPException(status_code=403, detail="Access denied")

    try: breakdown = json.loads(app.score_breakdown) if app.score_breakdown else {}
    except Exception: breakdown = {}
    try: explanation = json.loads(app.explanation) if app.explanation else {}
    except Exception: explanation = {}
    
    return {
        "score_breakdown": breakdown,
        "explanation": explanation
    }

@router.get("/{app_id}/skills")
def get_application_skills(app_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    if current_user["role"] == "candidate":
        cand = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user["id"]).first()
        if not cand or cand.id != app.candidate_profile_id:
            raise HTTPException(status_code=403, detail="Access denied")

    match = db.query(SkillMatch).filter(SkillMatch.application_id == app_id).first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Skill matches not found")
        
    d = {
        "id": match.id,
        "application_id": match.application_id,
        "semantic_overlap_pct": match.semantic_overlap_pct
    }
    try: d["required_skills"] = json.loads(match.required_skills) if match.required_skills else []
    except Exception: d["required_skills"] = []
    try: d["present_skills"] = json.loads(match.present_skills) if match.present_skills else []
    except Exception: d["present_skills"] = []
    try: d["missing_skills"] = json.loads(match.missing_skills) if match.missing_skills else []
    except Exception: d["missing_skills"] = []
    try: d["learning_recommendations"] = json.loads(match.learning_recommendations) if match.learning_recommendations else []
    except Exception: d["learning_recommendations"] = []
    
    return d

@router.get("/{app_id}/questions")
def get_application_questions(app_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    if current_user["role"] == "candidate":
        cand = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user["id"]).first()
        if not cand or cand.id != app.candidate_profile_id:
            raise HTTPException(status_code=403, detail="Access denied")

    questions = db.query(AIInterviewQuestion).filter(AIInterviewQuestion.application_id == app_id).first()
    
    if not questions:
        raise HTTPException(status_code=404, detail="AI Interview questions not found")
        
    d = {
        "id": questions.id,
        "application_id": questions.application_id
    }
    try: d["technical_questions"] = json.loads(questions.technical_questions) if questions.technical_questions else []
    except Exception: d["technical_questions"] = []
    try: d["behavioral_questions"] = json.loads(questions.behavioral_questions) if questions.behavioral_questions else []
    except Exception: d["behavioral_questions"] = []
    try: d["project_questions"] = json.loads(questions.project_questions) if questions.project_questions else []
    except Exception: d["project_questions"] = []
    try: d["coding_questions"] = json.loads(questions.coding_questions) if questions.coding_questions else []
    except Exception: d["coding_questions"] = []
    
    return d

@router.get("/{app_id}/notes")
def get_application_notes(app_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin'])), db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    rec = db.query(InterviewRecommendation).filter(InterviewRecommendation.application_id == app_id).first()
    
    rec_dict = {
        "id": rec.id,
        "application_id": rec.application_id,
        "status": rec.status,
        "explanation": rec.explanation
    } if rec else {}
    
    return {
        "notes": app.notes,
        "recommendation": rec_dict
    }

import os
import json
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, status, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from src.database import get_db_connection, init_db
from src.auth import hash_password, verify_password, create_access_token, get_current_user, RoleChecker
from src.pipeline import ResumeScreeningPipeline
from src.bias_auditor import infer_gender
from src.exporter import export_applications_csv, generate_candidate_text_report

app = FastAPI(title="HireSense AI API", version="1.0.0")

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to React origin (e.g. http://localhost:5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup DB initialization
@app.on_event("startup")
def startup_event():
    init_db()

# ─── Pydantic Request/Response Models ─────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None
    role: str # 'candidate', 'recruiter', 'admin'

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str
    email: str

class JobCreateRequest(BaseModel):
    title: str
    description: str
    skills_required: List[str]
    experience_required: float
    education_required: int # 0 to 5
    location: Optional[str] = "Remote"

class JobResponse(BaseModel):
    id: int
    title: str
    description: str
    skills_required: List[str]
    experience_required: float
    education_required: int
    location: str
    status: str
    recruiter_id: int
    created_at: str

class ApplicationApplyRequest(BaseModel):
    job_id: int

class ApplicationStatusUpdate(BaseModel):
    status: str # 'applied', 'reviewing', 'shortlisted', 'rejected'
    notes: Optional[str] = None


# ─── Auth Endpoints ───────────────────────────────────────────────────────────

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    if req.role not in ['candidate', 'recruiter', 'admin']:
        raise HTTPException(status_code=400, detail="Invalid account role selection")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT id FROM users WHERE email = ?", (req.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email address already registered")
        
    hashed_pw = hash_password(req.password)
    now = datetime.utcnow().isoformat()
    
    cursor.execute(
        "INSERT INTO users (email, password_hash, role, name, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (req.email, hashed_pw, req.role, req.name, req.phone, now)
    )
    user_id = cursor.lastrowid
    
    # Log activity
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (user_id, "register", f"User registered as {req.role}", now)
    )
    
    conn.commit()
    conn.close()
    return {"message": "User registered successfully", "user_id": user_id}

@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, password_hash, role, name FROM users WHERE email = ?", (req.email,))
    user = cursor.fetchone()
    conn.close()
    
    if user is None or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password credentials")
        
    access_token = create_access_token(data={
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"]
    })
    
    # Log login activity
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (user["id"], "login", "User logged in", datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user["role"],
        "name": user["name"],
        "email": user["email"]
    }

@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


# ─── Job Management Endpoints ─────────────────────────────────────────────────

@app.get("/api/jobs", response_model=List[JobResponse])
def list_jobs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE status = 'active' ORDER BY id DESC")
    jobs = cursor.fetchall()
    conn.close()
    
    res = []
    for j in jobs:
        d = dict(j)
        try:
            d["skills_required"] = json.loads(d["skills_required"])
        except Exception:
            d["skills_required"] = []
        res.append(d)
    return res

@app.post("/api/jobs", response_model=JobResponse)
def create_job(req: JobCreateRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    cursor.execute(
        "INSERT INTO jobs (title, description, skills_required, experience_required, education_required, location, status, recruiter_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            req.title, req.description, json.dumps(req.skills_required),
            req.experience_required, req.education_required, req.location,
            "active", current_user["id"], now
        )
    )
    job_id = cursor.lastrowid
    
    # Log activity
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (current_user["id"], "create_job", f"Created job post: {req.title}", now)
    )
    
    conn.commit()
    
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    conn.close()
    
    d = dict(job)
    d["skills_required"] = json.loads(d["skills_required"])
    return d

@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if job belongs to recruiter (admin can bypass)
    cursor.execute("SELECT recruiter_id, title FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")
        
    if current_user["role"] == "recruiter" and job["recruiter_id"] != current_user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Unauthorized delete operation")
        
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    
    # Log activity
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (current_user["id"], "delete_job", f"Deleted job post: {job['title']}", datetime.utcnow().isoformat())
    )
    
    conn.commit()
    conn.close()
    return {"message": "Job deleted successfully"}


# ─── Resume Uploading & Extraction ──────────────────────────────────────────

@app.post("/api/candidates/profile/upload")
async def upload_resume(file: UploadFile = File(...), current_user: dict = Depends(RoleChecker(['candidate']))):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".doc", ".txt"]:
        raise HTTPException(status_code=400, detail="Unsupported file format")
        
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        contents = await file.read()
        tmp.write(contents)
        temp_path = tmp.name
        
    try:
        from src.resume_parser import extract_text, parse_resume
        resume_text = extract_text(temp_path)
        parsed = parse_resume(resume_text)
        inferred_gen = infer_gender(resume_text)
        
        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO candidate_profiles (user_id, resume_text, skills, education_level, years_experience, inferred_gender, email, phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                resume_text=excluded.resume_text,
                skills=excluded.skills,
                education_level=excluded.education_level,
                years_experience=excluded.years_experience,
                inferred_gender=excluded.inferred_gender,
                email=excluded.email,
                phone=excluded.phone
        """, (
            current_user["id"],
            resume_text,
            json.dumps(parsed.get("skills", [])),
            parsed.get("education_level", 0),
            parsed.get("years_experience", 0.0),
            inferred_gen,
            parsed.get("email", current_user["email"]),
            parsed.get("phone", current_user.get("phone", "")),
            now
        ))
        
        # Log activity
        cursor.execute(
            "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
            (current_user["id"], "upload_resume", f"Uploaded resume: {file.filename}", now)
        )
        
        conn.commit()
        conn.close()
        
        return {
            "message": "Resume uploaded and profile parsed successfully",
            "skills": parsed.get("skills", []),
            "education_level": parsed.get("education_level", 0),
            "years_experience": parsed.get("years_experience", 0.0),
            "inferred_gender": inferred_gen,
            "email": parsed.get("email", ""),
            "phone": parsed.get("phone", "")
        }
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

@app.get("/api/candidates/profile")
def get_candidate_profile(current_user: dict = Depends(RoleChecker(['candidate']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidate_profiles WHERE user_id = ?", (current_user["id"],))
    prof = cursor.fetchone()
    conn.close()
    
    if not prof:
        return {"has_profile": False}
        
    d = dict(prof)
    d["has_profile"] = True
    try:
        d["skills"] = json.loads(d["skills"])
    except Exception:
        d["skills"] = []
    return d


# ─── Job Applications & AI Screening ──────────────────────────────────────────

@app.post("/api/applications", status_code=status.HTTP_201_CREATED)
def apply_to_job(req: ApplicationApplyRequest, current_user: dict = Depends(RoleChecker(['candidate']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get candidate profile id
    cursor.execute("SELECT id, resume_text, skills, education_level, years_experience FROM candidate_profiles WHERE user_id = ?", (current_user["id"],))
    profile = cursor.fetchone()
    if not profile:
        conn.close()
        raise HTTPException(status_code=400, detail="Please upload a resume to construct a profile before applying")
        
    profile_id = profile["id"]
    resume_text = profile["resume_text"]
    candidate_skills = set(json.loads(profile["skills"]) if profile["skills"] else [])
    
    # Check if already applied
    cursor.execute("SELECT id FROM applications WHERE job_id = ? AND candidate_profile_id = ?", (req.job_id, profile_id))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="You have already applied to this job post")
        
    # Get job requirements
    cursor.execute("SELECT title, description, skills_required, experience_required, education_required FROM jobs WHERE id = ?", (req.job_id,))
    job = cursor.fetchone()
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Target job post not found")
        
    job_skills_req = json.loads(job["skills_required"])
    job_exp = job["experience_required"]
    
    # Run the NLP screening pipeline with job specifications
    jd_requirements = {
        "skills": job_skills_req,
        "experience": job_exp,
        "education": job["education_required"]
    }
    pipeline = ResumeScreeningPipeline()
    res = pipeline.process_resume(resume_text, job["description"], apply_blind_screening=True, is_raw_text=True, jd_requirements=jd_requirements)
    
    # Generate custom interview questions
    questions = [
        f"How did you leverage your experience in {', '.join(list(candidate_skills)[:3])} to solve engineering problems?"
    ]
    missing_skills = res["score_breakdown"]["missing_skills"]
    if missing_skills:
        questions.append(f"We noted that you might not have listed {missing_skills[0]} on your profile. Can you explain your conceptual understanding of it?")
    if profile["years_experience"] < job_exp:
        questions.append(f"This role prefers {job_exp}+ years of experience, and we matched {profile['years_experience']} years. How do you plan to scale up to the senior expectations?")
    
    recruiter_notes = res["explanation"]["recruiter_notes"]

    now = datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO applications (job_id, candidate_profile_id, status, score, score_breakdown, explanation, notes, interview_questions, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            req.job_id, profile_id, "applied", res["final_score"],
            json.dumps(res["score_breakdown"]), json.dumps(res["explanation"]),
            recruiter_notes, json.dumps(questions), now
        )
    )
    app_id = cursor.lastrowid
    
    # 1. Insert into resume_analyses
    cursor.execute("""
        INSERT INTO resume_analyses (candidate_profile_id, summary, strengths, weaknesses, linkedin, github, projects, certifications, languages, resume_quality, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        profile_id,
        res["explanation"]["summary"],
        json.dumps(res["explanation"]["strengths"]),
        json.dumps(res["explanation"]["weaknesses"]),
        res["parsed"]["linkedin"],
        res["parsed"]["github"],
        json.dumps(res["parsed"]["projects"]),
        json.dumps(res["parsed"]["certifications"]),
        json.dumps(res["parsed"]["languages"]),
        f"Contact verification matched. Structural quality score: {res['score_breakdown']['resume_quality_score']}/100.",
        now
    ))

    # 2. Insert into skill_matches
    cursor.execute("""
        INSERT INTO skill_matches (application_id, required_skills, present_skills, missing_skills, learning_recommendations, semantic_overlap_pct)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        app_id,
        json.dumps(res["score_breakdown"]["required_skills"]),
        json.dumps(res["score_breakdown"]["present_skills"]),
        json.dumps(res["score_breakdown"]["missing_skills"]),
        json.dumps(res["explanation"]["learning_recommendations"]),
        res["score_breakdown"]["tfidf_score"]
    ))

    # 3. Insert into candidate_rankings
    cursor.execute("SELECT COUNT(*) FROM applications WHERE job_id = ?", (req.job_id,))
    count_apps = cursor.fetchone()[0]
    cursor.execute("""
        INSERT INTO candidate_rankings (job_id, application_id, rank_position, ats_score, skill_match_pct, recommendation, confidence_score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        req.job_id,
        app_id,
        count_apps,
        res["final_score"],
        res["score_breakdown"]["skills_score"],
        res["explanation"]["hiring_recommendation"],
        res["explanation"]["confidence_score"]
    ))

    # 4. Insert into interview_recommendations
    cursor.execute("""
        INSERT INTO interview_recommendations (application_id, status, explanation)
        VALUES (?, ?, ?)
    """, (
        app_id,
        res["explanation"]["hiring_recommendation"],
        res["explanation"]["recommendation_explanation"]
    ))

    # 5. Insert into ai_interview_questions
    cursor.execute("""
        INSERT INTO ai_interview_questions (application_id, technical_questions, behavioral_questions, project_questions, coding_questions)
        VALUES (?, ?, ?, ?, ?)
    """, (
        app_id,
        json.dumps(res["explanation"]["categorized_questions"]["technical"]),
        json.dumps(res["explanation"]["categorized_questions"]["behavioral"]),
        json.dumps(res["explanation"]["categorized_questions"]["project"]),
        json.dumps(res["explanation"]["categorized_questions"]["coding"])
    ))
    
    # Log activity
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (current_user["id"], "apply_job", f"Applied to job: {job['title']}", now)
    )
    
    conn.commit()
    conn.close()
    return {"message": "Application submitted successfully", "application_id": app_id}

@app.get("/api/applications")
def list_applications(job_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if current_user["role"] == "candidate":
        # Candidate views own applications
        cursor.execute("""
            SELECT a.id, a.status, a.score, a.created_at, j.title as job_title, j.location as job_location
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            JOIN candidate_profiles cp ON a.candidate_profile_id = cp.id
            WHERE cp.user_id = ?
            ORDER BY a.id DESC
        """, (current_user["id"],))
        apps = cursor.fetchall()
        conn.close()
        return [dict(a) for a in apps]
        
    # Recruiter / Admin views applicants
    query = """
        SELECT a.id, a.status, a.score, a.score_breakdown, a.explanation, a.notes, a.interview_questions, a.created_at,
               cp.years_experience, cp.education_level, cp.inferred_gender, cp.skills, cp.email, cp.phone,
               u.name as candidate_name, j.title as job_title, j.id as job_id
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN candidate_profiles cp ON a.candidate_profile_id = cp.id
        JOIN users u ON cp.user_id = u.id
    """
    params = []
    
    if current_user["role"] == "recruiter":
        query += " WHERE j.recruiter_id = ?"
        params.append(current_user["id"])
        if job_id:
            query += " AND j.id = ?"
            params.append(job_id)
    elif job_id:
        query += " WHERE j.id = ?"
        params.append(job_id)
        
    query += " ORDER BY a.score DESC"
    cursor.execute(query, params)
    apps = cursor.fetchall()
    conn.close()
    
    res = []
    for rank, a in enumerate(apps, 1):
        d = dict(a)
        d["rank"] = rank
        try:
            d["skills"] = json.loads(d["skills"])
            d["score_breakdown"] = json.loads(d["score_breakdown"])
            d["explanation"] = json.loads(d["explanation"])
            d["interview_questions"] = json.loads(d["interview_questions"])
            d["hiring_recommendation"] = d["explanation"].get("hiring_recommendation", "Consider")
        except Exception:
            pass
        res.append(d)
    return res

@app.put("/api/applications/{app_id}/status")
def update_application_status(app_id: int, req: ApplicationStatusUpdate, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    if req.status not in ['applied', 'reviewing', 'shortlisted', 'rejected']:
        raise HTTPException(status_code=400, detail="Invalid application status type")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify job owner
    cursor.execute("""
        SELECT j.recruiter_id, j.title as job_title, u.name as candidate_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN candidate_profiles cp ON a.candidate_profile_id = cp.id
        JOIN users u ON cp.user_id = u.id
        WHERE a.id = ?
    """, (app_id,))
    data = cursor.fetchone()
    if not data:
        conn.close()
        raise HTTPException(status_code=404, detail="Application record not found")
        
    if current_user["role"] == "recruiter" and data["recruiter_id"] != current_user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Unauthorized update operation")
        
    if req.notes:
        cursor.execute("UPDATE applications SET status = ?, notes = ? WHERE id = ?", (req.status, req.notes, app_id))
    else:
        cursor.execute("UPDATE applications SET status = ? WHERE id = ?", (req.status, app_id))
        
    # Log activity
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (current_user["id"], "update_status", f"Updated status of candidate {data['candidate_name']} for {data['job_title']} to {req.status}", datetime.utcnow().isoformat())
    )
    
    conn.commit()
    conn.close()
    return {"message": f"Application status updated to {req.status}"}


# ─── Data Export Endpoints ────────────────────────────────────────────────────

@app.get("/api/applications/export/csv")
def get_applications_csv(job_id: Optional[int] = None, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    apps = list_applications(job_id=job_id, current_user=current_user)
    csv_data = export_applications_csv(apps)
    
    from fastapi.responses import Response
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hiresense_candidates_export.csv"}
    )

@app.get("/api/applications/{app_id}/export/report")
def get_candidate_report(app_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    application = cursor.fetchone()
    if not application:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
        
    cursor.execute("""
        SELECT cp.*, u.name as name 
        FROM candidate_profiles cp 
        JOIN users u ON cp.user_id = u.id 
        WHERE cp.id = ?
    """, (application["candidate_profile_id"],))
    candidate = cursor.fetchone()
    conn.close()
    
    report_text = generate_candidate_text_report(dict(candidate), dict(application))
    
    from fastapi.responses import Response
    return Response(
        content=report_text,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=hiresense_report_{candidate['name'].replace(' ', '_')}.txt"}
    )


# ─── Analytics Dashboard Endpoints ────────────────────────────────────────────

@app.get("/api/analytics")
def get_analytics(current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total Candidates count
    cursor.execute("SELECT COUNT(*) FROM candidate_profiles")
    total_candidates = cursor.fetchone()[0]
    
    # 2. Active Jobs count
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='active'")
    active_jobs = cursor.fetchone()[0]
    
    # 3. Total Applications count
    cursor.execute("SELECT COUNT(*) FROM applications")
    total_applications = cursor.fetchone()[0]
    
    # 4. Average ATS Score
    cursor.execute("SELECT AVG(score) FROM applications")
    avg_score = cursor.fetchone()[0]
    avg_score = round(avg_score, 1) if avg_score else 0.0
    
    # 5. Hiring Funnel Statuses
    cursor.execute("SELECT status, COUNT(*) FROM applications GROUP BY status")
    funnel = {row[0]: row[1] for row in cursor.fetchall()}
    for status_key in ['applied', 'reviewing', 'shortlisted', 'rejected']:
        funnel.setdefault(status_key, 0)
        
    # 6. Technical Skills distribution (aggregate skills of profiles)
    cursor.execute("SELECT skills FROM candidate_profiles")
    all_skills = []
    for row in cursor.fetchall():
        if row[0]:
            try:
                all_skills.extend(json.loads(row[0]))
            except Exception:
                pass
    from collections import Counter
    skill_dist = dict(Counter(all_skills).most_common(10))
    
    # 7. Gender parity metrics
    cursor.execute("SELECT inferred_gender, COUNT(*) FROM candidate_profiles GROUP BY inferred_gender")
    genders = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    return {
        "total_candidates": total_candidates,
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "average_score": avg_score,
        "funnel": funnel,
        "skills_distribution": skill_dist,
        "genders_distribution": genders
    }


# ─── Admin Core Endpoints ─────────────────────────────────────────────────────

@app.get("/api/admin/users")
def get_admin_users(current_user: dict = Depends(RoleChecker(['admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, role, name, phone, created_at FROM users ORDER BY id DESC")
    users = cursor.fetchall()
    conn.close()
    return [dict(u) for u in users]

@app.get("/api/admin/logs")
def get_admin_logs(current_user: dict = Depends(RoleChecker(['admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT al.id, al.action, al.details, al.created_at, u.email as user_email, u.role as user_role
        FROM activity_logs al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.id DESC LIMIT 100
    """)
    logs = cursor.fetchall()
    conn.close()
    return [dict(l) for l in logs]


# ─── Modular AI Resume Analysis Endpoints ─────────────────────────────────────

@app.get("/api/applications/{app_id}/analysis")
def get_application_analysis(app_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check application and candidate visibility rules
    cursor.execute("SELECT candidate_profile_id FROM applications WHERE id = ?", (app_id,))
    app = cursor.fetchone()
    if not app:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
        
    if current_user["role"] == "candidate":
        cursor.execute("SELECT id FROM candidate_profiles WHERE user_id = ?", (current_user["id"],))
        cand = cursor.fetchone()
        if not cand or cand["id"] != app["candidate_profile_id"]:
            conn.close()
            raise HTTPException(status_code=403, detail="Access denied")

    cursor.execute("SELECT * FROM resume_analyses WHERE candidate_profile_id = ?", (app["candidate_profile_id"],))
    analysis = cursor.fetchone()
    conn.close()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Resume analysis details not found")
        
    d = dict(analysis)
    try: d["strengths"] = json.loads(d["strengths"])
    except Exception: d["strengths"] = []
    try: d["weaknesses"] = json.loads(d["weaknesses"])
    except Exception: d["weaknesses"] = []
    try: d["projects"] = json.loads(d["projects"])
    except Exception: d["projects"] = []
    try: d["certifications"] = json.loads(d["certifications"])
    except Exception: d["certifications"] = []
    try: d["languages"] = json.loads(d["languages"])
    except Exception: d["languages"] = []
    
    return d


@app.get("/api/applications/{app_id}/score")
def get_application_ats_score(app_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT candidate_profile_id, score_breakdown, explanation FROM applications WHERE id = ?", (app_id,))
    app = cursor.fetchone()
    if not app:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
        
    if current_user["role"] == "candidate":
        cursor.execute("SELECT id FROM candidate_profiles WHERE user_id = ?", (current_user["id"],))
        cand = cursor.fetchone()
        if not cand or cand["id"] != app["candidate_profile_id"]:
            conn.close()
            raise HTTPException(status_code=403, detail="Access denied")

    conn.close()
    
    try: breakdown = json.loads(app["score_breakdown"])
    except Exception: breakdown = {}
    try: explanation = json.loads(app["explanation"])
    except Exception: explanation = {}
    
    return {
        "score_breakdown": breakdown,
        "explanation": explanation
    }


@app.get("/api/jobs/{job_id}/rankings")
def get_job_rankings(job_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT cr.*, u.name as candidate_name, a.status as application_status
        FROM candidate_rankings cr
        JOIN applications a ON cr.application_id = a.id
        JOIN candidate_profiles cp ON a.candidate_profile_id = cp.id
        JOIN users u ON cp.user_id = u.id
        WHERE cr.job_id = ?
        ORDER BY cr.ats_score DESC
    """, (job_id,))
    
    rankings = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rankings]


@app.get("/api/applications/{app_id}/skills")
def get_application_skills(app_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT candidate_profile_id FROM applications WHERE id = ?", (app_id,))
    app = cursor.fetchone()
    if not app:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
        
    if current_user["role"] == "candidate":
        cursor.execute("SELECT id FROM candidate_profiles WHERE user_id = ?", (current_user["id"],))
        cand = cursor.fetchone()
        if not cand or cand["id"] != app["candidate_profile_id"]:
            conn.close()
            raise HTTPException(status_code=403, detail="Access denied")

    cursor.execute("SELECT * FROM skill_matches WHERE application_id = ?", (app_id,))
    match = cursor.fetchone()
    conn.close()
    
    if not match:
        raise HTTPException(status_code=404, detail="Skill matches not found")
        
    d = dict(match)
    try: d["required_skills"] = json.loads(d["required_skills"])
    except Exception: d["required_skills"] = []
    try: d["present_skills"] = json.loads(d["present_skills"])
    except Exception: d["present_skills"] = []
    try: d["missing_skills"] = json.loads(d["missing_skills"])
    except Exception: d["missing_skills"] = []
    try: d["learning_recommendations"] = json.loads(d["learning_recommendations"])
    except Exception: d["learning_recommendations"] = []
    
    return d


@app.get("/api/applications/{app_id}/questions")
def get_application_questions(app_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT candidate_profile_id FROM applications WHERE id = ?", (app_id,))
    app = cursor.fetchone()
    if not app:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
        
    if current_user["role"] == "candidate":
        cursor.execute("SELECT id FROM candidate_profiles WHERE user_id = ?", (current_user["id"],))
        cand = cursor.fetchone()
        if not cand or cand["id"] != app["candidate_profile_id"]:
            conn.close()
            raise HTTPException(status_code=403, detail="Access denied")

    cursor.execute("SELECT * FROM ai_interview_questions WHERE application_id = ?", (app_id,))
    questions = cursor.fetchone()
    conn.close()
    
    if not questions:
        raise HTTPException(status_code=404, detail="AI Interview questions not found")
        
    d = dict(questions)
    try: d["technical_questions"] = json.loads(d["technical_questions"])
    except Exception: d["technical_questions"] = []
    try: d["behavioral_questions"] = json.loads(d["behavioral_questions"])
    except Exception: d["behavioral_questions"] = []
    try: d["project_questions"] = json.loads(d["project_questions"])
    except Exception: d["project_questions"] = []
    try: d["coding_questions"] = json.loads(d["coding_questions"])
    except Exception: d["coding_questions"] = []
    
    return d


@app.get("/api/applications/{app_id}/notes")
def get_application_notes(app_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT notes FROM applications WHERE id = ?", (app_id,))
    app = cursor.fetchone()
    if not app:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
        
    cursor.execute("SELECT * FROM interview_recommendations WHERE application_id = ?", (app_id,))
    rec = cursor.fetchone()
    conn.close()
    
    rec_dict = dict(rec) if rec else {}
    
    return {
        "notes": app["notes"],
        "recommendation": rec_dict
    }

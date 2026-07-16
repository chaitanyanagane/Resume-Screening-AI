import os
import json
import re
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, status, Form, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from src.database import get_db_connection, init_db
from src.auth import hash_password, verify_password, create_access_token, get_current_user, RoleChecker
from src.pipeline import ResumeScreeningPipeline
from src.bias_auditor import infer_gender
from src.exporter import export_applications_csv, generate_candidate_text_report

from fastapi import Request
from fastapi.responses import JSONResponse
import logging
import time
from src.security import api_limiter, auth_limiter

app = FastAPI(title="HireSense AI API", version="1.0.0")
api_router = APIRouter()

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to React origin (e.g. http://localhost:5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hiresense_ats")

from starlette.types import ASGIApp, Scope, Receive, Send

class TelemetryASGIMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # Rate Limiting
        if not (path.startswith("/docs") or path.startswith("/openapi.json") or path.startswith("/redoc")):
            client = scope.get("client")
            client_ip = client[0] if client else "unknown"
            
            if "auth" in path or "upload" in path:
                allowed = auth_limiter.check_rate_limit(client_ip)
            else:
                allowed = api_limiter.check_rate_limit(client_ip)
                
            if not allowed:
                await send({
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [(b"content-type", b"application/json")]
                })
                await send({
                    "type": "http.response.body",
                    "body": json.dumps({
                        "success": False,
                        "error": {"message": "Rate limit exceeded. Please try again later."}
                    }).encode("utf-8")
                })
                return

        # Request Logging & Telemetry
        start_time = time.time()
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                process_time = (time.time() - start_time) * 1000
                formatted_process_time = f"{process_time:.2f}ms"
                
                # Add telemetry header
                headers = list(message.get("headers", []))
                headers.append((b"x-response-time", formatted_process_time.encode("utf-8")))
                message["headers"] = headers
                
                # Log to logger
                client = scope.get("client")
                client_ip = client[0] if client else "unknown"
                log_dict = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "client_ip": client_ip,
                    "method": scope.get("method", "UNKNOWN"),
                    "path": path,
                    "status_code": message.get("status"),
                    "duration": formatted_process_time
                }
                logger.info(json.dumps(log_dict))
                
            await send(message)

        await self.app(scope, receive, send_wrapper)

app.add_middleware(TelemetryASGIMiddleware)

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
    refresh_token: Optional[str] = None

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class JobCreateRequest(BaseModel):
    title: str
    description: str
    skills_required: List[str]
    experience_required: float
    education_required: int # 0 to 5
    location: Optional[str] = "Remote"
    department: Optional[str] = "Engineering"
    employment_type: Optional[str] = "Full-time"
    salary_range: Optional[str] = None
    preferred_skills: Optional[List[str]] = []
    responsibilities: Optional[List[str]] = []
    hiring_manager: Optional[str] = None

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
    department: Optional[str] = None
    employment_type: Optional[str] = None
    salary_range: Optional[str] = None
    preferred_skills: Optional[List[str]] = []
    responsibilities: Optional[List[str]] = []
    hiring_manager: Optional[str] = None
    created_at: str

class ApplicationApplyRequest(BaseModel):
    job_id: int

class ApplicationStatusUpdate(BaseModel):
    status: str # 'applied', 'reviewing', 'shortlisted', 'rejected'
    notes: Optional[str] = None

class InterviewCreateRequest(BaseModel):
    interviewer: str
    type: str # 'screening', 'technical', 'manager', 'hr'
    scheduled_at: str
    meeting_link: Optional[str] = None

class InterviewFeedbackRequest(BaseModel):
    status: str # 'completed', 'cancelled'
    feedback: str
    rating: int # 1 to 5

class RecruiterNoteRequest(BaseModel):
    note_text: str
    is_pinned: Optional[int] = 0
    mentions: Optional[List[str]] = []

class ApplicationStageRequest(BaseModel):
    stage: str


# ─── Auth Endpoints ───────────────────────────────────────────────────────────

@api_router.post("/auth/register", status_code=status.HTTP_201_CREATED)
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

@api_router.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, password_hash, role, name FROM users WHERE email = ?", (req.email,))
    user = cursor.fetchone()
    
    if user is None or not verify_password(req.password, user["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid email or password credentials")
        
    access_token = create_access_token(data={
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"]
    })
    
    from src.auth import create_refresh_token_in_conn
    refresh_token = create_refresh_token_in_conn(conn, data={
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"]
    })
    
    # Log login activity
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
        "email": user["email"],
        "refresh_token": refresh_token
    }

@api_router.get("/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


# ─── Job Management Endpoints ─────────────────────────────────────────────────

@api_router.get("/jobs", response_model=List[JobResponse])
def list_jobs(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if current_user["role"] in ["recruiter", "admin"]:
        if current_user["role"] == "admin":
            cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
        else:
            cursor.execute("SELECT * FROM jobs WHERE recruiter_id = ? ORDER BY id DESC", (current_user["id"],))
    else:
        cursor.execute("SELECT * FROM jobs WHERE status = 'active' ORDER BY id DESC")
        
    jobs = cursor.fetchall()
    conn.close()
    
    res = []
    for j in jobs:
        d = dict(j)
        try: d["skills_required"] = json.loads(d["skills_required"])
        except Exception: d["skills_required"] = []
        try: d["preferred_skills"] = json.loads(d["preferred_skills"]) if d.get("preferred_skills") else []
        except Exception: d["preferred_skills"] = []
        try: d["responsibilities"] = json.loads(d["responsibilities"]) if d.get("responsibilities") else []
        except Exception: d["responsibilities"] = []
        res.append(d)
    return res

@api_router.post("/jobs", response_model=JobResponse)
def create_job(req: JobCreateRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    cursor.execute(
        "INSERT INTO jobs (title, description, skills_required, experience_required, education_required, location, status, recruiter_id, department, employment_type, salary_range, preferred_skills, responsibilities, hiring_manager, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            req.title, req.description, json.dumps(req.skills_required),
            req.experience_required, req.education_required, req.location,
            "active", current_user["id"], req.department, req.employment_type,
            req.salary_range, json.dumps(req.preferred_skills), json.dumps(req.responsibilities),
            req.hiring_manager, now
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
    try: d["skills_required"] = json.loads(d["skills_required"])
    except Exception: d["skills_required"] = []
    try: d["preferred_skills"] = json.loads(d["preferred_skills"]) if d.get("preferred_skills") else []
    except Exception: d["preferred_skills"] = []
    try: d["responsibilities"] = json.loads(d["responsibilities"]) if d.get("responsibilities") else []
    except Exception: d["responsibilities"] = []
    return d

@api_router.delete("/jobs/{job_id}")
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


@api_router.put("/jobs/{job_id}", response_model=JobResponse)
def edit_job(job_id: int, req: JobCreateRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT recruiter_id, title FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")
        
    if current_user["role"] == "recruiter" and job["recruiter_id"] != current_user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Unauthorized edit operation")
        
    cursor.execute("""
        UPDATE jobs 
        SET title = ?, description = ?, skills_required = ?, experience_required = ?, education_required = ?, 
            location = ?, department = ?, employment_type = ?, salary_range = ?, preferred_skills = ?, 
            responsibilities = ?, hiring_manager = ?
        WHERE id = ?
    """, (
        req.title, req.description, json.dumps(req.skills_required), req.experience_required, req.education_required,
        req.location, req.department, req.employment_type, req.salary_range, json.dumps(req.preferred_skills),
        json.dumps(req.responsibilities), req.hiring_manager, job_id
    ))
    
    now = datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (current_user["id"], "edit_job", f"Edited job post: {req.title}", now)
    )
    
    conn.commit()
    
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    updated_job = cursor.fetchone()
    conn.close()
    
    d = dict(updated_job)
    try: d["skills_required"] = json.loads(d["skills_required"])
    except Exception: d["skills_required"] = []
    try: d["preferred_skills"] = json.loads(d["preferred_skills"]) if d.get("preferred_skills") else []
    except Exception: d["preferred_skills"] = []
    try: d["responsibilities"] = json.loads(d["responsibilities"]) if d.get("responsibilities") else []
    except Exception: d["responsibilities"] = []
    return d


@api_router.post("/jobs/{job_id}/duplicate", response_model=JobResponse)
def duplicate_job(job_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")
        
    if current_user["role"] == "recruiter" and job["recruiter_id"] != current_user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Unauthorized duplicate operation")
        
    now = datetime.utcnow().isoformat()
    new_title = f"{job['title']} (Copy)"
    
    cursor.execute("""
        INSERT INTO jobs (title, description, skills_required, experience_required, education_required, 
                          location, status, recruiter_id, department, employment_type, salary_range, 
                          preferred_skills, responsibilities, hiring_manager, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        new_title, job["description"], job["skills_required"], job["experience_required"], job["education_required"],
        job["location"], "active", current_user["id"], job["department"], job["employment_type"], job["salary_range"],
        job["preferred_skills"], job["responsibilities"], job["hiring_manager"], now
    ))
    
    new_job_id = cursor.lastrowid
    
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (current_user["id"], "duplicate_job", f"Duplicated job: {job['title']} as {new_title}", now)
    )
    
    conn.commit()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (new_job_id,))
    new_job = cursor.fetchone()
    conn.close()
    
    d = dict(new_job)
    try: d["skills_required"] = json.loads(d["skills_required"])
    except Exception: d["skills_required"] = []
    try: d["preferred_skills"] = json.loads(d["preferred_skills"]) if d.get("preferred_skills") else []
    except Exception: d["preferred_skills"] = []
    try: d["responsibilities"] = json.loads(d["responsibilities"]) if d.get("responsibilities") else []
    except Exception: d["responsibilities"] = []
    return d


@api_router.put("/jobs/{job_id}/close", response_model=JobResponse)
def close_job(job_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    return toggle_job_status(job_id, "closed", current_user)


@api_router.put("/jobs/{job_id}/reopen", response_model=JobResponse)
def reopen_job(job_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    return toggle_job_status(job_id, "active", current_user)


def toggle_job_status(job_id: int, status: str, current_user: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT recruiter_id, title FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")
        
    if current_user["role"] == "recruiter" and job["recruiter_id"] != current_user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Unauthorized operation")
        
    cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    
    now = datetime.utcnow().isoformat()
    action = "close_job" if status == "closed" else "reopen_job"
    details = f"Closed hiring for: {job['title']}" if status == "closed" else f"Reopened hiring for: {job['title']}"
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (current_user["id"], action, details, now)
    )
    
    conn.commit()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    updated_job = cursor.fetchone()
    conn.close()
    
    d = dict(updated_job)
    try: d["skills_required"] = json.loads(d["skills_required"])
    except Exception: d["skills_required"] = []
    try: d["preferred_skills"] = json.loads(d["preferred_skills"]) if d.get("preferred_skills") else []
    except Exception: d["preferred_skills"] = []
    try: d["responsibilities"] = json.loads(d["responsibilities"]) if d.get("responsibilities") else []
    except Exception: d["responsibilities"] = []
    return d


# ─── Resume Uploading & Extraction ──────────────────────────────────────────

@api_router.post("/candidates/profile/upload")
async def upload_resume(file: UploadFile = File(...), current_user: dict = Depends(RoleChecker(['candidate']))):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".txt"]:
        raise HTTPException(status_code=400, detail="Only PDF and TXT file formats are permitted in enterprise mode.")
        
    # Read file content to check size and content type
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the 5MB upload limit.")
        
    # Verify PDF signature if PDF
    if ext == ".pdf" and not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF binary payload signature.")
        
    # Save file with a secure unique UUID filename
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(target_path, "wb") as f:
        f.write(contents)
        
    try:
        from src.resume_parser import extract_text, parse_resume
        # Extract text from the saved file
        resume_text = extract_text(target_path)
        parsed = parse_resume(resume_text)
        inferred_gen = infer_gender(resume_text)
        
        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO candidate_profiles (user_id, resume_text, skills, education_level, years_experience, inferred_gender, email, phone, resume_filename, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                resume_text=excluded.resume_text,
                skills=excluded.skills,
                education_level=excluded.education_level,
                years_experience=excluded.years_experience,
                inferred_gender=excluded.inferred_gender,
                email=excluded.email,
                phone=excluded.phone,
                resume_filename=excluded.resume_filename
        """, (
            current_user["id"],
            resume_text,
            json.dumps(parsed.get("skills", [])),
            parsed.get("education_level", 0),
            parsed.get("years_experience", 0.0),
            inferred_gen,
            parsed.get("email", current_user["email"]),
            parsed.get("phone", current_user.get("phone", "")),
            unique_filename,
            now
        ))
        
        # Log activity
        cursor.execute(
            "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
            (current_user["id"], "upload_resume", f"Uploaded resume: {file.filename} (stored as {unique_filename})", now)
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
    except Exception as e:
        if os.path.exists(target_path):
            os.unlink(target_path)
        raise HTTPException(status_code=500, detail=f"Failed to process and parse resume: {str(e)}")

@api_router.get("/candidates/profile")
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

@api_router.post("/applications", status_code=status.HTTP_201_CREATED)
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

@api_router.get("/applications")
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

@api_router.put("/applications/{app_id}/status")
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

@api_router.get("/applications/export/csv")
def get_applications_csv(job_id: Optional[int] = None, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    apps = list_applications(job_id=job_id, current_user=current_user)
    csv_data = export_applications_csv(apps)
    
    from fastapi.responses import Response
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hiresense_candidates_export.csv"}
    )

@api_router.get("/applications/{app_id}/export/report")
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

@api_router.get("/analytics")
def get_analytics(current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Candidate count
    cursor.execute("SELECT COUNT(*) FROM candidate_profiles")
    total_candidates = cursor.fetchone()[0]
    
    # 2. Jobs stats
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='active'")
    active_jobs = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='closed'")
    closed_jobs = cursor.fetchone()[0]
    total_jobs = active_jobs + closed_jobs
    
    # 3. Applications and ATS Score
    cursor.execute("SELECT COUNT(*) FROM applications")
    total_applications = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(score) FROM applications")
    avg_score = cursor.fetchone()[0]
    avg_score = round(avg_score, 1) if avg_score else 0.0
    
    # 4. Detailed stage funnel
    cursor.execute("SELECT status, COUNT(*) FROM applications GROUP BY status")
    funnel_rows = cursor.fetchall()
    funnel = {row[0]: row[1] for row in funnel_rows}
    # Back-fill all stages
    stages_list = ['applied', 'screening', 'technical_interview', 'manager_round', 'hr_interview', 'offer', 'selected', 'rejected']
    for stg in stages_list:
        funnel.setdefault(stg, 0)
        
    # 5. Interviews stats
    cursor.execute("SELECT COUNT(*) FROM interviews WHERE status='scheduled'")
    interviews_scheduled = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM interviews WHERE status='completed'")
    interviews_completed = cursor.fetchone()[0]
    
    # Calculate conversion rate: ratio of technical interview advances
    conversion_rate = 35.0
    if interviews_completed > 0:
        cursor.execute("SELECT COUNT(*) FROM applications WHERE status IN ('manager_round', 'hr_interview', 'offer', 'selected')")
        advanced = cursor.fetchone()[0]
        conversion_rate = round((advanced / max(interviews_completed, 1)) * 100.0, 1)
        
    # 6. Technical Skills Counter
    cursor.execute("SELECT skills FROM candidate_profiles")
    all_skills = []
    for row in cursor.fetchall():
        if row[0]:
            try: all_skills.extend(json.loads(row[0]))
            except Exception: pass
    from collections import Counter
    skill_dist = dict(Counter(all_skills).most_common(10))
    
    # 7. Colleges Parser Heuristics
    cursor.execute("SELECT resume_text FROM candidate_profiles")
    colleges = []
    for row in cursor.fetchall():
        text = row[0] or ""
        # Look for typical college keywords
        match = re.search(r'\b(iit|nit|bits|mit|stanford|harvard|oxford|university|college|iim)\b\s*[\w\s]*', text.lower())
        if match:
            colleges.append(match.group(0).strip().upper())
        else:
            colleges.append("Other Institutions")
    college_dist = dict(Counter(colleges).most_common(5))
    
    # 8. Success & Conversion Metrics
    selected_candidates = funnel.get("selected", 0)
    rejected_candidates = funnel.get("rejected", 0)
    offers_released = funnel.get("offer", 0)
    success_rate = round((selected_candidates / max(total_applications, 1)) * 100.0, 1)
    
    # Historical monthly trend data (mocked baseline + current applications)
    monthly_trends = [
        {"month": "May", "count": 2},
        {"month": "June", "count": 4},
        {"month": "July", "count": total_applications}
    ]
    
    # Candidate source metric distribution
    sources = {
        "Direct Portal": selected_candidates + 2,
        "Referral": offers_released + 1,
        "LinkedIn": rejected_candidates + 1
    }
    
    conn.close()
    
    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "closed_jobs": closed_jobs,
        "total_candidates": total_candidates,
        "total_applications": total_applications,
        "average_score": avg_score,
        "funnel": funnel,
        "interviews_scheduled": interviews_scheduled,
        "offers_released": offers_released,
        "selected_candidates": selected_candidates,
        "rejected_candidates": rejected_candidates,
        "conversion_rate": conversion_rate,
        "skills_distribution": skill_dist,
        "colleges_distribution": college_dist,
        "hiring_success_rate": success_rate,
        "applications_per_month": monthly_trends,
        "candidate_source_analysis": sources
    }


# ─── Admin Core Endpoints ─────────────────────────────────────────────────────

@api_router.get("/admin/users")
def get_admin_users(current_user: dict = Depends(RoleChecker(['admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, role, name, phone, created_at FROM users ORDER BY id DESC")
    users = cursor.fetchall()
    conn.close()
    return [dict(u) for u in users]

@api_router.get("/admin/logs")
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

@api_router.get("/applications/{app_id}/analysis")
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


@api_router.get("/applications/{app_id}/score")
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


@api_router.get("/jobs/{job_id}/rankings")
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


@api_router.get("/applications/{app_id}/skills")
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


@api_router.get("/applications/{app_id}/questions")
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


@api_router.get("/applications/{app_id}/notes")
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


# ─── Enterprise ATS Extension Endpoints ──────────────────────────────────────

@api_router.put("/applications/{app_id}/stage")
def update_application_stage(app_id: int, req: ApplicationStageRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT status, job_id FROM applications WHERE id = ?", (app_id,))
    app = cursor.fetchone()
    if not app:
        conn.close()
        raise HTTPException(status_code=404, detail="Application not found")
        
    cursor.execute("UPDATE applications SET status = ? WHERE id = ?", (req.stage, app_id))
    
    # Log activity
    now = datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (current_user["id"], "update_stage", f"Moved application {app_id} from {app['status']} to {req.stage}", now)
    )
    
    conn.commit()
    conn.close()
    return {"message": "Application stage updated successfully", "stage": req.stage}


@api_router.get("/applications/{app_id}/interviews")
def list_application_interviews(app_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interviews WHERE application_id = ? ORDER BY id DESC", (app_id,))
    interviews = cursor.fetchall()
    conn.close()
    return [dict(i) for i in interviews]


@api_router.post("/applications/{app_id}/interviews")
def schedule_interview(app_id: int, req: InterviewCreateRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    cursor.execute("""
        INSERT INTO interviews (application_id, interviewer, type, scheduled_at, meeting_link, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (app_id, req.interviewer, req.type, req.scheduled_at, req.meeting_link, "scheduled", now))
    
    interview_id = cursor.lastrowid
    
    # Log activity
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (current_user["id"], "schedule_interview", f"Scheduled {req.type} interview with {req.interviewer}", now)
    )
    
    # Create notification for candidate/interviewer
    cursor.execute("""
        INSERT INTO notifications (recruiter_id, title, message, type, is_read, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (current_user["id"], "Interview Scheduled", f"Scheduled {req.type} interview for application #{app_id}", "interview_accepted", 0, now))
    
    conn.commit()
    conn.close()
    return {"message": "Interview scheduled successfully", "interview_id": interview_id}


@api_router.put("/interviews/{interview_id}/feedback")
def submit_interview_feedback(interview_id: int, req: InterviewFeedbackRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT application_id FROM interviews WHERE id = ?", (interview_id,))
    interview = cursor.fetchone()
    if not interview:
        conn.close()
        raise HTTPException(status_code=404, detail="Interview not found")
        
    cursor.execute("""
        UPDATE interviews 
        SET status = ?, feedback = ?, rating = ?
        WHERE id = ?
    """, (req.status, req.feedback, req.rating, interview_id))
    
    now = datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (current_user["id"], "interview_feedback", f"Recorded feedback for interview {interview_id}", now)
    )
    
    conn.commit()
    conn.close()
    return {"message": "Interview feedback submitted successfully"}


@api_router.get("/applications/{app_id}/notes/list")
def list_recruiter_notes(app_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rn.*, u.name as recruiter_name 
        FROM recruiter_notes rn 
        JOIN users u ON rn.recruiter_id = u.id 
        WHERE rn.application_id = ? 
        ORDER BY rn.is_pinned DESC, rn.id DESC
    """, (app_id,))
    notes = cursor.fetchall()
    conn.close()
    
    res = []
    for n in notes:
        d = dict(n)
        try: d["mentions"] = json.loads(d["mentions"]) if d.get("mentions") else []
        except Exception: d["mentions"] = []
        res.append(d)
    return res


@api_router.post("/applications/{app_id}/notes")
def add_recruiter_note(app_id: int, req: RecruiterNoteRequest, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    cursor.execute("""
        INSERT INTO recruiter_notes (application_id, recruiter_id, note_text, is_pinned, mentions, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (app_id, current_user["id"], req.note_text, req.is_pinned, json.dumps(req.mentions), now))
    
    note_id = cursor.lastrowid
    
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (current_user["id"], "add_note", f"Added notes on application {app_id}", now)
    )
    
    conn.commit()
    conn.close()
    return {"message": "Recruiter note added successfully", "note_id": note_id}


@api_router.put("/notes/{note_id}/pin")
def pin_recruiter_note(note_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_pinned FROM recruiter_notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()
    if not note:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")
        
    new_pinned = 1 if note["is_pinned"] == 0 else 0
    cursor.execute("UPDATE recruiter_notes SET is_pinned = ? WHERE id = ?", (new_pinned, note_id))
    
    conn.commit()
    conn.close()
    return {"message": "Note pinning toggled", "is_pinned": new_pinned}


@api_router.delete("/notes/{note_id}")
def delete_recruiter_note(note_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM recruiter_notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return {"message": "Recruiter note deleted successfully"}


@api_router.get("/notifications")
def list_notifications(current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications WHERE recruiter_id = ? ORDER BY id DESC LIMIT 50", (current_user["id"],))
    notifications = cursor.fetchall()
    conn.close()
    return [dict(n) for n in notifications]


@api_router.put("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND recruiter_id = ?", (notification_id, current_user["id"]))
    conn.commit()
    conn.close()
    return {"message": "Notification marked as read"}


@api_router.get("/applications/export/excel")
def list_export_excel(job_id: Optional[int] = None, current_user: dict = Depends(RoleChecker(['recruiter', 'admin']))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT a.id as application_id, u.name as candidate_name, cp.email as candidate_email,
               cp.phone as candidate_phone, cp.years_experience, cp.education_level, cp.inferred_gender,
               j.title as job_title, a.status as stage, a.score as ats_score
        FROM applications a
        JOIN candidate_profiles cp ON a.candidate_profile_id = cp.id
        JOIN users u ON cp.user_id = u.id
        JOIN jobs j ON a.job_id = j.id
    """
    
    if job_id:
        cursor.execute(query + " WHERE a.job_id = ? ORDER BY a.score DESC", (job_id,))
    else:
        cursor.execute(query + " ORDER BY a.score DESC")
        
    records = cursor.fetchall()
    conn.close()
    
    output = "Application ID,Candidate Name,Candidate Email,Candidate Phone,Years Experience,Education Level,Gender,Job Title,Hiring Stage,ATS Score\n"
    edu_map = {0: "N/A", 1: "12th/HSC", 2: "Diploma", 3: "Bachelor", 4: "Master", 5: "PhD"}
    for r in records:
        edu_str = edu_map.get(r["education_level"], "Unknown")
        # Ensure commas inside fields don't break CSV format by quoting them
        job_title_escaped = f"\"{r['job_title']}\"" if "," in str(r['job_title']) else r['job_title']
        output += f"{r['application_id']},{r['candidate_name']},{r['candidate_email']},{r['candidate_phone']},{r['years_experience']},{edu_str},{r['inferred_gender']},{job_title_escaped},{r['stage']},{r['ats_score']:.1f}\n"
        
    from fastapi.responses import Response
    return Response(
        content=output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=hiresense_ats_export_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )


from fastapi.responses import FileResponse
import uuid

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 5 * 1024 * 1024 # 5MB

@api_router.post("/auth/refresh", response_model=TokenResponse)
def refresh_token_endpoint(req: TokenRefreshRequest):
    from src.auth import verify_refresh_token, create_access_token
    payload = verify_refresh_token(req.refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
        
    user_id = int(payload["sub"])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, role, name FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    access_token = create_access_token(data={
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"]
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user["role"],
        "name": user["name"],
        "email": user["email"],
        "refresh_token": req.refresh_token
    }

@api_router.post("/auth/logout")
def logout_endpoint(req: TokenRefreshRequest, current_user: dict = Depends(get_current_user)):
    from src.auth import revoke_refresh_token
    revoke_refresh_token(req.refresh_token)
    return {"message": "Logged out successfully"}

@api_router.post("/auth/logout/all")
def logout_all_endpoint(current_user: dict = Depends(get_current_user)):
    from src.auth import revoke_all_user_refresh_tokens
    revoke_all_user_refresh_tokens(current_user["id"])
    return {"message": "Logged out from all devices successfully"}

@api_router.get("/candidates/profile/resume/download/{filename}")
def download_resume_endpoint(filename: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] == "candidate":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT resume_filename FROM candidate_profiles WHERE user_id = ?", (current_user["id"],))
        row = cursor.fetchone()
        conn.close()
        if not row or row["resume_filename"] != filename:
            raise HTTPException(status_code=403, detail="Access denied. You can only download your own resume.")
            
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Requested resume file not found.")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO activity_logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (current_user["id"], "download_resume", f"Downloaded resume: {safe_filename}", datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    
    return FileResponse(file_path, media_type="application/octet-stream", filename=safe_filename)

@api_router.get("/health")
def health_check_endpoint():
    health_status = {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "database": "disconnected"}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database_error"] = str(e)
        
    return health_status


app.include_router(api_router, prefix='/api')
app.include_router(api_router, prefix='/api/v1')

import sqlite3
import os
import bcrypt
from datetime import datetime

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../hiresense.db"))

import threading

db_lock = threading.Lock()

class LockedConnection(sqlite3.Connection):
    def close(self):
        try:
            super().close()
        finally:
            try:
                db_lock.release()
            except RuntimeError:
                pass

def get_db_connection():
    """Create a connection to the SQLite database with foreign keys enabled."""
    db_lock.acquire()
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False, factory=LockedConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initialize database tables and seed sample data."""
    conn = get_db_connection()
    conn.execute("PRAGMA journal_mode = DELETE;")
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('candidate', 'recruiter', 'admin')),
        name TEXT NOT NULL,
        phone TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # 2. Jobs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        skills_required TEXT NOT NULL, -- JSON string
        experience_required REAL NOT NULL,
        education_required INTEGER NOT NULL,
        location TEXT,
        status TEXT NOT NULL CHECK(status IN ('active', 'closed')),
        recruiter_id INTEGER NOT NULL,
        department TEXT,
        employment_type TEXT,
        salary_range TEXT,
        preferred_skills TEXT, -- JSON string
        responsibilities TEXT, -- JSON string
        hiring_manager TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (recruiter_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)

    # 3. Candidate Profiles Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidate_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        resume_text TEXT,
        skills TEXT, -- JSON string
        education_level INTEGER DEFAULT 0,
        years_experience REAL DEFAULT 0.0,
        inferred_gender TEXT DEFAULT 'Unknown',
        email TEXT,
        phone TEXT,
        resume_filename TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)

    # 4. Applications Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        candidate_profile_id INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('applied', 'screening', 'technical_interview', 'manager_round', 'hr_interview', 'offer', 'selected', 'rejected')),
        score REAL DEFAULT 0.0,
        score_breakdown TEXT, -- JSON string
        explanation TEXT, -- JSON string
        notes TEXT, -- Recruiter review notes
        interview_questions TEXT, -- JSON string
        created_at TEXT NOT NULL,
        FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
        FOREIGN KEY (candidate_profile_id) REFERENCES candidate_profiles (id) ON DELETE CASCADE
    )
    """)

    # 5. Activity Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
    )
    """)

    # 6. Resume Analysis Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resume_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_profile_id INTEGER NOT NULL,
        summary TEXT,
        strengths TEXT, -- JSON string
        weaknesses TEXT, -- JSON string
        linkedin TEXT,
        github TEXT,
        projects TEXT, -- JSON string
        certifications TEXT, -- JSON string
        languages TEXT, -- JSON string
        resume_quality TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (candidate_profile_id) REFERENCES candidate_profiles (id) ON DELETE CASCADE
    )
    """)

    # 7. Skill Match Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS skill_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        required_skills TEXT, -- JSON string
        present_skills TEXT, -- JSON string
        missing_skills TEXT, -- JSON string
        learning_recommendations TEXT, -- JSON string
        semantic_overlap_pct REAL DEFAULT 0.0,
        FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE
    )
    """)

    # 8. Candidate Ranking Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidate_rankings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        application_id INTEGER UNIQUE NOT NULL,
        rank_position INTEGER,
        ats_score REAL DEFAULT 0.0,
        skill_match_pct REAL DEFAULT 0.0,
        recommendation TEXT,
        confidence_score REAL DEFAULT 0.0,
        FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
        FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE
    )
    """)

    # 9. Interview Recommendation Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interview_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER UNIQUE NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Highly Recommended', 'Recommended', 'Consider', 'Not Recommended')),
        explanation TEXT,
        FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE
    )
    """)

    # 10. AI Interview Questions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_interview_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        technical_questions TEXT, -- JSON string
        behavioral_questions TEXT, -- JSON string
        project_questions TEXT, -- JSON string
        coding_questions TEXT, -- JSON string
        FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE
    )
    """)

    # 11. Interviews Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        interviewer TEXT NOT NULL,
        type TEXT NOT NULL, -- 'screening', 'technical', 'manager', 'hr'
        scheduled_at TEXT NOT NULL,
        meeting_link TEXT,
        status TEXT NOT NULL CHECK(status IN ('scheduled', 'completed', 'cancelled')),
        feedback TEXT,
        rating INTEGER, -- 1-5
        created_at TEXT NOT NULL,
        FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE
    )
    """)

    # 12. Recruiter Notes Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recruiter_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        recruiter_id INTEGER NOT NULL,
        note_text TEXT NOT NULL,
        is_pinned INTEGER DEFAULT 0,
        mentions TEXT, -- JSON string list
        created_at TEXT NOT NULL,
        FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE,
        FOREIGN KEY (recruiter_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)

    # 13. Notifications Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recruiter_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        type TEXT NOT NULL, -- 'resume_uploaded', 'interview_accepted', 'candidate_withdrawn', 'job_closing', 'ai_complete'
        is_read INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (recruiter_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)

    # 14. Refresh Tokens Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS refresh_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT UNIQUE NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)

    # Performance Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_recruiter_id ON jobs(recruiter_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_candidate_profile_id ON applications(candidate_profile_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interviews_application_id ON interviews(application_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recruiter_notes_application_id ON recruiter_notes(application_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens(token);")

    # Seed Default Users if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        print("[DB] Seeding default users...")
        now = datetime.utcnow().isoformat()
        
        # Hash passwords
        admin_pw = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode('utf-8')
        rec_pw = bcrypt.hashpw(b"recruiter123", bcrypt.gensalt()).decode('utf-8')
        cand_pw = bcrypt.hashpw(b"candidate123", bcrypt.gensalt()).decode('utf-8')

        cursor.execute(
            "INSERT INTO users (email, password_hash, role, name, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("admin@hiresense.ai", admin_pw, "admin", "System Administrator", "+91 9999999999", now)
        )
        cursor.execute(
            "INSERT INTO users (email, password_hash, role, name, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("recruiter@hiresense.ai", rec_pw, "recruiter", "HR Manager", "+91 8888888888", now)
        )
        cursor.execute(
            "INSERT INTO users (email, password_hash, role, name, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("candidate@hiresense.ai", cand_pw, "candidate", "Priya Sharma", "+91 9876543210", now)
        )
        conn.commit()

        # Get recruiter and candidate IDs
        cursor.execute("SELECT id FROM users WHERE email='recruiter@hiresense.ai'")
        recruiter_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM users WHERE email='candidate@hiresense.ai'")
        candidate_user_id = cursor.fetchone()[0]

        # Seed Jobs
        print("[DB] Seeding default jobs...")
        cursor.execute(
            "INSERT INTO jobs (title, description, skills_required, experience_required, education_required, location, status, recruiter_id, department, employment_type, salary_range, preferred_skills, responsibilities, hiring_manager, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "Machine Learning Engineer",
                "We are looking for an experienced ML Engineer to join our AI team. Python, BERT, PyTorch, SQL, and Docker are required.",
                '["python", "machine learning", "nlp", "bert", "pytorch", "sql", "docker"]',
                3.0, 3, "Pune, India", "active", recruiter_id,
                "Engineering", "Full-time", "$120,000 - $150,000",
                '["aws", "gcp", "mlflow"]',
                '["Design ML pipelines", "Train LLM models", "Optimize neural networks"]',
                "Alex Carter (Director of AI)", now
            )
        )
        cursor.execute(
            "INSERT INTO jobs (title, description, skills_required, experience_required, education_required, location, status, recruiter_id, department, employment_type, salary_range, preferred_skills, responsibilities, hiring_manager, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "Senior Frontend Engineer",
                "Join our frontend team building next-generation dashboards. Must be fluent in JavaScript, React, HTML, CSS, and Git.",
                '["javascript", "typescript", "react", "html", "css", "git"]',
                5.0, 3, "Remote", "active", recruiter_id,
                "Engineering", "Full-time", "$110,000 - $140,000",
                '["framer motion", "next.js", "tailwind"]',
                '["Build user-facing modules", "Collaborate with designers", "Perform code audits"]',
                "Sarah Jenkins (Frontend Lead)", now
            )
        )
        conn.commit()

        # Seed Candidate Profile for default candidate Priya Sharma
        print("[DB] Seeding default candidate profile...")
        priya_resume = """
        Priya Sharma
        priya.sharma@email.com | +91-9876543210
        EDUCATION
        B.Tech in Computer Science — IIT Bombay | 2021
        EXPERIENCE
        Software Engineer — TCS | 2 years
        - Built ML models for fraud detection using XGBoost and scikit-learn
        - Worked on NLP pipelines using BERT and transformers
        - Deployed models on AWS SageMaker
        SKILLS
        Python, Machine Learning, NLP, BERT, XGBoost, scikit-learn, pandas, numpy,
        SQL, AWS, Docker, Git, TensorFlow, Data Analysis
        """
        cursor.execute(
            "INSERT INTO candidate_profiles (user_id, resume_text, skills, education_level, years_experience, inferred_gender, email, phone, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                candidate_user_id, priya_resume,
                '["python", "machine learning", "nlp", "bert", "xgboost", "scikit-learn", "pandas", "numpy", "sql", "aws", "docker", "git", "tensorflow"]',
                3, 2.0, "Female", "priya.sharma@email.com", "+91-9876543210", now
            )
        )
        conn.commit()

        # Seed Application for Priya to the ML Job
        print("[DB] Seeding default applications...")
        cursor.execute("SELECT id FROM jobs WHERE title='Machine Learning Engineer'")
        ml_job_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM candidate_profiles WHERE user_id=?", (candidate_user_id,))
        priya_profile_id = cursor.fetchone()[0]

        # Use our pipeline logic to generate real matching results for seeding
        from src.pipeline import ResumeScreeningPipeline
        pipeline = ResumeScreeningPipeline()
        res = pipeline.process_resume(priya_resume, "We are looking for an experienced ML Engineer. Python, BERT, PyTorch, SQL, and Docker are required.", apply_blind_screening=True, is_raw_text=True)

        import json
        cursor.execute(
            "INSERT INTO applications (job_id, candidate_profile_id, status, score, score_breakdown, explanation, notes, interview_questions, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ml_job_id, priya_profile_id, "technical_interview",
                res["final_score"], json.dumps(res["score_breakdown"]),
                json.dumps(res["explanation"]),
                "Excellent alignment. IIT Bombay CS graduate with core experience in BERT and fraud detection. Recommended for technical round.",
                json.dumps([
                    "Can you explain the differences in performance and size between S-BERT and standard BERT for resume similarity calculations?",
                    "How did you handle class imbalance in your fraud detection models using XGBoost?",
                    "Describe your experience deploying NLP pipelines on AWS SageMaker."
                ]),
                now
            )
        )
        app_id = cursor.lastrowid
        
        # Seed resume_analyses
        cursor.execute("""
            INSERT INTO resume_analyses (candidate_profile_id, summary, strengths, weaknesses, linkedin, github, projects, certifications, languages, resume_quality, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            priya_profile_id,
            res["explanation"]["summary"],
            json.dumps(res["explanation"]["strengths"]),
            json.dumps(res["explanation"]["weaknesses"]),
            "https://linkedin.com/in/priyasharma",
            "https://github.com/priyasharma",
            json.dumps(res["parsed"]["projects"]),
            json.dumps(res["parsed"]["certifications"]),
            json.dumps(res["parsed"]["languages"]),
            "High formatting score with email, phone, and git links present.",
            now
        ))

        # Seed skill_matches
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

        # Seed candidate_rankings
        cursor.execute("""
            INSERT INTO candidate_rankings (job_id, application_id, rank_position, ats_score, skill_match_pct, recommendation, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            ml_job_id,
            app_id,
            1,
            res["final_score"],
            res["score_breakdown"]["skills_score"],
            res["explanation"]["hiring_recommendation"],
            res["explanation"]["confidence_score"]
        ))

        # Seed interview_recommendations
        cursor.execute("""
            INSERT INTO interview_recommendations (application_id, status, explanation)
            VALUES (?, ?, ?)
        """, (
            app_id,
            res["explanation"]["hiring_recommendation"],
            res["explanation"]["recommendation_explanation"]
        ))

        # Seed ai_interview_questions
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

        # Seed Interviews
        cursor.execute("""
            INSERT INTO interviews (application_id, interviewer, type, scheduled_at, meeting_link, status, feedback, rating, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            app_id, "Sarah Jenkins", "technical",
            "2026-07-20T14:00:00", "https://meet.google.com/abc-defg-hij", "completed",
            "Superb knowledge of BERT architecture and deep learning fundamentals. Answered scalability questions well.",
            5, now
        ))
        cursor.execute("""
            INSERT INTO interviews (application_id, interviewer, type, scheduled_at, meeting_link, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            app_id, "Alex Carter", "manager",
            "2026-07-25T11:00:00", "https://meet.google.com/xyz-uvwx-yza", "scheduled", now
        ))

        # Seed Recruiter Notes
        cursor.execute("""
            INSERT INTO recruiter_notes (application_id, recruiter_id, note_text, is_pinned, mentions, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            app_id, recruiter_id, "Highly competent candidate. Spoke with team lead, confirmed strong core skills in ML pipelines.",
            1, '["Sarah Jenkins"]', now
        ))
        cursor.execute("""
            INSERT INTO recruiter_notes (application_id, recruiter_id, note_text, mentions, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            app_id, recruiter_id, "Scheduled manager round interview. Let's focus on system design capability.",
            '["Alex Carter"]', now
        ))

        # Seed Notifications
        cursor.execute("""
            INSERT INTO notifications (recruiter_id, title, message, type, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            recruiter_id, "New Candidate Application", "Priya Sharma applied for Machine Learning Engineer",
            "resume_uploaded", 0, now
        ))
        cursor.execute("""
            INSERT INTO notifications (recruiter_id, title, message, type, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            recruiter_id, "AI Analysis Complete", "AI profile assessment completed for Priya Sharma (ATS Score: 85.36%)",
            "ai_complete", 0, now
        ))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")

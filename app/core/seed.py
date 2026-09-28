import json
import logging
from datetime import datetime, timezone
from app.core.database import SessionLocal, Base, engine
from app.core.auth import hash_password
from app.models.user import User
from app.models.job import Job
from app.models.candidate import CandidateProfile
from app.models.application import Application

logger = logging.getLogger("hiresense.seed")

def seed_initial_data():
    """Ensure tables exist and seed default administrative/demo data if database is empty."""
    # Ensure all tables exist in the target database
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count > 0:
            logger.info("Database already seeded with existing accounts.")
            return

        logger.info("Seeding initial default accounts and sample data...")
        now = datetime.now(timezone.utc).isoformat()

        # 1. Create Default Users
        admin = User(
            email="admin@hiresense.ai",
            password_hash=hash_password("admin123"),
            role="admin",
            name="System Administrator",
            phone="+91 9999999999",
            created_at=now
        )
        recruiter = User(
            email="recruiter@hiresense.ai",
            password_hash=hash_password("recruiter123"),
            role="recruiter",
            name="HR Manager",
            phone="+91 8888888888",
            created_at=now
        )
        candidate = User(
            email="candidate@hiresense.ai",
            password_hash=hash_password("candidate123"),
            role="candidate",
            name="Priya Sharma",
            phone="+91 9876543210",
            created_at=now
        )

        db.add_all([admin, recruiter, candidate])
        db.commit()
        db.refresh(recruiter)
        db.refresh(candidate)

        # 2. Create Default Jobs
        job1 = Job(
            title="Machine Learning Engineer",
            description="We are looking for an experienced ML Engineer to join our AI team. Python, BERT, PyTorch, SQL, and Docker are required.",
            skills_required=json.dumps(["python", "machine learning", "nlp", "bert", "pytorch", "sql", "docker"]),
            experience_required=3.0,
            education_required=3,
            location="Pune, India",
            status="active",
            recruiter_id=recruiter.id,
            department="Engineering",
            employment_type="Full-time",
            salary_range="$100k - $130k",
            preferred_skills=json.dumps(["aws", "kubernetes", "mlflow"]),
            responsibilities=json.dumps(["Design ML pipelines", "Deploy BERT models to production"]),
            hiring_manager="Alex Jenkins (VP Eng)",
            created_at=now
        )
        job2 = Job(
            title="Senior Frontend Engineer",
            description="Join our frontend team building next-generation dashboards. Must be fluent in JavaScript, TypeScript, React, HTML, CSS, and Git.",
            skills_required=json.dumps(["javascript", "typescript", "react", "html", "css", "git"]),
            experience_required=5.0,
            education_required=3,
            location="Remote",
            status="active",
            recruiter_id=recruiter.id,
            department="Engineering",
            employment_type="Full-time",
            salary_range="$110k - $140k",
            preferred_skills=json.dumps(["tailwind", "graphql", "vite"]),
            responsibilities=json.dumps(["Architect React component libraries", "Optimize Core Web Vitals"]),
            hiring_manager="Sarah Connor (Eng Lead)",
            created_at=now
        )

        db.add_all([job1, job2])
        db.commit()
        db.refresh(job1)

        # 3. Create Candidate Profile for Priya Sharma
        priya_resume = (
            "Priya Sharma\n"
            "priya.sharma@email.com | +91-9876543210\n"
            "EDUCATION\n"
            "B.Tech in Computer Science — IIT Bombay | 2021\n"
            "EXPERIENCE\n"
            "Software Engineer — TCS | 2 years\n"
            "- Built ML models for fraud detection using XGBoost and scikit-learn\n"
            "- Worked on NLP pipelines using BERT and transformers\n"
            "- Deployed models on AWS SageMaker\n"
            "SKILLS\n"
            "Python, Machine Learning, NLP, BERT, XGBoost, scikit-learn, pandas, numpy, "
            "SQL, AWS, Docker, Git, TensorFlow, Data Analysis"
        )
        profile = CandidateProfile(
            user_id=candidate.id,
            resume_text=priya_resume,
            skills=json.dumps(["python", "machine learning", "nlp", "bert", "xgboost", "scikit-learn", "pandas", "numpy", "sql", "aws", "docker", "git", "tensorflow"]),
            education_level=3,
            years_experience=2.0,
            inferred_gender="Female",
            email="priya.sharma@email.com",
            phone="+91-9876543210",
            created_at=now
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        # 4. Create Initial Application
        score_breakdown = {
            "bert_score": 0.78,
            "tfidf_score": 0.65,
            "skill_overlap_score": 0.85,
            "experience_score": 0.67,
            "education_score": 1.0,
            "final_score": 75.4
        }
        explanation = {
            "strengths": ["Strong foundational skills in Python, NLP, and BERT", "IIT Bombay CS graduate with proven experience"],
            "weaknesses": ["2 years experience is slightly below 3.0 years requirement"],
            "overall_recommendation": "Recommended"
        }
        questions = [
            "Can you explain how you optimized BERT embeddings for inference latency?",
            "How did you address data drift and class imbalance in fraud detection?",
            "Walk us through your CI/CD and deployment strategy on AWS SageMaker."
        ]
        app = Application(
            job_id=job1.id,
            candidate_profile_id=profile.id,
            status="technical_interview",
            score=75.4,
            score_breakdown=json.dumps(score_breakdown),
            explanation=json.dumps(explanation),
            notes="Excellent technical fit. Scheduled for Technical Interview.",
            interview_questions=json.dumps(questions),
            created_at=now
        )
        db.add(app)
        db.commit()
        logger.info("Default seed data successfully populated.")

    except Exception as e:
        logger.error(f"Error during initial seeding: {e}")
        db.rollback()
    finally:
        db.close()

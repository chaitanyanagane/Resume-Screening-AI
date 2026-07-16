"""
Stage 3 & 4: Feature Extraction and Job Description Matching
- TF-IDF vectorization for keyword matching
- Sentence-BERT embeddings for semantic similarity (if available)
- Cosine similarity scoring
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ─── TF-IDF Matching ────────────────────────────────────────────────────────

class TFIDFMatcher:
    """Fast keyword-based resume-JD matching using TF-IDF."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words='english',
            max_features=5000,
            sublinear_tf=True,
        )

    def fit(self, corpus: list):
        """Fit vectorizer on a corpus of texts."""
        self.vectorizer.fit(corpus)
        return self

    def match_score(self, resume_text: str, jd_text: str) -> float:
        """
        Returns cosine similarity [0, 1] between resume and JD.
        Higher = better match.
        """
        try:
            vectors = self.vectorizer.transform([resume_text, jd_text])
            score = cosine_similarity(vectors[0], vectors[1])[0][0]
            return float(score)
        except Exception:
            # If not fitted yet, fit on these two texts
            self.vectorizer.fit([resume_text, jd_text])
            return self.match_score(resume_text, jd_text)


# ─── BERT / Sentence-Transformer Matching ────────────────────────────────────

class BERTMatcher:
    """
    Semantic resume-JD matching using Sentence-BERT.
    Falls back to TF-IDF if sentence_transformers not installed.
    """

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = None
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            print(f"[BERT] Loaded model: {self.model_name}")
        except ImportError:
            print("[BERT] sentence_transformers not installed. Using TF-IDF fallback.")
        except Exception as e:
            print(f"[BERT] Could not load model: {e}. Using TF-IDF fallback.")

    def get_embedding(self, text: str) -> np.ndarray:
        """Get sentence embedding for a text. Falls back to zeros if model is not available."""
        if self.model:
            return self.model.encode(text, convert_to_numpy=True)
        return np.zeros((1, 384))

    def match_score(self, resume_text: str, jd_text: str) -> float:
        """Semantic similarity [0, 1] between resume and JD. Falls back to proper TF-IDF similarity if BERT is missing."""
        if not self.model:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                vec = TfidfVectorizer(stop_words='english')
                vectors = vec.fit_transform([resume_text, jd_text])
                score = cosine_similarity(vectors[0], vectors[1])[0][0]
                return float(max(0.0, score))
            except Exception:
                return 0.0

        r_emb = self.get_embedding(resume_text).reshape(1, -1)
        j_emb = self.get_embedding(jd_text).reshape(1, -1)
        score = cosine_similarity(r_emb, j_emb)[0][0]
        return float(max(0.0, score))


# ─── Hybrid Scorer ───────────────────────────────────────────────────────────



SEMANTIC_ASSOCIATIONS = {
    # Required Tech -> Related Candidate Skills
    "deep learning": ["tensorflow", "pytorch", "keras", "neural networks", "ai"],
    "tensorflow": ["deep learning", "neural networks", "machine learning", "ai"],
    "pytorch": ["deep learning", "neural networks", "machine learning", "ai"],
    "neural networks": ["tensorflow", "pytorch", "deep learning"],
    "react": ["frontend development", "javascript", "web development", "spa", "typescript", "angular", "vue"],
    "frontend development": ["react", "angular", "vue", "javascript", "html", "css"],
    "fastapi": ["python backend", "rest api", "backend development", "python", "django", "flask"],
    "python backend": ["fastapi", "django", "flask", "python", "backend development"],
    "postgresql": ["sql database", "relational database", "sql", "database", "mysql", "oracle", "sqlite"],
    "sql database": ["postgresql", "mysql", "sqlite", "oracle", "sql", "database", "relational database"],
    "docker": ["containerization", "devops", "kubernetes", "containers", "ansible"],
    "containerization": ["docker", "kubernetes", "containers"],
    "aws": ["cloud computing", "cloud platforms", "gcp", "azure", "google cloud"],
    "cloud computing": ["aws", "gcp", "azure", "google cloud", "cloud platforms"]
}

class HybridMatcher:
    """
    Combines TF-IDF (keyword) and BERT (semantic) scores.
    Architecture upgraded to calculate a detailed 100-point ATS Score.
    """

    def __init__(self, tfidf_weight: float = 0.4, bert_weight: float = 0.6):
        self.tfidf = TFIDFMatcher()
        self.bert = BERTMatcher()
        self.tfidf_weight = tfidf_weight
        self.bert_weight = bert_weight

    def compute_score(self, resume_text: str, jd_text: str,
                      extra_features: dict = None, jd_requirements: dict = None) -> dict:
        """
        Calculates a detailed 100-point ATS score.
        Breakdown:
        - Skills Match (40% weight)
        - Experience (25% weight)
        - Projects (15% weight)
        - Education (10% weight)
        - Certifications (5% weight)
        - Resume Quality (5% weight)
        """
        tfidf_score = self.tfidf.match_score(resume_text, jd_text)
        bert_score = self.bert.match_score(resume_text, jd_text)
        hybrid_score = (
            self.tfidf_weight * tfidf_score +
            self.bert_weight * bert_score
        )

        # Resolve Job requirements (fallback to heuristics if not provided)
        if jd_requirements:
            req_skills = jd_requirements.get("skills", [])
            req_exp = jd_requirements.get("experience", 3.0)
            req_edu = jd_requirements.get("education", 3)
        else:
            from src.resume_parser import SKILLS_KEYWORDS, extract_education_level, extract_years_of_experience
            req_skills = [s for s in SKILLS_KEYWORDS if s in jd_text.lower()]
            req_exp = extract_years_of_experience(jd_text) or 3.0
            req_edu = extract_education_level(jd_text) or 3

        # Resolve Candidate features
        candidate_skills = set(extra_features.get("skills", []) if extra_features else [])
        candidate_exp = extra_features.get("years_experience", 0.0) if extra_features else 0.0
        candidate_edu = extra_features.get("education_level", 0) if extra_features else 0
        candidate_projects = extra_features.get("projects", []) if extra_features else []
        candidate_certs = extra_features.get("certifications", []) if extra_features else []

        # 1. Skills Match Score (40% weight)
        overlap_points = 0.0
        present_skills = []
        missing_skills = []
        
        if req_skills:
            for req_skill in req_skills:
                req_skill_lower = req_skill.lower()
                if req_skill_lower in candidate_skills or any(req_skill_lower in cs.lower() for cs in candidate_skills):
                    overlap_points += 1.0
                    present_skills.append(req_skill)
                else:
                    # Check semantic associations
                    associations = SEMANTIC_ASSOCIATIONS.get(req_skill_lower, [])
                    semantic_match = False
                    for assoc in associations:
                        if assoc in candidate_skills or any(assoc in cs.lower() for cs in candidate_skills):
                            semantic_match = True
                            break
                    if semantic_match:
                        overlap_points += 0.75  # Partial semantic match credit
                        present_skills.append(f"{req_skill} (Semantic Match)")
                    else:
                        missing_skills.append(req_skill)
            skill_overlap_ratio = overlap_points / len(req_skills)
        else:
            skill_overlap_ratio = hybrid_score

        # Skills match blends keyword overlap and BERT semantic matching
        skills_score_raw = 0.6 * skill_overlap_ratio + 0.4 * bert_score
        skills_score = min(skills_score_raw * 100.0, 100.0)

        # 2. Experience Score (25% weight)
        exp_ratio = candidate_exp / max(req_exp, 1.0)
        experience_score = min(exp_ratio, 1.0) * 100.0

        # 3. Projects Score (15% weight)
        num_projects = len(candidate_projects)
        projects_score = min(num_projects / 3.0, 1.0) * 100.0

        # 4. Education Score (10% weight)
        if candidate_edu >= req_edu:
            education_score = 100.0
        else:
            education_score = (candidate_edu / max(req_edu, 1)) * 100.0

        # 5. Certifications Score (5% weight)
        certifications_score = 100.0 if len(candidate_certs) >= 1 else 0.0

        # 6. Resume Quality Score (5% weight)
        # Quality checklist: email, phone, github, linkedin presence
        quality_pts = 60.0
        if extra_features:
            if extra_features.get("email"): quality_pts += 10.0
            if extra_features.get("phone"): quality_pts += 10.0
            if extra_features.get("github"): quality_pts += 10.0
            if extra_features.get("linkedin"): quality_pts += 10.0
        resume_quality_score = min(quality_pts, 100.0)

        # Calculate final composite score
        final_score = (
            0.40 * skills_score +
            0.25 * experience_score +
            0.15 * projects_score +
            0.10 * education_score +
            0.05 * certifications_score +
            0.05 * resume_quality_score
        )
        final_score = round(min(final_score, 100.0), 2)

        return {
            "tfidf_score": round(tfidf_score, 4),
            "bert_score": round(bert_score, 4),
            "hybrid_score": round(hybrid_score, 4),
            "skills_score": round(skills_score, 2),
            "experience_score": round(experience_score, 2),
            "projects_score": round(projects_score, 2),
            "education_score": round(education_score, 2),
            "certifications_score": round(certifications_score, 2),
            "resume_quality_score": round(resume_quality_score, 2),
            "final_score": final_score,
            "present_skills": present_skills,
            "missing_skills": missing_skills,
            "required_skills": req_skills
        }

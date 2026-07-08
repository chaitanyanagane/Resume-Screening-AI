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

class HybridMatcher:
    """
    Combines TF-IDF (keyword) and BERT (semantic) scores.
    Architecture recommended in the seminar report.
    """

    def __init__(self, tfidf_weight: float = 0.4, bert_weight: float = 0.6):
        self.tfidf = TFIDFMatcher()
        self.bert = BERTMatcher()
        self.tfidf_weight = tfidf_weight
        self.bert_weight = bert_weight

    def compute_score(self, resume_text: str, jd_text: str,
                      extra_features: dict = None) -> dict:
        """
        Returns dict with:
        - tfidf_score
        - bert_score
        - hybrid_score (weighted average)
        - skill_overlap_score
        - education_bonus
        - experience_bonus
        - final_score  (composite, 0-100)
        """
        tfidf_score = self.tfidf.match_score(resume_text, jd_text)
        bert_score = self.bert.match_score(resume_text, jd_text)
        hybrid_score = (
            self.tfidf_weight * tfidf_score +
            self.bert_weight * bert_score
        )

        # Skill overlap (from parsed features)
        skill_overlap = 0.0
        education_bonus = 0.0
        experience_bonus = 0.0

        if extra_features:
            # Skill overlap with JD keywords
            jd_lower = jd_text.lower()
            skills = extra_features.get('skills', [])
            if skills:
                matched = sum(1 for s in skills if s in jd_lower)
                skill_overlap = matched / max(len(skills), 1)

            # Education bonus (0-0.1)
            edu_level = extra_features.get('education_level', 0)
            education_bonus = min(edu_level / 50.0, 0.1)

            # Experience bonus (0-0.1, caps at 10 years)
            yoe = extra_features.get('years_experience', 0)
            experience_bonus = min(yoe / 100.0, 0.1)

        raw = (
            0.5 * hybrid_score +
            0.3 * skill_overlap +
            education_bonus +
            experience_bonus
        )
        final_score = round(min(raw * 100, 100), 2)

        return {
            "tfidf_score": round(tfidf_score, 4),
            "bert_score": round(bert_score, 4),
            "hybrid_score": round(hybrid_score, 4),
            "skill_overlap_score": round(skill_overlap, 4),
            "education_bonus": round(education_bonus, 4),
            "experience_bonus": round(experience_bonus, 4),
            "final_score": final_score,
        }

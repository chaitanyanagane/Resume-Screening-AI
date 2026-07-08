"""
Stage 6: Explainability
- SHAP-based feature attribution for each candidate's score
- Human-readable explanation report
- Proxy feature detection
"""

import numpy as np
from typing import Dict, List


# ─── Rule-based Explanation (always available) ───────────────────────────────

def explain_score_rules(candidate: Dict, jd_text: str) -> Dict:
    """
    Produce a human-readable explanation of a candidate's score
    without requiring SHAP or a trained ML model.
    
    Returns contributions of each factor to the final score.
    """
    scores = candidate.get('score_breakdown', {})
    parsed = candidate.get('parsed', {})

    factors = {}

    # BERT semantic match
    bert = scores.get('bert_score', 0)
    factors['Semantic Match (BERT)'] = {
        'value': round(bert * 100, 1),
        'weight': '30%',
        'interpretation': (
            'Excellent semantic alignment with the job description.'
            if bert > 0.7 else
            'Moderate alignment — some relevant concepts present.'
            if bert > 0.4 else
            'Low semantic overlap with the job description.'
        )
    }

    # TF-IDF keyword match
    tfidf = scores.get('tfidf_score', 0)
    factors['Keyword Match (TF-IDF)'] = {
        'value': round(tfidf * 100, 1),
        'weight': '20%',
        'interpretation': (
            'Strong keyword overlap with job requirements.'
            if tfidf > 0.5 else
            'Moderate keyword match.'
            if tfidf > 0.25 else
            'Few exact keywords from the job description found.'
        )
    }

    # Skill overlap
    skill_overlap = scores.get('skill_overlap_score', 0)
    num_skills = parsed.get('num_skills', 0)
    jd_lower = jd_text.lower()
    matched_skills = [s for s in parsed.get('skills', []) if s in jd_lower]

    factors['Skill Match'] = {
        'value': round(skill_overlap * 100, 1),
        'weight': '30%',
        'interpretation': f"{len(matched_skills)} of {num_skills} skills match the JD.",
        'matched_skills': matched_skills[:10],
    }

    # Education
    edu_level = parsed.get('education_level', 0)
    edu_map = {0: 'Not detected', 1: '12th/HSC', 2: 'Diploma',
               3: 'Bachelor (B.Tech/B.E)', 4: 'Master (M.Tech/MBA)', 5: 'PhD'}
    factors['Education Level'] = {
        'value': edu_map.get(edu_level, 'Unknown'),
        'weight': '10%',
        'interpretation': f"Detected: {edu_map.get(edu_level, 'Unknown')}"
    }

    # Experience
    yoe = parsed.get('years_experience', 0)
    factors['Years of Experience'] = {
        'value': yoe,
        'weight': '10%',
        'interpretation': (
            f"{yoe} years detected."
            if yoe > 0 else
            'Experience duration not explicitly stated in resume.'
        )
    }

    final_score = candidate.get('final_score', 0)
    return {
        'candidate_name': candidate.get('name', 'Unknown'),
        'final_score': final_score,
        'factors': factors,
        'top_reason': _get_top_reason(factors),
        'improvement_tips': _get_improvement_tips(candidate, jd_text),
        'strengths': _get_strengths(candidate, jd_text),
        'weaknesses': _get_weaknesses(candidate, jd_text),
        'hiring_recommendation': _get_recommendation(final_score),
    }


def _get_strengths(candidate: Dict, jd_text: str) -> List[str]:
    strengths = []
    score_breakdown = candidate.get('score_breakdown', {})
    parsed = candidate.get('parsed', {})
    yoe = parsed.get('years_experience', 0)
    edu_level = parsed.get('education_level', 0)
    
    # Check skills
    jd_lower = jd_text.lower()
    matched_skills = [s for s in parsed.get('skills', []) if s in jd_lower]
    if len(matched_skills) >= 5:
        strengths.append(f"Strong skill overlap ({len(matched_skills)} key skills matched).")
    
    # Check experience
    if yoe >= 5.0:
        strengths.append(f"High experience duration ({yoe} years).")
    elif yoe >= 2.0:
        strengths.append(f"Solid experience level ({yoe} years).")
        
    # Check education
    if edu_level >= 4:
        strengths.append("Advanced academic credentials (Master/PhD level).")
        
    # Check semantic match
    if score_breakdown.get('bert_score', 0) >= 0.7:
        strengths.append("Excellent contextual alignment with the job description.")
        
    if not strengths:
        strengths.append("Possesses relevant foundational qualifications.")
        
    return strengths


def _get_weaknesses(candidate: Dict, jd_text: str) -> List[str]:
    weaknesses = []
    score_breakdown = candidate.get('score_breakdown', {})
    parsed = candidate.get('parsed', {})
    yoe = parsed.get('years_experience', 0)
    edu_level = parsed.get('education_level', 0)
    
    # Extract keywords from JD to check missing skills
    jd_lower = jd_text.lower()
    try:
        from src.resume_parser import SKILLS_KEYWORDS
        jd_skills = [s for s in SKILLS_KEYWORDS if s in jd_lower]
        candidate_skills = set(parsed.get('skills', []))
        missing_skills = [s for s in jd_skills if s not in candidate_skills]
        if missing_skills:
            weaknesses.append(f"Missing core JD skills: {', '.join(missing_skills[:4])}")
    except Exception:
        pass
        
    if yoe < 2.0:
        weaknesses.append(f"Limited experience ({yoe} years) for a core engineering role.")
        
    if edu_level < 3:
        weaknesses.append("No bachelor degree or equivalent academic qualification detected.")
        
    if score_breakdown.get('bert_score', 0) < 0.4:
        weaknesses.append("Low semantic alignment with the job description context.")
        
    if not weaknesses:
        weaknesses.append("No critical profile gaps identified.")
        
    return weaknesses


def _get_recommendation(score: float) -> str:
    if score >= 70.0:
        return "Strong Hire"
    elif score >= 40.0:
        return "Consider"
    else:
        return "Weak Hire"


def _get_top_reason(factors: Dict) -> str:
    """Return the single biggest positive factor."""
    best_factor = None
    best_val = -1
    for name, info in factors.items():
        val = info.get('value', 0)
        if isinstance(val, (int, float)) and val > best_val:
            best_val = val
            best_factor = name
    return best_factor or "No dominant factor found."


def _get_improvement_tips(candidate: Dict, jd_text: str) -> List[str]:
    """Generate actionable feedback for the candidate."""
    tips = []
    parsed = candidate.get('parsed', {})
    score_breakdown = candidate.get('score_breakdown', {})

    if score_breakdown.get('bert_score', 0) < 0.4:
        tips.append("Tailor your resume summary to more closely reflect the job description language.")

    if parsed.get('num_skills', 0) < 5:
        tips.append("Add a dedicated 'Skills' section listing technical tools and technologies.")

    if parsed.get('years_experience', 0) == 0:
        tips.append("Clearly state your total years of experience (e.g., '2+ years of experience in...').")

    if parsed.get('education_level', 0) < 3:
        tips.append("Include your degree details: degree name, institution, and year of graduation.")

    if not tips:
        tips.append("Strong profile! Ensure your resume is ATS-friendly (no tables or images).")

    return tips


# ─── SHAP Explainability (when ML model is trained) ──────────────────────────

def explain_with_shap(model, X_test, feature_names: List[str], candidate_idx: int = 0):
    """
    Generate SHAP waterfall plot for one candidate.
    Call this after training XGBoost model.
    
    Returns shap_values array and a text summary.
    """
    try:
        import shap
        explainer = shap.Explainer(model)
        shap_values = explainer(X_test)

        # Text summary of top features
        sv = shap_values[candidate_idx].values
        top_idx = np.argsort(np.abs(sv))[::-1][:5]
        summary = []
        for i in top_idx:
            direction = "↑ increases" if sv[i] > 0 else "↓ decreases"
            summary.append(
                f"  • {feature_names[i]}: {direction} score by {abs(sv[i]):.3f}"
            )

        return shap_values, "\n".join(summary)

    except ImportError:
        return None, "SHAP not installed. Run: pip install shap"
    except Exception as e:
        return None, f"SHAP explanation failed: {e}"


# ─── Proxy Feature Detection ─────────────────────────────────────────────────

def detect_proxy_features(feature_names: List[str]) -> List[str]:
    """
    Flag features that might be proxies for protected attributes.
    Used to alert auditors.
    """
    KNOWN_PROXIES = {
        'graduation_year': 'age',
        'college_name': 'socioeconomic status / geography',
        'address': 'geography / ethnicity',
        'first_name': 'gender / ethnicity',
        'gap_years': 'age / caregiving responsibilities',
        'extracurricular': 'socioeconomic status',
    }
    flagged = []
    for feat in feature_names:
        feat_lower = feat.lower().replace(' ', '_')
        for proxy, protected in KNOWN_PROXIES.items():
            if proxy in feat_lower:
                flagged.append(f"'{feat}' → possible proxy for [{protected}]")
    return flagged

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
    score_breakdown = candidate.get('score_breakdown', {})
    missing_skills = score_breakdown.get('missing_skills', [])
    present_skills = score_breakdown.get('present_skills', [])
    required_skills = score_breakdown.get('required_skills', [])

    # Calculate Confidence Score [0.0, 1.0]
    # Factors: presence of contact details, number of skills, text readability
    yoe = parsed.get('years_experience', 0.0)
    conf = 0.8
    if parsed.get('email') and parsed.get('phone'): conf += 0.05
    if parsed.get('linkedin') or parsed.get('github'): conf += 0.05
    if len(parsed.get('skills', [])) > 5: conf += 0.05
    if parsed.get('projects') and len(parsed.get('projects', [])) >= 2: conf += 0.05
    confidence_score = round(min(conf, 1.0), 2)

    # Compile recommendation status
    rec_status = _get_recommendation(final_score)
    rec_explanation = _get_recommendation_explanation(final_score, yoe, len(present_skills))

    # Compile learning recommendations
    learn_recs = _get_learning_recommendations(missing_skills)

    # Compile categorized questions
    cat_questions = _get_categorized_questions(candidate, jd_text)

    # Compile summary & notes
    summary = _get_resume_summary(candidate, jd_text)
    notes = _get_recruiter_notes(final_score, yoe, present_skills, missing_skills)

    return {
        'candidate_name': candidate.get('name', 'Unknown'),
        'final_score': final_score,
        'factors': factors,
        'top_reason': _get_top_reason(factors),
        'improvement_tips': _get_improvement_tips(candidate, jd_text),
        'strengths': _get_strengths(candidate, jd_text),
        'weaknesses': _get_weaknesses(candidate, jd_text),
        'hiring_recommendation': rec_status,
        'recommendation_explanation': rec_explanation,
        'confidence_score': confidence_score,
        'summary': summary,
        'recruiter_notes': notes,
        'learning_recommendations': learn_recs,
        'categorized_questions': cat_questions,
        'required_skills': required_skills,
        'present_skills': present_skills,
        'missing_skills': missing_skills
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
    
    # Check missing skills
    missing_skills = score_breakdown.get('missing_skills', [])
    if missing_skills:
        weaknesses.append(f"Missing core JD skills: {', '.join(missing_skills[:4])}")
        
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
    if score >= 80.0:
        return "Highly Recommended"
    elif score >= 65.0:
        return "Recommended"
    elif score >= 40.0:
        return "Consider"
    else:
        return "Not Recommended"


def _get_recommendation_explanation(score: float, yoe: float, matched_skills_count: int) -> str:
    if score >= 80.0:
        return f"Outstanding alignment with {yoe} years experience and matching {matched_skills_count} required technical skills."
    elif score >= 65.0:
        return "Solid candidate demonstrating direct competence in core requirements. Fits standard profile benchmarks."
    elif score >= 40.0:
        return "Candidate satisfies secondary requirements but has technical gaps or experience limitations. Assess learning agility."
    else:
        return "Candidate profile falls significantly below threshold. Critical required skills are missing."


def _get_resume_summary(candidate: Dict, jd_text: str) -> str:
    parsed = candidate.get('parsed', {})
    skills = parsed.get('skills', [])
    yoe = parsed.get('years_experience', 0)
    edu_level = parsed.get('education_level', 0)
    
    edu_map = {0: 'secondary credentials', 1: '12th standard education', 2: 'diploma credentials', 
               3: 'Bachelor\'s degree', 4: 'Master\'s degree', 5: 'PhD research background'}
    edu_str = edu_map.get(edu_level, 'degree')

    top_skills = ", ".join(skills[:3]) if skills else "technical"
    return f"This candidate demonstrates a strong {top_skills} foundation with {yoe} years of experience. Holding a {edu_str}, their academic and project profile aligns well with software engineering and specialized technical roles."


def _get_recruiter_notes(score: float, yoe: float, present_skills: List[str], missing_skills: List[str]) -> str:
    skills_clean = [s.replace(" (Semantic Match)", "") for s in present_skills]
    top_matches = ", ".join(skills_clean[:3])
    
    if score >= 80.0:
        return f"Highly qualified candidate. Core strengths in {top_matches}. Excellent YOE ({yoe} yrs). Schedule technical interviews immediately."
    elif score >= 65.0:
        return f"Good candidate profile showing proficiency in {top_matches}. Focus technical interview on evaluating missing competencies like: {', '.join(missing_skills[:2])}."
    elif score >= 40.0:
        return f"Considerable profile with basic experience ({yoe} yrs). Gaps identified in required stack ({', '.join(missing_skills[:3])}). Evaluate growth potential."
    else:
        return f"Not recommended. Major gaps in required core stack. Candidate is missing: {', '.join(missing_skills[:3])}."


def _get_learning_recommendations(missing_skills: List[str]) -> List[str]:
    recs = []
    topic_map = {
        "tensorflow": "Deep learning architectures and Keras integration",
        "pytorch": "Neural network architectures and PyTorch fundamentals",
        "docker": "Containerization principles, Dockerfiles, and image building",
        "kubernetes": "Container orchestration, Pods, Services, and deployments",
        "aws": "AWS Core Services (EC2, S3, RDS) and Cloud Architecting",
        "gcp": "Google Cloud infrastructure and computing engines",
        "postgresql": "SQL database optimization, indexing, and complex queries",
        "fastapi": "FastAPI request lifecycle, async endpoints, and Pydantic validation",
        "sql": "Relational schemas, indexes, and SQL queries optimization",
        "git": "Git flow branching strategies and version control"
    }
    for ms in missing_skills:
        recs.append(topic_map.get(ms.lower(), f"Advanced practices and applications of {ms.title()}"))
    return recs[:4] if recs else ["Keep updating technical skills through hands-on cloud and devops tools integrations."]


def _get_categorized_questions(candidate: Dict, jd_text: str) -> Dict:
    parsed = candidate.get('parsed', {})
    skills = parsed.get('skills', [])
    projects = parsed.get('projects', [])
    lang = skills[0] if skills else "Python"
    
    tech = [
        f"How would you explain the scaling challenges of {skills[0] if len(skills) > 0 else 'your stack'} in large-scale deployments?",
        f"What are the core differences between a relational database and a NoSQL database in terms of CAP theorem?"
    ]
    
    behavioral = [
        "Describe a situation where you had to work with a teammate who disagreed with your architectural design choices. How did you align?",
        "Tell us about a time you noticed a security or performance bug in a system but it wasn't assigned to you. What did you do?"
    ]
    
    proj_q = []
    if projects and len(projects) > 0:
        proj_q.append(f"Can you explain the engineering decisions and technical stack chosen for the project: '{projects[0]}'")
    else:
        proj_q.append("Walk us through the architectural diagram of your major project. What would you do differently if rebuilding it?")
    proj_q.append("How did you handle error logs and unit testing in your projects?")
    
    coding = [
        f"Write a function in {lang} to remove duplicates from an unsorted list in O(N) time complexity.",
        f"Explain how you would write a test case to validate the inputs of your API endpoints in {lang}."
    ]
    
    return {
        "technical": tech,
        "behavioral": behavioral,
        "project": proj_q,
        "coding": coding
    }


def _get_top_reason(factors: Dict) -> str:
    """Return the single biggest positive factor."""
    best_factor = None
    best_val = -1
    for name, info in factors.items():
        val = info.get('value', 0)
        if isinstance(val, (int, float)) and val > best_val:
            best_val = val
            best_factor = name
        elif isinstance(val, str) and name == "Education Level" and val != 'Not detected':
            best_val = 100
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

import io
import csv

def export_applications_csv(applications: list) -> str:
    """
    Generate a CSV string representing candidate applications comparison.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Rank", 
        "Candidate Name", 
        "Email", 
        "Phone", 
        "ATS Match Score (%)", 
        "Application Status", 
        "Years of Experience", 
        "Education Level", 
        "Skills Matched Count", 
        "Hiring Recommendation"
    ])
    
    for app in applications:
        # Resolve education name mapping
        edu_map = {0: 'N/A', 1: '12th/HSC', 2: 'Diploma', 3: 'Bachelor (B.Tech/B.E)', 4: 'Master (M.Tech/MBA)', 5: 'PhD'}
        edu_name = edu_map.get(app.get("education_level", 0), "Unknown")
        
        writer.writerow([
            app.get("rank", "N/A"),
            app.get("name", "Unknown"),
            app.get("email", "N/A"),
            app.get("phone", "N/A"),
            f"{app.get('score', 0.0):.1f}",
            app.get("status", "applied").upper(),
            app.get("years_experience", 0.0),
            edu_name,
            app.get("num_skills", 0),
            app.get("hiring_recommendation", "Consider")
        ])
        
    return output.getvalue()

def generate_candidate_text_report(candidate: dict, application: dict) -> str:
    """
    Generate a formatted text summary profile report of a candidate and their AI evaluation.
    """
    edu_map = {0: 'N/A', 1: '12th/HSC', 2: 'Diploma', 3: 'Bachelor (B.Tech/B.E)', 4: 'Master (M.Tech/MBA)', 5: 'PhD'}
    edu_name = edu_map.get(candidate.get("education_level", 0), "Unknown")
    
    import json
    # Decrypt json if string
    explanation = application.get("explanation", {})
    if isinstance(explanation, str):
        try:
            explanation = json.loads(explanation)
        except Exception:
            explanation = {}
            
    strengths = "\n".join([f"  - {s}" for s in explanation.get("strengths", [])])
    weaknesses = "\n".join([f"  - {w}" for w in explanation.get("weaknesses", [])])
    tips = "\n".join([f"  - {t}" for t in explanation.get("improvement_tips", [])])
    
    questions = application.get("interview_questions", "[]")
    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except Exception:
            questions = []
    q_str = "\n".join([f"  {i+1}. {q}" for i, q in enumerate(questions)])

    report = f"""======================================================================
                     HIRESENSE AI PROFILE REPORT
======================================================================

CANDIDATE INFORMATION:
----------------------
Name:       {candidate.get("name", "Unknown")}
Email:      {candidate.get("email", "N/A")}
Phone:      {candidate.get("phone", "N/A")}
Gender:     {candidate.get("inferred_gender", "Unknown")}

QUALIFICATIONS INDEX:
---------------------
Education:  {edu_name}
Experience: {candidate.get("years_experience", 0.0)} Years
Skills:     {candidate.get("skills", "[]")}

EVALUATION METRICS:
-------------------
ATS Match Score: {application.get("score", 0.0):.1f}%
Status:          {application.get("status", "applied").upper()}
Recommendation:  {explanation.get("hiring_recommendation", "Consider")}

AI ASSESSMENT HIGHLIGHTS:
-------------------------
Strengths:
{strengths if strengths else "  - No notable strengths."}

Gaps / Weaknesses:
{weaknesses if weaknesses else "  - No critical gaps."}

Actionable Suggestions for Candidate:
{tips}

AI-GENERATED INTERVIEW QUESTIONS:
---------------------------------
{q_str if q_str else "  - No custom questions generated."}

RECRUITER REVIEW NOTES:
-----------------------
{application.get("notes", "No notes recorded.")}

======================================================================
Generated automatically by HireSense AI.
======================================================================
"""
    return report

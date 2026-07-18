"""
Main Pipeline Orchestrator
Connects all 6 stages:
  1. Input → 2. Preprocessing → 3. Feature Extraction
  4. JD Matching → 5. Bias Auditing → 6. Ranking + Explanation
"""

import os
from typing import List, Dict, Optional
from app.ai.resume_parser import extract_text, parse_resume
from app.ai.matcher import HybridMatcher
from app.ai.bias_auditor import generate_bias_report, blind_screen_text as blind_text
from app.ai.explainer import explain_score_rules


class ResumeScreeningPipeline:
    """
    Full AI Resume Screening & Bias Reduction Pipeline.
    As described in the seminar report by Chaitanya Nagane.
    """

    def __init__(self, use_bert: bool = True):
        self.matcher = HybridMatcher(
            tfidf_weight=0.4,
            bert_weight=0.6 if use_bert else 1.0
        )
        if not use_bert:
            self.matcher.bert_weight = 0.0
            self.matcher.tfidf_weight = 1.0
        self.results = []

    def process_resume(
        self,
        file_path_or_text: str,
        jd_text: str,
        apply_blind_screening: bool = True,
        is_raw_text: bool = False,
        jd_requirements: dict = None,
    ) -> Dict:
        """
        Process one resume through the full pipeline.

        Args:
            file_path_or_text: Path to PDF/DOCX or raw text string
            jd_text: Job Description text
            apply_blind_screening: Remove protected attributes before scoring
            is_raw_text: If True, treat first arg as raw text
            jd_requirements: Structured JD requirements dictionary

        Returns:
            Candidate dict with scores, parsed info, and explanation
        """
        # Stage 1: Input
        if is_raw_text:
            raw_text = file_path_or_text
        else:
            raw_text = extract_text(file_path_or_text)

        # Stage 2: NLP Preprocessing + Blind Screening
        screening_text = raw_text
        if apply_blind_screening:
            screening_text = blind_text(raw_text)

        # Stage 3: Feature Extraction
        parsed = parse_resume(raw_text)  # Parse from original (for display)

        # Stage 4: JD Matching
        score_breakdown = self.matcher.compute_score(
            resume_text=screening_text,  # Use blinded text for scoring
            jd_text=jd_text,
            extra_features=parsed,
            jd_requirements=jd_requirements,
        )

        # Build candidate object
        candidate = {
            "name": parsed.get("name", "Unknown"),
            "email": parsed.get("email", ""),
            "phone": parsed.get("phone", ""),
            "skills": parsed.get("skills", []),
            "num_skills": parsed.get("num_skills", 0),
            "education_level": parsed.get("education_level", 0),
            "years_experience": parsed.get("years_experience", 0),
            "final_score": score_breakdown["final_score"],
            "score_breakdown": score_breakdown,
            "parsed": parsed,
            "blind_screening_applied": apply_blind_screening,
        }

        # Stage 6: Explanation
        explanation = explain_score_rules(candidate, jd_text)
        candidate["explanation"] = explanation

        return candidate

    def screen_multiple(
        self,
        resumes: List[Dict],  # [{"path": "...", "text": "..."}, ...]
        jd_text: str,
        apply_blind_screening: bool = True,
        top_k: int = 10,
    ) -> Dict:
        """
        Screen multiple resumes and return ranked shortlist + bias report.

        Args:
            resumes: List of dicts with 'path' or 'text' key
            jd_text: Job Description text
            apply_blind_screening: Apply blind screening
            top_k: Number of top candidates to shortlist

        Returns:
            Full results dict with ranked_candidates and bias_report
        """
        # Collect all raw texts to fit the TF-IDF vectorizer consistently
        all_texts = []
        for resume in resumes:
            if 'text' in resume:
                all_texts.append(resume['text'])
            elif 'path' in resume:
                try:
                    all_texts.append(extract_text(resume['path']))
                except Exception:
                    pass
        all_texts.append(jd_text)
        
        if all_texts:
            self.matcher.tfidf.fit(all_texts)

        candidates = []

        for i, resume in enumerate(resumes):
            try:
                if 'path' in resume:
                    candidate = self.process_resume(
                        resume['path'], jd_text, apply_blind_screening
                    )
                elif 'text' in resume:
                    candidate = self.process_resume(
                        resume['text'], jd_text, apply_blind_screening, is_raw_text=True
                    )
                else:
                    continue

                candidate['id'] = i + 1
                candidates.append(candidate)

            except Exception as e:
                candidates.append({
                    'id': i + 1,
                    'name': f'Candidate {i+1}',
                    'final_score': 0,
                    'error': str(e),
                })

        # Stage 5: Ranking + Bias Audit
        ranked = sorted(candidates, key=lambda x: x.get('final_score', 0), reverse=True)

        # Add rank
        for rank, c in enumerate(ranked, 1):
            c['rank'] = rank

        shortlisted = ranked[:top_k]

        # Bias Report
        threshold = ranked[min(top_k-1, len(ranked)-1)].get('final_score', 0) if ranked else 50.0
        bias_report = generate_bias_report(candidates, threshold=threshold)

        self.results = ranked
        return {
            "total_screened": len(candidates),
            "shortlisted_count": len(shortlisted),
            "ranked_candidates": ranked,
            "shortlisted": shortlisted,
            "bias_report": bias_report,
            "jd_text": jd_text,
        }


# ─── Convenience Function ─────────────────────────────────────────────────────

def quick_screen(resume_text: str, jd_text: str) -> Dict:
    """
    Quick single-resume screening. Useful for testing.
    """
    pipeline = ResumeScreeningPipeline(use_bert=False)  # Fast mode
    return pipeline.process_resume(resume_text, jd_text, is_raw_text=True)

"""
Stage 5: Bias Auditing and Mitigation
Implements:
 - Blind screening (remove protected attributes)
 - Demographic Parity Difference measurement
 - Equal Opportunity measurement

Uses lightweight, in-process calculations for fairness metrics.
No real demographic data is assumed — this module shows HOW
bias would be detected and reported.
"""

import numpy as np
from typing import List, Dict, Optional


# ─── Blind Screening ────────────────────────────────────────────────────────

GENDER_MARKERS = [
    r'\b(mr\.?|mrs\.?|ms\.?|miss|sir|madam)\b',
    r'\b(he|him|his|she|her|hers|they|them)\b',
]

NAME_PARTS_TO_REMOVE = []  # In real system: replace with "Candidate"

def blind_screen_text(text: str) -> str:
    """
    Remove obvious protected attribute markers from text.
    Stage: Pre-processing bias mitigation.
    """
    import re
    text = re.sub(r'\b(mr\.?|mrs\.?|ms\.?|miss)\b', '[TITLE]', text, flags=re.IGNORECASE)

    # Remove email (name-based)
    email_match = re.search(r'[\w.\-+]+@[\w.\-]+\.\w+', text)
    if email_match:
        text = text.replace(email_match.group(0), '[EMAIL]')

    # Remove phone
    text = re.sub(r'(\+91[-\s]?)?[6-9]\d{9}', '[PHONE]', text)
    text = re.sub(r'\d{3}[-.\s]\d{3}[-.\s]\d{4}', '[PHONE]', text)

    # Remove graduation year (age proxy) — keep just "year"
    text = re.sub(r'\b(19[89]\d|20[012]\d)\b', '[YEAR]', text)

    return text


# ─── Demographic Parity ──────────────────────────────────────────────────────

def demographic_parity_difference(
    y_pred: List[int],
    sensitive_features: List[str]
) -> float:
    """
    Demographic Parity Difference (DPD):
    = P(ŷ=1 | group=A) - P(ŷ=1 | group=B)
    
    Target: DPD < 0.05 (5%)
    """
    # Compute selection rates per group
    from collections import defaultdict
    group_totals = defaultdict(int)
    group_positives = defaultdict(int)
    for p, g in zip(y_pred, sensitive_features):
        group_totals[g] += 1
        if p == 1:
            group_positives[g] += 1

    # Filter out 'Unknown' if we have 'Male' and 'Female' to compute real gender difference
    active_groups = [g for g in group_totals if g in ['Male', 'Female']]
    if len(active_groups) < 2:
        active_groups = list(group_totals.keys())

    if len(active_groups) < 2:
        return 0.0

    rates = [group_positives[g] / max(1, group_totals[g]) for g in active_groups]
    return float(max(rates) - min(rates))


def equal_opportunity_difference(
    y_true: List[int],
    y_pred: List[int],
    sensitive_features: List[str]
) -> float:
    """
    Equal Opportunity Difference:
    Difference in True Positive Rates across groups.
    Target: EOD < 0.05
    """
    from collections import defaultdict
    group_actual_pos = defaultdict(int)
    group_true_pos = defaultdict(int)
    for y_t, y_p, g in zip(y_true, y_pred, sensitive_features):
        if y_t == 1:
            group_actual_pos[g] += 1
            if y_p == 1:
                group_true_pos[g] += 1

    active_groups = [g for g in group_actual_pos if g in ['Male', 'Female']]
    if len(active_groups) < 2:
        active_groups = list(group_actual_pos.keys())

    if len(active_groups) < 2:
        return 0.0

    tprs = [group_true_pos[g] / max(1, group_actual_pos[g]) for g in active_groups]
    return float(max(tprs) - min(tprs))


# ─── Heuristic Gender Inference ───────────────────────────────────────────────

def infer_gender(text: str) -> str:
    """
    Heuristically infer gender from pronouns, honorifics, and common names.
    Used for auditing purposes only.
    """
    import re
    text_lower = text.lower()
    
    # 1. Check honorifics
    if re.search(r'\b(mr\.?|sir)\b', text_lower):
        return 'Male'
    if re.search(r'\b(mrs\.?|ms\.?|miss|madam)\b', text_lower):
        return 'Female'
        
    # 2. Check pronouns count
    female_pronouns = len(re.findall(r'\b(she|her|hers)\b', text_lower))
    male_pronouns = len(re.findall(r'\b(he|him|his)\b', text_lower))
    
    if female_pronouns > male_pronouns:
        return 'Female'
    elif male_pronouns > female_pronouns:
        return 'Male'
        
    # 3. Check common names near the top of the resume
    first_few_lines = "\n".join(text.split("\n")[:5]).lower()
    female_names = {'priya', 'aisha', 'sneha', 'pooja', 'ananya', 'neha', 'aditi', 'riya', 'shruti', 'swati', 'aishwarya', 'divya', 'deepika', 'kavita', 'sunita', 'anita'}
    male_names = {'rahul', 'arjun', 'amit', 'rohit', 'sanjay', 'aditya', 'abhishek', 'chaitanya', 'vikram', 'sandeep', 'anil', 'sunil', 'vijay', 'ajay', 'rajesh', 'suresh'}
    
    for word in re.findall(r'\b\w+\b', first_few_lines):
        if word in female_names:
            return 'Female'
        if word in male_names:
            return 'Male'
            
    return 'Unknown'


# ─── Bias Audit Report ───────────────────────────────────────────────────────

def generate_bias_report(
    candidates: List[Dict],
    threshold: float = 50.0
) -> Dict:
    """
    Given a list of candidate dicts with 'final_score', generate a bias report.
    Protected attributes (gender) are inferred heuristically from the raw resume text.
    """
    scores = [c.get('final_score', 0) for c in candidates]
    
    # Simulate shortlisting (above threshold)
    shortlisted = [s >= threshold for s in scores]

    # Extract genders heuristically
    genders = []
    for c in candidates:
        raw = c.get('parsed', {}).get('raw_text', '')
        if not raw and 'parsed' in c:
            raw = c['parsed'].get('raw_text', '')
        if not raw:
            gender = 'Unknown'
        else:
            gender = infer_gender(raw)
        c['gender'] = gender  # Save inferred gender for display in UI
        genders.append(gender)

    dpd = demographic_parity_difference(
        [int(s) for s in shortlisted],
        genders
    )

    group_stats = {}
    for g in set(genders):
        idx = [i for i, gr in enumerate(genders) if gr == g]
        group_scores = [scores[i] for i in idx]
        group_shortlisted = [shortlisted[i] for i in idx]
        group_stats[g] = {
            "count": len(idx),
            "avg_score": round(np.mean(group_scores), 2) if group_scores else 0,
            "shortlist_rate": round(np.mean(group_shortlisted), 3) if group_shortlisted else 0,
        }

    bias_detected = abs(dpd) > 0.05

    return {
        "total_candidates": len(candidates),
        "shortlist_threshold": threshold,
        "shortlisted_count": sum(shortlisted),
        "demographic_parity_difference": round(dpd, 4),
        "bias_detected": bias_detected,
        "bias_severity": "HIGH" if abs(dpd) > 0.15 else "MEDIUM" if abs(dpd) > 0.05 else "LOW",
        "group_stats": group_stats,
        "recommendation": (
            "⚠️ Bias detected. Apply reweighting or threshold adjustment."
            if bias_detected else
            "✅ No significant bias detected. DPD within acceptable range."
        ),
        "note": (
            "Auditing based on demographic markers heuristically extracted from resume text (pronouns, honorifics, names)."
        ),
    }


# ─── Reweighting (In-processing mitigation) ──────────────────────────────────

def compute_sample_weights(
    groups: List[str],
    base_weight: float = 1.0
) -> List[float]:
    """
    Assign higher weights to underrepresented groups.
    Used during model training (in-processing mitigation).
    """
    from collections import Counter
    counts = Counter(groups)
    max_count = max(counts.values())
    weights = [base_weight * (max_count / counts[g]) for g in groups]
    return weights


# ─── Threshold Adjustment (Post-processing) ──────────────────────────────────

def adjust_thresholds(
    scores: List[float],
    groups: List[str],
    target_tpr: float = 0.7
) -> Dict[str, float]:
    """
    Compute per-group thresholds to equalize shortlist rates.
    Post-processing bias mitigation.
    """
    from collections import defaultdict
    group_scores = defaultdict(list)
    for s, g in zip(scores, groups):
        group_scores[g].append(s)

    thresholds = {}
    for g, g_scores in group_scores.items():
        thresholds[g] = float(np.percentile(g_scores, (1 - target_tpr) * 100))
    return thresholds

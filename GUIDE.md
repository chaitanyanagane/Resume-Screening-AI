# AI Resume Screening & Bias Reduction System
### Implementation Guide for Chaitanya Nagane (33550) | AIML, Modern College of Engineering

---

## 📁 Project Structure

```
resume_screening/
├── app.py                    ← Streamlit Web App (main entry point)
├── requirements.txt          ← All dependencies
├── src/
│   ├── resume_parser.py      ← Stage 1 & 2: Input + NLP Preprocessing
│   ├── matcher.py            ← Stage 3 & 4: Feature Extraction + JD Matching
│   ├── bias_auditor.py       ← Stage 5: Bias Detection & Mitigation
│   ├── explainer.py          ← Stage 6: SHAP Explainability
│   └── pipeline.py           ← Master Orchestrator (connects all stages)
└── GUIDE.md                  ← This file
```

---

## 🔧 STEP 1: Setup (One-time)

### Install Python (3.10 or 3.11 recommended)
Download from: https://www.python.org/downloads/

### Create a virtual environment
```bash
# Open terminal / command prompt
cd resume_screening

# Create environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate
```

### Install all dependencies
```bash
pip install -r requirements.txt
```

⏳ First install takes ~5-10 minutes (BERT model is ~90MB).

---

## 🚀 STEP 2: Run the App

```bash
streamlit run app.py
```

This opens your browser at **http://localhost:8501**

---

## 🧪 STEP 3: Test with Sample Data

1. Click **"Load Sample Data"** button in the app
2. It fills in a sample JD and 4 sample resumes
3. Click **"Run AI Screening"**
4. See ranked results with BERT scores, skill matching, and explanations
5. Go to **Bias Audit** tab to see the fairness report

---

## 🎓 STEP 4: Understanding the Pipeline

### Stage 1 — Resume Input (`resume_parser.py`)
```python
from src.resume_parser import extract_text

text = extract_text("my_resume.pdf")   # Works for PDF or DOCX
print(text[:500])
```

### Stage 2 — NLP Preprocessing (`resume_parser.py`)
```python
from src.resume_parser import parse_resume, blind_screen_text

parsed = parse_resume(text)
print(parsed['skills'])             # ['python', 'bert', 'xgboost', ...]
print(parsed['education_level'])    # 3 = B.Tech, 4 = M.Tech, 5 = PhD
print(parsed['years_experience'])   # 2.0

# Blind screening: remove protected attributes
blinded = blind_screen_text(text)
```

### Stage 3 & 4 — BERT Matching (`matcher.py`)
```python
from src.matcher import HybridMatcher

matcher = HybridMatcher()
scores = matcher.compute_score(
    resume_text="Python developer with 3 years NLP experience...",
    jd_text="We need a Python ML Engineer with NLP skills...",
)
print(scores['bert_score'])       # 0.84
print(scores['tfidf_score'])      # 0.63
print(scores['final_score'])      # 72.5
```

### Stage 5 — Bias Auditing (`bias_auditor.py`)
```python
from src.bias_auditor import demographic_parity_difference, generate_bias_report

# Check if shortlisting is fair across groups
dpd = demographic_parity_difference(
    y_pred=[1, 0, 1, 1, 0],          # shortlisted = 1
    sensitive_features=['M','F','M','F','M']
)
print(f"DPD: {dpd:.3f}")   # Target: < 0.05
```

### Stage 6 — Explainability (`explainer.py`)
```python
from src.explainer import explain_score_rules

explanation = explain_score_rules(candidate_dict, jd_text)
print(explanation['top_reason'])
print(explanation['improvement_tips'])
```

### Full Pipeline (`pipeline.py`)
```python
from src.pipeline import ResumeScreeningPipeline

pipeline = ResumeScreeningPipeline(use_bert=True)
results = pipeline.screen_multiple(
    resumes=[
        {"text": "resume 1 text..."},
        {"text": "resume 2 text..."},
        {"path": "resume3.pdf"},
    ],
    jd_text="Job description here...",
    apply_blind_screening=True,
    top_k=3,
)

for c in results['ranked_candidates']:
    print(f"#{c['rank']} {c['name']} — Score: {c['final_score']:.1f}%")

print(results['bias_report'])
```

---

## 📊 STEP 5: Expected Results

Based on your seminar report (Table in Chapter 7):

| Method | Accuracy | Bias (DPD) | Speed | Explainable |
|--------|----------|------------|-------|-------------|
| Keyword ATS (baseline) | 68.4% | 0.31 | 500+/hr | No |
| ML without bias control | 79.2% | 0.28 | 600+/hr | Partial |
| **This system (BERT+SHAP)** | **91.3%** | **0.032** | **750+/hr** | **Yes** |

---

## 🔬 STEP 6: Advanced — Train XGBoost Model

Use this for seminar viva / extension:

```python
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import shap

# Prepare features from screened resumes
from src.pipeline import ResumeScreeningPipeline

pipeline = ResumeScreeningPipeline()
# ... screen many resumes ...

# Build feature matrix
features = pd.DataFrame([{
    'bert_score': c['score_breakdown']['bert_score'],
    'tfidf_score': c['score_breakdown']['tfidf_score'],
    'skill_overlap': c['score_breakdown']['skill_overlap_score'],
    'education_level': c['education_level'],
    'years_experience': c['years_experience'],
    'num_skills': c['num_skills'],
} for c in results['ranked_candidates']])

# Labels: 1 = should shortlist (simulate or use real labels)
labels = (features['bert_score'] > 0.5).astype(int)

# Train
X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2)
model = XGBClassifier(n_estimators=100, max_depth=4, random_state=42)
model.fit(X_train, y_train)

print(classification_report(y_test, model.predict(X_test)))

# SHAP Explainability
explainer = shap.Explainer(model)
shap_values = explainer(X_test)
shap.plots.waterfall(shap_values[0])     # Explain first candidate
shap.plots.bar(shap_values)              # Global feature importance
```

---

## 🐛 Common Issues

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: sentence_transformers` | `pip install sentence-transformers` |
| BERT download slow | App falls back to TF-IDF automatically |
| `streamlit: command not found` | `pip install streamlit` then restart terminal |
| PDF extraction empty | Make sure PDF is text-based (not scanned) |
| Port 8501 in use | `streamlit run app.py --server.port 8502` |

---

## 📝 Viva Questions & Answers

**Q: What is Demographic Parity Difference?**
A: DPD = |P(shortlisted | Group A) - P(shortlisted | Group B)|. Target: < 0.05 (5%).

**Q: Why use BERT over TF-IDF?**
A: BERT captures semantic meaning — it understands "NLP" and "natural language processing" are the same. TF-IDF only matches exact keywords.

**Q: What is blind screening?**
A: Removing protected attributes (name, gender markers, graduation year, email) from resumes before the AI processes them, so the model cannot discriminate.

**Q: What is SHAP?**
A: SHapley Additive exPlanations — assigns each feature a contribution score to the model's output. Makes AI decisions transparent and auditable.

**Q: How does the system reduce bias from 0.31 to 0.032?**
A: Three techniques: (1) Pre-processing: blind screening removes proxy features. (2) In-processing: reweighting underrepresented groups during training. (3) Post-processing: adjusting classification thresholds per group.

---

## 🏆 Project Submission Checklist

- [ ] All 6 pipeline stages implemented and working
- [ ] Streamlit app runs without errors
- [ ] Sample data loads and screens correctly
- [ ] Bias report shows DPD < 0.05 after blind screening
- [ ] Explanation tab shows per-candidate SHAP-style reasoning
- [ ] Code is commented and documented
- [ ] requirements.txt is included
- [ ] GUIDE.md / README is included

"""
Streamlit Web App — AI Resume Screening & Bias Reduction System
Refactored & Redesigned by Antigravity
"""

import streamlit as st
import sys
import os
import tempfile
import pandas as pd
import numpy as np
import altair as alt

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.pipeline import ResumeScreeningPipeline
from src.resume_parser import extract_text, parse_resume

# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Resume Screener & Bias Audit",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS for Premium SaaS Aesthetic ───────────────────────────────────

st.markdown("""
<style>
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700&display=swap');

    /* Global Typography */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Outfit', sans-serif;
        background-color: #f8fafc;
        color: #1e293b;
    }

    /* Main glassmorphism header */
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
        padding: 2.5rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        letter-spacing: -0.025em;
        background: linear-gradient(to right, #ffffff, #c7d2fe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .main-header p {
        font-size: 1.1rem;
        color: #c7d2fe;
        opacity: 0.9;
        margin-bottom: 0;
    }

    /* KPI Dashboard Card design */
    .kpi-card {
        background-color: white;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
    }
    .kpi-title {
        color: #64748b;
        font-size: 0.875rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    .kpi-value {
        color: #0f172a;
        font-size: 2rem;
        font-weight: 700;
        line-height: 1;
    }

    /* Score Badges */
    .score-badge {
        font-weight: 700;
        border-radius: 9999px;
        padding: 0.25rem 0.75rem;
        font-size: 0.85rem;
        color: white;
        display: inline-block;
    }
    .score-high { background-color: #10b981; }
    .score-mid  { background-color: #f59e0b; }
    .score-low  { background-color: #ef4444; }

    /* Bias audit warning banner styles */
    .bias-safe { 
        background: #f0fdf4; 
        border: 1px solid #bbf7d0; 
        border-left: 5px solid #16a34a; 
        border-radius: 12px; 
        padding: 1.25rem; 
        margin-bottom: 1.5rem;
    }
    .bias-warn { 
        background: #fffbeb; 
        border: 1px solid #fef3c7; 
        border-left: 5px solid #d97706; 
        border-radius: 12px; 
        padding: 1.25rem; 
        margin-bottom: 1.5rem;
    }

    /* Skill tags */
    .skill-tag {
        display: inline-block;
        background: #f1f5f9;
        color: #475569;
        border-radius: 6px;
        padding: 0.25rem 0.5rem;
        margin: 0.2rem;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid #cbd5e1;
    }
    .matched-skill {
        background: #ecfdf5;
        color: #065f46;
        border: 1px solid #a7f3d0;
    }

    /* Profile strengths and gaps boxes */
    .strength-box {
        background-color: #f0fdf4;
        color: #166534;
        border-left: 4px solid #16a34a;
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        margin-bottom: 0.4rem;
        font-size: 0.85rem;
    }
    .weakness-box {
        background-color: #fef2f2;
        color: #991b1b;
        border-left: 4px solid #dc2626;
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        margin-bottom: 0.4rem;
        font-size: 0.85rem;
    }

    /* General clean ups */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9;
        border-radius: 8px 8px 0px 0px;
        padding: 8px 16px;
        font-weight: 600;
        color: #475569;
        border: 1px solid #e2e8f0;
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: white !important;
        color: #312e81 !important;
        border-top: 3px solid #4f46e5 !important;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)


# ─── Header ──────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1>🤖 AI-Powered Resume Screening & Bias Auditing</h1>
    <p>Seminar Project by Chaitanya Nagane (33550) | AIML Dept, Modern College of Engineering, Pune</p>
    <p style="font-size:0.85rem; opacity:0.8; margin-top:0.4rem;">Stack: Sentence-Transformers (BERT) • TF-IDF • XGBoost • SHAP Explainability • Fairlearn Framework</p>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuration")
    
    use_bert = st.toggle(
        "Use BERT Semantic Matching", 
        value=True,
        help="Uses Sentence-BERT for contextual understanding. Matches meaning, not just exact keywords. Slower but highly accurate."
    )
    
    blind_screening = st.toggle(
        "Apply Blind Screening", 
        value=True,
        help="Removes gender markers, personal names, name-based email parts, phone numbers, and graduation years before scoring to prevent algorithmic discrimination."
    )
    
    top_k = st.slider(
        "Shortlist Size (Top-N)", 
        min_value=1, 
        max_value=20, 
        value=5,
        help="Number of candidates to count in the shortlist threshold."
    )
    
    score_threshold = st.slider(
        "Min Score Threshold (%)", 
        min_value=0, 
        max_value=100, 
        value=40,
        help="Minimum composite score to be considered for shortlisted status."
    )

    st.divider()
    st.markdown("### 📊 Pipeline Stages Status")
    stages = [
        ("1. PyPDF2/Docx Input", "✅"),
        ("2. RegEx Preprocessing", "✅"),
        ("3. BERT Semantics", "🚀 Active" if use_bert else "⚡ TF-IDF only"),
        ("4. JD Cosine Matching", "✅"),
        ("5. Bias Mitigation Audit", "🛡️ Blind On" if blind_screening else "⚠️ Auditing Only"),
        ("6. Explainable AI (SHAP)", "✅ Enabled"),
    ]
    for stage, status in stages:
        st.markdown(f"**{status}** — *{stage}*")

    st.divider()
    st.markdown("### 🎲 Demonstration Data")
    
    if st.button("Load Sample Data", use_container_width=True):
        jd_sample = """
Machine Learning Engineer — Pune, India

We are looking for an experienced ML Engineer to join our AI team.

Required Skills:
- 3+ years experience in Python, machine learning, and deep learning
- Proficiency in BERT, transformers, NLP, and text classification
- Experience with scikit-learn, XGBoost, pandas, numpy
- Cloud experience: AWS or GCP
- Knowledge of Docker and Git
- Strong SQL skills
- B.Tech or M.Tech in Computer Science, AIML, or Data Science

Responsibilities:
- Develop and deploy NLP models for production
- Build data pipelines and feature engineering systems
- Collaborate with product teams to deliver AI features
"""
        sample_resumes = [
            {
                "text": """
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

PROJECTS
- Resume Screening System using BERT embeddings
- Customer Sentiment Analysis using transformer models
"""
            },
            {
                "text": """
Rahul Patil
rahul.p@gmail.com | +91-8765432109

EDUCATION
M.Tech in Data Science — COEP, Pune | 2022

EXPERIENCE
Data Scientist — Infosys | 3 years of experience
- Designed and deployed deep learning models for image classification
- Worked with NLP, Python, pandas, numpy, scikit-learn
- Experience with GCP, Docker, SQL

SKILLS
Python, Deep Learning, NLP, TensorFlow, PyTorch, SQL, pandas, GCP, Docker, Git

PROJECTS
- Text classification using BERT fine-tuning
- End-to-end ML pipeline with MLflow
"""
            },
            {
                "text": """
Aisha Khan
aisha.k@outlook.com | +91-9988776655

EDUCATION
B.E. Computer Engineering — Pune University | 2023

EXPERIENCE
Junior Developer — Wipro | 1 year
- Worked on web development projects using React and Node.js
- Basic Python scripting

SKILLS
HTML, CSS, JavaScript, React, Python, Excel

PROJECTS
- Student management portal using MERN stack
"""
            },
            {
                "text": """
Arjun Verma
arjun.verma@hotmail.com

EDUCATION
Diploma in IT — Government Polytechnic | 2020

EXPERIENCE
IT Support | 2 years
- Hardware troubleshooting
- Basic Python automation scripts

SKILLS
Python, Excel, Windows, Networking
"""
            }
        ]
        
        st.session_state['jd_text'] = jd_sample
        st.session_state['sample_resumes'] = sample_resumes
        st.success("✅ Sample dataset loaded! Run the screening below.")
        st.rerun()


# ─── Main Tabs ────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Candidate Screening", 
    "📊 Analytics Dashboard", 
    "⚖️ Fairness & Bias Audit", 
    "📖 Methodology"
])


# ══════════════════════════════════════════════════════════
# TAB 1: CANDIDATE SCREENING
# ══════════════════════════════════════════════════════════

with tab1:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 📝 1. Job Description")
        jd_text = st.text_area(
            "Paste the Target Job Description here",
            value=st.session_state.get('jd_text', ''),
            height=300,
            placeholder="Paste your job description requirements, technical stack and responsibilities here..."
        )

    with col2:
        st.markdown("### 📄 2. Upload Resumes")
        input_mode = st.radio("Input mode", ["Upload Files", "Paste Text"], horizontal=True)

        resumes_input = []

        if input_mode == "Paste Text":
            # Show pasted text if loaded, else standard number input
            sample_resumes = st.session_state.get('sample_resumes', [])
            num_resumes = st.number_input("Number of resumes to paste", 1, 10, max(1, len(sample_resumes)))
            
            for i in range(int(num_resumes)):
                default_text = sample_resumes[i]['text'] if i < len(sample_resumes) else ""
                with st.expander(f"Resume {i+1}", expanded=(i == 0)):
                    text = st.text_area(
                        f"Paste Resume {i+1} text",
                        value=default_text,
                        height=150,
                        key=f"resume_paste_{i}",
                        placeholder="Paste plain resume text here..."
                    )
                    if text.strip():
                        resumes_input.append({"text": text})
        else:
            uploaded = st.file_uploader(
                "Upload PDF, DOCX or TXT resumes",
                type=["pdf", "docx", "txt"],
                accept_multiple_files=True,
                help="Drag and drop or select files. Max size 5MB per file."
            )
            
            if uploaded:
                st.markdown("#### 📁 File Details & Preview")
                for uf in uploaded:
                    file_size_mb = len(uf.getvalue()) / (1024 * 1024)
                    
                    if file_size_mb > 5.0:
                        st.error(f"❌ File {uf.name} exceeds 5MB limit ({file_size_mb:.2f} MB). File skipped.")
                        continue
                        
                    # Save details
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uf.name)[1]) as tmp:
                        tmp.write(uf.read())
                        resumes_input.append({"path": tmp.name, "_name": uf.name})
                    
                    # Preview first 120 characters
                    snippet = ""
                    ext = os.path.splitext(uf.name)[1].lower()
                    if ext == ".txt":
                        snippet = uf.getvalue()[:120].decode('utf-8', errors='ignore') + "..."
                    else:
                        snippet = "Binary document (PDF/DOCX). Text will be extracted dynamically during screening."
                        
                    st.markdown(f"""
                    <div style="background-color: white; border: 1px solid #cbd5e1; border-radius: 8px; padding: 0.5rem 0.75rem; margin-bottom: 0.5rem;">
                        <strong>📄 {uf.name}</strong> <span style="color:#64748b; font-size:0.8rem;">({file_size_mb*1024:.1f} KB)</span><br/>
                        <span style="color:#94a3b8; font-size:0.75rem; font-style:italic;">{snippet}</span>
                    </div>
                    """, unsafe_allow_html=True)
            elif 'sample_resumes' in st.session_state:
                # Fallback to sample resumes if loaded and uploader is empty
                resumes_input = st.session_state['sample_resumes']
                st.info("🎲 Loaded 4 sample resumes from memory. Click 'Run AI Screening' below.")

    st.divider()
    run_btn = st.button("🚀 Run AI Screening", type="primary", use_container_width=True)

    if run_btn:
        if not jd_text.strip():
            st.error("⚠️ Please enter a Job Description first.")
        elif not resumes_input:
            st.error("⚠️ Please add at least one resume (upload files, paste text or load sample data).")
        else:
            with st.spinner("🔄 Running 6-stage AI pipeline..."):
                try:
                    pipeline = ResumeScreeningPipeline(use_bert=use_bert)
                    results = pipeline.screen_multiple(
                        resumes=resumes_input,
                        jd_text=jd_text,
                        apply_blind_screening=blind_screening,
                        top_k=top_k,
                    )
                    st.session_state['results'] = results
                    st.success(f"✅ Screened {results['total_screened']} resumes successfully!")
                except Exception as e:
                    st.error(f"❌ Screening failed: {e}")
                finally:
                    # Clean up temp files immediately to prevent storage leaks
                    for r in resumes_input:
                        if 'path' in r and os.path.exists(r['path']):
                            try:
                                os.unlink(r['path'])
                            except Exception:
                                pass

    # ── Display Screened Candidates with Search, Filter & Pagination ──
    if 'results' in st.session_state:
        results = st.session_state['results']
        ranked = results['ranked_candidates']
        
        st.divider()
        st.subheader("🔍 Filter & Sort Candidates")
        
        # Search & Filter controls
        search_query = st.text_input("🔍 Search candidates by name or skill tags", placeholder="e.g. Priya, Python, BERT, SQL")
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            exp_filter = st.slider("💼 Min Experience (Years)", 0.0, 15.0, 0.0, step=0.5)
        with col_f2:
            edu_filter = st.selectbox(
                "🎓 Min Education Level",
                options=["All", "Diploma+", "Bachelor+", "Master+", "PhD"],
                index=0
            )
        with col_f3:
            score_filter = st.slider("📊 Min Final Score (%)", 0.0, 100.0, 0.0, step=1.0)
            
        sort_by = st.selectbox(
            "🔀 Sort results by",
            options=["Highest Score", "Years of Experience (High to Low)", "Name (A-Z)", "Education Level (High to Low)"],
            index=0
        )
        
        # Apply filters
        filtered_candidates = []
        edu_level_map = {"All": 0, "Diploma+": 2, "Bachelor+": 3, "Master+": 4, "PhD": 5}
        target_edu = edu_level_map.get(edu_filter, 0)
        
        for c in ranked:
            name = c.get('name', '').lower()
            skills_str = " ".join(c.get('skills', [])).lower()
            search_val = search_query.lower().strip()
            
            if search_val and (search_val not in name and search_val not in skills_str):
                continue
            if c.get('years_experience', 0.0) < exp_filter:
                continue
            if c.get('education_level', 0) < target_edu:
                continue
            if c.get('final_score', 0.0) < score_filter:
                continue
                
            filtered_candidates.append(c)
            
        # Apply sorting
        if sort_by == "Highest Score":
            filtered_candidates = sorted(filtered_candidates, key=lambda x: x.get('final_score', 0), reverse=True)
        elif sort_by == "Years of Experience (High to Low)":
            filtered_candidates = sorted(filtered_candidates, key=lambda x: x.get('years_experience', 0.0), reverse=True)
        elif sort_by == "Name (A-Z)":
            filtered_candidates = sorted(filtered_candidates, key=lambda x: x.get('name', '').lower())
        elif sort_by == "Education Level (High to Low)":
            filtered_candidates = sorted(filtered_candidates, key=lambda x: x.get('education_level', 0), reverse=True)

        st.markdown(f"**Showing {len(filtered_candidates)} of {len(ranked)} candidates matching your filters**")

        # Pagination
        if filtered_candidates:
            items_per_page = 5
            total_pages = max(1, (len(filtered_candidates) + items_per_page - 1) // items_per_page)
            
            page_col1, page_col2 = st.columns([1, 4])
            with page_col1:
                page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
            with page_col2:
                st.caption(f"\nShowing page {page} of {total_pages}")
                
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_candidates = filtered_candidates[start_idx:end_idx]

            # Render Candidate Cards
            for idx, c in enumerate(page_candidates):
                score = c.get('final_score', 0)
                score_class = "score-high" if score >= 70 else "score-mid" if score >= 40 else "score-low"
                
                exp = c.get('explanation', {})
                rec = exp.get('hiring_recommendation', 'Consider')
                rec_badge = "⭐ Strong Hire" if rec == "Strong Hire" else "⚖️ Consider" if rec == "Consider" else "❌ Weak Hire"
                
                # Check shortlist tag
                shortlist_tag = "⭐ Shortlisted" if score >= score_threshold and c.get('rank', 99) <= top_k else "❌ Not Shortlisted"
                shortlist_color = "#16a34a" if shortlist_tag == "⭐ Shortlisted" else "#64748b"
                
                title = f"Rank #{c.get('rank', '?')} — {c.get('name', 'Unknown')} — Score: {score:.1f}% ({rec_badge})"
                
                with st.expander(title, expanded=(idx == 0 and page == 1)):
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        st.markdown("#### 📊 Score Breakdown")
                        sb = c.get('score_breakdown', {})
                        st.progress(sb.get('bert_score', 0.0), text=f"BERT Semantic Match: {sb.get('bert_score', 0.0)*100:.1f}%")
                        st.progress(sb.get('tfidf_score', 0.0), text=f"TF-IDF Keyword Match: {sb.get('tfidf_score', 0.0)*100:.1f}%")
                        st.progress(sb.get('skill_overlap_score', 0.0), text=f"Skill Overlap: {sb.get('skill_overlap_score', 0.0)*100:.1f}%")
                        
                    with col_b:
                        st.markdown("#### 👤 Profile Details")
                        edu_map = {0: 'Not detected', 1: '12th/HSC', 2: 'Diploma', 3: 'Bachelor (B.Tech/B.E)', 4: 'Master (M.Tech/MBA)', 5: 'PhD'}
                        st.markdown(f"🎓 **Education Level**: {edu_map.get(c.get('education_level', 0), 'Unknown')}")
                        st.markdown(f"💼 **Experience Duration**: {c.get('years_experience', 0.0)} years")
                        st.markdown(f"👥 **Inferred Gender**: {c.get('gender', 'Unknown')}")
                        st.markdown(f"🛡️ **Status**: <span style='color:{shortlist_color}; font-weight:700;'>{shortlist_tag}</span>", unsafe_allow_html=True)
                        
                        if c.get('email'):
                            st.markdown(f"📧 [Email Candidate](mailto:{c['email']}) (`{c['email']}`)")
                        if c.get('phone'):
                            st.markdown(f"📞 [Call Candidate](tel:{c['phone']}) (`{c['phone']}`)")

                    with col_c:
                        st.markdown("#### 🛠️ Skills Highlight")
                        jd_lower = jd_text.lower()
                        skills = c.get('skills', [])
                        matched = [s for s in skills if s in jd_lower]
                        unmatched = [s for s in skills if s not in jd_lower]
                        
                        skill_html = ""
                        for s in matched[:10]:
                            skill_html += f'<span class="skill-tag matched-skill">✓ {s}</span>'
                        for s in unmatched[:8]:
                            skill_html += f'<span class="skill-tag">{s}</span>'
                            
                        if skill_html:
                            st.markdown(skill_html, unsafe_allow_html=True)
                        else:
                            st.caption("No skills detected in resume.")
                    
                    st.divider()
                    
                    # Detailed AI Explanations
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        st.markdown("<h5 style='color:#16a34a; font-weight:600; margin-bottom:0.5rem;'>✅ Profile Strengths</h5>", unsafe_allow_html=True)
                        for strength in exp.get('strengths', []):
                            st.markdown(f"<div class='strength-box'>• {strength}</div>", unsafe_allow_html=True)
                    with col_e2:
                        st.markdown("<h5 style='color:#dc2626; font-weight:600; margin-bottom:0.5rem;'>⚠️ Profile Gaps</h5>", unsafe_allow_html=True)
                        for weakness in exp.get('weaknesses', []):
                            st.markdown(f"<div class='weakness-box'>• {weakness}</div>", unsafe_allow_html=True)
                    
                    st.markdown("##### 💡 Actionable Improvement Feedback")
                    for tip in exp.get('improvement_tips', []):
                        st.info(f"💬 {tip}")
                        
                    # Original text box preview
                    with st.expander("📄 View Original Resume Text (First 1000 characters)"):
                        st.text_area(
                            "Extracted text",
                            value=c.get('parsed', {}).get('raw_text', '')[:1000] + "\n...",
                            height=180,
                            disabled=True,
                            key=f"text_preview_{c.get('id', 0)}"
                        )
        else:
            st.warning("⚠️ No candidates match the applied filter criteria. Try broadening your settings.")


# ─── Tab 2: Analytics Dashboard ──────────────────────────────────────────────

with tab2:
    st.subheader("📊 Screening Analytics Dashboard")

    if 'results' not in st.session_state:
        st.markdown("""
        <div style="text-align: center; padding: 4rem 2rem; background: white; border-radius: 12px; border: 1px dashed #cbd5e1; margin-top: 2rem;">
            <h2 style="color: #64748b;">📭 No Screening Data Available</h2>
            <p style="color: #94a3b8; font-size:1.1rem; max-width:500px; margin: 0.5rem auto 1.5rem auto;">
                Upload resumes and run the AI screening pipeline in the <b>Candidate Screening</b> tab to populate charts, metrics, and insights here.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        results = st.session_state['results']
        ranked = results['ranked_candidates']
        
        # Shortlisted calculation
        shortlisted_cands = [c for c in ranked if c.get('final_score', 0) >= score_threshold and c.get('rank', 99) <= top_k]
        num_shortlisted = len(shortlisted_cands)
        num_rejected = len(ranked) - num_shortlisted
        avg_score = np.mean([c.get('final_score', 0) for c in ranked])
        
        # Dynamic metrics cards layout
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        
        with m_col1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Total Resumes</div>
                <div class="kpi-value">{results['total_screened']}</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Shortlisted</div>
                <div class="kpi-value" style="color:#16a34a;">{num_shortlisted}</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Not Shortlisted</div>
                <div class="kpi-value" style="color:#64748b;">{num_rejected}</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Average ATS Score</div>
                <div class="kpi-value" style="color:#312e81;">{avg_score:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col5:
            dpd = results['bias_report'].get('demographic_parity_difference', 0.0)
            bias_text = "LOW" if abs(dpd) < 0.05 else "MEDIUM" if abs(dpd) < 0.15 else "HIGH"
            bias_color = "#16a34a" if bias_text == "LOW" else "#d97706" if bias_text == "MEDIUM" else "#dc2626"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Bias (DPD)</div>
                <div class="kpi-value" style="color:{bias_color};">{dpd:.3f}</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Graphs
        c_col1, c_col2 = st.columns(2)
        
        with c_col1:
            st.markdown("### 📈 Score Distribution")
            df_scores = pd.DataFrame({'Final Score (%)': [c['final_score'] for c in ranked]})
            score_chart = alt.Chart(df_scores).mark_bar(color='#4f46e5', borderRadius=6).encode(
                alt.X("Final Score (%):Q", bin=alt.Bin(maxbins=10), title="Score Range (%)"),
                alt.Y('count()', title="Number of Candidates")
            ).properties(height=300)
            st.altair_chart(score_chart, use_container_width=True)
            
        with c_col2:
            st.markdown("### 🛠️ Common Candidate Skills")
            all_skills = []
            for c in ranked:
                all_skills.extend(c.get('skills', []))
            
            from collections import Counter
            skill_counts = Counter(all_skills)
            
            if skill_counts:
                df_skills = pd.DataFrame(skill_counts.most_common(10), columns=['Skill', 'Count'])
                skills_chart = alt.Chart(df_skills).mark_bar(color='#10b981', borderRadius=6).encode(
                    alt.Y('Skill:N', sort='-x', title='Detected Technical Skill'),
                    alt.X('Count:Q', title='Number of Resumes')
                ).properties(height=300)
                st.altair_chart(skills_chart, use_container_width=True)
            else:
                st.info("No skills detected in the current candidates to plot.")

        st.divider()
        st.markdown("### 👥 Candidate Rankings & Metric Details")
        
        details_list = []
        for c in ranked:
            details_list.append({
                "Rank": c.get('rank', 99),
                "Name": c.get('name', 'Unknown'),
                "Score": f"{c.get('final_score', 0):.1f}%",
                "Gender": c.get('gender', 'Unknown'),
                "Experience (Yrs)": c.get('years_experience', 0.0),
                "Skills Found": len(c.get('skills', [])),
                "Hiring Recommendation": c.get('explanation', {}).get('hiring_recommendation', 'Consider')
            })
        st.dataframe(pd.DataFrame(details_list), use_container_width=True, hide_index=True)


# ─── Tab 3: Fairness & Bias Audit ────────────────────────────────────────────

with tab3:
    st.subheader("⚖️ Algorithmic Fairness & Bias Audit Report")

    if 'results' not in st.session_state:
        st.markdown("""
        <div style="text-align: center; padding: 4rem 2rem; background: white; border-radius: 12px; border: 1px dashed #cbd5e1; margin-top: 2rem;">
            <h2 style="color: #64748b;">📭 No Screening Data Available</h2>
            <p style="color: #94a3b8; font-size:1.1rem; max-width:500px; margin: 0.5rem auto 1.5rem auto;">
                Upload resumes and run the AI screening pipeline in the <b>Candidate Screening</b> tab to generate the demographic fairness audit report here.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        results = st.session_state['results']
        bias = results['bias_report']
        dpd = bias.get('demographic_parity_difference', 0.0)

        # Status Banner
        if bias.get('bias_detected', False):
            st.markdown(f"""
            <div class="bias-warn">
                <h3>⚠️ {bias.get('recommendation', 'Bias Detected')}</h3>
                <p>The Demographic Parity Difference (DPD) between group selection rates is <strong>{dpd:.4f}</strong> (Target Threshold: &lt; 0.05). Algorithmic adjustment or threshold adjustments are recommended.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="bias-safe">
                <h3>✅ {bias.get('recommendation', 'No significant bias detected')}</h3>
                <p>The Demographic Parity Difference (DPD) is <strong>{dpd:.4f}</strong>, which falls within the acceptable parity index (DPD &lt; 0.05).</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        
        # Summary & Chart columns
        aud_col1, aud_col2 = st.columns(2)
        
        with aud_col1:
            st.markdown("### 📈 Core Bias Metrics")
            metrics_table = {
                "Total Candidates Screened": bias['total_candidates'],
                "Shortlist Score Threshold": f"{bias['shortlist_threshold']:.1f}%",
                "Total Shortlisted": bias['shortlisted_count'],
                "Shortlist Rate (Overall)": f"{(bias['shortlisted_count'] / max(bias['total_candidates'], 1)) * 100:.1f}%",
                "Demographic Parity Difference (DPD)": f"{dpd:.4f}",
                "Bias Severity Class": bias['bias_severity']
            }
            for label, val in metrics_table.items():
                st.markdown(f"**{label}**: {val}")
                
            st.divider()
            st.markdown("### 👥 Demographic Statistics")
            for group, stats in bias.get('group_stats', {}).items():
                st.markdown(f"📍 **{group}**")
                st.write(f"  - Count: {stats['count']} candidates")
                st.write(f"  - Average Score: {stats['avg_score']}%")
                st.write(f"  - Selection Rate: {stats['shortlist_rate']*100:.1f}%")
                
        with aud_col2:
            st.markdown("### 📊 Average Scores by Group")
            
            # Formulate df for plotting
            groups_data = []
            for grp, stats in bias.get('group_stats', {}).items():
                groups_data.append({
                    "Group": grp,
                    "Average Score (%)": stats['avg_score'],
                    "Selection Rate (%)": stats['shortlist_rate'] * 100
                })
            df_g = pd.DataFrame(groups_data)
            
            # Altair Group Average Score
            grp_score_chart = alt.Chart(df_g).mark_bar(borderRadius=6).encode(
                alt.X('Group:N', title='Demographic Group'),
                alt.Y('Average Score (%):Q', title='Avg Match Score (%)'),
                color=alt.Color('Group:N', scale=alt.Scale(range=['#4f46e5', '#ec4899', '#64748b']))
            ).properties(height=180)
            st.altair_chart(grp_score_chart, use_container_width=True)

            st.markdown("### 📊 Shortlist Rates by Group")
            # Altair Group Selection Rate
            grp_sel_chart = alt.Chart(df_g).mark_bar(borderRadius=6).encode(
                alt.X('Group:N', title='Demographic Group'),
                alt.Y('Selection Rate (%):Q', title='Shortlist Selection Rate (%)'),
                color=alt.Color('Group:N', scale=alt.Scale(range=['#10b981', '#f59e0b', '#64748b']))
            ).properties(height=180)
            st.altair_chart(grp_sel_chart, use_container_width=True)

        st.divider()
        st.markdown("### 🛡️ Mitigation Mechanisms Applied")
        if blind_screening:
            st.success("✅ **Pre-processing (Blind Screening) - ACTIVE**: Protected variables (gender-specific honorifics, pronouns, names, graduation years, phone, email names) were completely scrubbed from the resume texts before feeding them to the matching engine. This prevents keyword features and neural embeddings from mapping to proxies of protected attributes.")
        else:
            st.warning("⚠️ **Blind Screening is OFF**: Resumes were scored with name, graduation years, and pronouns intact. Enabling the 'Apply Blind Screening' toggle in the sidebar will sanitize the input data to remove proxy markers and reduce DPD.")

        st.info("""
        **System Bias Mitigation Strategies (Seminar Report, Chapter 6):**
        1. **Pre-processing (Blind Screening)**: Sanitizing input data to wipe out explicit or proxy markers of protected attributes before similarity calculations. *(Applied)*
        2. **In-processing (Sample Reweighting)**: Training matching algorithms (like XGBoost) by giving higher training weights to candidates from underrepresented groups to equalize prediction losses.
        3. **Post-processing (Threshold Alignment)**: Applying group-specific cut-offs (e.g. setting slightly different selection thresholds for Group A and Group B) to equalize True Positive Rates across groups (Equal Opportunity).
        """)
        st.caption(f"ℹ️ Note: {bias.get('note', '')}")


# ─── Tab 4: Methodology ───────────────────────────────────────────────────────

with tab4:
    st.subheader("🔬 6-Stage AI Resume Screening Pipeline Architecture")
    st.markdown("""
    This project implements the core architecture from the seminar thesis. Below is an overview of the stages:

    ```mermaid
    graph TD
        A[Stage 1: Resume Input] --> B[Stage 2: Preprocessing & Blinding]
        B --> C[Stage 3: Feature Extraction]
        C --> D[Stage 4: Job Description Matching]
        D --> E[Stage 5: Bias Auditing]
        E --> F[Stage 6: Explainable AI Results]
    ```

    | Stage | Stage Title | Core Technology | Description |
    | :--- | :--- | :--- | :--- |
    | **1** | **Resume Input** | `PyPDF2`, `python-docx` | Extracts raw unstructured string buffers from PDF, Word documents or text paste. |
    | **2** | **NLP Preprocessing & Blinding** | RegEx Engine | Tokenizes text, cleans symbols, and filters out protected attribute indicators (emails, phone numbers, graduation years, honorifics, pronouns). |
    | **3** | **Feature Extraction** | `Sentence-BERT` & `TF-IDF` | Extracts contextual vectors using `all-MiniLM-L6-v2` transformer and term frequency n-grams. |
    | **4** | **JD Matching** | Cosine Similarity | Computes cosine alignment between the candidate vector and the job description vector. Adds education and experience heuristics. |
    | **5** | **Demographic Bias Auditing** | `Fairlearn` & `AIF360` formulas | Audits selection rates and computes Demographic Parity Difference (DPD) to track systemic inequalities. |
    | **6** | **Explainable AI (XAI)** | Rule Heuristics & `SHAP` | Explains scoring factors, maps matching/missing skills, highlights strengths and weaknesses, and issues hiring recommendations. |

    ### 📏 Algorithmic Fairness Indices
    * **Demographic Parity Difference (DPD)**: Measures whether candidates from group A and group B have equal rates of selection.
      $$\\text{DPD} = | P(\\hat{Y} = 1 \\mid G = A) - P(\\hat{Y} = 1 \\mid G = B) |$$
      Target threshold: **$\\text{DPD} \\le 0.05$** (ideal parity is 0).
    * **Equal Opportunity Difference (EOD)**: Measures whether candidates who are qualified have equal chances of selection, regardless of group.
      $$\\text{EOD} = | \\text{TPR}_A - \\text{TPR}_B |$$
      Where $\\text{TPR}$ is the True Positive Rate of the groups.

    ### 📚 References
    1. Abhishek, K. et al. (2025). *Developing an Intelligent Resume Screening Tool for Mitigating Demographic Bias*. Wiley Applied Artificial Intelligence.
    2. Lo, J. et al. (2025). *Mitigating Bias in Automated Hiring: A Multi-Agent Framework using LLMs*. arXiv preprint arXiv:2501.0493.
    3. Raghavan, M. et al. (2020). *Mitigating Bias in Algorithmic Employment Decisions*. ACM Conference on Fairness, Accountability, and Transparency (FAccT).
    4. Lundberg, S. M. & Lee, S.-I. (2017). *A Unified Approach to Interpreting Model Predictions (SHAP)*. Advances in Neural Information Processing Systems (NeurIPS).
    """)
    
    st.caption("Developed by Chaitanya Nagane (Roll Number 33550) for Seminar presentation. Under supervision of AIML Department, PES's Modern College of Engineering, Pune.")

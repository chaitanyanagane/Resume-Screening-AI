# HireSense AI — Intelligent Resume Screening & Recruitment Platform

HireSense AI is a production-ready, full-stack enterprise recruitment and applicant tracking platform. It upgrades the data science Streamlit prototype into a modern, multi-tenant system built with a **FastAPI backend** (SQLite + JWT RBAC auth + BERT matching pipeline) and a high-fidelity **React + TypeScript + Framer Motion frontend** inspired by premium SaaS tools like Ashby and Linear.

---

## 🏗️ Platform Architecture Diagram

The system decouples the frontend client workspace from the machine learning scoring and database transaction layer:

```mermaid
graph TD
    subgraph Client Panel (React + TypeScript)
        A[Login / Register] --> B{Role Auth Router}
        B -->|Candidate| C[Candidate Dashboard]
        B -->|Recruiter| D[Recruiter Dashboard]
        B -->|Admin| E[Admin Control Panel]
        C & D & E --> F[Methodology Guide]
    end

    subgraph Service Layer (FastAPI Backend)
        C & D & E -->|REST APIs + JWT Token| G[FastAPI Router]
        G --> H[Auth & RBAC Handler]
        G --> I[Job Manager]
        G --> J[Resume Uploader & Parser]
        G --> K[AI Screening Pipeline]
        G --> L[Analytics Telemetry Engine]
        G --> M[Report / CSV Exporter]
    end

    subgraph Storage Layer
        H & I & J & K & L --> N[(SQLite Database: hiresense.db)]
    end

    subgraph NLP Core Engine
        K --> O[Sentence-BERT Embeddings]
        K --> P[TF-IDF N-Gram Vectorizer]
        K --> Q[Heuristic Demographic Auditor]
    end
```

---

## 🗄️ Database ER Diagram Schema

HireSense AI uses a local SQLite database (`hiresense.db`) with normalized, indexed relationships to track application lifecycles:

* **users**: Stores accounts. `role` CHECK constraint enforces `('candidate', 'recruiter', 'admin')`.
* **jobs**: Stores job postings created by Recruiters. Cascades deletion to linked applications.
* **candidate_profiles**: Contains parsed skills, education index, experience duration, and gender estimations.
* **applications**: Links candidate profiles to jobs. Stores overall ATS score, sub-scores (BERT, TF-IDF, skills overlap), weaknesses/strengths lists, review notes, and AI-generated interview questions.
* **activity_logs**: Stores system events and user actions for administrators to audit.

---

## 📂 Project Structure

```
resume_screening/
├── main.py                    ← FastAPI Backend application server
├── requirements.txt            ← Python backend package dependencies
├── hiresense.db                ← Local transactional SQLite database (created on startup)
├── README.md                   ← Project documentation (this file)
├── src/                        ← Python Backend Modules
│   ├── database.py             ← SQLite table setup & default data seedings
│   ├── auth.py                 ← Password hashing (bcrypt) and JWT RBAC dependencies
│   ├── exporter.py             ← CSV comparisons and profile report formatters
│   ├── resume_parser.py        ← Skill boundaries & qualification parser
│   ├── matcher.py              ← BERT + TF-IDF fallback similarity matcher
│   ├── pipeline.py             ← Master screening pipeline manager
│   ├── bias_auditor.py         ← Heuristic gender auditor
│   └── explainer.py            ← AI recommendations & strength/gap explainer
└── frontend/                   ← Single-Page React App (Vite + TS client)
    ├── package.json            ← Client packages (Framer Motion, Lucide icons)
    ├── index.html              ← Root mounting page
    ├── src/
    │   ├── main.tsx            ← Vite mounting point
    │   ├── App.tsx             ← Dashboard router, theme toggle, session state
    │   ├── index.css           ← Custom vanilla CSS Linear-inspired stylesheet
    │   └── views/
    │       ├── LoginRegister.tsx       ← Authentication & registration tabs
    │       ├── CandidateDashboard.tsx  ← Drag & drop upload, timeline tracking
    │       ├── RecruiterDashboard.tsx  ← Job builder, candidate comparisons matrix
    │       ├── AdminDashboard.tsx      ← Role management, system activity logs
    │       └── Methodology.tsx         ← Core NLP stage & formula walkthroughs
```

---

## 🔧 Installation & Quick Setup

Follow these steps to run the full-stack system locally:

### 1. Backend Server Setup
From the project root:
```bash
# 1. Activate python virtual environment
source venv/bin/activate

# 2. Install dependencies (adds FastAPI, Uvicorn, bcrypt, PyJWT)
pip install -r requirements.txt

# 3. Launch the FastAPI server
PYTHONPATH=. ./venv/bin/uvicorn main:app --reload --port 8000
```
*The database file `hiresense.db` is initialized and pre-seeded on server startup.*

### 2. Frontend Client Setup
In a new terminal window, navigate to the `frontend/` folder:
```bash
cd frontend

# 1. Install frontend packages
npm install

# 2. Run the Vite development server
npm run dev
```
*Vite will start the client dev server. Open the application link:*
🔗 **[http://localhost:5173](http://localhost:5173)**

---

## 🔐 Default Seeding Accounts (Sign In Credentials)

The database automatically seeds default credentials for immediate evaluation. Test role features by logging in with:

| Role | Username | Password | Key Actions |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@hiresense.ai` | `admin123` | View logs, manage user roles, platform statistics. |
| **Recruiter** | `recruiter@hiresense.ai` | `recruiter123` | Create/delete jobs, sort/search candidates matrix, write notes. |
| **Candidate** | `candidate@hiresense.ai` | `candidate123` | Upload resumes, browse jobs, apply, check application timeline. |

---

## 🔬 Core AI Matcher & Bias Mitigation Heuristics

* **Blind Screening (Stage 2)**: Strives for fairness. Strips candidate name, honorific, gender-identifying pronouns, phone, email, and graduation years before scoring to prevent age/gender proxy bias.
* **Semantic Vector Match (Stage 4)**: Maps JD requirements against resumes using the Sentence-BERT `all-MiniLM-L6-v2` neural model to evaluate conceptual alignment rather than strict keyword lookups.
* **Fairness Telemetry Audit (Stage 5)**: Resolves bias loops. Estimates applicant gender *before* blinding to compute the Demographic Parity Difference (DPD) across applicants, highlighting selection rates.

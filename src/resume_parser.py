"""
Stage 1 & 2: Resume Input and NLP Preprocessing
- Extracts text from PDF/DOCX
- Cleans and tokenizes text
- Uses regex-based NER for skills, experience, education
"""

import re
import os

# ─── Text Extraction ────────────────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text from a PDF resume."""
    try:
        import PyPDF2
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"[PDF extraction error: {e}]"


def extract_text_from_docx(file_path: str) -> str:
    """Extract raw text from a DOCX resume."""
    try:
        import docx
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return f"[DOCX extraction error: {e}]"


def extract_text(file_path: str) -> str:
    """Auto-detect format and extract text."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        return extract_text_from_docx(file_path)
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


# ─── NLP Preprocessing ──────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Clean raw text: lowercase, remove special chars, normalize whitespace."""
    text = text.lower()
    text = re.sub(r'[^\w\s@.\-+]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ─── Feature Extraction (Regex-based NER) ────────────────────────────────────

SKILLS_KEYWORDS = [
    # Programming languages
    "python", "java", "c++", "c#", "javascript", "typescript", "r", "scala",
    "sql", "go", "rust", "kotlin", "swift", "matlab", "php", "ruby",
    # ML/AI
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "reinforcement learning", "tensorflow", "pytorch",
    "keras", "scikit-learn", "xgboost", "bert", "transformers", "llm",
    # Data
    "data analysis", "data science", "pandas", "numpy", "matplotlib",
    "seaborn", "tableau", "power bi", "excel", "sql", "mongodb", "postgresql",
    # Cloud & Tools
    "aws", "azure", "gcp", "docker", "kubernetes", "git", "github",
    "linux", "spark", "hadoop", "airflow", "mlflow",
    # Web
    "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
    "html", "css", "rest api", "graphql",
]

EDUCATION_KEYWORDS = {
    "phd": 5, "doctorate": 5,
    "m.tech": 4, "mtech": 4, "m.e": 4, "master": 4, "msc": 4, "mba": 4,
    "b.tech": 3, "btech": 3, "b.e": 3, "bachelor": 3, "bsc": 3, "be": 3,
    "diploma": 2,
    "12th": 1, "hsc": 1,
}


def extract_skills(text: str) -> list:
    """Extract skills from resume text."""
    text_lower = text.lower()
    found = []
    for skill in SKILLS_KEYWORDS:
        # Determine if skill ends with a word character
        if re.search(r'\w$', skill):
            pattern = r'\b' + re.escape(skill) + r'\b'
        else:
            pattern = r'\b' + re.escape(skill) + r'(?=[^a-zA-Z0-9+#]|$)'
        if re.search(pattern, text_lower):
            found.append(skill)
    return found


def extract_education_level(text: str) -> int:
    """Return numeric education level (1-5) using word boundaries, with case-sensitive check for 'BE'."""
    max_level = 0
    for keyword, level in EDUCATION_KEYWORDS.items():
        if keyword == "be":
            # Match 'BE' or 'B.E' case-sensitively to avoid matching lowercase 'be' verb
            pattern = r'\b(BE|B\.E)\b'
            if re.search(pattern, text):
                max_level = max(max_level, level)
        else:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text.lower()):
                max_level = max(max_level, level)
    return max_level


def extract_years_of_experience(text: str) -> float:
    """Estimate years of experience by finding the maximum duration stated in text."""
    patterns = [
        r'(\d+\.?\d*)\s*\+?\s*years?\s+of\s+experience',
        r'(\d+\.?\d*)\s*\+?\s*yrs?\s+experience',
        r'experience\s+of\s+(\d+\.?\d*)\s*\+?\s*years?',
        r'(\d+\.?\d*)\s*\+?\s*years?\s+working',
        r'(\d+\.?\d*)\s*\+?\s*years?\s+in\b',
        r'(\d+\.?\d*)\s*\+?\s*yrs?\s+in\b',
    ]
    found_years = [0.0]
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        for m in matches:
            try:
                found_years.append(float(m))
            except ValueError:
                pass
    return max(found_years)


def extract_email(text: str) -> str:
    """Extract email address."""
    match = re.search(r'[\w.\-+]+@[\w.\-]+\.\w+', text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    """Extract phone number."""
    match = re.search(r'(\+91[-\s]?)?[6-9]\d{9}|(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})', text)
    return match.group(0) if match else ""


def extract_name(text: str) -> str:
    """Heuristic: first non-empty line (excluding resume headers) is likely the name."""
    ignore_headers = {
        'resume', 'cv', 'curriculum', 'vitae', 'curriculum vitae', 
        'summary', 'profile', 'contact', 'experience', 'education', 
        'skills', 'projects', 'about', 'about me'
    }
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.lower() in ignore_headers:
            continue
        if any(line.lower().startswith(h + ' ') for h in ignore_headers):
            continue
        if len(line) > 2 and len(line) < 60 and not any(c in line for c in ['@', ':', '/']):
            words = line.split()
            if all(w.replace('.','').isalpha() for w in words[:3]):
                return line[:50]
    return "Unknown"


def parse_resume(text: str) -> dict:
    """Full resume parsing pipeline. Returns structured dict."""
    skills = extract_skills(text)
    return {
        "raw_text": text,
        "skills": skills,
        "num_skills": len(skills),
        "education_level": extract_education_level(text),
        "years_experience": extract_years_of_experience(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "name": extract_name(text),
    }

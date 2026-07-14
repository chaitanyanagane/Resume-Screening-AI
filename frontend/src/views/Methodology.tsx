import { Database, Filter, Layers, CheckCircle2, Shield, Eye } from "lucide-react";

export default function Methodology() {
  const stages = [
    {
      num: 1,
      title: "Resume Input",
      tech: "PyPDF2 / Docx",
      icon: <Database size={24} />,
      desc: "Accepts uploads or pasted text. Auto-detects document file signature and runs custom textual streams extractor."
    },
    {
      num: 2,
      title: "NLP Preprocessing & Blinding",
      tech: "RegEx Sanitizer",
      icon: <Filter size={24} />,
      desc: "Normalizes spacing and cleans syntax. Scrubbing engine strips out pronouns, honorifics, emails, phone numbers, and graduation dates to prevent gender and age biases (Pre-processing mitigation)."
    },
    {
      num: 3,
      title: "Feature Extraction",
      tech: "S-BERT & TF-IDF",
      icon: <Layers size={24} />,
      desc: "Extracts term n-grams using TfidfVectorizer and generates high-dimensional contextual embeddings using the 'all-MiniLM-L6-v2' Sentence-BERT model."
    },
    {
      num: 4,
      title: "JD Cosine Matching",
      tech: "Scikit-Learn Math",
      icon: <CheckCircle2 size={24} />,
      desc: "Calculates the cosine similarity index between job description vectors and candidate resume vectors. Compiles weighted experience bonuses and academic credential scales."
    },
    {
      num: 5,
      title: "Demographic Bias Auditing",
      tech: "Fairlearn Standards",
      icon: <Shield size={24} />,
      desc: "Scans original text (pre-blinding) for demographic markers to group candidates. Calculates Demographic Parity Difference (DPD) to audit hiring pipelines for adverse impact."
    },
    {
      num: 6,
      title: "Explainable AI (XAI)",
      tech: "Rule & SHAP Insights",
      icon: <Eye size={24} />,
      desc: "Constructs feature attribution lists, flags strengths and missing skills, calculates tips, drafts interview questions, and assigns hiring recommendations."
    }
  ];

  return (
    <div style={{ maxWidth: "900px", margin: "0 auto", paddingBottom: "3rem" }}>
      <div className="card-table-wrapper" style={{ padding: "2.5rem", marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: "700", marginBottom: "0.5rem" }}>Core Engine Methodology</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.95rem" }}>
          HireSense AI implements a rigorous **6-stage pipeline** to parse, evaluate, audit, and explain candidate resumes without introducing historic dataset biases.
        </p>
        
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", marginTop: "2rem" }}>
          {stages.map((stage) => (
            <div 
              key={stage.num} 
              style={{ display: "flex", gap: "1.5rem", padding: "1.25rem", border: "1px solid var(--border-color)", borderRadius: "10px", backgroundColor: "var(--bg-app)" }}
            >
              <div 
                style={{ width: "50px", height: "50px", borderRadius: "8px", backgroundColor: "var(--bg-card)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)", border: "1px solid var(--border-color)" }}
              >
                {stage.icon}
              </div>
              <div style={{ flexGrow: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
                  <h4 style={{ fontWeight: "700", fontSize: "0.95rem" }}>Stage {stage.num}: {stage.title}</h4>
                  <span style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--accent)" }}>{stage.tech}</span>
                </div>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>{stage.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Fairness Mathematics */}
      <div className="card-table-wrapper" style={{ padding: "2rem" }}>
        <h3 style={{ fontSize: "1.1rem", fontWeight: "700", marginBottom: "1rem" }}>Fairness Metrics Formulae</h3>
        
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
          <div style={{ padding: "1rem", border: "1px solid var(--border-color)", borderRadius: "8px", backgroundColor: "var(--bg-app)" }}>
            <strong style={{ color: "var(--text-main)", display: "block", marginBottom: "0.25rem" }}>Demographic Parity Difference (DPD)</strong>
            <span>
              DPD checks whether selection rates (the percentage of applicants shortlisted) are equal across groups (e.g. Male vs Female).
            </span>
            <div style={{ padding: "0.5rem", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "4px", margin: "0.5rem 0", fontFamily: "monospace", textAlign: "center" }}>
              DPD = | P(Shortlist = 1 | Gender = Male) - P(Shortlist = 1 | Gender = Female) |
            </div>
            <span>HireSense AI flags a potential audit warning if DPD exceeds **0.05** (5% selection parity gap).</span>
          </div>

          <div style={{ padding: "1rem", border: "1px solid var(--border-color)", borderRadius: "8px", backgroundColor: "var(--bg-app)" }}>
            <strong style={{ color: "var(--text-main)", display: "block", marginBottom: "0.25rem" }}>Equal Opportunity Difference (EOD)</strong>
            <span>
              EOD checks whether qualified candidates have equal chances of being shortlisted, regardless of group (equality of True Positive Rates).
            </span>
            <div style={{ padding: "0.5rem", background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "4px", margin: "0.5rem 0", fontFamily: "monospace", textAlign: "center" }}>
              EOD = | True Positive Rate (Male) - True Positive Rate (Female) |
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

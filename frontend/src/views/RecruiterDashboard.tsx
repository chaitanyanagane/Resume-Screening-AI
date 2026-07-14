import { useState, useEffect } from "react";
import { Trash2, FileSpreadsheet, FileText, ChevronRight, X, Star } from "lucide-react";

interface RecruiterDashboardProps {
  token: string;
}

export default function RecruiterDashboard({ token }: RecruiterDashboardProps) {
  const [jobs, setJobs] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  
  // Job Form State
  const [title, setTitle] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [skillsReq, setSkillsReq] = useState<string>("");
  const [expReq, setExpReq] = useState<string>("");
  const [eduReq, setEduReq] = useState<number>(3); // Default Bachelor
  const [location, setLocation] = useState<string>("Remote");
  
  // Search & Filter State
  const [selectedJob, setSelectedJob] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [minScore, setMinScore] = useState<number>(0);
  const [sortField, setSortField] = useState<string>("score");

  // Selected Candidate Drawer State
  const [selectedApp, setSelectedApp] = useState<any | null>(null);
  const [reviewNotes, setReviewNotes] = useState<string>("");
  const [reviewStatus, setReviewStatus] = useState<string>("reviewing");

  const [loading, setLoading] = useState<boolean>(true);
  const [formMsg, setFormMsg] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      // 1. Fetch active jobs list
      const jobsRes = await fetch("http://localhost:8000/api/jobs", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const jobsData = await jobsRes.json();
      setJobs(jobsData);

      // 2. Fetch candidates applications list
      const appsRes = await fetch("http://localhost:8000/api/applications", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const appsData = await appsRes.json();
      setApplications(appsData);

      // 3. Fetch analytics telemetry
      const analRes = await fetch("http://localhost:8000/api/analytics", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const analData = await analRes.json();
      setAnalytics(analData);
    } catch (err) {
      console.error("Error fetching recruiter dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Post Job Action
  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormMsg(null);
    try {
      const skillsArray = skillsReq.split(",").map(s => s.trim().toLowerCase()).filter(s => s);
      const expVal = parseFloat(expReq) || 0.0;
      
      const res = await fetch("http://localhost:8000/api/jobs", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          title, description, location,
          skills_required: skillsArray,
          experience_required: expVal,
          education_required: eduReq
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create job");
      
      setFormMsg("Job post created successfully!");
      setTitle("");
      setDescription("");
      setSkillsReq("");
      setExpReq("");
      fetchData();
    } catch (err: any) {
      alert(err.message || "Error posting job opening");
    }
  };

  // Delete Job Action
  const handleDeleteJob = async (jobId: number) => {
    if (!confirm("Are you sure you want to delete this job post? All applications for this job will be deleted.")) return;
    try {
      const res = await fetch(`http://localhost:8000/api/jobs/${jobId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Deletion failed");
      
      fetchData();
    } catch (err) {
      alert("Error deleting job");
    }
  };

  // Update Candidate Review Status
  const handleUpdateStatus = async () => {
    if (!selectedApp) return;
    try {
      const res = await fetch(`http://localhost:8000/api/applications/${selectedApp.id}/status`, {
        method: "PUT",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ status: reviewStatus, notes: reviewNotes })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to update candidate state");
      
      alert("Candidate review saved successfully!");
      setSelectedApp(null);
      fetchData();
    } catch (err: any) {
      alert(err.message || "Error updating candidate status");
    }
  };

  // Trigger candidates list download CSV
  const handleDownloadCSV = () => {
    const url = selectedJob === "all" 
      ? "http://localhost:8000/api/applications/export/csv" 
      : `http://localhost:8000/api/applications/export/csv?job_id=${selectedJob}`;
    
    window.open(url, "_blank");
  };

  if (loading) {
    return <div style={{ textAlign: "center", padding: "3rem" }}>Loading recruiter analytics...</div>;
  }

  // Filter applications list
  const filtered = applications.filter((app) => {
    if (selectedJob !== "all" && app.job_id.toString() !== selectedJob) return false;
    
    // Search query match
    const name = app.candidate_name.toLowerCase();
    const skills = app.skills ? app.skills.join(" ").toLowerCase() : "";
    const query = searchQuery.toLowerCase().trim();
    if (query && !name.includes(query) && !skills.includes(query)) return false;
    
    // Limits
    if (app.score < minScore) return false;
    
    return true;
  });

  // Apply sorting
  const sorted = [...filtered].sort((a, b) => {
    if (sortField === "score") return b.score - a.score;
    if (sortField === "experience") return b.years_experience - a.years_experience;
    if (sortField === "education") return b.education_level - a.education_level;
    return 0;
  });

  const getEducationName = (level: number) => {
    const eduMap: any = { 0: 'N/A', 1: '12th/HSC', 2: 'Diploma', 3: 'Bachelor (B.Tech/B.E)', 4: 'Master (M.Tech/MBA)', 5: 'PhD' };
    return eduMap[level] || "Unknown";
  };

  return (
    <div>
      {/* Metrics Row */}
      {analytics && (
        <div className="metrics-row">
          <div className="metric-card">
            <span className="metric-label">Active Jobs Posted</span>
            <span className="metric-val">{analytics.active_jobs}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Total Applications Received</span>
            <span className="metric-val">{analytics.total_applications}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Average ATS Score</span>
            <span className="metric-val">{analytics.average_score}%</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Shortlisted Candidates</span>
            <span className="metric-val" style={{ color: "var(--success)" }}>
              {analytics.funnel ? analytics.funnel.shortlisted : 0}
            </span>
          </div>
        </div>
      )}

      {/* Main Layout Split */}
      <div className="layout-split">
        
        {/* Left Section: Jobs Builder and Candidates Table */}
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
          
          {/* Active Job Postings */}
          <div className="card-table-wrapper">
            <div className="section-header">
              <h3>Create Job Posting</h3>
            </div>
            
            <form onSubmit={handleCreateJob} style={{ padding: "1.5rem" }}>
              {formMsg && (
                <div className="badge badge-success" style={{ display: "block", marginBottom: "1rem", textTransform: "none" }}>
                  {formMsg}
                </div>
              )}
              
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
                <div className="form-group">
                  <label className="form-label">Job Title</label>
                  <input type="text" className="form-input" required placeholder="e.g. Machine Learning Engineer" value={title} onChange={(e) => setTitle(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Location</label>
                  <input type="text" className="form-input" placeholder="e.g. Pune, India or Remote" value={location} onChange={(e) => setLocation(e.target.value)} />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Job Description</label>
                <textarea className="form-input" style={{ height: "100px", resize: "none" }} required placeholder="Enter requirements, responsibilities, and qualifications..." value={description} onChange={(e) => setDescription(e.target.value)} />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1.2fr", gap: "1.5rem" }}>
                <div className="form-group">
                  <label className="form-label">Required Skills (Comma separated)</label>
                  <input type="text" className="form-input" placeholder="e.g. python, bert, sql, git" value={skillsReq} onChange={(e) => setSkillsReq(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Min Experience (Yrs)</label>
                  <input type="number" className="form-input" step="0.5" placeholder="e.g. 3.0" value={expReq} onChange={(e) => setExpReq(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Min Education level</label>
                  <select className="form-input" value={eduReq} onChange={(e) => setEduReq(parseInt(e.target.value))}>
                    <option value={1}>12th/HSC</option>
                    <option value={2}>Diploma</option>
                    <option value={3}>Bachelor's degree</option>
                    <option value={4}>Master's degree</option>
                    <option value={5}>PhD</option>
                  </select>
                </div>
              </div>

              <button type="submit" className="form-btn" style={{ width: "auto", padding: "0.6rem 2rem" }}>Post Job Opening</button>
            </form>

            {jobs.length > 0 && (
              <div style={{ padding: "0 1.5rem 1.5rem 1.5rem" }}>
                <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "0.75rem", fontWeight: "600" }}>Active Job Openings</h4>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
                  {jobs.map((j) => (
                    <div key={j.id} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.5rem 0.85rem", border: "1px solid var(--border-color)", borderRadius: "8px", backgroundColor: "var(--bg-app)" }}>
                      <span style={{ fontSize: "0.85rem", fontWeight: "600" }}>{j.title}</span>
                      <button onClick={() => handleDeleteJob(j.id)} style={{ border: "none", background: "none", color: "var(--danger)", cursor: "pointer", display: "flex" }}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Candidates Comparison Table */}
          <div className="card-table-wrapper">
            <div className="section-header">
              <h3>Candidate Comparison Matrix</h3>
              <button className="btn-secondary" onClick={handleDownloadCSV}>
                <FileSpreadsheet size={16} />
                <span>Export CSV</span>
              </button>
            </div>

            {/* Grid Search & Filters */}
            <div style={{ padding: "1.25rem 1.5rem 0.5rem 1.5rem" }} className="grid-filters">
              <input type="text" className="form-input" placeholder="Search by name or skills..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
              
              <select className="form-input" value={selectedJob} onChange={(e) => setSelectedJob(e.target.value)}>
                <option value="all">All Jobs</option>
                {jobs.map((j) => (
                  <option key={j.id} value={j.id.toString()}>{j.title}</option>
                ))}
              </select>

              <select className="form-input" value={sortField} onChange={(e) => setSortField(e.target.value)}>
                <option value="score">Sort: Match Score</option>
                <option value="experience">Sort: Experience</option>
                <option value="education">Sort: Education</option>
              </select>

              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input 
                  type="number" 
                  className="form-input" 
                  style={{ width: "70px", padding: "0.4rem" }} 
                  placeholder="Score" 
                  value={minScore || ""} 
                  onChange={(e) => setMinScore(parseFloat(e.target.value) || 0)} 
                />
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>% Min</span>
              </div>
            </div>

            {/* Candidates Table Grid */}
            <div style={{ overflowX: "auto" }}>
              <table className="hs-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Candidate</th>
                    <th>ATS Score</th>
                    <th>Experience</th>
                    <th>Education</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: "center", color: "var(--text-muted)", padding: "2.5rem" }}>
                        No candidate applications match the filter criteria.
                      </td>
                    </tr>
                  ) : (
                    sorted.map((app, index) => {
                      const score = app.score;
                      const ringClass = score >= 70 ? "ats-high" : score >= 40 ? "ats-mid" : "ats-low";
                      const statusClass = app.status === "shortlisted" ? "badge-success" : app.status === "rejected" ? "badge-danger" : app.status === "reviewing" ? "badge-warning" : "badge-neutral";
                      
                      return (
                        <tr key={app.id}>
                          <td><strong>#{index + 1}</strong></td>
                          <td>
                            <div style={{ display: "flex", flexDirection: "column" }}>
                              <span style={{ fontWeight: "600" }}>{app.candidate_name}</span>
                              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Target: {app.job_title}</span>
                            </div>
                          </td>
                          <td>
                            <div className={`ats-score-ring ${ringClass}`}>{score.toFixed(0)}%</div>
                          </td>
                          <td>{app.years_experience} Years</td>
                          <td>{getEducationName(app.education_level)}</td>
                          <td>
                            <span className={`badge ${statusClass}`}>{app.status}</span>
                          </td>
                          <td>
                            <button 
                              className="btn-secondary" 
                              style={{ padding: "0.3rem 0.6rem" }}
                              onClick={() => {
                                setSelectedApp(app);
                                setReviewNotes(app.notes || "");
                                setReviewStatus(app.status || "reviewing");
                              }}
                            >
                              <span>AI Scorecard</span>
                              <ChevronRight size={14} />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Side: AI Detail Scorecard Drawer */}
        <div>
          {!selectedApp ? (
            <div className="ai-detail-drawer" style={{ textAlign: "center", padding: "4rem 2rem", borderStyle: "dashed" }}>
              <Star size={36} style={{ color: "var(--text-muted)", margin: "0 auto 1rem auto" }} />
              <h4>AI Evaluation Profile</h4>
              <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
                Select a candidate from the table matrix to view their matching scores, strengths, weaknesses, custom interview questions, and write recruiter evaluation notes.
              </p>
            </div>
          ) : (
            <div className="ai-detail-drawer">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
                <h3 style={{ fontSize: "1.1rem", fontWeight: "700" }}>AI Screening Scorecard</h3>
                <button onClick={() => setSelectedApp(null)} style={{ border: "none", background: "none", cursor: "pointer", color: "var(--text-muted)" }}>
                  <X size={20} />
                </button>
              </div>

              {/* Match Score Gauge */}
              <div style={{ display: "flex", alignItems: "center", gap: "1rem", padding: "1rem", border: "1px solid var(--border-color)", borderRadius: "8px", backgroundColor: "var(--bg-app)", marginBottom: "1.5rem" }}>
                <div className={`ats-score-ring ${
                  selectedApp.score >= 70 ? 'ats-high' : selectedApp.score >= 40 ? 'ats-mid' : 'ats-low'
                }`} style={{ width: "50px", height: "50px", fontSize: "1rem" }}>
                  {selectedApp.score.toFixed(0)}%
                </div>
                <div>
                  <h4 style={{ fontSize: "0.95rem", fontWeight: "700" }}>{selectedApp.candidate_name}</h4>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>AI Rec: {selectedApp.hiring_recommendation}</span>
                </div>
              </div>

              {/* Progress Meters */}
              <div style={{ marginBottom: "1.5rem" }}>
                <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: "600", marginBottom: "0.75rem" }}>Score Breakdown</h4>
                
                <div className="meter-wrapper">
                  <div className="meter-header">
                    <span>BERT Semantic Match</span>
                    <span>{(selectedApp.score_breakdown.bert_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="meter-bar-container">
                    <div className="meter-bar" style={{ width: `${selectedApp.score_breakdown.bert_score * 100}%` }}></div>
                  </div>
                </div>

                <div className="meter-wrapper">
                  <div className="meter-header">
                    <span>TF-IDF Keyword Similarity</span>
                    <span>{(selectedApp.score_breakdown.tfidf_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="meter-bar-container">
                    <div className="meter-bar" style={{ width: `${selectedApp.score_breakdown.tfidf_score * 100}%` }}></div>
                  </div>
                </div>

                <div className="meter-wrapper">
                  <div className="meter-header">
                    <span>Skills Keyword Overlap</span>
                    <span>{(selectedApp.score_breakdown.skill_overlap_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="meter-bar-container">
                    <div className="meter-bar" style={{ width: `${selectedApp.score_breakdown.skill_overlap_score * 100}%` }}></div>
                  </div>
                </div>
              </div>

              {/* Strengths & Gaps */}
              <div style={{ marginBottom: "1.5rem" }}>
                <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: "600", marginBottom: "0.5rem" }}>AI Assessment</h4>
                
                <span style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--success)" }}>Profile Strengths</span>
                <ul className="bullet-points" style={{ marginTop: "0.2rem", marginBottom: "0.75rem" }}>
                  {selectedApp.explanation.strengths && selectedApp.explanation.strengths.map((s: string, i: number) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>

                <span style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--danger)" }}>Profile Gaps</span>
                <ul className="bullet-points" style={{ marginTop: "0.2rem" }}>
                  {selectedApp.explanation.weaknesses && selectedApp.explanation.weaknesses.map((w: string, i: number) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>

              {/* Generated Interview Questions */}
              <div style={{ marginBottom: "1.5rem" }}>
                <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: "600", marginBottom: "0.5rem" }}>Suggested Interview Questions</h4>
                <div style={{ backgroundColor: "var(--bg-app)", padding: "0.85rem", borderRadius: "8px", border: "1px solid var(--border-color)", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  {selectedApp.interview_questions && selectedApp.interview_questions.map((q: string, i: number) => (
                    <p key={i} style={{ marginBottom: "0.4rem" }}><strong>{i+1}.</strong> {q}</p>
                  ))}
                </div>
              </div>

              {/* Review & Status */}
              <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
                <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: "600", marginBottom: "0.75rem" }}>Recruiter Review</h4>
                
                <div className="form-group">
                  <label className="form-label">Hiring Status</label>
                  <select className="form-input" value={reviewStatus} onChange={(e) => setReviewStatus(e.target.value)}>
                    <option value="reviewing">Under Review</option>
                    <option value="shortlisted">Shortlist Candidate</option>
                    <option value="rejected">Reject Application</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Review Evaluation Notes</label>
                  <textarea 
                    className="form-input" 
                    style={{ height: "80px", resize: "none" }} 
                    placeholder="Write recruiter notes here..." 
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                  />
                </div>

                <div style={{ display: "flex", gap: "0.75rem" }}>
                  <button className="form-btn" style={{ flex: 2 }} onClick={handleUpdateStatus}>Save Review</button>
                  <a 
                    href={`http://localhost:8000/api/applications/${selectedApp.id}/export/report`}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary" 
                    style={{ flex: 1, textDecoration: "none", display: "inline-flex", justifyContent: "center" }}
                    title="Download candidate report"
                  >
                    <FileText size={16} />
                  </a>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from "react";
import { Upload, FileText, Clock } from "lucide-react";

interface CandidateDashboardProps {
  token: string;
}

export default function CandidateDashboard({ token }: CandidateDashboardProps) {
  const [profile, setProfile] = useState<any>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  
  const [loading, setLoading] = useState<boolean>(true);
  const [uploading, setUploading] = useState<boolean>(false);
  const [applyLoading, setApplyLoading] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  // Fetch candidate profile, jobs list, and applications list
  const fetchData = async () => {
    try {
      // 1. Candidate Profile
      const profRes = await fetch("http://localhost:8000/api/candidates/profile", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const profData = await profRes.json();
      setProfile(profData.has_profile ? profData : null);

      // 2. Browse Jobs list
      const jobsRes = await fetch("http://localhost:8000/api/jobs", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const jobsData = await jobsRes.json();
      setJobs(jobsData);

      // 3. Applications
      const appsRes = await fetch("http://localhost:8000/api/applications", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const appsData = await appsRes.json();
      setApplications(appsData);
    } catch (err) {
      console.error("Error fetching candidate data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Handle Drag & Drop / File Select Upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    
    setUploading(true);
    setMsg(null);
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/candidates/profile/upload", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData,
      });
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }
      
      setMsg("Resume uploaded and parsed successfully!");
      fetchData();
    } catch (err: any) {
      alert(err.message || "Error uploading resume");
    } finally {
      setUploading(false);
    }
  };

  // Apply to Job
  const handleApply = async (jobId: number) => {
    setApplyLoading(jobId.toString());
    try {
      const res = await fetch("http://localhost:8000/api/applications", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify({ job_id: jobId }),
      });
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Application failed");
      }
      
      alert("Applied successfully! AI screening has ranked your resume.");
      fetchData();
    } catch (err: any) {
      alert(err.message || "Error submitting application");
    } finally {
      setApplyLoading(null);
    }
  };

  if (loading) {
    return <div style={{ textAlign: "center", padding: "3rem" }}>Loading dashboard details...</div>;
  }

  const getEducationName = (level: number) => {
    const eduMap: any = { 0: 'N/A', 1: '12th/HSC', 2: 'Diploma', 3: 'Bachelor (B.Tech/B.E)', 4: 'Master (M.Tech/MBA)', 5: 'PhD' };
    return eduMap[level] || "Unknown";
  };

  return (
    <div>
      {/* Metrics Panel */}
      <div className="metrics-row">
        <div className="metric-card">
          <span className="metric-label">Applications Submitted</span>
          <span className="metric-val">{applications.length}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Active Jobs Available</span>
          <span className="metric-val">{jobs.length}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Profile Status</span>
          <span className="metric-val" style={{ fontSize: "1.25rem", color: profile ? "var(--success)" : "var(--danger)" }}>
            {profile ? "✓ Resume Active" : "❌ Resume Missing"}
          </span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "2rem", marginTop: "2rem" }}>
        
        {/* Left Side: Upload & Browse Jobs */}
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
          
          {/* Resume Upload Card */}
          <div className="card-table-wrapper" style={{ padding: "1.5rem" }}>
            <h3 style={{ marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <FileText size={20} className="text-indigo-600" />
              <span>Resume & Profile Details</span>
            </h3>
            
            {msg && (
              <div className="badge badge-success" style={{ display: "block", marginBottom: "1rem", textTransform: "none" }}>
                {msg}
              </div>
            )}

            {!profile ? (
              <div className="dropzone">
                <input 
                  type="file" 
                  id="resumeFile" 
                  style={{ display: "none" }} 
                  onChange={handleFileUpload}
                  accept=".pdf,.docx,.txt"
                />
                <label htmlFor="resumeFile" style={{ cursor: "pointer", display: "block" }}>
                  <Upload size={36} className="dropzone-icon" style={{ margin: "0 auto 1rem auto" }} />
                  <h4>{uploading ? "Parsing Document..." : "Drag & Drop or Click to upload Resume"}</h4>
                  <p>Supports PDF, DOCX and TXT format (Max 5MB)</p>
                </label>
              </div>
            ) : (
              <div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
                  <div>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: "600" }}>Years of Experience</span>
                    <h4 style={{ fontSize: "1.1rem" }}>{profile.years_experience} Years</h4>
                  </div>
                  <div>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: "600" }}>Education level</span>
                    <h4 style={{ fontSize: "1.1rem" }}>{getEducationName(profile.education_level)}</h4>
                  </div>
                </div>

                <div style={{ marginBottom: "1rem" }}>
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: "600" }}>Extracted Skills</span>
                  <div className="skills-container">
                    {profile.skills && profile.skills.map((s: string, i: number) => (
                      <span key={i} className="skill-tag">{s}</span>
                    ))}
                  </div>
                </div>

                <label htmlFor="resumeReplace" className="btn-secondary" style={{ cursor: "pointer", display: "inline-flex" }}>
                  <Upload size={16} />
                  <span>{uploading ? "Uploading..." : "Replace Resume"}</span>
                </label>
                <input 
                  type="file" 
                  id="resumeReplace" 
                  style={{ display: "none" }} 
                  onChange={handleFileUpload} 
                  accept=".pdf,.docx,.txt"
                  disabled={uploading}
                />
              </div>
            )}
          </div>

          {/* Browse Active Jobs */}
          <div className="card-table-wrapper">
            <div className="section-header">
              <h3>Browse Active Openings</h3>
            </div>
            
            <div style={{ padding: "1rem" }}>
              {jobs.length === 0 ? (
                <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "1.5rem" }}>
                  No jobs currently open. Check back later!
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  {jobs.map((j) => {
                    const alreadyApplied = applications.some((a) => a.job_title === j.title);
                    return (
                      <div 
                        key={j.id} 
                        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "1rem", border: "1px solid var(--border-color)", borderRadius: "8px", backgroundColor: "var(--bg-card)" }}
                      >
                        <div>
                          <h4 style={{ fontWeight: "600" }}>{j.title}</h4>
                          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{j.location} • Req YOE: {j.experience_required}+ yrs</span>
                        </div>
                        <button 
                          className="btn-secondary"
                          style={{
                            backgroundColor: alreadyApplied ? "var(--success-bg)" : "var(--accent)",
                            color: alreadyApplied ? "var(--success)" : "var(--text-white)",
                            border: "none",
                            padding: "0.4rem 0.8rem",
                            cursor: alreadyApplied ? "default" : "pointer"
                          }}
                          disabled={alreadyApplied || !profile || applyLoading === j.id.toString()}
                          onClick={() => handleApply(j.id)}
                        >
                          {alreadyApplied 
                            ? "Applied" 
                            : !profile 
                            ? "Upload Resume to Apply" 
                            : applyLoading === j.id.toString() 
                            ? "Applying..." 
                            : "Apply Now"
                          }
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Side: Timeline Track Applications */}
        <div className="card-table-wrapper" style={{ padding: "1.5rem" }}>
          <h3 style={{ marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Clock size={20} className="text-indigo-600" />
            <span>Application Status Timeline</span>
          </h3>

          {applications.length === 0 ? (
            <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "3rem" }}>
              No applications submitted yet. Browse jobs to get started.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
              {applications.map((app) => {
                // Determine step classes for status timeline
                const status = app.status; // 'applied', 'reviewing', 'shortlisted', 'rejected'
                
                return (
                  <div key={app.id} style={{ border: "1px solid var(--border-color)", padding: "1.25rem", borderRadius: "10px", backgroundColor: "var(--bg-app)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
                      <div>
                        <h4 style={{ fontWeight: "700" }}>{app.job_title}</h4>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Submitted: {new Date(app.created_at).toLocaleDateString()}</span>
                      </div>
                      <span className={`badge ${
                        status === 'shortlisted' ? 'badge-success' : 
                        status === 'rejected' ? 'badge-danger' : 
                        status === 'reviewing' ? 'badge-warning' : 'badge-neutral'
                      }`}>
                        {status.toUpperCase()}
                      </span>
                    </div>

                    {/* Timeline */}
                    <div className="timeline">
                      <div className={`timeline-item completed`}>
                        <div className="timeline-dot"></div>
                        <div className="timeline-content">
                          <div className="timeline-title">Application Submitted</div>
                          <div className="timeline-date">Verified & scrubbed for blind screening</div>
                        </div>
                      </div>

                      <div className={`timeline-item ${['reviewing', 'shortlisted', 'rejected'].includes(status) ? 'completed' : 'active'}`}>
                        <div className="timeline-dot"></div>
                        <div className="timeline-content">
                          <div className="timeline-title">AI Screening Completed</div>
                          <div className="timeline-date">Matched score: {app.score.toFixed(1)}%</div>
                        </div>
                      </div>

                      <div className={`timeline-item ${status === 'shortlisted' ? 'completed' : status === 'rejected' ? 'active' : ''}`}>
                        <div className="timeline-dot"></div>
                        <div className="timeline-content">
                          <div className="timeline-title">Recruiter Review</div>
                          <div className="timeline-date">
                            {status === 'shortlisted' ? "Selected for Interviews!" : 
                             status === 'rejected' ? "Application Closed" : 
                             "Reviewing details"}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect } from "react";
import { 
  Trash2, FileSpreadsheet, FileText, X, Star, 
  Briefcase, Users, Plus, Search, 
  Filter, Edit, Copy, Archive, Check, RotateCcw, 
  Sparkles, Pin, Bell, Download, Trash, Eye, 
  List, Send
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

interface RecruiterDashboardProps {
  token: string;
}

export default function RecruiterDashboard({ token }: RecruiterDashboardProps) {
  // Navigation tabs: 'home' | 'jobs' | 'pipeline' | 'candidates' | 'analytics'
  const [activeTab, setActiveTab] = useState<string>("home");
  
  // Core datasets
  const [jobs, setJobs] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [activityLogs, setActivityLogs] = useState<any[]>([]);
  
  // Job Form Modal State
  const [showJobModal, setShowJobModal] = useState<boolean>(false);
  const [editingJobId, setEditingJobId] = useState<number | null>(null);
  const [jobTitle, setJobTitle] = useState<string>("");
  const [jobDescription, setJobDescription] = useState<string>("");
  const [jobSkillsReq, setJobSkillsReq] = useState<string>("");
  const [jobPreferredSkills, setJobPreferredSkills] = useState<string>("");
  const [jobResponsibilities, setJobResponsibilities] = useState<string>("");
  const [jobExpReq, setJobExpReq] = useState<string>("");
  const [jobEduReq, setJobEduReq] = useState<number>(3);
  const [jobLocation, setJobLocation] = useState<string>("Remote");
  const [jobDepartment, setJobDepartment] = useState<string>("Engineering");
  const [jobEmploymentType, setJobEmploymentType] = useState<string>("Full-time");
  const [jobSalaryRange, setJobSalaryRange] = useState<string>("");
  const [jobHiringManager, setJobHiringManager] = useState<string>("");

  // Search & Multi-Filters
  const [selectedJob, setSelectedJob] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [filterMinScore, setFilterMinScore] = useState<number>(0);
  const [filterExpMin, setFilterExpMin] = useState<string>("");
  const [filterExpMax, setFilterExpMax] = useState<string>("");
  const [filterLocation, setFilterLocation] = useState<string>("all");
  const [filterDegree, setFilterDegree] = useState<string>("all");
  const [filterRecLevel, setFilterRecLevel] = useState<string>("all");
  const [filterStage, setFilterStage] = useState<string>("all");
  const [sortField, setSortField] = useState<string>("score");

  // Selected Candidate Drawer
  const [selectedApp, setSelectedApp] = useState<any | null>(null);
  const [drawerTab, setDrawerTab] = useState<string>("evaluation"); // 'evaluation' | 'interviews' | 'notes' | 'email'
  
  // Interviews state
  const [interviews, setInterviews] = useState<any[]>([]);
  const [newIntInterviewer, setNewIntInterviewer] = useState<string>("");
  const [newIntType, setNewIntType] = useState<string>("technical");
  const [newIntDate, setNewIntDate] = useState<string>("");
  const [newIntLink, setNewIntLink] = useState<string>("");
  const [feedbackIntId, setFeedbackIntId] = useState<number | null>(null);
  const [feedbackText, setFeedbackText] = useState<string>("");
  const [feedbackRating, setFeedbackRating] = useState<number>(5);

  // Recruiter Notes state
  const [notes, setNotes] = useState<any[]>([]);
  const [newNoteText, setNewNoteText] = useState<string>("");
  const [newNotePinned, setNewNotePinned] = useState<boolean>(false);
  const [newNoteMentions, setNewNoteMentions] = useState<string>("");

  // Candidate Comparison side-by-side Matrix
  const [selectedCompareIds, setSelectedCompareIds] = useState<number[]>([]);
  const [showCompareModal, setShowCompareModal] = useState<boolean>(false);

  // Email state
  const [emailSubject, setEmailSubject] = useState<string>("");
  const [emailBody, setEmailBody] = useState<string>("");

  // Toast Feedback Alerts
  const [toasts, setToasts] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Show Toast Helper
  const showToast = (message: string, type: "success" | "warning" | "danger" | "info" = "success") => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const fetchData = async () => {
    try {
      // 1. Fetch jobs list
      const jobsRes = await fetch(`${API_BASE}/api/jobs`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (jobsRes.ok) {
        const jobsData = await jobsRes.json();
        setJobs(jobsData);
      }

      // 2. Fetch candidates applications list
      const appsRes = await fetch(`${API_BASE}/api/applications`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (appsRes.ok) {
        const appsData = await appsRes.json();
        setApplications(appsData);
      }

      // 3. Fetch analytics telemetry
      const analRes = await fetch(`${API_BASE}/api/analytics`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (analRes.ok) {
        const analData = await analRes.json();
        setAnalytics(analData);
      }

      // 4. Fetch notifications
      const notifRes = await fetch(`${API_BASE}/api/notifications`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (notifRes.ok) {
        const notifData = await notifRes.json();
        setNotifications(notifData);
      }

      // 5. Fetch Activity Logs
      const logsRes = await fetch(`${API_BASE}/api/admin/logs`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setActivityLogs(logsData);
      }

    } catch (err) {
      console.error("Error loading recruiter dashboard datasets:", err);
      showToast("Error connection failed to fetch data", "danger");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token]);

  // Fetch drawer related notes & interviews when selected app changes
  useEffect(() => {
    if (selectedApp) {
      fetchAppInterviews(selectedApp.id);
      fetchAppNotes(selectedApp.id);
      
      // Auto fill standard recruiter email invite templates
      setEmailSubject(`Interview Schedule Request — ${selectedApp.candidate_name}`);
      setEmailBody(`Hi ${selectedApp.candidate_name},\n\nHope you are doing well!\n\nOur team has reviewed your AI screening profile score for the Job Opening and we are excited to move you to the next stage.\n\nWe would like to schedule a virtual session with our engineers. Please let us know your availability.\n\nBest Regards,\nRecruiting Team`);
    }
  }, [selectedApp]);

  const fetchAppInterviews = async (appId: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/applications/${appId}/interviews`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setInterviews(data);
      }
    } catch (err) {}
  };

  const fetchAppNotes = async (appId: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/applications/${appId}/notes/list`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setNotes(data);
      }
    } catch (err) {}
  };

  // Job Actions CRUD
  const handleSaveJob = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const skillsArray = jobSkillsReq.split(",").map(s => s.trim().toLowerCase()).filter(s => s);
      const prefSkillsArray = jobPreferredSkills.split(",").map(s => s.trim().toLowerCase()).filter(s => s);
      const respArray = jobResponsibilities.split("\n").map(r => r.trim()).filter(r => r);
      const expVal = parseFloat(jobExpReq) || 0.0;
      
      const payload = {
        title: jobTitle,
        description: jobDescription,
        skills_required: skillsArray,
        experience_required: expVal,
        education_required: jobEduReq,
        location: jobLocation,
        department: jobDepartment,
        employment_type: jobEmploymentType,
        salary_range: jobSalaryRange || null,
        preferred_skills: prefSkillsArray,
        responsibilities: respArray,
        hiring_manager: jobHiringManager || null
      };

      let res;
      if (editingJobId) {
        // Edit job
        res = await fetch(`${API_BASE}/api/jobs/${editingJobId}`, {
          method: "PUT",
          headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
      } else {
        // Create job
        res = await fetch(`${API_BASE}/api/jobs`, {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
      }

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save job opening");
      }

      showToast(editingJobId ? "Job opening updated successfully!" : "New Job post created successfully!", "success");
      setShowJobModal(false);
      resetJobForm();
      fetchData();
    } catch (err: any) {
      showToast(err.message || "Error saving job listing", "danger");
    }
  };

  const resetJobForm = () => {
    setEditingJobId(null);
    setJobTitle("");
    setJobDescription("");
    setJobSkillsReq("");
    setJobPreferredSkills("");
    setJobResponsibilities("");
    setJobExpReq("");
    setJobEduReq(3);
    setJobLocation("Remote");
    setJobDepartment("Engineering");
    setJobEmploymentType("Full-time");
    setJobSalaryRange("");
    setJobHiringManager("");
  };

  const handleEditJobClick = (job: any) => {
    setEditingJobId(job.id);
    setJobTitle(job.title);
    setJobDescription(job.description);
    setJobSkillsReq(job.skills_required ? job.skills_required.join(", ") : "");
    setJobPreferredSkills(job.preferred_skills ? job.preferred_skills.join(", ") : "");
    setJobResponsibilities(job.responsibilities ? job.responsibilities.join("\n") : "");
    setJobExpReq(job.experience_required.toString());
    setJobEduReq(job.education_required);
    setJobLocation(job.location || "Remote");
    setJobDepartment(job.department || "Engineering");
    setJobEmploymentType(job.employment_type || "Full-time");
    setJobSalaryRange(job.salary_range || "");
    setJobHiringManager(job.hiring_manager || "");
    
    setShowJobModal(true);
  };

  const handleDuplicateJob = async (jobId: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${jobId}/duplicate`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Duplication request failed");
      showToast("Job duplicated successfully!", "success");
      fetchData();
    } catch (err) {
      showToast("Failed to duplicate job post", "danger");
    }
  };

  const handleToggleJobStatus = async (jobId: number, currentStatus: string) => {
    const action = currentStatus === "active" ? "close" : "reopen";
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${jobId}/${action}`, {
        method: "PUT",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to change job hiring status");
      showToast(action === "close" ? "Hiring closed for this job post" : "Hiring reopened for this job post", "warning");
      fetchData();
    } catch (err) {
      showToast("Failed to toggle job hiring status", "danger");
    }
  };

  const handleDeleteJob = async (jobId: number) => {
    if (!confirm("Are you sure you want to delete this job opening? All associated applicant evaluations and records will be deleted permanently.")) return;
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${jobId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Deletion request failed");
      showToast("Job opening deleted successfully", "success");
      fetchData();
    } catch (err) {
      showToast("Error deleting job listing", "danger");
    }
  };

  // Pipeline transitions stage
  const handleMoveCandidateStage = async (appId: number, targetStage: string) => {
    // Optimistic UI updates
    setApplications((prev) =>
      prev.map((app) => (app.id === appId ? { ...app, status: targetStage } : app))
    );
    if (selectedApp && selectedApp.id === appId) {
      setSelectedApp((prev: any) => ({ ...prev, status: targetStage }));
    }

    try {
      const res = await fetch(`${API_BASE}/api/applications/${appId}/stage`, {
        method: "PUT",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ stage: targetStage })
      });
      if (!res.ok) throw new Error("Backend update failed");
      showToast(`Candidate moved successfully to stage: ${targetStage}`, "success");
      fetchData();
    } catch (err) {
      showToast("Failed to transition candidate stage", "danger");
      fetchData(); // Rollback local state from server
    }
  };

  // Schedule Interview Actions
  const handleScheduleInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedApp) return;
    try {
      const res = await fetch(`${API_BASE}/api/applications/${selectedApp.id}/interviews`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          interviewer: newIntInterviewer,
          type: newIntType,
          scheduled_at: newIntDate,
          meeting_link: newIntLink || null
        })
      });
      if (!res.ok) throw new Error("Failed to schedule interview");
      
      showToast("Interview scheduled and email invitation dispatched!", "success");
      setNewIntInterviewer("");
      setNewIntLink("");
      setNewIntDate("");
      fetchAppInterviews(selectedApp.id);
      fetchData();
    } catch (err: any) {
      showToast(err.message || "Failed to schedule session", "danger");
    }
  };

  // Submit Feedback Rating
  const handleSaveInterviewFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedbackIntId || !selectedApp) return;
    try {
      const res = await fetch(`${API_BASE}/api/interviews/${feedbackIntId}/feedback`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          status: "completed",
          feedback: feedbackText,
          rating: feedbackRating
        })
      });
      if (!res.ok) throw new Error("Failed to record feedback evaluation");
      
      showToast("Interview feedback scorecard saved successfully!", "success");
      setFeedbackIntId(null);
      setFeedbackText("");
      fetchAppInterviews(selectedApp.id);
      fetchData();
    } catch (err: any) {
      showToast(err.message || "Failed to submit feedback", "danger");
    }
  };

  // Notes CRUD
  const handleSaveNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedApp) return;
    try {
      const mentionsArray = newNoteMentions.split(",").map(m => m.trim()).filter(m => m);
      const res = await fetch(`${API_BASE}/api/applications/${selectedApp.id}/notes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          note_text: newNoteText,
          is_pinned: newNotePinned ? 1 : 0,
          mentions: mentionsArray
        })
      });
      if (!res.ok) throw new Error("Failed to save note");
      
      showToast("Recruiter evaluation note logged successfully!", "success");
      setNewNoteText("");
      setNewNotePinned(false);
      setNewNoteMentions("");
      fetchAppNotes(selectedApp.id);
    } catch (err: any) {
      showToast(err.message || "Failed to log note", "danger");
    }
  };

  const handleTogglePinNote = async (noteId: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/notes/${noteId}/pin`, {
        method: "PUT",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Note pin failed");
      showToast("Pin toggled", "info");
      if (selectedApp) fetchAppNotes(selectedApp.id);
    } catch (err) {
      showToast("Failed to toggle note pin", "danger");
    }
  };

  const handleDeleteNote = async (noteId: number) => {
    if (!confirm("Delete this recruiter note?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/notes/${noteId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to delete note");
      showToast("Note deleted successfully", "warning");
      if (selectedApp) fetchAppNotes(selectedApp.id);
    } catch (err) {
      showToast("Failed to delete note", "danger");
    }
  };

  // Mock send email
  const handleSendEmail = (e: React.FormEvent) => {
    e.preventDefault();
    showToast(`Email successfully sent to candidate ${selectedApp.candidate_name}!`, "success");
    setEmailSubject("");
    setEmailBody("");
    setDrawerTab("evaluation");
  };

  const handleMarkNotificationRead = async (notifId: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/notifications/${notifId}/read`, {
        method: "PUT",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        setNotifications((prev) => prev.map(n => n.id === notifId ? { ...n, is_read: 1 } : n));
      }
    } catch (err) {}
  };

  const handleDownloadCSV = () => {
    const url = selectedJob === "all" 
      ? `${API_BASE}/api/applications/export/excel` 
      : `${API_BASE}/api/applications/export/excel?job_id=${selectedJob}`;
    window.open(url, "_blank");
    showToast("Exporting ATS applications CSV list...", "info");
  };

  const handleCompareClick = () => {
    if (selectedCompareIds.length !== 2) {
      showToast("Please select exactly two candidate profiles to run side-by-side matrices", "warning");
      return;
    }
    setShowCompareModal(true);
  };

  const toggleSelectCompare = (id: number) => {
    setSelectedCompareIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter(c => c !== id);
      } else {
        if (prev.length >= 2) {
          showToast("Comparison is limited to two profiles concurrently. Deselect a candidate to select a different one.", "info");
          return prev;
        }
        return [...prev, id];
      }
    });
  };

  // Get education helpers
  const getEducationName = (level: number) => {
    const eduMap: any = { 0: 'N/A', 1: '12th/HSC', 2: 'Diploma', 3: 'Bachelor', 4: 'Master', 5: 'PhD' };
    return eduMap[level] || "Unknown";
  };

  if (loading) {
    return (
      <div style={{ padding: "4rem", textAlign: "center" }}>
        <div className="skeleton-line" style={{ width: "20%", height: "2rem", margin: "0 auto 1.5rem auto" }}></div>
        <div className="skeleton-line" style={{ width: "80%", height: "1.25rem", margin: "0 auto 1rem auto" }}></div>
        <div className="skeleton-line" style={{ width: "60%", height: "1.25rem", margin: "0 auto 3rem auto" }}></div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1.5rem" }}>
          <div className="skeleton-line" style={{ height: "150px", borderRadius: "12px" }}></div>
          <div className="skeleton-line" style={{ height: "150px", borderRadius: "12px" }}></div>
          <div className="skeleton-line" style={{ height: "150px", borderRadius: "12px" }}></div>
        </div>
      </div>
    );
  }

  // Filter application algorithms
  const filteredApps = applications.filter((app) => {
    if (selectedJob !== "all" && app.job_id.toString() !== selectedJob) return false;
    
    // Multi-filters
    if (app.score < filterMinScore) return false;
    if (filterExpMin !== "" && app.years_experience < parseFloat(filterExpMin)) return false;
    if (filterExpMax !== "" && app.years_experience > parseFloat(filterExpMax)) return false;
    if (filterLocation !== "" && filterLocation !== "all" && !(app.candidate_location || "").toLowerCase().includes(filterLocation.toLowerCase())) return false;
    if (filterDegree !== "all" && app.education_level < parseInt(filterDegree)) return false;
    if (filterRecLevel !== "all" && app.hiring_recommendation !== filterRecLevel) return false;
    if (filterStage !== "all" && app.status !== filterStage) return false;

    // Search query match
    const q = searchQuery.toLowerCase().trim();
    if (q) {
      const nameMatch = app.candidate_name.toLowerCase().includes(q);
      const skillsMatch = app.skills ? app.skills.join(" ").toLowerCase().includes(q) : false;
      const colMatch = (app.resume_text || "").toLowerCase().includes(q);
      const emailMatch = (app.candidate_email || "").toLowerCase().includes(q);
      if (!nameMatch && !skillsMatch && !colMatch && !emailMatch) return false;
    }

    return true;
  });

  // Sort applications
  const sortedApps = [...filteredApps].sort((a, b) => {
    if (sortField === "score") return b.score - a.score;
    if (sortField === "experience") return b.years_experience - a.years_experience;
    if (sortField === "education") return b.education_level - a.education_level;
    return 0;
  });

  // Unread notification count
  const unreadNotifCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="recruiter-container">
      {/* Toast Alert Drawer */}
      <div className="toast-wrapper">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            {t.message}
          </div>
        ))}
      </div>

      {/* Recruiter Top Ribbon Actions */}
      <div className="recruiter-header">
        <div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: "700", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Sparkles size={20} style={{ color: "var(--accent)" }} />
            <span>Enterprise Recruiter Suite</span>
          </h2>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
            Manage job posts, interviews, candidate pipelines, and side-by-side screening scorecards.
          </p>
        </div>

        {/* Global Toolbar and Tabs */}
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          {/* Unread Notifications Bell */}
          <div className="notif-bell-container" style={{ position: "relative" }}>
            <button className="btn-secondary" style={{ padding: "0.5rem 0.75rem", borderRadius: "100px" }} title="Notification panel">
              <Bell size={18} />
              {unreadNotifCount > 0 && (
                <span className="notif-badge">{unreadNotifCount}</span>
              )}
            </button>
            
            {/* Simple Floating Dropdown */}
            <div className="notif-dropdown">
              <div className="notif-header">Notifications ({unreadNotifCount} unread)</div>
              <div className="notif-list">
                {notifications.length === 0 ? (
                  <div className="notif-empty">No alerts received</div>
                ) : (
                  notifications.map((n) => (
                    <div key={n.id} className={`notif-item ${!n.is_read ? 'notif-unread' : ''}`} onClick={() => handleMarkNotificationRead(n.id)}>
                      <div className="notif-title">{n.title}</div>
                      <div className="notif-msg">{n.message}</div>
                      <div className="notif-time">{new Date(n.created_at).toLocaleTimeString()}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <button className="btn-primary" onClick={() => { resetJobForm(); setShowJobModal(true); }}>
            <Plus size={16} />
            <span>Create Job</span>
          </button>
        </div>
      </div>

      {/* Tab Navigation Menu */}
      <div className="ats-tabs-bar">
        <button className={`ats-tab-btn ${activeTab === 'home' ? 'active' : ''}`} onClick={() => setActiveTab("home")}>
          <List size={16} />
          <span>Dashboard Home</span>
        </button>
        <button className={`ats-tab-btn ${activeTab === 'jobs' ? 'active' : ''}`} onClick={() => setActiveTab("jobs")}>
          <Briefcase size={16} />
          <span>Job Openings ({jobs.length})</span>
        </button>
        <button className={`ats-tab-btn ${activeTab === 'pipeline' ? 'active' : ''}`} onClick={() => setActiveTab("pipeline")}>
          <RotateCcw size={16} />
          <span>Hiring Pipeline</span>
        </button>
        <button className={`ats-tab-btn ${activeTab === 'candidates' ? 'active' : ''}`} onClick={() => setActiveTab("candidates")}>
          <Users size={16} />
          <span>Candidate Center ({applications.length})</span>
        </button>
        <button className={`ats-tab-btn ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab("analytics")}>
          <FileSpreadsheet size={16} />
          <span>Analytics Reports</span>
        </button>
      </div>

      {/* ─── TAB CONTENT 1: HOME ────────────────────────────────────────────── */}
      {activeTab === "home" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
          
          {/* Executive KPI Stats Cards Grid */}
          {analytics && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1.25rem" }}>
              <div className="metric-card">
                <span className="metric-label">Total Job Openings</span>
                <span className="metric-val">{analytics.total_jobs}</span>
                <span className="metric-sub">{analytics.active_jobs} Active | {analytics.closed_jobs} Closed</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Total Applications</span>
                <span className="metric-val">{analytics.total_applications}</span>
                <span className="metric-sub">Across all posts</span>
              </div>
              <div className="metric-card">
                <span className="metric-label font-accent">Interviews Scheduled</span>
                <span className="metric-val" style={{ color: "var(--accent)" }}>{analytics.interviews_scheduled}</span>
                <span className="metric-sub">Screening & Technical</span>
              </div>
              <div className="metric-card">
                <span className="metric-label font-success">Offers Dispatched</span>
                <span className="metric-val" style={{ color: "var(--success)" }}>{analytics.offers_released}</span>
                <span className="metric-sub">Hiring decision pending</span>
              </div>
              <div className="metric-card">
                <span className="metric-label font-success">Selected Hires</span>
                <span className="metric-val" style={{ color: "var(--success)" }}>{analytics.selected_candidates}</span>
                <span className="metric-sub">Success Rate: {analytics.hiring_success_rate}%</span>
              </div>
              <div className="metric-card">
                <span className="metric-label font-danger">Rejected Applications</span>
                <span className="metric-val" style={{ color: "var(--danger)" }}>{analytics.rejected_candidates}</span>
                <span className="metric-sub">Screening fallouts</span>
              </div>
            </div>
          )}

          {/* Quick Actions Shortcuts Banner */}
          <div style={{ padding: "1.5rem", border: "1px solid var(--border-color)", borderRadius: "12px", backgroundColor: "var(--bg-card)" }}>
            <h4 style={{ fontSize: "0.9rem", fontWeight: "700", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "1rem" }}>
              Quick Recruiter Actions
            </h4>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              <button className="btn-secondary" onClick={() => { resetJobForm(); setShowJobModal(true); }}>
                <Plus size={16} />
                <span>Post Job Opening</span>
              </button>
              <button className="btn-secondary" onClick={() => setActiveTab("candidates")}>
                <Search size={16} />
                <span>Search Candidates</span>
              </button>
              <button className="btn-secondary" onClick={() => handleDownloadCSV()}>
                <FileSpreadsheet size={16} />
                <span>Export Candidates CSV</span>
              </button>
              <button className="btn-secondary" onClick={() => setActiveTab("analytics")}>
                <FileText size={16} />
                <span>View Analytics Data</span>
              </button>
            </div>
          </div>

          {/* Split Row: Recent Activity Logs and Notification Feed */}
          <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: "2rem" }}>
            {/* Activity Logs */}
            <div className="card-table-wrapper" style={{ padding: "1.5rem" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: "700", marginBottom: "1.25rem" }}>Recruiter Activity Feed</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem", maxHeight: "400px", overflowY: "auto" }}>
                {activityLogs.length === 0 ? (
                  <div style={{ color: "var(--text-muted)", textAlign: "center", padding: "2rem" }}>No recruiter activities recorded yet</div>
                ) : (
                  activityLogs.map((log) => (
                    <div key={log.id} style={{ display: "flex", justifyContent: "space-between", paddingBottom: "0.85rem", borderBottom: "1px solid var(--border-color)", fontSize: "0.85rem" }}>
                      <div style={{ display: "flex", flexDirection: "column" }}>
                        <span style={{ fontWeight: "600" }}>{log.details}</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>By {log.user_email} ({log.user_role})</span>
                      </div>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", alignSelf: "center" }}>
                        {new Date(log.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Notification center summaries */}
            <div className="card-table-wrapper" style={{ padding: "1.5rem" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: "700", marginBottom: "1.25rem" }}>ATS System Alerts</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                {notifications.slice(0, 5).map((n) => (
                  <div key={n.id} style={{ padding: "0.75rem", borderRadius: "8px", border: "1px solid var(--border-color)", backgroundColor: n.is_read ? "var(--bg-app)" : "var(--success-bg)", position: "relative" }}>
                    <div style={{ fontSize: "0.85rem", fontWeight: "700" }}>{n.title}</div>
                    <div style={{ fontSize: "0.8" + "rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>{n.message}</div>
                    {!n.is_read && (
                      <button onClick={() => handleMarkNotificationRead(n.id)} style={{ border: "none", background: "none", cursor: "pointer", color: "var(--success)", position: "absolute", top: "8px", right: "8px" }} title="Dismiss">
                        <Check size={14} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB CONTENT 2: JOBS BOARD ──────────────────────────────────────── */}
      {activeTab === "jobs" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
          
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ fontSize: "1.2rem", fontWeight: "700" }}>Corporate Job Openings ({jobs.length})</h3>
            <button className="btn-primary" onClick={() => { resetJobForm(); setShowJobModal(true); }}>
              <Plus size={16} />
              <span>Post Job Opening</span>
            </button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1.5rem" }}>
            {jobs.length === 0 ? (
              <div style={{ gridColumn: "1/-1", textAlign: "center", padding: "4rem 2rem", border: "1px dashed var(--border-color)", borderRadius: "12px" }}>
                <Briefcase size={40} style={{ color: "var(--text-muted)", margin: "0 auto 1rem auto" }} />
                <h4>No Jobs Posted Yet</h4>
                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "0.5rem" }}>
                  Add a job description spec to begin scoring candidate resumes automatically.
                </p>
              </div>
            ) : (
              jobs.map((job) => (
                <div key={job.id} style={{ display: "flex", flexDirection: "column", padding: "1.5rem", border: "1px solid var(--border-color)", borderRadius: "12px", backgroundColor: "var(--bg-card)", boxShadow: "var(--card-shadow)", position: "relative" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                    <div>
                      <span className={`badge ${job.status === 'active' ? 'badge-success' : 'badge-danger'}`} style={{ marginBottom: "0.5rem" }}>
                        {job.status === 'active' ? 'Active Hiring' : 'Archived'}
                      </span>
                      <h4 style={{ fontSize: "1.1rem", fontWeight: "700", color: "var(--text-main)" }}>{job.title}</h4>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{job.department} · {job.employment_type}</span>
                    </div>
                  </div>

                  <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", flexGrow: 1, lineClamp: 3, display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden", marginBottom: "1rem" }}>
                    {job.description}
                  </p>

                  <div style={{ fontSize: "0.8rem", marginBottom: "1rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                    <div><strong>Hiring Manager:</strong> {job.hiring_manager || "Not Assigned"}</div>
                    <div><strong>Salary Range:</strong> {job.salary_range || "Competitive"}</div>
                    <div><strong>Location:</strong> {job.location || "Remote"}</div>
                    <div><strong>Min Experience:</strong> {job.experience_required} Years</div>
                  </div>

                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem", marginBottom: "1.5rem" }}>
                    {job.skills_required && job.skills_required.slice(0, 4).map((s: string, idx: number) => (
                      <span key={idx} style={{ fontSize: "0.7rem", padding: "0.2rem 0.5rem", borderRadius: "4px", backgroundColor: "var(--bg-app)", border: "1px solid var(--border-color)" }}>{s}</span>
                    ))}
                    {job.skills_required && job.skills_required.length > 4 && (
                      <span style={{ fontSize: "0.7rem", padding: "0.2rem 0.5rem", color: "var(--text-muted)" }}>+{job.skills_required.length - 4} more</span>
                    )}
                  </div>

                  <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
                    <button className="btn-secondary" style={{ padding: "0.4rem 0.6rem" }} onClick={() => handleEditJobClick(job)} title="Edit details">
                      <Edit size={14} />
                    </button>
                    <button className="btn-secondary" style={{ padding: "0.4rem 0.6rem" }} onClick={() => handleDuplicateJob(job.id)} title="Duplicate spec">
                      <Copy size={14} />
                    </button>
                    <button className="btn-secondary" style={{ padding: "0.4rem 0.6rem", color: job.status === 'active' ? 'var(--warning)' : 'var(--success)' }} onClick={() => handleToggleJobStatus(job.id, job.status)} title={job.status === 'active' ? 'Close hiring' : 'Reopen hiring'}>
                      {job.status === 'active' ? <Archive size={14} /> : <RotateCcw size={14} />}
                    </button>
                    <button className="btn-secondary" style={{ padding: "0.4rem 0.6rem", color: "var(--danger)" }} onClick={() => handleDeleteJob(job.id)} title="Delete posting">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ─── TAB CONTENT 3: HIRING PIPELINE KANBAN ──────────────────────────── */}
      {activeTab === "pipeline" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ fontSize: "1.2rem", fontWeight: "700" }}>Visual Kanban Hiring Lanes</h3>
            <select className="form-input" style={{ width: "250px" }} value={selectedJob} onChange={(e) => setSelectedJob(e.target.value)}>
              <option value="all">Display All Job Vacancies</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id.toString()}>{j.title}</option>
              ))}
            </select>
          </div>

          <div className="kanban-pipeline-wrapper">
            {[
              { id: "applied", label: "Applied", color: "#64748b" },
              { id: "screening", label: "Screening", color: "#3b82f6" },
              { id: "technical_interview", label: "Technical Round", color: "#8b5cf6" },
              { id: "manager_round", label: "Manager Review", color: "#ec4899" },
              { id: "hr_interview", label: "HR Session", color: "#f59e0b" },
              { id: "offer", label: "Offer Out", color: "#10b981" },
              { id: "selected", label: "Hired 🎉", color: "#10b981" },
              { id: "rejected", label: "Declined ✕", color: "#ef4444" }
            ].map((lane) => {
              const laneApps = applications.filter(app => {
                if (selectedJob !== "all" && app.job_id.toString() !== selectedJob) return false;
                return app.status === lane.id;
              });

              return (
                <div key={lane.id} className="kanban-column">
                  <div className="kanban-column-header" style={{ borderTop: `4px solid ${lane.color}` }}>
                    <span className="kanban-column-title">{lane.label}</span>
                    <span className="kanban-column-count">{laneApps.length}</span>
                  </div>

                  <div className="kanban-cards-feed">
                    {laneApps.length === 0 ? (
                      <div className="kanban-empty-state">No candidates</div>
                    ) : (
                      laneApps.map((app) => (
                        <div key={app.id} className="kanban-card" onClick={() => setSelectedApp(app)}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                            <span style={{ fontWeight: "700", fontSize: "0.85rem" }}>{app.candidate_name}</span>
                            <span className={`ats-score-ring ${app.score >= 70 ? 'ats-high' : app.score >= 40 ? 'ats-mid' : 'ats-low'}`} style={{ width: "30px", height: "30px", fontSize: "0.75rem" }}>
                              {app.score.toFixed(0)}%
                            </span>
                          </div>
                          
                          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
                            {app.job_title}
                          </div>

                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px dashed var(--border-color)", paddingTop: "0.5rem", marginTop: "0.5rem" }}>
                            <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>{app.years_experience} Yrs Exp</span>
                            
                            {/* Actions to move */}
                            <select 
                              style={{ fontSize: "0.65rem", padding: "0.15rem", borderRadius: "4px", border: "1px solid var(--border-color)", backgroundColor: "var(--bg-app)" }}
                              value={app.status}
                              onClick={(e) => e.stopPropagation()}
                              onChange={(e) => handleMoveCandidateStage(app.id, e.target.value)}
                            >
                              <option value="applied">Applied</option>
                              <option value="screening">Screening</option>
                              <option value="technical_interview">Technical</option>
                              <option value="manager_round">Manager</option>
                              <option value="hr_interview">HR</option>
                              <option value="offer">Offer</option>
                              <option value="selected">Hired</option>
                              <option value="rejected">Declined</option>
                            </select>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ─── TAB CONTENT 4: CANDIDATE CENTER ───────────────────────────────── */}
      {activeTab === "candidates" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          
          {/* Collapsible/Sticky Multi Filters Block */}
          <div className="card-table-wrapper" style={{ padding: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Filter size={18} style={{ color: "var(--accent)" }} />
                <h4 style={{ fontWeight: "700", fontSize: "0.95rem" }}>Advanced Multi-Field Filters</h4>
              </div>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button className="btn-secondary" style={{ padding: "0.35rem 0.75rem", fontSize: "0.8rem" }} onClick={() => {
                  setSelectedJob("all");
                  setSearchQuery("");
                  setFilterMinScore(0);
                  setFilterExpMin("");
                  setFilterExpMax("");
                  setFilterLocation("all");
                  setFilterDegree("all");
                  setFilterRecLevel("all");
                  setFilterStage("all");
                }}>
                  Reset Filters
                </button>
                {selectedCompareIds.length === 2 && (
                  <button className="btn-primary" style={{ padding: "0.35rem 0.75rem", fontSize: "0.8rem" }} onClick={handleCompareClick}>
                    Compare Candidates ({selectedCompareIds.length})
                  </button>
                )}
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem" }}>
              <div className="form-group">
                <label className="form-label" style={{ fontSize: "0.75rem" }}>Global Query Search</label>
                <input type="text" className="form-input" style={{ padding: "0.4rem 0.6rem" }} placeholder="Name, skills, college..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontSize: "0.75rem" }}>Target Role</label>
                <select className="form-input" style={{ padding: "0.4rem 0.6rem" }} value={selectedJob} onChange={(e) => setSelectedJob(e.target.value)}>
                  <option value="all">All Job Specs</option>
                  {jobs.map((j) => (
                    <option key={j.id} value={j.id.toString()}>{j.title}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontSize: "0.75rem" }}>Min ATS Score: {filterMinScore}%</label>
                <input type="range" min="0" max="100" className="form-input" style={{ padding: "0" }} value={filterMinScore} onChange={(e) => setFilterMinScore(parseInt(e.target.value))} />
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontSize: "0.75rem" }}>Experience Min/Max</label>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input type="number" className="form-input" style={{ padding: "0.4rem 0.6rem" }} placeholder="Min" value={filterExpMin} onChange={(e) => setFilterExpMin(e.target.value)} />
                  <input type="number" className="form-input" style={{ padding: "0.4rem 0.6rem" }} placeholder="Max" value={filterExpMax} onChange={(e) => setFilterExpMax(e.target.value)} />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontSize: "0.75rem" }}>Required Location</label>
                <input type="text" className="form-input" style={{ padding: "0.4rem 0.6rem" }} placeholder="e.g. Pune" value={filterLocation === "all" ? "" : filterLocation} onChange={(e) => setFilterLocation(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontSize: "0.75rem" }}>Min Education Degree</label>
                <select className="form-input" style={{ padding: "0.4rem 0.6rem" }} value={filterDegree} onChange={(e) => setFilterDegree(e.target.value)}>
                  <option value="all">All Degrees</option>
                  <option value="1">12th/HSC</option>
                  <option value="2">Diploma</option>
                  <option value="3">Bachelor's Degree</option>
                  <option value="4">Master's Degree</option>
                  <option value="5">PhD</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontSize: "0.75rem" }}>AI Recommendation</label>
                <select className="form-input" style={{ padding: "0.4rem 0.6rem" }} value={filterRecLevel} onChange={(e) => setFilterRecLevel(e.target.value)}>
                  <option value="all">All Ratings</option>
                  <option value="Highly Recommended">Highly Recommended</option>
                  <option value="Recommended">Recommended</option>
                  <option value="Consider">Consider</option>
                  <option value="Not Recommended">Not Recommended</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontSize: "0.75rem" }}>Hiring pipeline stage</label>
                <select className="form-input" style={{ padding: "0.4rem 0.6rem" }} value={filterStage} onChange={(e) => setFilterStage(e.target.value)}>
                  <option value="all">All Stages</option>
                  <option value="applied">Applied</option>
                  <option value="screening">Screening</option>
                  <option value="technical_interview">Technical Round</option>
                  <option value="manager_round">Manager Round</option>
                  <option value="hr_interview">HR Session</option>
                  <option value="offer">Offer Released</option>
                  <option value="selected">Hired</option>
                  <option value="rejected">Declined</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontSize: "0.75rem" }}>Sort Results By</label>
                <select className="form-input" style={{ padding: "0.4rem 0.6rem" }} value={sortField} onChange={(e) => setSortField(e.target.value)}>
                  <option value="score">Match Score</option>
                  <option value="experience">Years Experience</option>
                  <option value="education">Education Level</option>
                </select>
              </div>
            </div>
          </div>

          {/* Candidates Matrix List Table */}
          <div className="card-table-wrapper">
            <div className="section-header">
              <h3>Qualified Candidate Matrix ({sortedApps.length})</h3>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button className="btn-secondary" onClick={() => handleDownloadCSV()}>
                  <Download size={16} />
                  <span>Export CSV</span>
                </button>
              </div>
            </div>

            <div style={{ overflowX: "auto" }}>
              <table className="hs-table">
                <thead>
                  <tr>
                    <th style={{ width: "40px" }}>Compare</th>
                    <th>Rank</th>
                    <th>Candidate</th>
                    <th>ATS Score</th>
                    <th>Experience</th>
                    <th>Education</th>
                    <th>AI Evaluation</th>
                    <th>Hiring Stage</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedApps.length === 0 ? (
                    <tr>
                      <td colSpan={9} style={{ textAlign: "center", color: "var(--text-muted)", padding: "3rem" }}>
                        No profiles matching current search matrix filters.
                      </td>
                    </tr>
                  ) : (
                    sortedApps.map((app, idx) => {
                      const ringClass = app.score >= 70 ? "ats-high" : app.score >= 40 ? "ats-mid" : "ats-low";
                      const statusClass = 
                        app.status === "selected" || app.status === "offer" ? "badge-success" : 
                        app.status === "rejected" ? "badge-danger" : 
                        app.status === "applied" ? "badge-neutral" : "badge-warning";
                      
                      return (
                        <tr key={app.id} style={{ cursor: "pointer" }} onClick={() => setSelectedApp(app)}>
                          <td onClick={(e) => e.stopPropagation()}>
                            <input 
                              type="checkbox" 
                              checked={selectedCompareIds.includes(app.id)}
                              onChange={() => toggleSelectCompare(app.id)}
                            />
                          </td>
                          <td><strong>#{idx + 1}</strong></td>
                          <td>
                            <div style={{ display: "flex", flexDirection: "column" }}>
                              <span style={{ fontWeight: "700" }}>{app.candidate_name}</span>
                              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Target: {app.job_title}</span>
                            </div>
                          </td>
                          <td>
                            <div className={`ats-score-ring ${ringClass}`} style={{ width: "38px", height: "38px", fontSize: "0.85rem" }}>
                              {app.score.toFixed(0)}%
                            </div>
                          </td>
                          <td>{app.years_experience} Years</td>
                          <td>{getEducationName(app.education_level)}</td>
                          <td>
                            <span style={{ fontSize: "0.8rem", fontWeight: "600", color: 
                              app.hiring_recommendation === 'Highly Recommended' ? 'var(--success)' :
                              app.hiring_recommendation === 'Recommended' ? 'var(--success)' :
                              app.hiring_recommendation === 'Consider' ? 'var(--warning)' : 'var(--danger)'
                            }}>
                              {app.hiring_recommendation}
                            </span>
                          </td>
                          <td>
                            <span className={`badge ${statusClass}`} style={{ textTransform: "capitalize" }}>
                              {app.status.replace("_", " ")}
                            </span>
                          </td>
                          <td onClick={(e) => e.stopPropagation()}>
                            <div style={{ display: "flex", gap: "0.25rem" }}>
                              <button className="btn-secondary" style={{ padding: "0.35rem 0.55rem" }} onClick={() => setSelectedApp(app)}>
                                <Eye size={14} />
                              </button>
                              <a href={`${API_BASE}/api/applications/${app.id}/export/report`} target="_blank" rel="noreferrer" className="btn-secondary" style={{ padding: "0.35rem 0.55rem" }} title="Download Report">
                                <FileText size={14} />
                              </a>
                            </div>
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
      )}

      {/* ─── TAB CONTENT 5: ANALYTICS REPORT ────────────────────────────────── */}
      {activeTab === "analytics" && analytics && (
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
          
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
            
            {/* applications per month chart */}
            <div className="card-table-wrapper" style={{ padding: "1.5rem" }}>
              <h4 style={{ fontWeight: "700", marginBottom: "1.5rem" }}>Monthly Applications Inflow</h4>
              <div style={{ display: "flex", justifyContent: "space-around", alignItems: "flex-end", height: "200px", padding: "1rem 0" }}>
                {analytics.applications_per_month && analytics.applications_per_month.map((item: any, idx: number) => (
                  <div key={idx} style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "60px" }}>
                    <div style={{ 
                      height: `${(item.count / Math.max(...analytics.applications_per_month.map((m: any) => m.count))) * 140}px`,
                      width: "35px",
                      backgroundColor: "var(--accent)",
                      borderRadius: "6px 6px 0 0",
                      transition: "height 0.5s ease-out",
                      position: "relative"
                    }} className="bar-chart-bar">
                      <span className="chart-bar-tooltip">{item.count}</span>
                    </div>
                    <span style={{ fontSize: "0.75rem", fontWeight: "600", marginTop: "0.5rem" }}>{item.month}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* hiring funnel conversion metrics */}
            <div className="card-table-wrapper" style={{ padding: "1.5rem" }}>
              <h4 style={{ fontWeight: "700", marginBottom: "1rem" }}>Pipeline Funnel Distribution</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                {[
                  { key: "applied", label: "1. Applied", color: "#64748b" },
                  { key: "screening", label: "2. Screening", color: "#3b82f6" },
                  { key: "technical_interview", label: "3. Technical Round", color: "#8b5cf6" },
                  { key: "offer", label: "4. Offer Released", color: "#10b981" },
                  { key: "selected", label: "5. Selected Hires", color: "#10b981" }
                ].map((item) => {
                  const val = analytics.funnel[item.key] || 0;
                  const total = analytics.total_applications || 1;
                  const pct = Math.min(((val / total) * 100), 100).toFixed(0);
                  
                  return (
                    <div key={item.key}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "0.25rem", fontWeight: "600" }}>
                        <span>{item.label}</span>
                        <span>{val} ({pct}%)</span>
                      </div>
                      <div className="meter-bar-container" style={{ height: "10px" }}>
                        <div className="meter-bar" style={{ width: `${Math.max(val / total * 100, 4)}%`, backgroundColor: item.color, height: "100%" }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* college tier analytics */}
            <div className="card-table-wrapper" style={{ padding: "1.5rem" }}>
              <h4 style={{ fontWeight: "700", marginBottom: "1rem" }}>Top College Talents</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                {Object.entries(analytics.colleges_distribution || {}).map(([colName, colVal]: any, idx) => {
                  const total = Object.values(analytics.colleges_distribution).reduce((a: any, b: any) => a + b, 0) as number;
                  const pct = ((colVal / total) * 100).toFixed(0);
                  return (
                    <div key={idx}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "0.25rem" }}>
                        <strong>{colName}</strong>
                        <span>{colVal} ({pct}%)</span>
                      </div>
                      <div className="meter-bar-container" style={{ height: "8px" }}>
                        <div className="meter-bar" style={{ width: `${pct}%`, height: "100%", backgroundColor: "var(--accent)" }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* candidate source analysis */}
            <div className="card-table-wrapper" style={{ padding: "1.5rem" }}>
              <h4 style={{ fontWeight: "700", marginBottom: "1rem" }}>Candidate Source Channels</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                {Object.entries(analytics.candidate_source_analysis || {}).map(([srcName, srcVal]: any, idx) => {
                  const total = Object.values(analytics.candidate_source_analysis).reduce((a: any, b: any) => a + b, 0) as number;
                  const pct = ((srcVal / total) * 100).toFixed(0);
                  return (
                    <div key={idx}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "0.25rem" }}>
                        <strong>{srcName}</strong>
                        <span>{srcVal} ({pct}%)</span>
                      </div>
                      <div className="meter-bar-container" style={{ height: "8px" }}>
                        <div className="meter-bar" style={{ width: `${pct}%`, height: "100%", backgroundColor: "var(--success)" }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

          </div>
        </div>
      )}

      {/* ─── JOB MODAL CREATE/EDIT ────────────────────────────────────────── */}
      {showJobModal && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ width: "700px" }}>
            <div className="modal-header">
              <h3>{editingJobId ? "Modify Job Spec" : "Post Corporate Opening"}</h3>
              <button onClick={() => setShowJobModal(false)} className="btn-icon">
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleSaveJob} style={{ display: "flex", flexDirection: "column", gap: "1.25rem", padding: "1.5rem" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
                <div className="form-group">
                  <label className="form-label">Job Title</label>
                  <input type="text" className="form-input" placeholder="e.g. Senior PyTorch Engineer" required value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Department</label>
                  <select className="form-input" value={jobDepartment} onChange={(e) => setJobDepartment(e.target.value)}>
                    <option value="Engineering">Engineering</option>
                    <option value="Product Management">Product Management</option>
                    <option value="Data Science">Data Science</option>
                    <option value="Marketing">Marketing</option>
                    <option value="Human Resources">Human Resources</option>
                  </select>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr", gap: "1.25rem" }}>
                <div className="form-group">
                  <label className="form-label">Employment Type</label>
                  <select className="form-input" value={jobEmploymentType} onChange={(e) => setJobEmploymentType(e.target.value)}>
                    <option value="Full-time">Full-time</option>
                    <option value="Part-time">Part-time</option>
                    <option value="Contractor">Contractor</option>
                    <option value="Internship">Internship</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Salary Range</label>
                  <input type="text" className="form-input" placeholder="e.g. $120k - $150k" value={jobSalaryRange} onChange={(e) => setJobSalaryRange(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Location</label>
                  <input type="text" className="form-input" placeholder="e.g. Remote or Pune" value={jobLocation} onChange={(e) => setJobLocation(e.target.value)} />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Job Description Specification</label>
                <textarea className="form-input" style={{ height: "90px", resize: "none" }} required placeholder="Brief summary of candidate scope, tech stack, and goals..." value={jobDescription} onChange={(e) => setJobDescription(e.target.value)} />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
                <div className="form-group">
                  <label className="form-label">Required Skills (Comma separated)</label>
                  <input type="text" className="form-input" placeholder="python, pytorch, docker" value={jobSkillsReq} onChange={(e) => setJobSkillsReq(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Preferred Skills (Comma separated)</label>
                  <input type="text" className="form-input" placeholder="aws, kubernetes, mlflow" value={jobPreferredSkills} onChange={(e) => setJobPreferredSkills(e.target.value)} />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Responsibilities (One per line)</label>
                <textarea className="form-input" style={{ height: "65px", resize: "none" }} placeholder="Design ML APIs&#10;Deploy pipelines to AWS" value={jobResponsibilities} onChange={(e) => setJobResponsibilities(e.target.value)} />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1.2fr", gap: "1.25rem" }}>
                <div className="form-group">
                  <label className="form-label">Min Yrs Experience</label>
                  <input type="number" step="0.5" className="form-input" placeholder="3.0" value={jobExpReq} onChange={(e) => setJobExpReq(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Min Degree Level</label>
                  <select className="form-input" value={jobEduReq} onChange={(e) => setJobEduReq(parseInt(e.target.value))}>
                    <option value={1}>12th/HSC</option>
                    <option value={2}>Diploma</option>
                    <option value={3}>Bachelor's Degree</option>
                    <option value={4}>Master's Degree</option>
                    <option value={5}>PhD</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Hiring Manager</label>
                  <input type="text" className="form-input" placeholder="e.g. Alex Jenkins (Dir)" value={jobHiringManager} onChange={(e) => setJobHiringManager(e.target.value)} />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem", marginTop: "1rem" }}>
                <button type="button" className="btn-secondary" onClick={() => setShowJobModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Save Job Spec</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─── SIDE-BY-SIDE COMPARISON MODAL MATRIX ─────────────────────────── */}
      {showCompareModal && selectedCompareIds.length === 2 && (() => {
        const app1 = applications.find(a => a.id === selectedCompareIds[0]);
        const app2 = applications.find(a => a.id === selectedCompareIds[1]);
        if (!app1 || !app2) return null;
        
        return (
          <div className="modal-backdrop">
            <div className="modal-content" style={{ width: "850px", maxWidth: "90%" }}>
              <div className="modal-header">
                <h3>Candidate Comparison Matrix</h3>
                <button onClick={() => setShowCompareModal(false)} className="btn-icon">
                  <X size={20} />
                </button>
              </div>

              <div style={{ padding: "1.5rem", overflowX: "auto" }}>
                <table className="hs-table">
                  <thead>
                    <tr>
                      <th style={{ width: "20%" }}>Criterion</th>
                      <th style={{ width: "40%", textAlign: "center" }}>{app1.candidate_name}</th>
                      <th style={{ width: "40%", textAlign: "center" }}>{app2.candidate_name}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><strong>ATS Overall Score</strong></td>
                      <td style={{ textAlign: "center" }}>
                        <div className={`ats-score-ring ${app1.score >= 70 ? 'ats-high' : app1.score >= 40 ? 'ats-mid' : 'ats-low'}`} style={{ margin: "0 auto", width: "45px", height: "45px" }}>
                          {app1.score.toFixed(0)}%
                        </div>
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <div className={`ats-score-ring ${app2.score >= 70 ? 'ats-high' : app2.score >= 40 ? 'ats-mid' : 'ats-low'}`} style={{ margin: "0 auto", width: "45px", height: "45px" }}>
                          {app2.score.toFixed(0)}%
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td><strong>Hiring Recommendation</strong></td>
                      <td style={{ textAlign: "center", fontWeight: "700" }}>{app1.hiring_recommendation}</td>
                      <td style={{ textAlign: "center", fontWeight: "700" }}>{app2.hiring_recommendation}</td>
                    </tr>
                    <tr>
                      <td><strong>Years Experience</strong></td>
                      <td style={{ textAlign: "center" }} className={app1.years_experience > app2.years_experience ? "font-success" : ""}>
                        {app1.years_experience} Years
                      </td>
                      <td style={{ textAlign: "center" }} className={app2.years_experience > app1.years_experience ? "font-success" : ""}>
                        {app2.years_experience} Years
                      </td>
                    </tr>
                    <tr>
                      <td><strong>Education level</strong></td>
                      <td style={{ textAlign: "center" }} className={app1.education_level > app2.education_level ? "font-success" : ""}>
                        {getEducationName(app1.education_level)}
                      </td>
                      <td style={{ textAlign: "center" }} className={app2.education_level > app1.education_level ? "font-success" : ""}>
                        {getEducationName(app2.education_level)}
                      </td>
                    </tr>
                    <tr>
                      <td><strong>Extracted Skills</strong></td>
                      <td>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.2rem" }}>
                          {app1.skills && app1.skills.map((s: string, i: number) => (
                            <span key={i} style={{ fontSize: "0.7rem", padding: "0.15rem 0.4rem", borderRadius: "4px", backgroundColor: "var(--bg-app)", border: "1px solid var(--border-color)" }}>{s}</span>
                          ))}
                        </div>
                      </td>
                      <td>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.2rem" }}>
                          {app2.skills && app2.skills.map((s: string, i: number) => (
                            <span key={i} style={{ fontSize: "0.7rem", padding: "0.15rem 0.4rem", borderRadius: "4px", backgroundColor: "var(--bg-app)", border: "1px solid var(--border-color)" }}>{s}</span>
                          ))}
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td><strong>Core Strengths</strong></td>
                      <td>
                        <ul style={{ fontSize: "0.75rem", paddingLeft: "1rem" }}>
                          {app1.explanation && app1.explanation.strengths && app1.explanation.strengths.slice(0, 3).map((st: string, idx: number) => (
                            <li key={idx} style={{ marginBottom: "0.25rem" }}>{st}</li>
                          ))}
                        </ul>
                      </td>
                      <td>
                        <ul style={{ fontSize: "0.75rem", paddingLeft: "1rem" }}>
                          {app2.explanation && app2.explanation.strengths && app2.explanation.strengths.slice(0, 3).map((st: string, idx: number) => (
                            <li key={idx} style={{ marginBottom: "0.25rem" }}>{st}</li>
                          ))}
                        </ul>
                      </td>
                    </tr>
                    <tr>
                      <td><strong>Profile Gaps</strong></td>
                      <td>
                        <ul style={{ fontSize: "0.75rem", paddingLeft: "1rem" }}>
                          {app1.explanation && app1.explanation.weaknesses && app1.explanation.weaknesses.slice(0, 3).map((wk: string, idx: number) => (
                            <li key={idx} style={{ marginBottom: "0.25rem" }} className="font-danger">{wk}</li>
                          ))}
                        </ul>
                      </td>
                      <td>
                        <ul style={{ fontSize: "0.75rem", paddingLeft: "1rem" }}>
                          {app2.explanation && app2.explanation.weaknesses && app2.explanation.weaknesses.slice(0, 3).map((wk: string, idx: number) => (
                            <li key={idx} style={{ marginBottom: "0.25rem" }} className="font-danger">{wk}</li>
                          ))}
                        </ul>
                      </td>
                    </tr>
                  </tbody>
                </table>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem", marginTop: "1.5rem" }}>
                  <button className="btn-secondary" onClick={() => setShowCompareModal(false)}>Close Comparison</button>
                  <button className="btn-primary" onClick={() => {
                    setSelectedCompareIds([]);
                    setShowCompareModal(false);
                  }}>
                    Clear Selection
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })()}

      {/* ─── CANDIDATE DETAIL SCORECARD DRAWER ──────────────────────────────── */}
      {selectedApp && (
        <div className="drawer-overlay" onClick={() => setSelectedApp(null)}>
          <div className="drawer-container" onClick={(e) => e.stopPropagation()}>
            
            {/* Drawer Header Toolbar */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-color)", paddingBottom: "1rem", marginBottom: "1.25rem" }}>
              <div>
                <h3 style={{ fontSize: "1.2rem", fontWeight: "700" }}>{selectedApp.candidate_name}</h3>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Target Spec: {selectedApp.job_title}</span>
              </div>
              <button className="btn-icon" onClick={() => setSelectedApp(null)}>
                <X size={20} />
              </button>
            </div>

            {/* Status Stage Switcher */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1.25rem", padding: "0.5rem", backgroundColor: "var(--bg-app)", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: "700" }}>Hiring Phase:</span>
              <select 
                className="form-input" 
                style={{ padding: "0.25rem 0.5rem", fontSize: "0.8rem", width: "auto" }}
                value={selectedApp.status}
                onChange={(e) => handleMoveCandidateStage(selectedApp.id, e.target.value)}
              >
                <option value="applied">Applied</option>
                <option value="screening">Screening</option>
                <option value="technical_interview">Technical Round</option>
                <option value="manager_round">Manager Round</option>
                <option value="hr_interview">HR Session</option>
                <option value="offer">Offer Released</option>
                <option value="selected">Hired</option>
                <option value="rejected">Declined</option>
              </select>
            </div>

            {/* Scorecard Drawer Tab Selection Links */}
            <div style={{ display: "flex", borderBottom: "1px solid var(--border-color)", marginBottom: "1.5rem" }}>
              <button className={`drawer-tab-btn ${drawerTab === 'evaluation' ? 'active' : ''}`} onClick={() => setDrawerTab("evaluation")}>
                Scorecard
              </button>
              <button className={`drawer-tab-btn ${drawerTab === 'interviews' ? 'active' : ''}`} onClick={() => setDrawerTab("interviews")}>
                Interviews ({interviews.length})
              </button>
              <button className={`drawer-tab-btn ${drawerTab === 'notes' ? 'active' : ''}`} onClick={() => setDrawerTab("notes")}>
                Recruiter Notes ({notes.length})
              </button>
              <button className={`drawer-tab-btn ${drawerTab === 'email' ? 'active' : ''}`} onClick={() => setDrawerTab("email")}>
                Send Email
              </button>
            </div>

            {/* ─── DRAWER SUB-TAB 1: EVALUATION SCORECARD ──────────────────── */}
            {drawerTab === "evaluation" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                
                {/* Score gauge ring section */}
                <div style={{ display: "flex", gap: "1.5rem", alignItems: "center", padding: "1.25rem", border: "1px solid var(--border-color)", borderRadius: "10px", backgroundColor: "var(--bg-app)" }}>
                  <div className={`ats-score-ring ${selectedApp.score >= 70 ? 'ats-high' : selectedApp.score >= 40 ? 'ats-mid' : 'ats-low'}`} style={{ width: "65px", height: "65px", fontSize: "1.25rem" }}>
                    {selectedApp.score.toFixed(0)}%
                  </div>
                  <div>
                    <h4 style={{ fontSize: "1rem", fontWeight: "700" }}>AI Screening Assessment</h4>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "block", marginTop: "0.2rem" }}>
                      Rating Match: <strong>{selectedApp.hiring_recommendation}</strong>
                    </span>
                  </div>
                </div>

                {/* Score breakdown bar charts */}
                <div>
                  <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: "600", marginBottom: "0.75rem" }}>Score Breakdown</h4>
                  
                  {selectedApp.score_breakdown && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                      <div className="meter-wrapper">
                        <div className="meter-header">
                          <span>BERT Semantic Logic</span>
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
                          <span>Required Skills Overlap</span>
                          <span>{(selectedApp.score_breakdown.skill_overlap_score * 100).toFixed(0)}%</span>
                        </div>
                        <div className="meter-bar-container">
                          <div className="meter-bar" style={{ width: `${selectedApp.score_breakdown.skill_overlap_score * 100}%` }}></div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Assessment Strengths and Weaknesses lists */}
                <div>
                  <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: "600", marginBottom: "0.5rem" }}>AI Screening Assessment</h4>
                  
                  <span style={{ fontSize: "0.8rem", fontWeight: "600", color: "var(--success)" }}>Profile Strengths</span>
                  <ul className="bullet-points" style={{ marginTop: "0.25rem", marginBottom: "0.85rem" }}>
                    {selectedApp.explanation?.strengths && selectedApp.explanation.strengths.map((s: string, i: number) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>

                  <span style={{ fontSize: "0.8rem", fontWeight: "600", color: "var(--danger)" }}>Profile Gaps</span>
                  <ul className="bullet-points" style={{ marginTop: "0.25rem" }}>
                    {selectedApp.explanation?.weaknesses && selectedApp.explanation.weaknesses.map((w: string, i: number) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>

                {/* Suggested Questions */}
                {selectedApp.interview_questions && (
                  <div>
                    <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: "600", marginBottom: "0.5rem" }}>Suggested Interview Questions</h4>
                    <div style={{ backgroundColor: "var(--bg-app)", padding: "0.85rem", borderRadius: "8px", border: "1px solid var(--border-color)", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      {selectedApp.interview_questions.map((q: string, i: number) => (
                        <p key={i} style={{ marginBottom: "0.4rem" }}><strong>{i+1}.</strong> {q}</p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ─── DRAWER SUB-TAB 2: INTERVIEWS LIST & SCHEDULER ───────────── */}
            {drawerTab === "interviews" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                
                {/* Schedule Interview Form */}
                <form onSubmit={handleScheduleInterview} style={{ padding: "1rem", border: "1px solid var(--border-color)", borderRadius: "8px", backgroundColor: "var(--bg-app)", display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                  <h4 style={{ fontSize: "0.85rem", fontWeight: "700" }}>Schedule New Session</h4>
                  
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                    <div className="form-group">
                      <label className="form-label" style={{ fontSize: "0.75rem" }}>Interviewer</label>
                      <input type="text" className="form-input" style={{ padding: "0.35rem 0.6rem", fontSize: "0.8rem" }} placeholder="Sarah Jenkins" required value={newIntInterviewer} onChange={(e) => setNewIntInterviewer(e.target.value)} />
                    </div>
                    <div className="form-group">
                      <label className="form-label" style={{ fontSize: "0.75rem" }}>Round Type</label>
                      <select className="form-input" style={{ padding: "0.35rem 0.6rem", fontSize: "0.8rem" }} value={newIntType} onChange={(e) => setNewIntType(e.target.value)}>
                        <option value="screening">Screening</option>
                        <option value="technical">Technical Round</option>
                        <option value="manager">Manager Round</option>
                        <option value="hr">HR Round</option>
                      </select>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label" style={{ fontSize: "0.75rem" }}>Date & Time</label>
                    <input type="datetime-local" className="form-input" style={{ padding: "0.35rem 0.6rem", fontSize: "0.8rem" }} required value={newIntDate} onChange={(e) => setNewIntDate(e.target.value)} />
                  </div>

                  <div className="form-group">
                    <label className="form-label" style={{ fontSize: "0.75rem" }}>Meeting Link</label>
                    <input type="text" className="form-input" style={{ padding: "0.35rem 0.6rem", fontSize: "0.8rem" }} placeholder="https://meet.google.com/..." value={newIntLink} onChange={(e) => setNewIntLink(e.target.value)} />
                  </div>

                  <button type="submit" className="btn-primary" style={{ width: "100%", padding: "0.45rem", fontSize: "0.8rem" }}>
                    Schedule and Invite
                  </button>
                </form>

                {/* Interviews List Summary */}
                <div>
                  <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: "600", marginBottom: "0.75rem" }}>Scheduled Sessions</h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    {interviews.length === 0 ? (
                      <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "0.8rem", padding: "1rem" }}>No interviews scheduled</div>
                    ) : (
                      interviews.map((item) => (
                        <div key={item.id} style={{ padding: "0.85rem", border: "1px solid var(--border-color)", borderRadius: "8px", backgroundColor: "var(--bg-card)" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                            <span style={{ fontWeight: "700", fontSize: "0.85rem", textTransform: "capitalize" }}>{item.type} Interview</span>
                            <span className={`badge ${item.status === 'completed' ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: "0.65rem" }}>
                              {item.status}
                            </span>
                          </div>
                          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "0.2rem" }}>
                            <div><strong>Interviewer:</strong> {item.interviewer}</div>
                            <div><strong>Time:</strong> {new Date(item.scheduled_at).toLocaleString()}</div>
                            {item.meeting_link && (
                              <div><strong>Meeting:</strong> <a href={item.meeting_link} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>Link</a></div>
                            )}
                          </div>

                          {/* Record Feedback Form toggle button */}
                          {item.status === "scheduled" && feedbackIntId !== item.id && (
                            <button className="btn-secondary" style={{ width: "100%", fontSize: "0.75rem", padding: "0.3rem", marginTop: "0.5rem" }} onClick={() => setFeedbackIntId(item.id)}>
                              Record Feedback Scorecard
                            </button>
                          )}

                          {/* Active feedback input card */}
                          {feedbackIntId === item.id && (
                            <form onSubmit={handleSaveInterviewFeedback} style={{ borderTop: "1px solid var(--border-color)", paddingTop: "0.5rem", marginTop: "0.5rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                <span style={{ fontSize: "0.75rem", fontWeight: "700" }}>Rating:</span>
                                <div style={{ display: "flex", gap: "0.15rem" }}>
                                  {[1, 2, 3, 4, 5].map((stars) => (
                                    <Star 
                                      key={stars} 
                                      size={14} 
                                      style={{ cursor: "pointer", fill: stars <= feedbackRating ? "var(--warning)" : "none", color: "var(--warning)" }}
                                      onClick={() => setFeedbackRating(stars)}
                                    />
                                  ))}
                                </div>
                              </div>
                              <textarea 
                                className="form-input" 
                                style={{ height: "55px", fontSize: "0.75rem", resize: "none" }}
                                required
                                placeholder="Write feedback notes..."
                                value={feedbackText}
                                onChange={(e) => setFeedbackText(e.target.value)}
                              />
                              <div style={{ display: "flex", gap: "0.5rem" }}>
                                <button type="button" className="btn-secondary" style={{ flex: 1, padding: "0.25rem", fontSize: "0.7rem" }} onClick={() => setFeedbackIntId(null)}>Cancel</button>
                                <button type="submit" className="btn-primary" style={{ flex: 1, padding: "0.25rem", fontSize: "0.7rem" }}>Save Feedback</button>
                              </div>
                            </form>
                          )}

                          {/* Recorded feedback displays */}
                          {item.status === "completed" && item.feedback && (
                            <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "0.5rem", marginTop: "0.5rem", fontSize: "0.75rem" }}>
                              <div style={{ display: "flex", gap: "0.15rem", marginBottom: "0.25rem" }}>
                                {[1, 2, 3, 4, 5].map((s) => (
                                  <Star key={s} size={10} style={{ fill: s <= item.rating ? "var(--warning)" : "none", color: "var(--warning)" }} />
                                ))}
                              </div>
                              <p style={{ fontStyle: "italic", color: "var(--text-muted)" }}>"{item.feedback}"</p>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>

              </div>
            )}

            {/* ─── DRAWER SUB-TAB 3: RECRUITER NOTES WIDGET ────────────────── */}
            {drawerTab === "notes" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                
                {/* Add note card */}
                <form onSubmit={handleSaveNote} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  <textarea 
                    className="form-input"
                    style={{ height: "70px", resize: "none" }}
                    placeholder="Write candidate review note here..."
                    required
                    value={newNoteText}
                    onChange={(e) => setNewNoteText(e.target.value)}
                  />
                  
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: "0.75rem" }}>
                    <div className="form-group">
                      <label className="form-label" style={{ fontSize: "0.75rem" }}>Mentions (Comma separated)</label>
                      <input type="text" className="form-input" style={{ padding: "0.3rem 0.5rem", fontSize: "0.75rem" }} placeholder="Sarah Jenkins" value={newNoteMentions} onChange={(e) => setNewNoteMentions(e.target.value)} />
                    </div>
                    
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "1rem" }}>
                      <input 
                        type="checkbox" 
                        id="pin-note-checkbox" 
                        checked={newNotePinned} 
                        onChange={(e) => setNewNotePinned(e.target.checked)} 
                      />
                      <label htmlFor="pin-note-checkbox" style={{ fontSize: "0.75rem", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                        <Pin size={12} /> Pin Note at Top
                      </label>
                    </div>
                  </div>

                  <button type="submit" className="btn-primary" style={{ width: "auto", alignSelf: "flex-end", padding: "0.4rem 1.2rem", fontSize: "0.8rem" }}>
                    Add Review Note
                  </button>
                </form>

                {/* List of notes */}
                <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                  {notes.length === 0 ? (
                    <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "0.8rem", padding: "1.5rem" }}>No recruiter notes yet</div>
                  ) : (
                    notes.map((item) => (
                      <div key={item.id} style={{ 
                        padding: "0.85rem", 
                        border: item.is_pinned ? "1px solid var(--accent)" : "1px solid var(--border-color)", 
                        borderRadius: "8px", 
                        backgroundColor: item.is_pinned ? "var(--warning-bg)" : "var(--bg-card)",
                        position: "relative"
                      }}>
                        {item.is_pinned === 1 && (
                          <span style={{ fontSize: "0.6rem", fontWeight: "700", textTransform: "uppercase", color: "var(--accent)", position: "absolute", top: "8px", right: "45px", display: "inline-flex", alignItems: "center", gap: "0.25rem" }}>
                            <Pin size={10} /> Pinned
                          </span>
                        )}
                        <div style={{ fontSize: "0.75rem", color: "var(--text-main)", whiteSpace: "pre-line", marginBottom: "0.5rem" }}>
                          {item.note_text}
                        </div>
                        {item.mentions && item.mentions.length > 0 && (
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem", marginBottom: "0.5rem" }}>
                            {item.mentions.map((men: string, i: number) => (
                              <span key={i} style={{ fontSize: "0.65rem", padding: "0.1rem 0.3rem", borderRadius: "3px", backgroundColor: "var(--bg-app)", color: "var(--accent)", fontWeight: "600" }}>@{men}</span>
                            ))}
                          </div>
                        )}
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px dashed var(--border-color)", paddingTop: "0.5rem", marginTop: "0.5rem", fontSize: "0.7rem", color: "var(--text-muted)" }}>
                          <span>By {item.recruiter_name} · {new Date(item.created_at).toLocaleString()}</span>
                          <div style={{ display: "flex", gap: "0.4rem" }}>
                            <button onClick={() => handleTogglePinNote(item.id)} style={{ border: "none", background: "none", cursor: "pointer", color: "var(--text-muted)" }} title="Toggle Pin">
                              <Pin size={12} />
                            </button>
                            <button onClick={() => handleDeleteNote(item.id)} style={{ border: "none", background: "none", cursor: "pointer", color: "var(--danger)" }} title="Delete Note">
                              <Trash size={12} />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>

              </div>
            )}

            {/* ─── DRAWER SUB-TAB 4: SEND EMAIL ────────────────────────────── */}
            {drawerTab === "email" && (
              <form onSubmit={handleSendEmail} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <div className="form-group">
                  <label className="form-label">Subject</label>
                  <input type="text" className="form-input" required value={emailSubject} onChange={(e) => setEmailSubject(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Email Body Content</label>
                  <textarea className="form-input" style={{ height: "200px", resize: "none", fontFamily: "monospace" }} required value={emailBody} onChange={(e) => setEmailBody(e.target.value)} />
                </div>
                <button type="submit" className="btn-primary" style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "0.5rem", padding: "0.55rem" }}>
                  <Send size={16} />
                  <span>Send Candidate invitation Email</span>
                </button>
              </form>
            )}

          </div>
        </div>
      )}

    </div>
  );
}

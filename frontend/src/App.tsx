import { useState, useEffect } from "react";
import { 
  Briefcase, 
  LogOut, 
  Sun, 
  Moon, 
  Shield, 
  BookOpen
} from "lucide-react";
import LoginRegister from "./views/LoginRegister";
import CandidateDashboard from "./views/CandidateDashboard";
import RecruiterDashboard from "./views/RecruiterDashboard";
import AdminDashboard from "./views/AdminDashboard";
import Methodology from "./views/Methodology";

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [role, setRole] = useState<string | null>(localStorage.getItem("role"));
  const [userName, setUserName] = useState<string | null>(localStorage.getItem("name"));
  const [currentView, setCurrentView] = useState<string>("dashboard");
  const [theme, setTheme] = useState<string>(localStorage.getItem("theme") || "light");

  // Sync theme to document body
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Handle successful login
  const handleLoginSuccess = (userToken: string, userRole: string, name: string) => {
    localStorage.setItem("token", userToken);
    localStorage.setItem("role", userRole);
    localStorage.setItem("name", name);
    setToken(userToken);
    setRole(userRole);
    setUserName(name);
    setCurrentView("dashboard");
  };

  // Handle logout
  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("name");
    setToken(null);
    setRole(null);
    setUserName(null);
    setCurrentView("dashboard");
  };

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  // If not logged in, render auth screen
  if (!token || !role) {
    return <LoginRegister onLoginSuccess={handleLoginSuccess} theme={theme} toggleTheme={toggleTheme} />;
  }

  // Determine views based on roles
  const renderView = () => {
    switch (currentView) {
      case "methodology":
        return <Methodology />;
      case "dashboard":
      default:
        if (role === "candidate") return <CandidateDashboard token={token} />;
        if (role === "recruiter") return <RecruiterDashboard token={token} />;
        if (role === "admin") return <AdminDashboard token={token} />;
        return <div>Invalid Role Configuration</div>;
    }
  };

  const getTitle = () => {
    if (currentView === "methodology") return "Methodology & Architecture Overview";
    return `${role.charAt(0).toUpperCase() + role.slice(1)} Dashboard`;
  };

  return (
    <div className="app-container">
      {/* Sidebar Panel */}
      <aside className="sidebar">
        <div className="logo-section">
          <Shield size={24} className="text-indigo-500" />
          <span>HireSense AI</span>
        </div>

        <nav className="nav-links">
          <button 
            className={`nav-item ${currentView === "dashboard" ? "active" : ""}`}
            onClick={() => setCurrentView("dashboard")}
            style={{ border: "none", background: "none", textAlign: "left", width: "100%" }}
          >
            <Briefcase size={18} />
            <span>Dashboard</span>
          </button>
          
          <button 
            className={`nav-item ${currentView === "methodology" ? "active" : ""}`}
            onClick={() => setCurrentView("methodology")}
            style={{ border: "none", background: "none", textAlign: "left", width: "100%" }}
          >
            <BookOpen size={18} />
            <span>Methodology</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <span className="user-name">{userName}</span>
            <span style={{ fontSize: "0.75rem", opacity: 0.8 }}>Role: {role.toUpperCase()}</span>
          </div>

          <button 
            className="nav-item" 
            onClick={handleLogout}
            style={{ border: "none", background: "none", textAlign: "left", width: "100%", marginTop: "0.5rem" }}
          >
            <LogOut size={18} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Workspace */}
      <main className="main-panel">
        <header className="top-bar">
          <div className="top-bar-title">{getTitle()}</div>
          <div className="theme-user-section">
            <button className="theme-toggle-btn" onClick={toggleTheme} title="Toggle Light/Dark Theme">
              {theme === "light" ? <Moon size={20} /> : <Sun size={20} />}
            </button>
          </div>
        </header>

        <div className="content-body">
          {renderView()}
        </div>
      </main>
    </div>
  );
}

import React, { useState } from "react";
import { Shield, AlertCircle } from "lucide-react";

interface LoginRegisterProps {
  onLoginSuccess: (token: string, role: string, name: string) => void;
  theme: string;
  toggleTheme: () => void;
}

export default function LoginRegister({ onLoginSuccess }: LoginRegisterProps) {
  const [isLogin, setIsLogin] = useState<boolean>(true);
  const [role, setRole] = useState<string>("candidate");
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [name, setName] = useState<string>("");
  const [phone, setPhone] = useState<string>("");
  
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      if (isLogin) {
        // Login Flow
        const response = await fetch("http://localhost:8000/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.detail || "Login failed");
        }
        
        onLoginSuccess(data.access_token, data.role, data.name);
      } else {
        // Registration Flow
        const response = await fetch("http://localhost:8000/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password, name, phone, role }),
        });
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.detail || "Registration failed");
        }
        
        setSuccessMsg("Account created successfully! Switching to sign in...");
        setIsLogin(true);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <Shield size={40} style={{ color: "var(--accent)", marginBottom: "0.75rem", display: "inline-block" }} />
          <h2>{isLogin ? "Sign In to HireSense AI" : "Create HireSense Account"}</h2>
          <p>{isLogin ? "Enterprise Recruitment Intelligence Platform" : "Get started by creating your account"}</p>
        </div>

        {errorMsg && (
          <div className="badge badge-danger" style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.6rem 0.8rem", width: "100%", textTransform: "none", borderRadius: "8px", marginBottom: "1rem" }}>
            <AlertCircle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div className="badge badge-success" style={{ display: "block", padding: "0.6rem 0.8rem", width: "100%", textTransform: "none", borderRadius: "8px", marginBottom: "1rem" }}>
            {successMsg}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {!isLogin && (
            <div className="role-selector-tab">
              <button 
                type="button"
                className={`role-tab-btn ${role === "candidate" ? "active" : ""}`}
                onClick={() => setRole("candidate")}
              >
                Candidate
              </button>
              <button 
                type="button"
                className={`role-tab-btn ${role === "recruiter" ? "active" : ""}`}
                onClick={() => setRole("recruiter")}
              >
                Recruiter
              </button>
              <button 
                type="button"
                className={`role-tab-btn ${role === "admin" ? "active" : ""}`}
                onClick={() => setRole("admin")}
              >
                Admin
              </button>
            </div>
          )}

          {!isLogin && (
            <>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input 
                  type="text" 
                  className="form-input" 
                  required
                  placeholder="e.g. Priya Sharma"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Phone Number</label>
                <input 
                  type="text" 
                  className="form-input" 
                  placeholder="e.g. +91 98765 43210"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input 
              type="email" 
              className="form-input" 
              required
              placeholder="e.g. candidate@hiresense.ai"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input 
              type="password" 
              className="form-input" 
              required
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="form-btn" style={{ marginTop: "1rem" }} disabled={loading}>
            {loading ? "Processing..." : isLogin ? "Sign In" : "Register Account"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: "1.5rem", fontSize: "0.85rem" }}>
          <span style={{ color: "var(--text-muted)" }}>
            {isLogin ? "New to HireSense? " : "Already have an account? "}
          </span>
          <button 
            onClick={() => {
              setIsLogin(!isLogin);
              setErrorMsg(null);
              setSuccessMsg(null);
            }}
            style={{ background: "none", border: "none", color: "var(--accent)", fontWeight: "600", cursor: "pointer" }}
          >
            {isLogin ? "Create Account" : "Sign In"}
          </button>
        </div>
      </div>
    </div>
  );
}

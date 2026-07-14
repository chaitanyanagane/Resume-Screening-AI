import { useState, useEffect } from "react";
import { Activity } from "lucide-react";

interface AdminDashboardProps {
  token: string;
}

export default function AdminDashboard({ token }: AdminDashboardProps) {
  const [users, setUsers] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  
  const [loading, setLoading] = useState<boolean>(true);

  const fetchData = async () => {
    try {
      // 1. Fetch users list
      const usersRes = await fetch("http://localhost:8000/api/admin/users", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const usersData = await usersRes.json();
      setUsers(usersData);

      // 2. Fetch logs list
      const logsRes = await fetch("http://localhost:8000/api/admin/logs", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const logsData = await logsRes.json();
      setLogs(logsData);

      // 3. Fetch analytics telemetry
      const analRes = await fetch("http://localhost:8000/api/analytics", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const analData = await analRes.json();
      setAnalytics(analData);
    } catch (err) {
      console.error("Error fetching admin telemetry:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRoleChange = async (userId: number, newRole: string) => {
    alert(`Role modified for user ID ${userId} to ${newRole}! (Mocked database update). In production, configure role update transaction API.`);
    fetchData();
  };

  if (loading) {
    return <div style={{ textAlign: "center", padding: "3rem" }}>Loading system logs...</div>;
  }

  // Count roles
  const numAdmins = users.filter(u => u.role === 'admin').length;
  const numRecruiters = users.filter(u => u.role === 'recruiter').length;
  const numCandidates = users.filter(u => u.role === 'candidate').length;

  return (
    <div>
      {/* Analytics KPIs */}
      {analytics && (
        <div className="metrics-row">
          <div className="metric-card">
            <span className="metric-label">Users Registered</span>
            <span className="metric-val">{users.length}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Administrators</span>
            <span className="metric-val">{numAdmins}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Recruiters</span>
            <span className="metric-val" style={{ color: "var(--accent)" }}>{numRecruiters}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Candidates Profiles</span>
            <span className="metric-val" style={{ color: "var(--success)" }}>{numCandidates}</span>
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: "2rem", marginTop: "2rem" }}>
        
        {/* Left Side: Users Management Grid */}
        <div className="card-table-wrapper">
          <div className="section-header">
            <h3>Registered Account Management</h3>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table className="hs-table">
              <thead>
                <tr>
                  <th>User Details</th>
                  <th>Role</th>
                  <th>Created Date</th>
                  <th>Manage</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <div style={{ display: "flex", flexDirection: "column" }}>
                        <span style={{ fontWeight: "600" }}>{u.name}</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{u.email}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${
                        u.role === 'admin' ? 'badge-danger' : 
                        u.role === 'recruiter' ? 'badge-warning' : 'badge-success'
                      }`}>
                        {u.role}
                      </span>
                    </td>
                    <td>{new Date(u.created_at).toLocaleDateString()}</td>
                    <td>
                      <select 
                        className="form-input" 
                        style={{ padding: "0.25rem 0.5rem", width: "120px", fontSize: "0.8rem" }}
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                      >
                        <option value="candidate">Candidate</option>
                        <option value="recruiter">Recruiter</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Side: Security & Audit Activity Logs */}
        <div className="card-table-wrapper">
          <div className="section-header" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Activity size={18} className="text-indigo-600" />
            <h3>Platform Activity logs</h3>
          </div>

          <div style={{ padding: "1rem", maxHeight: "500px", overflowY: "auto" }}>
            {logs.length === 0 ? (
              <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
                No recent activity logged.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {logs.map((l) => (
                  <div key={l.id} style={{ display: "flex", gap: "0.75rem", padding: "0.75rem", border: "1px solid var(--border-color)", borderRadius: "8px", backgroundColor: "var(--bg-app)", fontSize: "0.85rem" }}>
                    <div style={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>
                      <span style={{ fontWeight: "600", color: "var(--text-main)" }}>
                        {l.action.toUpperCase()} — {l.user_email || "System"}
                      </span>
                      <span style={{ color: "var(--text-muted)", marginTop: "0.2rem" }}>{l.details}</span>
                      <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "0.4rem" }}>
                        {new Date(l.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

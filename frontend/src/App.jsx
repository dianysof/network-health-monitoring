import { useState, useEffect } from "react";
import "./App.css";

// Chart.js
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Legend,
  Tooltip,
} from "chart.js";

ChartJS.register(
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Legend,
  Tooltip
);

// Base URL configurable por .env (Vite)
const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("token") || "");
  const [email, setEmail] = useState("diana@example.com");
  const [password, setPassword] = useState("supersecret");

  const [endpoints, setEndpoints] = useState([]);
  const [summary, setSummary] = useState([]);
  const [newName, setNewName] = useState("");
  const [newUrl, setNewUrl] = useState("");

  // history + stats + alerts UI
  const [selectedEndpointId, setSelectedEndpointId] = useState(null);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);

  const [alertConfig, setAlertConfig] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [alertSaving, setAlertSaving] = useState(false);

  // auth UI state
  const [authMode, setAuthMode] = useState("login");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  const isLoggedIn = !!token;
  const isLogin = authMode === "login";

  useEffect(() => {
    if (!token) return;
    fetchEndpoints();
    fetchSummary();
  }, [token]);

  // ============================
  // AUTH
  // ============================

  async function handleAuth(e) {
    e.preventDefault();
    setAuthError("");
    setAuthLoading(true);

    try {
      if (!isLogin) {
        const signupRes = await fetch(`${API_BASE}/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });

        if (!signupRes.ok) {
          const body = await signupRes.json().catch(() => ({}));
          throw new Error(body.detail || "Error creating account");
        }
      }

      const loginRes = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!loginRes.ok) {
        const body = await loginRes.json().catch(() => ({}));
        throw new Error(body.detail || "Login failed");
      }

      const data = await loginRes.json();
      setToken(data.access_token);
      localStorage.setItem("token", data.access_token);
    } catch (err) {
      console.error(err);
      setAuthError(err.message || "Authentication error");
    } finally {
      setAuthLoading(false);
    }
  }

  // ============================
  // API CALLS
  // ============================

  async function fetchEndpoints() {
    try {
      const res = await fetch(`${API_BASE}/api/endpoints`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setEndpoints(data.endpoints || []);
    } catch (err) {
      console.error(err);
    }
  }

  async function fetchSummary() {
    try {
      const res = await fetch(`${API_BASE}/api/endpoints/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setSummary(data.endpoints || []);
    } catch (err) {
      console.error(err);
    }
  }

  async function createEndpoint(e) {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/api/endpoints`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: newName, url: newUrl }),
      });

      if (!res.ok) {
        alert("Failed to create endpoint");
        return;
      }

      setNewName("");
      setNewUrl("");
      await fetchEndpoints();
      await fetchSummary();
    } catch (err) {
      console.error(err);
    }
  }

  async function deleteEndpoint(id) {
    if (!confirm("Delete this endpoint?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/endpoints/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) return alert("Failed to delete");

      await fetchEndpoints();
      await fetchSummary();

      if (selectedEndpointId === id) {
        setSelectedEndpointId(null);
        setHistory([]);
        setStats(null);
        setAlertConfig(null);
        setAlerts([]);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function measureNow(id) {
    try {
      const res = await fetch(`${API_BASE}/api/endpoints/${id}/measure`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) return alert("Failed to measure");

      await fetchSummary();
      if (selectedEndpointId === id) {
        await openDetails(id);
      }
    } catch (err) {
      console.error(err);
    }
  }

  function logout() {
    setToken("");
    localStorage.removeItem("token");
    setEndpoints([]);
    setSummary([]);
    setSelectedEndpointId(null);
    setHistory([]);
    setStats(null);
    setAlertConfig(null);
    setAlerts([]);
  }

  // ============================
  // HISTORY + STATS + ALERTS
  // ============================

  async function openDetails(id) {
    setSelectedEndpointId(id);
    try {
      const [histRes, statsRes, configRes, alertsRes] = await Promise.all([
        fetch(`${API_BASE}/api/endpoints/${id}/measurements?limit=50`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE}/api/endpoints/${id}/stats?hours=24`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE}/api/endpoints/${id}/alert-config`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE}/api/endpoints/${id}/alerts?limit=50`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (histRes.ok) {
        const data = await histRes.json();
        setHistory(data.measurements || []);
      }

      if (statsRes.ok) {
        const s = await statsRes.json();
        setStats(s);
      }

      if (configRes.ok) {
        const c = await configRes.json();
        setAlertConfig(c);
      } else {
        setAlertConfig(null);
      }

      if (alertsRes.ok) {
        const a = await alertsRes.json();
        setAlerts(a.alerts || []);
      } else {
        setAlerts([]);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function saveAlertConfig(e) {
    e.preventDefault();
    if (!alertConfig) return;

    setAlertSaving(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/endpoints/${selectedEndpointId}/alert-config`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            latency_threshold_ms: Number(alertConfig.latency_threshold_ms),
            consecutive_fail_threshold: Number(
              alertConfig.consecutive_fail_threshold
            ),
          }),
        }
      );

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        alert(body.detail || "Failed to update alert config");
        return;
      }

      await fetchSummary();
      alert("Alert configuration updated");
    } catch (err) {
      console.error(err);
    } finally {
      setAlertSaving(false);
    }
  }

  // ============================
  // LOGIN VIEW
  // ============================

  if (!isLoggedIn) {
    return (
      <div className="app-shell">
        <div className="app-login">
          <h1 className="login-title">Network Health Dashboard</h1>

          <p className="login-subtitle">
            {isLogin
              ? "Log in to monitor your endpoints."
              : "Create an account to begin."}
          </p>

          <form onSubmit={handleAuth} className="login-form">
            <label className="form-label">
              Email
              <input
                className="form-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>

            <label className="form-label">
              Password
              <input
                className="form-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>

            {authError && (
              <div className="error-box" style={{ color: "red" }}>
                {authError}
              </div>
            )}

            <button className="button" type="submit">
              {authLoading ? "Please wait..." : isLogin ? "Login" : "Create"}
            </button>
          </form>

          <div style={{ marginTop: "20px", textAlign: "center" }}>
            {isLogin ? (
              <>
                <span>Don't have an account? </span>
                <button
                  className="button secondary"
                  onClick={() => setAuthMode("signup")}
                >
                  Sign Up
                </button>
              </>
            ) : (
              <>
                <span>Already registered? </span>
                <button
                  className="button secondary"
                  onClick={() => setAuthMode("login")}
                >
                  Login
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ============================
  // MAIN DASHBOARD
  // ============================

  return (
    <div className="app-shell">
      <div className="app-main">
        <header className="app-header">
          <div>
            <p className="app-eyebrow">FastAPI · Kubernetes · React</p>

            <h1 className="app-title app-title-gradient">
              Network Health Dashboard
            </h1>

            <p className="app-subtitle">
              Track endpoint uptime, latency trends and smart alerts in real time.
            </p>
          </div>

          <button className="button secondary" onClick={logout}>
            Logout
          </button>
        </header>


        {/* NEW ENDPOINT */}
        <section className="section">
          <h2 className="section-title">Add new endpoint</h2>

          <form onSubmit={createEndpoint} className="new-endpoint-form">
            <label className="form-label">
              Name
              <input
                className="form-input"
                placeholder="e.g., Google"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </label>

            <label className="form-label">
              URL
              <input
                className="form-input"
                placeholder="https://example.com"
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
              />
            </label>

            <button className="button" type="submit">
              Add
            </button>
          </form>
        </section>

        {/* ENDPOINT LIST */}
        <section className="section">
          <h2 className="section-title">Your endpoints</h2>

          {endpoints.length === 0 ? (
            <p className="empty-text">No endpoints yet.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>URL</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {endpoints.map((ep) => (
                    <tr key={ep.id}>
                      <td>{ep.id}</td>
                      <td>{ep.name}</td>
                      <td>{ep.url}</td>
                      <td>{new Date(ep.created_at).toLocaleString()}</td>
                      <td>
                        <button
                          className="button secondary"
                          onClick={() => measureNow(ep.id)}
                        >
                          Measure
                        </button>
                        <button
                          className="button secondary"
                          onClick={() => deleteEndpoint(ep.id)}
                        >
                          Delete
                        </button>
                        <button
                          className="button secondary"
                          onClick={() => openDetails(ep.id)}
                        >
                          Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* SUMMARY */}
        <section className="section">
          <h2 className="section-title">Summary</h2>

          {summary.length === 0 ? (
            <p className="empty-text">No summary yet.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>URL</th>
                    <th>Status</th>
                    <th>Latency</th>
                    <th>Observed</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.map((ep) => {
                    const statusLabel = ep.last_status || "UNKNOWN";
                    const badgeClass = ep.alert
                      ? "down"
                      : statusLabel === "UP"
                      ? "up"
                      : statusLabel === "UNKNOWN"
                      ? "unknown"
                      : "down";

                    return (
                      <tr key={ep.id}>
                        <td>{ep.id}</td>
                        <td>{ep.name}</td>
                        <td>{ep.url}</td>
                        <td>
                          <span className={`status-badge ${badgeClass}`}>
                            ● {ep.alert ? "ALERT" : statusLabel}
                          </span>
                        </td>
                        <td>{ep.last_latency_ms ?? "-"}</td>
                        <td>
                          {ep.last_observed_at
                            ? new Date(ep.last_observed_at).toLocaleString()
                            : "-"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* HISTORY + STATS + ALERTS */}
        {selectedEndpointId && (
          <section className="section">
            <h2 className="section-title">
              Details for endpoint #{selectedEndpointId}
            </h2>

            {stats && (
              <div className="stats-box">
                <p>
                  Last {stats.window_hours}h —{" "}
                  <strong>{stats.uptime_percent ?? "-"}% uptime</strong>, avg
                  latency: <strong>{stats.avg_latency_ms ?? "-"} ms</strong>{" "}
                  ({stats.total_checks} checks)
                </p>
              </div>
            )}

            {/* ALERT CONFIG */}
            {alertConfig && (
              <form
                className="alert-config-panel"
                onSubmit={saveAlertConfig}
                autoComplete="off"
              >
                <div className="alert-config-header">
                  <span>Alert configuration</span>
                  <span
                    className={`status-badge ${
                      alertConfig.alert_active ? "down" : "up"
                    }`}
                  >
                    ● {alertConfig.alert_active ? "ALERT ACTIVE" : "Healthy"}
                  </span>
                </div>

                <div className="alert-config-grid">
                  <label className="form-label small">
                    Latency threshold (ms)
                    <input
                      className="form-input"
                      type="number"
                      min={1}
                      value={alertConfig.latency_threshold_ms}
                      onChange={(e) =>
                        setAlertConfig((prev) => ({
                          ...prev,
                          latency_threshold_ms: e.target.value,
                        }))
                      }
                    />
                  </label>

                  <label className="form-label small">
                    Consecutive failures
                    <input
                      className="form-input"
                      type="number"
                      min={1}
                      value={alertConfig.consecutive_fail_threshold}
                      onChange={(e) =>
                        setAlertConfig((prev) => ({
                          ...prev,
                          consecutive_fail_threshold: e.target.value,
                        }))
                      }
                    />
                  </label>
                </div>

                <div className="alert-meta-row">
                  <span>
                    Current consecutive failures:{" "}
                    <strong>{alertConfig.consecutive_failures}</strong>
                  </span>
                  <span>
                    Last alert:{" "}
                    <strong>
                      {alertConfig.last_alert_at
                        ? new Date(
                            alertConfig.last_alert_at
                          ).toLocaleString()
                        : "—"}
                    </strong>
                  </span>
                </div>

                <button className="button" type="submit" disabled={alertSaving}>
                  {alertSaving ? "Saving..." : "Save alert settings"}
                </button>
              </form>
            )}

            {/* LATENCY CHART */}
            {history.length > 0 && (
              <div className="chart-box" style={{ marginBottom: "1.5rem" }}>
                <Line
                  data={{
                    labels: history.map((h) =>
                      new Date(h.observed_at).toLocaleTimeString()
                    ),
                    datasets: [
                      {
                        label: "Latency (ms)",
                        data: history.map((h) => h.latency_ms || 0),
                        fill: false,
                        borderColor: "#22c55e",
                        tension: 0.2,
                      },
                    ],
                  }}
                  options={{
                    responsive: true,
                    plugins: {
                      legend: { display: false },
                    },
                    scales: {
                      x: { ticks: { color: "#e2e8f0" } },
                      y: { ticks: { color: "#e2e8f0" } },
                    },
                  }}
                />
              </div>
            )}

            {/* HISTORY TABLE */}
            {history.length === 0 ? (
              <p className="empty-text">No measurements yet.</p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Observed At</th>
                      <th>Status</th>
                      <th>Latency (ms)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((m, idx) => (
                      <tr key={idx}>
                        <td>{new Date(m.observed_at).toLocaleString()}</td>
                        <td>{m.status}</td>
                        <td>{m.latency_ms ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* ALERTS TABLE */}
            <h3 className="alerts-title">Recent alerts</h3>
            {alerts.length === 0 ? (
              <p className="empty-text">No alerts for this endpoint yet.</p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>When</th>
                      <th>Type</th>
                      <th>Message</th>
                      <th>Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {alerts.map((a) => (
                      <tr key={a.id}>
                        <td>{new Date(a.created_at).toLocaleString()}</td>
                        <td>{a.type}</td>
                        <td>{a.message}</td>
                        <td>{a.value ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

export default App;

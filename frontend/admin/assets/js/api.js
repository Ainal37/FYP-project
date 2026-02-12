// ===== SIT Admin – API Helper =====

const BASE_URL = "http://127.0.0.1:8001";

// ── Token helpers ──
function getToken()  { return localStorage.getItem("sit_token"); }
function setToken(t) { localStorage.setItem("sit_token", t); }
function clearToken() { localStorage.removeItem("sit_token"); }

// ── Auth guard ──
function requireAuth() {
  if (!getToken()) window.location.href = "login.html";
}

// ── Logout ──
function logout() {
  clearToken();
  window.location.href = "login.html";
}

// ── Offline banner ──
function showOfflineBanner(show) {
  let b = document.getElementById("offlineBanner");
  if (!b && show) {
    b = document.createElement("div");
    b.id = "offlineBanner";
    b.className = "offline-banner";
    b.textContent = "Backend offline \u2013 retrying\u2026";
    document.body.prepend(b);
  }
  if (b) b.style.display = show ? "block" : "none";
}

// ── Core fetch wrapper (adds Bearer header) ──
async function authFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) headers["Authorization"] = "Bearer " + token;

  try {
    const res = await fetch(BASE_URL + path, { ...options, headers });
    showOfflineBanner(false);
    if (res.status === 401) {
      clearToken();
      window.location.href = "login.html";
      return;
    }
    return res;
  } catch (err) {
    showOfflineBanner(true);
    throw err;
  }
}

// ── Auth ──
async function login(email, password) {
  const res = await fetch(BASE_URL + "/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Login failed");
  setToken(data.access_token);
  return data;
}

// ── Dashboard ──
async function loadDashboardStats() {
  const res = await authFetch("/dashboard/stats");
  if (!res) return null;
  return res.json();
}

// ── Scans ──
async function createScan(payload) {
  const res = await authFetch("/scans", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!res) return null;
  return res.json();
}

async function listScans(limit = 200) {
  const res = await authFetch("/scans?limit=" + limit);
  if (!res) return [];
  return res.json();
}

// ── Reports ──
async function createReport(payload) {
  const res = await authFetch("/reports", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!res) return null;
  return res.json();
}

async function listReports(limit = 200) {
  const res = await authFetch("/reports?limit=" + limit);
  if (!res) return [];
  return res.json();
}

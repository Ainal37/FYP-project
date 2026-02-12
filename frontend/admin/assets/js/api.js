// ===== SIT Admin – API & Shared Utilities =====

const BASE_URL = "http://127.0.0.1:8001";

// ── Token ──
function getToken()   { return localStorage.getItem("sit_token"); }
function setToken(t)  { localStorage.setItem("sit_token", t); }
function clearToken() { localStorage.removeItem("sit_token"); }
function requireAuth() { if (!getToken()) window.location.href = "login.html"; }
function logout() { clearToken(); window.location.href = "login.html"; }

// ── Offline banner ──
function showOfflineBanner(show) {
  let b = document.getElementById("offlineBanner");
  if (!b && show) {
    b = document.createElement("div"); b.id = "offlineBanner";
    b.className = "offline-banner"; b.textContent = "Backend offline \u2013 retrying\u2026";
    document.body.prepend(b);
  }
  if (b) b.style.display = show ? "block" : "none";
}

// ── Toast notifications ──
function showToast(msg, type = "info") {
  let c = document.getElementById("toastContainer");
  if (!c) { c = document.createElement("div"); c.id = "toastContainer"; c.className = "toast-container"; document.body.appendChild(c); }
  const t = document.createElement("div"); t.className = "toast toast-" + type; t.textContent = msg;
  c.appendChild(t);
  requestAnimationFrame(() => t.classList.add("show"));
  setTimeout(() => { t.classList.remove("show"); setTimeout(() => t.remove(), 300); }, 3500);
}

// ── Core fetch ──
async function authFetch(path, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = "Bearer " + token;
  try {
    const res = await fetch(BASE_URL + path, { ...options, headers });
    showOfflineBanner(false);
    if (res.status === 401) { clearToken(); window.location.href = "login.html"; return; }
    if (res.status === 429) { showToast("Rate limit hit – slow down", "error"); return; }
    return res;
  } catch (err) { showOfflineBanner(true); throw err; }
}

// ── Auth ──
async function login(email, password) {
  const res = await fetch(BASE_URL + "/auth/login", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Login failed");
  setToken(data.access_token); return data;
}

// ── Dashboard ──
async function loadDashboardStats() { const r = await authFetch("/dashboard/stats"); return r ? r.json() : null; }

// ── Scans ──
async function createScan(payload) { const r = await authFetch("/scans", { method: "POST", body: JSON.stringify(payload) }); return r ? r.json() : null; }
async function listScans(limit = 200) { const r = await authFetch("/scans?limit=" + limit); return r ? r.json() : []; }
async function getScan(id) { const r = await authFetch("/scans/" + id); return r ? r.json() : null; }
async function analyzeMessage(message) { const r = await authFetch("/scans/analyze-message", { method: "POST", body: JSON.stringify({ message }) }); return r ? r.json() : null; }

// ── Reports ──
async function createReport(payload) { const r = await authFetch("/reports", { method: "POST", body: JSON.stringify(payload) }); return r ? r.json() : null; }
async function listReports(limit = 200) { const r = await authFetch("/reports?limit=" + limit); return r ? r.json() : []; }
async function updateReport(id, payload) {
  const r = await authFetch("/reports/" + id, { method: "PATCH", body: JSON.stringify(payload) });
  return r ? r.json() : null;
}

// ── Evaluation ──
async function getMetrics() { const r = await authFetch("/evaluation/metrics"); return r ? r.json() : null; }
async function runEvaluation() { const r = await authFetch("/evaluation/run", { method: "POST" }); return r ? r.json() : null; }

// ── Command Palette (Ctrl+K) ──
(function initCommandPalette() {
  const ACTIONS = [
    { label: "Go to Dashboard", key: "D", action: () => window.location.href = "dashboard.html" },
    { label: "Go to Scans",     key: "S", action: () => window.location.href = "scans.html" },
    { label: "Go to Reports",   key: "R", action: () => window.location.href = "reports.html" },
    { label: "Quick Scan URL",  key: "Q", action: () => { window.location.href = "scans.html"; } },
    { label: "Logout",          key: "L", action: logout },
  ];

  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "k") { e.preventDefault(); togglePalette(); }
    if (e.key === "Escape") closePalette();
  });

  function togglePalette() {
    let el = document.getElementById("cmdPalette");
    if (el) { el.style.display = el.style.display === "none" ? "flex" : "none"; if (el.style.display === "flex") el.querySelector("input").focus(); return; }
    el = document.createElement("div"); el.id = "cmdPalette"; el.className = "cmd-overlay"; el.style.display = "flex";
    el.innerHTML = '<div class="cmd-box"><input class="cmd-input" placeholder="Type a command\u2026" /><div class="cmd-list" id="cmdList"></div></div>';
    document.body.appendChild(el);
    el.addEventListener("click", e => { if (e.target === el) closePalette(); });
    const input = el.querySelector("input"); input.focus();
    renderCmds(""); input.addEventListener("input", () => renderCmds(input.value));
  }

  function renderCmds(q) {
    const list = document.getElementById("cmdList"); if (!list) return;
    const filtered = ACTIONS.filter(a => a.label.toLowerCase().includes(q.toLowerCase()));
    list.innerHTML = filtered.map((a, i) =>
      '<div class="cmd-item' + (i === 0 ? ' active' : '') + '" data-idx="' + i + '">' + a.label +
      '<span class="cmd-key">' + a.key + '</span></div>'
    ).join("");
    list.querySelectorAll(".cmd-item").forEach((el, i) => {
      el.addEventListener("click", () => { closePalette(); filtered[i].action(); });
    });
  }

  function closePalette() {
    const el = document.getElementById("cmdPalette"); if (el) el.style.display = "none";
  }
})();

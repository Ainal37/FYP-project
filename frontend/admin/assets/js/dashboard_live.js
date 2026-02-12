// dashboard_live.js
// Auto-refresh stats + latest scans every 5s, highlight new row

let __lastTopScanId = null;

function fmtTime(d = new Date()) {
  return d.toLocaleString();
}

function setStatus(text) {
  const el = document.getElementById("liveStatus");
  if (el) el.textContent = text;
}

async function safeJson(res) {
  const txt = await res.text();
  try { return JSON.parse(txt); } catch { return { raw: txt, status: res.status }; }
}

async function fetchStats() {
  // expects /dashboard/stats
  const res = await apiGet("/dashboard/stats");
  return res;
}

async function fetchLatestScans(limit = 10) {
  // expects /scans (backend already used by your dashboard)
  const res = await apiGet(`/scans?limit=${limit}`);
  return res;
}

function updateStatsUI(stats) {
  // Sesuaikan ID ikut HTML kau (kalau lain, rename)
  // Kalau HTML kau tak ada id ni, skip je (tak crash).
  const map = {
    total_scans: "statTotalScans",
    total_reports: "statTotalReports",
    scam_detected: "statScam",
    suspicious: "statSuspicious",
    safe: "statSafe",
  };

  for (const [k, id] of Object.entries(map)) {
    const el = document.getElementById(id);
    if (el && stats && stats[k] !== undefined) el.textContent = stats[k];
  }
}

function rowHtml(s) {
  const verdict = (s.verdict || "").toLowerCase();
  let badgeClass = "badge-safe";
  let badgeText = "Safe";

  if (verdict.includes("scam")) { badgeClass = "badge-scam"; badgeText = "Scam"; }
  else if (verdict.includes("susp")) { badgeClass = "badge-suspicious"; badgeText = "Suspicious"; }

  const link = (s.link || s.url || "").toString();
  const date = (s.created_at || s.date || "").toString();

  return `
    <tr data-scan-id="${s.id}">
      <td>${s.id ?? ""}</td>
      <td style="max-width:380px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
        ${link}
      </td>
      <td><span class="badge ${badgeClass}">${badgeText}</span></td>
      <td>${s.score ?? 0}</td>
      <td>${date}</td>
    </tr>
  `;
}

function updateLatestScansUI(scans) {
  const tbody = document.querySelector("#latestScansBody");
  if (!tbody || !Array.isArray(scans)) return;

  tbody.innerHTML = scans.map(rowHtml).join("");

  // highlight new top row
  const top = scans[0];
  if (top && top.id !== null && top.id !== undefined) {
    if (__lastTopScanId !== null && top.id !== __lastTopScanId) {
      const tr = tbody.querySelector(`tr[data-scan-id="${top.id}"]`);
      if (tr) {
        tr.classList.add("row-new");
        setTimeout(() => tr.classList.remove("row-new"), 2500);
      }
    }
    __lastTopScanId = top.id;
  }
}

async function refreshAll() {
  try {
    setStatus("Updating...");
    const stats = await fetchStats();
    updateStatsUI(stats);

    const scansResp = await fetchLatestScans(10);
    // support: backend may return {items:[...]} or [...]
    const scans = Array.isArray(scansResp) ? scansResp : (scansResp.items || scansResp.data || []);
    updateLatestScansUI(scans);

    setStatus("Last updated: " + fmtTime());
  } catch (e) {
    console.error(e);
    setStatus("Update failed (check backend/token).");
  }
}

window.addEventListener("load", () => {
  refreshAll();
  setInterval(refreshAll, 5000);
});

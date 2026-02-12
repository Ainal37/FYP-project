// ===== SIT Admin – Dashboard Page =====

requireAuth();

let lastTopId = null;

function setStatus(msg) {
  const el = document.getElementById("liveStatus");
  if (el) el.textContent = msg;
}

function renderDashboard(data) {
  if (!data) return;

  document.getElementById("totalScans").textContent     = data.total_scans ?? "--";
  document.getElementById("totalReports").textContent    = data.total_reports ?? "--";
  document.getElementById("scamCount").textContent       = data.breakdown?.scam ?? "--";
  document.getElementById("suspiciousCount").textContent  = data.breakdown?.suspicious ?? "--";
  document.getElementById("safeCount").textContent       = data.breakdown?.safe ?? "--";

  // ── Latest Scans ──
  const tbody = document.getElementById("latestScansBody");
  const scans = data.latest_scans || [];

  if (scans.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center">No scans yet.</td></tr>';
  } else {
    tbody.innerHTML = scans.map(s => `
      <tr data-id="${s.id}">
        <td>${s.id}</td>
        <td class="link-cell" title="${s.link}">${s.link}</td>
        <td><span class="badge ${s.verdict}">${s.verdict}</span></td>
        <td>${s.score}</td>
        <td>${s.created_at || "\u2014"}</td>
      </tr>
    `).join("");

    const topId = scans[0]?.id;
    if (lastTopId !== null && topId && topId !== lastTopId) {
      const tr = tbody.querySelector('tr[data-id="' + topId + '"]');
      if (tr) {
        tr.classList.add("row-new");
        setTimeout(() => tr.classList.remove("row-new"), 2500);
      }
    }
    lastTopId = topId;
  }

  // ── Latest Reports ──
  const rtbody = document.getElementById("latestReportsBody");
  if (rtbody) {
    const reports = data.latest_reports || [];
    if (reports.length === 0) {
      rtbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center">No reports yet.</td></tr>';
    } else {
      rtbody.innerHTML = reports.map(r => `
        <tr>
          <td>${r.id}</td>
          <td class="link-cell" title="${r.link || ''}">${r.link || "\u2014"}</td>
          <td>${r.report_type || "\u2014"}</td>
          <td><span class="badge ${r.status}">${r.status}</span></td>
          <td>${r.created_at || "\u2014"}</td>
        </tr>
      `).join("");
    }
  }
}

async function refresh() {
  try {
    setStatus("Updating\u2026");
    const data = await loadDashboardStats();
    renderDashboard(data);
    setStatus("Last updated: " + new Date().toLocaleString());
  } catch (err) {
    console.error("Dashboard load error:", err);
    setStatus("Update failed (check backend/token).");
  }
}

refresh();
setInterval(refresh, 5000);

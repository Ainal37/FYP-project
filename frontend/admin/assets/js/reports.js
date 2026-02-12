// ===== SIT Admin – Reports Page =====

requireAuth();

const PER_PAGE = 10;
let allReports    = [];
let currentPage   = 1;
let typingTimer   = null;
let refreshPaused = false;
let lastTopId     = null;

function setStatus(msg) {
  const el = document.getElementById("liveStatus");
  if (el) el.textContent = msg;
}

function getFiltered() {
  const q      = document.getElementById("searchInput").value.trim().toLowerCase();
  const status = document.getElementById("statusFilter").value;
  return allReports.filter(r => {
    if (status && r.status !== status) return false;
    if (q) {
      const hay = ((r.link || "") + " " + (r.description || "")).toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function render() {
  const filtered   = getFiltered();
  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  if (currentPage > totalPages) currentPage = totalPages;

  const start = (currentPage - 1) * PER_PAGE;
  const page  = filtered.slice(start, start + PER_PAGE);

  const tbody = document.getElementById("reportsBody");
  if (page.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-muted text-center">No reports found.</td></tr>';
  } else {
    tbody.innerHTML = page.map(r => `
      <tr data-id="${r.id}">
        <td>${r.id}</td>
        <td class="link-cell" title="${r.link || ''}">${r.link || '\u2014'}</td>
        <td>${r.report_type || '\u2014'}</td>
        <td>${r.description || '\u2014'}</td>
        <td><span class="badge ${r.status}">${r.status}</span></td>
        <td>${r.created_at || '\u2014'}</td>
      </tr>
    `).join("");

    const topId = allReports[0]?.id;
    if (lastTopId !== null && topId && topId !== lastTopId && currentPage === 1) {
      const tr = tbody.querySelector('tr[data-id="' + topId + '"]');
      if (tr) { tr.classList.add("row-new"); setTimeout(() => tr.classList.remove("row-new"), 2500); }
    }
    lastTopId = topId;
  }

  document.getElementById("pageInfo").textContent =
    filtered.length + " result" + (filtered.length !== 1 ? "s" : "") +
    " \u2014 Page " + currentPage + " / " + totalPages;
  document.getElementById("prevBtn").disabled = currentPage <= 1;
  document.getElementById("nextBtn").disabled = currentPage >= totalPages;
}

async function refresh() {
  if (refreshPaused) return;
  try {
    setStatus("Updating\u2026");
    allReports = await listReports() || [];
    render();
    setStatus("Last updated: " + new Date().toLocaleString());
  } catch (err) {
    console.error("Reports load error:", err);
    setStatus("Update failed (check backend/token).");
  }
}

// ── Events ──
document.getElementById("searchInput").addEventListener("input", () => {
  refreshPaused = true;
  clearTimeout(typingTimer);
  typingTimer = setTimeout(() => { refreshPaused = false; }, 2000);
  currentPage = 1;
  render();
});
document.getElementById("statusFilter").addEventListener("change", () => { currentPage = 1; render(); });
document.getElementById("prevBtn").addEventListener("click", () => { if (currentPage > 1) { currentPage--; render(); } });
document.getElementById("nextBtn").addEventListener("click", () => {
  if (currentPage < Math.ceil(getFiltered().length / PER_PAGE)) { currentPage++; render(); }
});

// ── Submit Report form ──
document.getElementById("reportForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const resultDiv = document.getElementById("reportResult");
  resultDiv.style.display = "none";

  const payload = {
    link:        document.getElementById("reportLink").value.trim() || null,
    report_type: document.getElementById("reportType").value,
    description: document.getElementById("reportDescription").value.trim(),
  };

  try {
    const data = await createReport(payload);
    if (!data) return;
    resultDiv.style.display = "block";
    resultDiv.innerHTML = '<div class="stat-card" style="margin-top:12px;">' +
      '<div class="label">Report Submitted</div>' +
      '<div>ID: <strong>' + data.id + '</strong> &nbsp;' +
      '<span class="badge ' + data.status + '">' + data.status + '</span></div></div>';
    document.getElementById("reportForm").reset();
    refreshPaused = false;
    await refresh();
  } catch (err) {
    resultDiv.style.display = "block";
    resultDiv.innerHTML = '<p style="color:var(--danger);">Error: ' + err.message + '</p>';
  }
});

refresh();
setInterval(refresh, 5000);

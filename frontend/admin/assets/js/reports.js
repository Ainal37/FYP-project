// ===== SIT Admin – Reports Page (Table + Kanban) =====
requireAuth();

const PER_PAGE = 10;
let allReports = [], currentPage = 1, typingTimer = null, refreshPaused = false, lastTopId = null;
let viewMode = "table"; // "table" or "kanban"

function setStatus(msg) { const el = document.getElementById("liveStatus"); if (el) el.textContent = msg; }

function getFiltered() {
  const q = document.getElementById("searchInput").value.trim().toLowerCase();
  const st = document.getElementById("statusFilter").value;
  return allReports.filter(r => {
    if (st && r.status !== st) return false;
    if (q) { const h = ((r.link || "") + " " + (r.description || "")).toLowerCase(); if (!h.includes(q)) return false; }
    return true;
  });
}

// ── Table view ──
function renderTable() {
  const f = getFiltered(), tp = Math.max(1, Math.ceil(f.length / PER_PAGE));
  if (currentPage > tp) currentPage = tp;
  const start = (currentPage - 1) * PER_PAGE, page = f.slice(start, start + PER_PAGE);
  const tbody = document.getElementById("reportsBody");

  if (page.length === 0) { tbody.innerHTML = '<tr><td colspan="7" class="text-muted text-center">No reports found</td></tr>'; }
  else {
    tbody.innerHTML = page.map(r =>
      '<tr data-id="' + r.id + '">' +
      '<td>' + r.id + '</td>' +
      '<td class="link-cell" title="' + (r.link || "") + '">' + (r.link || "\u2014") + '</td>' +
      '<td>' + (r.report_type || "\u2014") + '</td>' +
      '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + (r.description || "\u2014") + '</td>' +
      '<td><span class="badge ' + r.status + '">' + r.status + '</span></td>' +
      '<td>' + (r.assignee || "\u2014") + '</td>' +
      '<td><select class="status-select" data-id="' + r.id + '" style="font-size:11px;padding:2px 6px;border:1px solid var(--border);border-radius:4px">' +
      ['new','investigating','resolved'].map(s => '<option value="' + s + '"' + (r.status === s ? ' selected' : '') + '>' + s + '</option>').join("") +
      '</select></td></tr>'
    ).join("");
    tbody.querySelectorAll(".status-select").forEach(sel => {
      sel.addEventListener("change", async e => {
        const id = e.target.dataset.id;
        await updateReport(id, { status: e.target.value });
        showToast("Status updated", "success"); await refresh();
      });
    });
    const topId = allReports[0]?.id;
    if (lastTopId !== null && topId && topId !== lastTopId && currentPage === 1) {
      const tr = tbody.querySelector('tr[data-id="' + topId + '"]');
      if (tr) { tr.classList.add("row-new"); setTimeout(() => tr.classList.remove("row-new"), 2500); }
    }
    lastTopId = topId;
  }
  document.getElementById("pageInfo").textContent = f.length + " result" + (f.length !== 1 ? "s" : "") + " \u2014 Page " + currentPage + " / " + tp;
  document.getElementById("prevBtn").disabled = currentPage <= 1;
  document.getElementById("nextBtn").disabled = currentPage >= tp;
}

// ── Kanban view ──
function renderKanban() {
  ["new", "investigating", "resolved"].forEach(status => {
    const col = document.getElementById("kanban-" + status);
    if (!col) return;
    const items = allReports.filter(r => r.status === status);
    const countEl = col.parentElement.querySelector(".count");
    if (countEl) countEl.textContent = items.length;
    if (items.length === 0) { col.innerHTML = '<div class="text-muted" style="font-size:12px;padding:8px">No items</div>'; return; }
    col.innerHTML = items.slice(0, 20).map(r =>
      '<div class="kanban-card" data-id="' + r.id + '">' +
      '<div class="kc-link">' + (r.link || "No link") + '</div>' +
      '<div style="font-size:11px;color:var(--text-2);margin:4px 0">' + (r.description || "").substring(0, 80) + '</div>' +
      '<div class="kc-meta"><span>' + r.report_type + '</span><span>#' + r.id + '</span></div></div>'
    ).join("");
  });
}

function render() {
  if (viewMode === "kanban") { renderKanban(); } else { renderTable(); }
  document.getElementById("tableView").style.display = viewMode === "table" ? "block" : "none";
  document.getElementById("kanbanView").style.display = viewMode === "kanban" ? "block" : "none";
}

async function refresh() {
  if (refreshPaused) return;
  try { setStatus("Updating\u2026"); allReports = await listReports() || []; render(); setStatus("Last updated: " + new Date().toLocaleTimeString()); }
  catch (e) { setStatus("Update failed"); }
}

// Events
document.getElementById("searchInput").addEventListener("input", () => {
  refreshPaused = true; clearTimeout(typingTimer);
  typingTimer = setTimeout(() => { refreshPaused = false; }, 2000);
  currentPage = 1; render();
});
document.getElementById("statusFilter").addEventListener("change", () => { currentPage = 1; render(); });
document.getElementById("prevBtn").addEventListener("click", () => { if (currentPage > 1) { currentPage--; render(); } });
document.getElementById("nextBtn").addEventListener("click", () => { if (currentPage < Math.ceil(getFiltered().length / PER_PAGE)) { currentPage++; render(); } });
document.getElementById("viewToggle").addEventListener("click", () => {
  viewMode = viewMode === "table" ? "kanban" : "table";
  document.getElementById("viewToggle").textContent = viewMode === "table" ? "Kanban View" : "Table View";
  render();
});

// Submit Report
document.getElementById("reportForm").addEventListener("submit", async e => {
  e.preventDefault();
  const rd = document.getElementById("reportResult"); rd.style.display = "none";
  const payload = {
    link: document.getElementById("reportLink").value.trim() || null,
    report_type: document.getElementById("reportType").value,
    description: document.getElementById("reportDescription").value.trim(),
  };
  try {
    const d = await createReport(payload);
    if (!d) return;
    rd.style.display = "block";
    rd.innerHTML = '<div class="stat-card" style="margin-top:10px"><div class="label">Report Submitted</div><div>ID: <strong>' +
      d.id + '</strong> <span class="badge ' + d.status + '">' + d.status + '</span></div></div>';
    document.getElementById("reportForm").reset();
    showToast("Report submitted", "success");
    refreshPaused = false; await refresh();
  } catch (err) { rd.style.display = "block"; rd.innerHTML = '<p style="color:#dc2626">Error: ' + err.message + '</p>'; }
});

refresh();
setInterval(refresh, 5000);

// ===== SIT Admin – Scans Page =====

requireAuth();

const PER_PAGE = 10;
let allScans     = [];
let currentPage  = 1;
let typingTimer  = null;
let refreshPaused = false;
let lastTopId    = null;

function setStatus(msg) {
  const el = document.getElementById("liveStatus");
  if (el) el.textContent = msg;
}

function getFiltered() {
  const q       = document.getElementById("searchInput").value.trim().toLowerCase();
  const verdict = document.getElementById("verdictFilter").value;
  return allScans.filter(s => {
    if (verdict && s.verdict !== verdict) return false;
    if (q && !(s.link || "").toLowerCase().includes(q)) return false;
    return true;
  });
}

function render() {
  const filtered   = getFiltered();
  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  if (currentPage > totalPages) currentPage = totalPages;

  const start = (currentPage - 1) * PER_PAGE;
  const page  = filtered.slice(start, start + PER_PAGE);

  const tbody = document.getElementById("scansBody");
  if (page.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-muted text-center">No scans found.</td></tr>';
  } else {
    tbody.innerHTML = page.map(s => `
      <tr data-id="${s.id}">
        <td>${s.id}</td>
        <td>${s.telegram_username || s.telegram_user_id || 'Admin'}</td>
        <td class="link-cell" title="${s.link}">${s.link}</td>
        <td><span class="badge ${s.verdict}">${s.verdict}</span></td>
        <td>${s.score}</td>
        <td>${s.reason || '\u2014'}</td>
        <td>${s.created_at || '\u2014'}</td>
      </tr>
    `).join("");

    const topId = allScans[0]?.id;
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
    allScans = await listScans() || [];
    render();
    setStatus("Last updated: " + new Date().toLocaleString());
  } catch (err) {
    console.error("Scans load error:", err);
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
document.getElementById("verdictFilter").addEventListener("change", () => { currentPage = 1; render(); });
document.getElementById("prevBtn").addEventListener("click", () => { if (currentPage > 1) { currentPage--; render(); } });
document.getElementById("nextBtn").addEventListener("click", () => {
  if (currentPage < Math.ceil(getFiltered().length / PER_PAGE)) { currentPage++; render(); }
});

// ── Quick Scan form ──
document.getElementById("scanForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const link = document.getElementById("scanLink").value.trim();
  const resultDiv = document.getElementById("scanResult");
  resultDiv.style.display = "none";
  try {
    const data = await createScan({ link });
    if (!data) return;
    resultDiv.style.display = "block";
    resultDiv.innerHTML = '<div class="stat-card" style="margin-top:12px;">' +
      '<div class="label">Result</div>' +
      '<div><span class="badge ' + data.verdict + '" style="font-size:14px;">' + data.verdict + '</span>' +
      ' &nbsp; Score: <strong>' + data.score + '</strong></div>' +
      '<div class="mt-1 text-muted" style="font-size:13px;">' + data.reason + '</div></div>';
    document.getElementById("scanLink").value = "";
    refreshPaused = false;
    await refresh();
  } catch (err) {
    resultDiv.style.display = "block";
    resultDiv.innerHTML = '<p style="color:var(--danger);">Error: ' + err.message + '</p>';
  }
});

refresh();
setInterval(refresh, 5000);

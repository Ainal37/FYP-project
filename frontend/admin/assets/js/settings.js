/* settings.js – Settings page logic */
(function () {
  if (!getToken()) { window.location.href = "login.html"; return; }

  loadSettings();
  load2FAStatus();
  loadLastBackup();

  function setStatus(msg) {
    var el = document.getElementById("liveStatus");
    if (el) el.textContent = msg;
  }

  /* ── General Settings ── */
  window.loadSettings = async function () {
    try {
      var res = await authFetch("/settings");
      if (!res) return;
      var d = await res.json();
      document.getElementById("settSystemName").value = d.system_name || "";
      var tz = document.getElementById("settTimezone");
      if (tz) { tz.value = d.timezone || "Asia/Kuala_Lumpur"; }
      var ab = document.getElementById("toggleAutoBackup");
      if (ab) { ab.checked = (d.auto_backup === "true"); }
      var bs = document.getElementById("backupScheduleText");
      if (bs) { bs.textContent = d.backup_schedule || "Daily 3:00 AM"; }
      setStatus("Settings loaded");
    } catch (e) { setStatus("Failed to load settings"); }
  };

  window.saveGeneralSettings = async function () {
    try {
      var body = {
        system_name: document.getElementById("settSystemName").value,
        timezone: document.getElementById("settTimezone").value,
      };
      var res = await authFetch("/settings", {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      if (!res) return;
      showToast("General settings saved", "success");
    } catch (e) { showToast("Failed to save settings", "error"); }
  };

  /* ── Change Password ── */
  window.changePassword = async function () {
    var cur = document.getElementById("settCurrentPw").value;
    var nw = document.getElementById("settNewPw").value;
    var cf = document.getElementById("settConfirmPw").value;
    if (!cur || !nw) { showToast("Fill in both password fields", "error"); return; }
    if (nw !== cf) { showToast("Passwords do not match", "error"); return; }
    if (nw.length < 6) { showToast("Password must be at least 6 characters", "error"); return; }
    try {
      var res = await authFetch("/security/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: cur, new_password: nw }),
      });
      if (!res) return;
      if (res.ok) {
        showToast("Password changed", "success");
        document.getElementById("settCurrentPw").value = "";
        document.getElementById("settNewPw").value = "";
        document.getElementById("settConfirmPw").value = "";
      } else {
        var d = await res.json();
        showToast(d.detail || "Failed to change password", "error");
      }
    } catch (e) { showToast("Error changing password", "error"); }
  };

  /* ── 2FA ── */
  window.load2FAStatus = async function () {
    try {
      var res = await authFetch("/security/2fa/status");
      if (!res) return;
      var d = await res.json();
      var toggle = document.getElementById("toggle2FA");
      if (toggle) toggle.checked = d.totp_enabled || false;
    } catch (e) {}
  };

  window.handle2FAToggle = async function (el) {
    if (el.checked) {
      // Start 2FA setup
      try {
        var res = await authFetch("/security/2fa/setup", { method: "POST" });
        if (!res) { el.checked = false; return; }
        if (res.ok) {
          var d = await res.json();
          document.getElementById("twofaSecret").textContent = d.secret;
          document.getElementById("twofaSetupPanel").style.display = "block";
          showToast("Add the secret to your authenticator app", "info");
        } else {
          var err = await res.json();
          showToast(err.detail || "2FA setup failed", "error");
          el.checked = false;
        }
      } catch (e) { el.checked = false; showToast("Failed to setup 2FA", "error"); }
    } else {
      // Disable 2FA
      try {
        var res = await authFetch("/security/2fa/disable", { method: "POST" });
        if (!res) { el.checked = true; return; }
        if (res.ok) {
          document.getElementById("twofaSetupPanel").style.display = "none";
          showToast("2FA disabled", "success");
        } else {
          var err = await res.json();
          showToast(err.detail || "Failed to disable 2FA", "error");
          el.checked = true;
        }
      } catch (e) { el.checked = true; }
    }
  };

  window.confirm2FA = async function () {
    var code = document.getElementById("twofaConfirmCode").value.trim();
    if (code.length !== 6) { showToast("Enter a 6-digit code", "error"); return; }
    try {
      var res = await authFetch("/security/2fa/confirm", {
        method: "POST",
        body: JSON.stringify({ code: code }),
      });
      if (!res) return;
      if (res.ok) {
        document.getElementById("twofaSetupPanel").style.display = "none";
        showToast("2FA enabled successfully!", "success");
      } else {
        var d = await res.json();
        showToast(d.detail || "Invalid code", "error");
      }
    } catch (e) { showToast("Error confirming 2FA", "error"); }
  };

  /* ── Backup ── */
  window.loadLastBackup = async function () {
    try {
      var res = await authFetch("/backup?limit=1");
      if (!res) return;
      var list = await res.json();
      if (list.length > 0) {
        document.getElementById("lastBackupTime").textContent = list[0].created_at || "Unknown";
      }
    } catch (e) {}
  };

  window.runManualBackup = async function () {
    try {
      var res = await authFetch("/backup/run", {
        method: "POST",
        body: JSON.stringify({ scopes: ["system_settings", "admin_users", "reports", "audit_logs"] }),
      });
      if (!res) return;
      if (res.ok) {
        showToast("Backup completed", "success");
        loadLastBackup();
      } else {
        showToast("Backup failed", "error");
      }
    } catch (e) { showToast("Backup error", "error"); }
  };

  window.downloadLatestBackup = async function () {
    var btn = document.getElementById("btnDownloadBackup");
    if (btn) { btn.disabled = true; btn.textContent = "Downloading..."; }
    try {
      var list = await listBackups();
      if (!list || list.length === 0) { showToast("No backups to download", "error"); return; }
      var latest = list[0];
      if (latest.status !== "done" || !latest.file_path) { showToast("Latest backup has no file", "error"); return; }
      await downloadBackup(latest.id);
      showToast("Download started", "success");
    } catch (e) { showToast(e.message || "Download failed", "error"); }
    if (btn) { btn.disabled = false; btn.textContent = "Download latest backup"; }
  };

  window.openRestoreModal = function () {
    var sel = document.getElementById("restoreBackupId");
    var modal = document.getElementById("restoreBackupModal");
    if (!sel || !modal) return;
    sel.innerHTML = "<option value=\"\">Loading...</option>";
    modal.style.display = "flex";
    listBackups().then(function (list) {
      sel.innerHTML = "";
      if (!list || list.length === 0) { sel.innerHTML = "<option value=\"\">No backups</option>"; return; }
      list.forEach(function (b) {
        if (b.status === "done" && b.file_path) {
          var opt = document.createElement("option");
          opt.value = b.id;
          opt.textContent = "Backup #" + b.id + " – " + (b.created_at || "");
          sel.appendChild(opt);
        }
      });
      if (sel.options.length === 0) sel.innerHTML = "<option value=\"\">No completed backups</option>";
    });
    document.getElementById("restoreConfirm").value = "";
  };

  window.closeRestoreModal = function () {
    var modal = document.getElementById("restoreBackupModal");
    if (modal) modal.style.display = "none";
  };

  window.submitRestore = async function () {
    var confirmVal = document.getElementById("restoreConfirm").value.trim();
    if (confirmVal !== "RESTORE") { showToast("Type RESTORE to confirm", "error"); return; }
    var backupId = document.getElementById("restoreBackupId").value;
    var mode = document.getElementById("restoreMode").value || "safe";
    if (!backupId) { showToast("Select a backup", "error"); return; }
    var btn = document.getElementById("btnRestoreSubmit");
    if (btn) { btn.disabled = true; btn.textContent = "Restoring..."; }
    try {
      var res = await restoreBackup(parseInt(backupId, 10), mode);
      if (res && res.ok) {
        showToast("Restore completed: " + mode, "success");
        closeRestoreModal();
        loadSettings();
        loadLastBackup();
      } else {
        showToast(res && res.detail ? res.detail : "Restore failed", "error");
      }
    } catch (e) { showToast(e.message || "Restore failed", "error"); }
    if (btn) { btn.disabled = false; btn.textContent = "Restore"; }
  };

  window.saveAutoBackup = async function (el) {
    try {
      var res = await authFetch("/settings", {
        method: "PATCH",
        body: JSON.stringify({ auto_backup: el.checked ? "true" : "false" }),
      });
      if (res && res.ok) {
        showToast("Auto-backup " + (el.checked ? "enabled" : "disabled"), "success");
      }
    } catch (e) {}
  };
})();

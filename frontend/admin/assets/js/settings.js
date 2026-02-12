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
        body: JSON.stringify({ scopes: ["user_data", "reports", "system_settings", "audit_logs"] }),
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

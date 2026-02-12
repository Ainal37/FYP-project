// ===== SIT Admin – Login (with 2FA support) =====
if (getToken()) window.location.href = "dashboard.html";

var _tempToken = null;

document.getElementById("loginForm").addEventListener("submit", async function (e) {
  e.preventDefault();
  var err = document.getElementById("errorMsg");
  err.style.display = "none";
  try {
    var data = await login(
      document.getElementById("email").value.trim(),
      document.getElementById("password").value
    );

    if (data.requires_2fa && data.temp_token) {
      // Show 2FA step
      _tempToken = data.temp_token;
      document.getElementById("loginForm").style.display = "none";
      document.getElementById("twofaSection").style.display = "block";
      document.getElementById("twofaCode").focus();
    } else if (data.access_token) {
      setToken(data.access_token);
      window.location.href = "dashboard.html";
    }
  } catch (ex) {
    err.textContent = ex.message || "Login failed";
    err.style.display = "block";
  }
});

// 2FA form handler
var twofaForm = document.getElementById("twofaForm");
if (twofaForm) {
  twofaForm.addEventListener("submit", async function (e) {
    e.preventDefault();
    var err = document.getElementById("errorMsg");
    err.style.display = "none";
    var code = document.getElementById("twofaCode").value.trim();
    if (code.length !== 6) {
      err.textContent = "Enter a 6-digit code";
      err.style.display = "block";
      return;
    }
    try {
      var data = await verify2FA(_tempToken, code);
      if (data.access_token) {
        setToken(data.access_token);
        window.location.href = "dashboard.html";
      }
    } catch (ex) {
      err.textContent = ex.message || "Invalid 2FA code";
      err.style.display = "block";
    }
  });
}

// Back to login link
window.show2FABack = function () {
  _tempToken = null;
  document.getElementById("twofaSection").style.display = "none";
  document.getElementById("loginForm").style.display = "block";
  document.getElementById("errorMsg").style.display = "none";
  document.getElementById("twofaCode").value = "";
};

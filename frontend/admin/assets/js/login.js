// ===== SIT Admin – Login =====
if (getToken()) window.location.href = "dashboard.html";

document.getElementById("loginForm").addEventListener("submit", async e => {
  e.preventDefault();
  const err = document.getElementById("errorMsg"); err.style.display = "none";
  try {
    await login(document.getElementById("email").value.trim(), document.getElementById("password").value);
    window.location.href = "dashboard.html";
  } catch (ex) {
    err.textContent = ex.message || "Login failed"; err.style.display = "block";
  }
});

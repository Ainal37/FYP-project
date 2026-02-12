// ===== SIT Admin – Login Page =====

if (getToken()) window.location.href = "dashboard.html";

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorDiv = document.getElementById("errorMsg");
  errorDiv.style.display = "none";

  const email    = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  try {
    await login(email, password);
    window.location.href = "dashboard.html";
  } catch (err) {
    errorDiv.textContent = err.message || "Login failed. Is the backend running?";
    errorDiv.style.display = "block";
  }
});

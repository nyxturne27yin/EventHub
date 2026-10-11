const form = document.getElementById("loginForm");
const errorBox = document.getElementById("loginError");

form.addEventListener("submit", async function (event) {
    event.preventDefault();
    errorBox.classList.add("d-none");

    try {
        const response = await fetch("http://127.0.0.1:8000/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: document.getElementById("email").value.trim().toLowerCase(),
                password: document.getElementById("password").value
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Login failed.");
        }

        sessionStorage.setItem("access_token", data.access_token);
        window.location.href = "profile.html";
    } catch (error) {
        errorBox.textContent = error.message || "Cannot connect to backend.";
        errorBox.classList.remove("d-none");
    }
});

"use strict";

const form = document.getElementById("loginForm");
const errorBox = document.getElementById("loginError");
const submitButton = document.getElementById("loginSubmit");
const passwordInput = document.getElementById("password");
const togglePasswordButton = document.getElementById("togglePassword");
const API_BASE_URL = "http://127.0.0.1:8000";

if (togglePasswordButton && passwordInput) {
    togglePasswordButton.addEventListener("click", () => {
        const showPassword = passwordInput.type === "password";
        passwordInput.type = showPassword ? "text" : "password";
        togglePasswordButton.textContent = showPassword ? "Hide" : "Show";
        togglePasswordButton.setAttribute("aria-pressed", String(showPassword));
        togglePasswordButton.setAttribute(
            "aria-label",
            showPassword ? "Hide password" : "Show password"
        );
    });
}

if (form && errorBox && submitButton) {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        errorBox.textContent = "";
        errorBox.classList.add("d-none");

        if (!form.reportValidity()) return;

        submitButton.disabled = true;
        submitButton.setAttribute("aria-busy", "true");
        submitButton.textContent = "Logging in…";

        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json"
                },
                body: JSON.stringify({
                    email: document.getElementById("email").value.trim().toLowerCase(),
                    password: passwordInput.value
                })
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                const detail = data.detail;
                throw new Error(
                    Array.isArray(detail)
                        ? detail.map((item) => item.msg).join(" ")
                        : (typeof detail === "string" ? detail : "Login failed. Please check your credentials.")
                );
            }

            if (!data.access_token) {
                throw new Error("Login succeeded, but no access token was received.");
            }

            sessionStorage.setItem("access_token", data.access_token);
            window.location.href = "profile.html";
        } catch (error) {
            errorBox.textContent = error.message || "Cannot connect to EventHub. Check that the backend is running.";
            errorBox.classList.remove("d-none");
        } finally {
            submitButton.disabled = false;
            submitButton.removeAttribute("aria-busy");
            submitButton.textContent = "Log in";
        }
    });
}

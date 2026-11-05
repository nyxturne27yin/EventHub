
"use strict";

const form = document.getElementById("loginForm");
const errorBox = document.getElementById("loginError");
const submitButton = document.getElementById("loginSubmit");
const passwordInput = document.getElementById("password");
const togglePasswordButton = document.getElementById("togglePassword");

const API_BASE_URL = window.EVENTHUB_API_BASE_URL;

if (togglePasswordButton && passwordInput) {
    togglePasswordButton.addEventListener("click", () => {
        const showPassword = passwordInput.type === "password";

        passwordInput.type = showPassword ? "text" : "password";
        togglePasswordButton.textContent = showPassword ? "Hide" : "Show";

        togglePasswordButton.setAttribute(
            "aria-pressed",
            String(showPassword)
        );

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
            // Step 1: Authenticate the user.
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json"
                },
                body: JSON.stringify({
                    email: document.getElementById("email")
                        .value.trim().toLowerCase(),
                    password: passwordInput.value
                })
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                const detail = data.detail;

                throw new Error(
                    Array.isArray(detail)
                        ? detail.map((item) => item.msg).join(" ")
                        : (
                            typeof detail === "string"
                                ? detail
                                : "Login failed. Please check your credentials."
                        )
                );
            }

            if (!data.access_token) {
                throw new Error(
                    "Login succeeded, but no access token was received."
                );
            }

            // Step 2: Store the authentication token.
            sessionStorage.setItem("access_token", data.access_token);

            // Step 3: Retrieve the actual authenticated user's role.
            const profileResponse = await fetch(`${API_BASE_URL}/auth/me`, {
                method: "GET",
                headers: {
                    Accept: "application/json",
                    Authorization: `Bearer ${data.access_token}`
                }
            });

            const profile = await profileResponse.json().catch(() => ({}));

            if (!profileResponse.ok) {
                throw new Error(
                    "Unable to retrieve your account information. Please log in again."
                );
            }

            // Step 4: Redirect according to the server-provided role.
            const role = profile.role;

            const roleRedirects = {
    student: "student-dashboard.html",
    organizer: "organizer-dashboard.html",
    administrator: "admin-dashboard.html"
};

            const destination = roleRedirects[role];

            if (!destination) {
                throw new Error(
                    "Your account does not have a configured dashboard. Please contact support."
                );
            }

            window.location.href = destination;

        } catch (error) {
            sessionStorage.removeItem("access_token");

            errorBox.textContent =
                error.message ||
                "Cannot connect to EventHub. Check that the backend is running.";

            errorBox.classList.remove("d-none");

        } finally {
            submitButton.disabled = false;
            submitButton.removeAttribute("aria-busy");
            submitButton.textContent = "Log in";
        }
    });
}

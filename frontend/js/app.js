
// Accessible show/hide controls shared by password fields on authentication pages.
document.querySelectorAll("[data-toggle-password]").forEach((button) => {
    button.addEventListener("click", () => {
        const input = document.getElementById(button.dataset.togglePassword);
        if (!input) return;

        const showPassword = input.type === "password";
        input.type = showPassword ? "text" : "password";
        button.textContent = showPassword ? "Hide" : "Show";
        button.setAttribute("aria-pressed", String(showPassword));
        button.setAttribute("aria-label", showPassword ? "Hide password" : "Show password");
    });
});

const API_BASE_URL = "http://127.0.0.1:8000";

const form = document.getElementById("registrationForm");
const errorBox = document.getElementById("registrationError");
const successBox = document.getElementById("registrationSuccess");

if (form && errorBox && successBox) {
    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        errorBox.textContent = "";
        errorBox.classList.remove("d-none");
        errorBox.style.display = "none";
        successBox.textContent = "";
        successBox.classList.add("d-none");

        const fullName = document.getElementById("fullName").value.trim();
        const email = document.getElementById("email").value.trim().toLowerCase();
        const password = document.getElementById("password").value;
        const confirmPassword = document.getElementById("confirmPassword").value;

        function showError(message) {
            errorBox.textContent = message;
            errorBox.classList.remove("d-none");
            errorBox.style.display = "block";
        }

        if (!fullName || !/^[0-9]{8,}@uap-bd\.edu$/i.test(email)) {
            showError("Enter your name and a valid UAP email.");
            return;
        }

        if (password.length < 8 || !/[A-Za-z]/.test(password) ||
            !/\d/.test(password) || !/[@$!%*?&]/.test(password)) {
            showError("Password needs 8 characters, a letter, a number and a symbol.");
            return;
        }

        if (password !== confirmPassword) {
            showError("Passwords do not match.");
            return;
        }

        const button = form.querySelector('button[type="submit"]');
        if (button) {
            button.disabled = true;
            button.setAttribute("aria-busy", "true");
            button.textContent = "Creating account…";
        }

        try {
            const response = await fetch(API_BASE_URL + "/auth/register", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Accept": "application/json" },
                body: JSON.stringify({
                    full_name: fullName,
                    email: email,
                    password: password,
                    confirm_password: confirmPassword
                })
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                const detail = data.detail;
                throw new Error(
                    Array.isArray(detail)
                        ? detail.map(item => item.msg).join(", ")
                        : (detail || "Registration failed.")
                );
            }

            successBox.replaceChildren();
            const successText = document.createElement("p");
            successText.className = "mb-2";
            successText.textContent = "Registration successful! Your account has been created.";
            const loginLink = document.createElement("a");
            loginLink.className = "btn btn-success btn-sm";
            loginLink.href = "login.html";
            loginLink.textContent = "Continue to log in";
            successBox.append(successText, loginLink);
            successBox.classList.remove("d-none");
            successBox.style.display = "block";
        } catch (error) {
            showError(error.message || "Cannot connect to backend. Check that it is running.");
            console.error("Registration error:", error);
        } finally {
            if (button) {
                button.disabled = false;
                button.removeAttribute("aria-busy");
                button.textContent = "Create Account";
            }
        }
    });
}

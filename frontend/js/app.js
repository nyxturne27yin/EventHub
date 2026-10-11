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
            button.textContent = "Creating Account...";
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

            successBox.textContent = "Registration successful! Your account has been created.";
            successBox.classList.remove("d-none");
            successBox.style.display = "block";
        } catch (error) {
            showError(error.message || "Cannot connect to backend. Check that it is running.");
            console.error("Registration error:", error);
        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = "Create Account";
            }
        }
    });
} else {
    console.error("Registration form or message boxes are missing from register.html.");
}

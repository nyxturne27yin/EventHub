
"use strict";

const form = document.getElementById("resetForm");
const newPasswordInput = document.getElementById("newPassword");
const confirmPasswordInput = document.getElementById("confirmPassword");
const messageBox = document.getElementById("message");
const submitButton = document.getElementById("submitButton");

const API_BASE_URL = "http://127.0.0.1:8000";
const resetToken = new URLSearchParams(window.location.search).get("token");

function showMessage(message, type) {
    messageBox.textContent = message;
    messageBox.className = `alert alert-${type}`;
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!resetToken) {
        showMessage(
            "Reset token is missing. Please request a new password reset link.",
            "danger"
        );
        return;
    }

    const newPassword = newPasswordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    if (newPassword !== confirmPassword) {
        showMessage("Passwords do not match.", "danger");
        return;
    }

    const passwordPattern = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&]).{8,128}$/;

    if (!passwordPattern.test(newPassword)) {
        showMessage(
            "Password must be 8–128 characters and contain a letter, a number, and a special character (@$!%*?&).",
            "danger"
        );
        return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Resetting...";

    try {
        const response = await fetch(
            `${API_BASE_URL}/auth/reset-password`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    token: resetToken,
                    new_password: newPassword
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Password reset failed. Please request a new link."
            );
        }

        showMessage(
            "Password reset successfully! You can now log in with your new password.",
            "success"
        );

        form.reset();
        submitButton.disabled = true;
    } catch (error) {
        showMessage(
            error.message ||
                "Could not connect to EventHub. Please try again.",
            "danger"
        );
    } finally {
        if (!submitButton.disabled) {
            submitButton.textContent = "Reset password";
        }
    }
});

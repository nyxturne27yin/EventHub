
"use strict";

const form = document.getElementById("forgotForm");
const emailInput = document.getElementById("email");
const messageBox = document.getElementById("message");
const submitButton = document.getElementById("submitButton");

const API_BASE_URL = "http://127.0.0.1:8000";

function showMessage(message, type) {
    messageBox.textContent = message;
    messageBox.className = `alert alert-${type}`;
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = emailInput.value.trim();

    if (!email) {
        showMessage("Please enter your email address.", "danger");
        return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Sending...";

    try {
        const response = await fetch(
            `${API_BASE_URL}/auth/forgot-password`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ email })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Unable to process your request. Please try again."
            );
        }

        showMessage(
            data.message ||
                "If an eligible account exists, password reset instructions will be sent to its email address.",
            "success"
        );

        form.reset();
    } catch (error) {
        showMessage(
            "Could not connect to EventHub. Please ensure the backend server is running and try again.",
            "danger"
        );
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Send reset link";
    }
});

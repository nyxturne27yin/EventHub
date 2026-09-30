// EventHub API configuration
const API_BASE_URL = "http://127.0.0.1:8000";

// Make a GET request to an EventHub API endpoint
async function getFromApi(endpoint) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);

    if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
    }

    return response.json();
}

// Registration form validation
const registrationForm = document.getElementById("registrationForm");

if (registrationForm) {
    registrationForm.addEventListener("submit", function (event) {
        event.preventDefault();

        const fullName = document.getElementById("fullName");
        const email = document.getElementById("email");
        const password = document.getElementById("password");
        const confirmPassword = document.getElementById("confirmPassword");

        const errorMessage = document.getElementById("registrationError");
        const successMessage = document.getElementById("registrationSuccess");

        // Reset previous validation state
        registrationForm.classList.remove("was-validated");
        errorMessage.classList.add("d-none");
        successMessage.classList.add("d-none");

        let isValid = true;

        // Full name validation
        if (!fullName.value.trim()) {
            fullName.classList.add("is-invalid");
            isValid = false;
        } else {
            fullName.classList.remove("is-invalid");
        }

        // Email validation
        const emailPattern = /^[^\s@]+@uap-bd\.edu$/i;

        if (!emailPattern.test(email.value.trim())) {
            email.classList.add("is-invalid");
            isValid = false;
        } else {
            email.classList.remove("is-invalid");
        }

        // Password validation
        const passwordPattern =
            /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&]).{8,128}$/;

        if (!passwordPattern.test(password.value)) {
            password.classList.add("is-invalid");
            isValid = false;
        } else {
            password.classList.remove("is-invalid");
        }

        // Confirm password validation
        if (
            !confirmPassword.value ||
            confirmPassword.value !== password.value
        ) {
            confirmPassword.classList.add("is-invalid");
            isValid = false;
        } else {
            confirmPassword.classList.remove("is-invalid");
        }

        // Show validation result
        if (!isValid) {
            errorMessage.textContent =
                "Please correct the highlighted fields and try again.";
            errorMessage.classList.remove("d-none");
            return;
        }

        // Temporary success feedback
        successMessage.textContent =
            "Registration information is valid and ready to be submitted.";
        successMessage.classList.remove("d-none");
    });
}

console.log("EventHub frontend JavaScript loaded successfully.");
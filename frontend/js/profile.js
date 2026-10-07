const PROFILE_API_URL = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", loadProfile);

async function loadProfile() {
    const loading = document.getElementById("profileLoading");
    const error = document.getElementById("profileError");
    const content = document.getElementById("profileContent");

    const token = sessionStorage.getItem("access_token");

    if (!token) {
        loading.classList.add("d-none");
        error.textContent = "Please log in to view your profile.";
        error.classList.remove("d-none");
        return;
    }

    try {
        const response = await fetch(`${PROFILE_API_URL}/auth/me`, {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            }
        });

        if (response.status === 401) {
            throw new Error("Your session has expired. Please log in again.");
        }

        if (!response.ok) {
            throw new Error("Unable to load your profile.");
        }

        const user = await response.json();

        document.getElementById("profileName").textContent = user.name || "-";
        document.getElementById("profileEmail").textContent = user.email || "-";
        document.getElementById("profileRole").textContent = user.role || "-";

        loading.classList.add("d-none");
        content.classList.remove("d-none");

    } catch (err) {
        loading.classList.add("d-none");
        error.textContent = err.message;
        error.classList.remove("d-none");
    }
}

document.getElementById("editProfileBtn")?.addEventListener("click", function () {
    alert("Profile editing will be available soon.");
});
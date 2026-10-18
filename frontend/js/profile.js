
const PROFILE_API_URL = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", loadProfile);

let organizerProfile = null;

async function loadProfile() {
    const loading = document.getElementById("profileLoading");
    const error = document.getElementById("profileError");
    const content = document.getElementById("profileContent");
    const message = document.getElementById("profileMessage");

    const token = sessionStorage.getItem("access_token");

    if (!token) {
        loading.classList.add("d-none");
        error.textContent = "Please log in to view your profile.";
        error.classList.remove("d-none");
        return;
    }

    try {
        const response = await fetch(`${PROFILE_API_URL}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` }
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

        if (String(user.role || "").toLowerCase() === "organizer") {
            document.getElementById("organizerProfileSection").classList.remove("d-none");
            await loadOrganizerProfile(token);
        }

        loading.classList.add("d-none");
        content.classList.remove("d-none");
    } catch (err) {
        loading.classList.add("d-none");
        error.textContent = err.message;
        error.classList.remove("d-none");
    }
}

async function loadOrganizerProfile(token) {
    const response = await fetch(`${PROFILE_API_URL}/organizer-profiles/me`, {
        headers: { Authorization: `Bearer ${token}` }
    });

    if (!response.ok) {
        throw new Error("Unable to load organizer profile.");
    }

    organizerProfile = await response.json();
    showOrganizerProfile(organizerProfile);
}

function showOrganizerProfile(profile) {
    document.getElementById("organizationNameDisplay").textContent =
        profile.organization_name || "Not provided";
    document.getElementById("departmentDisplay").textContent =
        profile.department || "Not provided";
    document.getElementById("bioDisplay").textContent =
        profile.bio || "Not provided";
    document.getElementById("contactPhoneDisplay").textContent =
        profile.contact_phone || "Not provided";
}

function showMessage(text, type = "success") {
    const message = document.getElementById("profileMessage");
    message.textContent = text;
    message.className = `alert alert-${type}`;
}

document.getElementById("editProfileBtn")?.addEventListener("click", () => {
    if (!organizerProfile) return;

    document.getElementById("organizationName").value =
        organizerProfile.organization_name || "";
    document.getElementById("department").value =
        organizerProfile.department || "";
    document.getElementById("bio").value = organizerProfile.bio || "";
    document.getElementById("contactPhone").value =
        organizerProfile.contact_phone || "";

    document.getElementById("organizerProfileDetails").classList.add("d-none");
    document.getElementById("organizerProfileForm").classList.remove("d-none");
    document.getElementById("profileMessage").classList.add("d-none");
});

document.getElementById("cancelProfileBtn")?.addEventListener("click", () => {
    document.getElementById("organizerProfileForm").classList.add("d-none");
    document.getElementById("organizerProfileDetails").classList.remove("d-none");
});

document.getElementById("organizerProfileForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();

    const token = sessionStorage.getItem("access_token");
    const saveButton = document.getElementById("saveProfileBtn");

    if (!token) {
        showMessage("Please log in again.", "danger");
        return;
    }

    const payload = {
        organization_name: document.getElementById("organizationName").value,
        department: document.getElementById("department").value,
        bio: document.getElementById("bio").value,
        contact_phone: document.getElementById("contactPhone").value
    };

    saveButton.disabled = true;

    try {
        const response = await fetch(`${PROFILE_API_URL}/organizer-profiles/me`, {
            method: "PUT",
            headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (response.status === 401) {
            throw new Error("Your session has expired. Please log in again.");
        }
        if (response.status === 403) {
            throw new Error("Only organizer accounts can update this profile.");
        }
        if (!response.ok) {
            const result = await response.json().catch(() => ({}));
            throw new Error(result.detail || "Could not save organizer profile.");
        }

        organizerProfile = await response.json();
        showOrganizerProfile(organizerProfile);
        document.getElementById("organizerProfileForm").classList.add("d-none");
        document.getElementById("organizerProfileDetails").classList.remove("d-none");
        showMessage("Organizer profile saved successfully.");
    } catch (err) {
        showMessage(err.message, "danger");
    } finally {
        saveButton.disabled = false;
    }
});

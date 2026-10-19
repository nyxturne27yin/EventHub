
const PROFILE_API_URL = "http://127.0.0.1:8000";

let organizerProfile = null;
let studentCertificates = [];
let activeCertificateCategory = "All";

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
            headers: { Authorization: `Bearer ${token}` }
        });

        if (response.status === 401) {
            throw new Error("Your session has expired. Please log in again.");
        }

        if (!response.ok) {
            throw new Error("Unable to load your profile.");
        }

        const user = await response.json();
        const role = String(
            typeof user.role === "object" ? user.role?.name : user.role || ""
        ).toLowerCase();

        document.getElementById("profileName").textContent = user.name || "-";
        document.getElementById("profileEmail").textContent = user.email || "-";
        document.getElementById("profileRole").textContent = role || "-";

        if (role === "organizer") {
            document.getElementById("organizerProfileSection")
                .classList.remove("d-none");
            await loadOrganizerProfile(token);
        }

        if (role === "student") {
            document.getElementById("studentCertificatesSection")
                .classList.remove("d-none");
            await loadStudentCertificates(token);
        }

        loading.classList.add("d-none");
        content.classList.remove("d-none");
    } catch (err) {
        loading.classList.add("d-none");
        error.textContent = err.message || "Unable to load your profile.";
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

document.getElementById("organizerProfileForm")?.addEventListener(
    "submit",
    async (event) => {
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
            const response = await fetch(
                `${PROFILE_API_URL}/organizer-profiles/me`,
                {
                    method: "PUT",
                    headers: {
                        Authorization: `Bearer ${token}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(payload)
                }
            );

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
    }
);

async function loadStudentCertificates(token) {
    const message = document.getElementById("certificateMessage");
    const empty = document.getElementById("certificatesEmpty");
    const list = document.getElementById("certificatesList");

    try {
        const response = await fetch(`${PROFILE_API_URL}/certificates/me`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error("Your session has expired. Please log in again.");
            }

            if (response.status === 403) {
                throw new Error("Only student accounts can view these certificates.");
            }

            throw new Error("Unable to load certificates.");
        }

        studentCertificates = await response.json();
        renderStudentCertificates();
    } catch (err) {
        list.replaceChildren();
        empty.classList.add("d-none");
        message.textContent = err.message;
        message.className = "alert alert-danger";
    }
}

function renderStudentCertificates() {
    const list = document.getElementById("certificatesList");
    const empty = document.getElementById("certificatesEmpty");
    const message = document.getElementById("certificateMessage");

    list.replaceChildren();
    message.classList.add("d-none");

    const certificates = studentCertificates.filter((cert) =>
        activeCertificateCategory === "All" ||
        cert.category === activeCertificateCategory
    );

    empty.textContent = certificates.length
        ? ""
        : activeCertificateCategory === "All"
            ? "No certificates are available yet."
            : `No ${activeCertificateCategory} certificates found.`;

    empty.classList.toggle("d-none", certificates.length > 0);

    certificates.forEach((cert) => {
        const column = document.createElement("div");
        column.className = "col-12 col-md-6";

        const card = document.createElement("div");
        card.className = "card h-100";

        const body = document.createElement("div");
        body.className = "card-body";

        const title = document.createElement("h3");
        title.className = "h5";
        title.textContent = cert.title || `${cert.event_title} Certificate`;

        const event = document.createElement("p");
        event.className = "mb-1";
        event.textContent = `Event: ${cert.event_title}`;

        const category = document.createElement("p");
        category.className = "mb-1";
        category.textContent = `Category: ${cert.category}`;

        const issued = document.createElement("p");
        issued.className = "mb-1";
        issued.textContent = `Issued: ${
            cert.issued_at
                ? new Date(cert.issued_at).toLocaleDateString()
                : "Not available"
        }`;

        const id = document.createElement("p");
        id.className = "small text-muted";
        id.textContent = `Certificate ID: ${cert.certificate_id}`;

        const link = document.createElement("a");
        link.className = "btn btn-primary btn-sm";
        link.href = `${PROFILE_API_URL}${cert.verification_path}`;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Verify Certificate";

        body.append(title, event, category, issued, id, link);
        card.append(body);
        column.append(card);
        list.append(column);
    });
}

document.querySelectorAll(".certificate-filter").forEach((button) => {
    button.addEventListener("click", () => {
        activeCertificateCategory = button.dataset.category;

        document.querySelectorAll(".certificate-filter").forEach((item) => {
            const selected = item.dataset.category === activeCertificateCategory;
            item.classList.toggle("btn-primary", selected);
            item.classList.toggle("btn-outline-primary", !selected);
        });

        renderStudentCertificates();
    });
});

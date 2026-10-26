
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
            typeof user.role === "object"
                ? user.role?.name
                : user.role || ""
        ).toLowerCase();

        const requestedOrganizerId =
            new URLSearchParams(window.location.search).get("organizer_id");

        if (requestedOrganizerId && /^\d+$/.test(requestedOrganizerId)) {
            const organizerResponse = await fetch(
                `${PROFILE_API_URL}/organizer-profiles/${requestedOrganizerId}`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            if (!organizerResponse.ok) throw new Error("Unable to load this organizer profile.");
            const organizer = await organizerResponse.json();
            document.getElementById("profileName").textContent = organizer.organization_name || organizer.name || `Organizer #${requestedOrganizerId}`;
            document.getElementById("profileEmail").textContent = "-";
            document.getElementById("profileRole").textContent = "organizer";
            document.getElementById("organizerProfileSection").classList.remove("d-none");
            document.getElementById("editProfileBtn").classList.add("d-none");
            document.getElementById("organizerProfileForm").classList.add("d-none");
            showOrganizerProfile(organizer);
            await loadOrganizerEvents(requestedOrganizerId, token);
            loading.classList.add("d-none");
            content.classList.remove("d-none");
            return;
        }

        document.getElementById("profileName").textContent =
            user.name || "-";
        document.getElementById("profileEmail").textContent =
            user.email || "-";
        document.getElementById("profileRole").textContent =
            role || "-";

        if (role === "organizer") {
            document.getElementById("organizerProfileSection")
                .classList.remove("d-none");

            await loadOrganizerProfile(token);

            if (user.id != null) {
                await loadOrganizerEvents(user.id, token);
            }
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
        error.textContent =
            err.message || "Unable to load your profile.";
        error.classList.remove("d-none");
    }
}

async function loadOrganizerProfile(token) {
    const response = await fetch(
        `${PROFILE_API_URL}/organizer-profiles/me`,
        {
            headers: { Authorization: `Bearer ${token}` }
        }
    );

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

async function loadOrganizerEvents(organizerId, token) {
    const section = document.getElementById("organizerEventsSection");
    const loading = document.getElementById("organizerEventsLoading");
    const error = document.getElementById("organizerEventsError");
    const empty = document.getElementById("organizerEventsEmpty");

    section.classList.remove("d-none");
    loading.classList.remove("d-none");
    error.classList.add("d-none");
    empty.classList.add("d-none");

    try {
        const response = await fetch(
            `${PROFILE_API_URL}/organizer-profiles/${organizerId}`,
            {
                headers: { Authorization: `Bearer ${token}` }
            }
        );

        if (response.status === 401) {
            throw new Error("Your session has expired. Please log in again.");
        }

        if (!response.ok) {
            throw new Error("Unable to load this organizer's events.");
        }

        const data = await response.json();

        // The organizer profile endpoint should return its events in "events".
        if (!Array.isArray(data.events)) {
            throw new Error(
                "The organizer profile response did not contain an events list."
            );
        }

        renderOrganizerEvents(data.events);
    } catch (err) {
        error.textContent =
            err.message || "Unable to load organizer events.";
        error.classList.remove("d-none");
    } finally {
        loading.classList.add("d-none");
    }
}

function renderOrganizerEvents(events) {
    const empty = document.getElementById("organizerEventsEmpty");

    const groups = {
        upcoming: {
            section: document.getElementById(
                "organizerUpcomingEventsSection"
            ),
            list: document.getElementById(
                "organizerUpcomingEventsList"
            ),
            events: []
        },
        completed: {
            section: document.getElementById(
                "organizerCompletedEventsSection"
            ),
            list: document.getElementById(
                "organizerCompletedEventsList"
            ),
            events: []
        },
        cancelled: {
            section: document.getElementById(
                "organizerCancelledEventsSection"
            ),
            list: document.getElementById(
                "organizerCancelledEventsList"
            ),
            events: []
        }
    };

    Object.values(groups).forEach(({ section, list }) => {
        section.classList.add("d-none");
        list.replaceChildren();
    });

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    events.forEach((event) => {
        const status = String(event.status || "").toLowerCase();

        if (status === "cancelled") {
            groups.cancelled.events.push(event);
            return;
        }

        const eventDate = event.event_date
            ? new Date(`${event.event_date}T00:00:00`)
            : null;

        if (
            status === "completed" ||
            (eventDate && !Number.isNaN(eventDate.getTime()) &&
                eventDate < today)
        ) {
            groups.completed.events.push(event);
        } else {
            groups.upcoming.events.push(event);
        }
    });

    let displayedCount = 0;

    Object.values(groups).forEach((group) => {
        group.events.forEach((event) => {
            group.list.appendChild(createOrganizerEventCard(event));
            displayedCount++;
        });

        if (group.events.length > 0) {
            group.section.classList.remove("d-none");
        }
    });

    empty.textContent = "This organizer has no events to display yet.";
    empty.classList.toggle("d-none", displayedCount > 0);
}

function createOrganizerEventCard(event) {
    const column = document.createElement("div");
    column.className = "col-12 col-md-6";

    const card = document.createElement("article");
    card.className = "card h-100 shadow-sm";

    const body = document.createElement("div");
    body.className = "card-body";

    const title = document.createElement("h4");
    title.className = "h5 card-title";
    title.textContent = event.title || "Untitled event";

    const date = document.createElement("p");
    date.className = "mb-1";
    date.textContent = `Date: ${formatEventDate(event.event_date)}`;

    const time = document.createElement("p");
    time.className = "mb-1";
    time.textContent =
        `Time: ${event.start_time || "Not specified"}` +
        (event.end_time ? ` â€“ ${event.end_time}` : "");

    const mode = document.createElement("p");
    mode.className = "mb-1";
    mode.textContent = `Mode: ${event.mode || "Not specified"}`;

    const venue = document.createElement("p");
    venue.className = "mb-3";
    venue.textContent = `Venue: ${event.venue || "Not specified"}`;

    const status = document.createElement("span");
    status.className = "badge text-bg-secondary mb-3";
    status.textContent = event.status || "Status unavailable";

    const detailsLink = document.createElement("a");
    detailsLink.className = "btn btn-outline-primary btn-sm";
    detailsLink.href =
        `event-details.html?id=${encodeURIComponent(event.id)}`;
    detailsLink.textContent = "View Event Details";

    body.append(title, date, time, mode, venue, status, detailsLink);
    card.appendChild(body);
    column.appendChild(card);

    return column;
}

function formatEventDate(value) {
    if (!value) {
        return "Not specified";
    }

    const date = new Date(`${value}T00:00:00`);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleDateString();
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

    document.getElementById("bio").value =
        organizerProfile.bio || "";

    document.getElementById("contactPhone").value =
        organizerProfile.contact_phone || "";

    document.getElementById("organizerProfileDetails")
        .classList.add("d-none");

    document.getElementById("organizerProfileForm")
        .classList.remove("d-none");

    document.getElementById("profileMessage")
        .classList.add("d-none");
});

document.getElementById("cancelProfileBtn")?.addEventListener("click", () => {
    document.getElementById("organizerProfileForm")
        .classList.add("d-none");

    document.getElementById("organizerProfileDetails")
        .classList.remove("d-none");
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
            organization_name:
                document.getElementById("organizationName").value,
            department: document.getElementById("department").value,
            bio: document.getElementById("bio").value,
            contact_phone:
                document.getElementById("contactPhone").value
        };

        saveButton.disabled = true;
        saveButton.setAttribute("aria-busy", "true");
        saveButton.textContent = "Saving…";

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
                throw new Error(
                    "Your session has expired. Please log in again."
                );
            }

            if (response.status === 403) {
                throw new Error(
                    "Only organizer accounts can update this profile."
                );
            }

            if (!response.ok) {
                const result = await response.json().catch(() => ({}));
                throw new Error(
                    result.detail || "Could not save organizer profile."
                );
            }

            organizerProfile = await response.json();
            showOrganizerProfile(organizerProfile);

            document.getElementById("organizerProfileForm")
                .classList.add("d-none");

            document.getElementById("organizerProfileDetails")
                .classList.remove("d-none");

            showMessage("Organizer profile saved successfully.");
        } catch (err) {
            showMessage(err.message, "danger");
        } finally {
            saveButton.disabled = false;
            saveButton.removeAttribute("aria-busy");
            saveButton.textContent = "Save Profile";
        }
    }
);

async function loadStudentCertificates(token) {
    const message = document.getElementById("certificateMessage");
    const empty = document.getElementById("certificatesEmpty");
    const list = document.getElementById("certificatesList");

    try {
        const response = await fetch(
            `${PROFILE_API_URL}/certificates/me`,
            {
                headers: { Authorization: `Bearer ${token}` }
            }
        );

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error(
                    "Your session has expired. Please log in again."
                );
            }

            if (response.status === 403) {
                throw new Error(
                    "Only student accounts can view these certificates."
                );
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
        title.textContent =
            cert.title || `${cert.event_title} Certificate`;

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
        card.appendChild(body);
        column.appendChild(card);
        list.appendChild(column);
    });
}

document.querySelectorAll(".certificate-filter").forEach((button) => {
    button.addEventListener("click", () => {
        activeCertificateCategory = button.dataset.category;

        document.querySelectorAll(".certificate-filter").forEach((item) => {
            const selected =
                item.dataset.category === activeCertificateCategory;

            item.classList.toggle("btn-primary", selected);
            item.classList.toggle("btn-outline-primary", !selected);
        });

        renderStudentCertificates();
    });
});

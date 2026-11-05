const API_URL = window.EVENTHUB_API_BASE_URL;

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("retryBtn")
        .addEventListener("click", loadOrganizerDashboard);

    document.getElementById("logoutBtn")
        .addEventListener("click", logout);

    loadOrganizerDashboard();
});

function getToken() {
    return sessionStorage.getItem("access_token");
}

function logout() {
    sessionStorage.removeItem("access_token");
    window.location.href = "login.html";
}

async function apiRequest(url, token) {
    const response = await fetch(`${API_URL}${url}`, {
        headers: {
            Authorization: `Bearer ${token}`
        }
    });

    if (response.status === 401) {
        sessionStorage.removeItem("access_token");
        window.location.href = "login.html";
        throw new Error("Your session has expired. Please log in again.");
    }

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));

        throw new Error(
            errorData.detail || `Request failed (${response.status}).`
        );
    }

    return response.json();
}

function showError(message) {
    document.getElementById("dashboardLoading").classList.add("d-none");
    document.getElementById("dashboardContent").classList.add("d-none");

    document.getElementById("dashboardErrorMessage").textContent = message;
    document.getElementById("dashboardError").classList.remove("d-none");
}

async function loadOrganizerDashboard() {
    const loading = document.getElementById("dashboardLoading");
    const error = document.getElementById("dashboardError");
    const content = document.getElementById("dashboardContent");

    loading.classList.remove("d-none");
    error.classList.add("d-none");
    content.classList.add("d-none");

    const token = getToken();

    if (!token) {
        window.location.href = "login.html";
        return;
    }

    try {
        // Step 1: Get the logged-in user.
        const user = await apiRequest("/auth/me", token);

        const role = String(
            typeof user.role === "object"
                ? user.role?.name
                : user.role || ""
        ).toLowerCase();

        if (role !== "organizer") {
            showError("Access denied. This dashboard is only available to organizers.");
            return;
        }

        document.getElementById("organizerName").textContent =
            user.name || "Organizer";

        // Step 2: Load the organizer profile.
        const profile = await apiRequest("/organizer-profiles/me", token);

        document.getElementById("organizationName").textContent =
            profile.organization_name || "Not provided";

        document.getElementById("departmentName").textContent =
            profile.department || "Not provided";

        // Step 3: Load this organizer's events.
        if (user.id == null) {
            throw new Error("Your account ID could not be found.");
        }

        const organizer = await apiRequest(
            `/organizer-profiles/${encodeURIComponent(user.id)}`,
            token
        );

        if (!Array.isArray(organizer.events)) {
            throw new Error("The organizer event list was not returned correctly.");
        }

        renderEvents(organizer.events);
        updateStatistics(organizer.events);

        loading.classList.add("d-none");
        error.classList.add("d-none");
        content.classList.remove("d-none");

    } catch (err) {
        showError(err.message || "Unable to load your organizer dashboard.");
    }
}

function updateStatistics(events) {
    const getStatus = event =>
        String(event.status || "").toLowerCase();

    document.getElementById("totalEvents").textContent = events.length;

    document.getElementById("draftEvents").textContent =
        events.filter(event => getStatus(event) === "draft").length;

    document.getElementById("pendingEvents").textContent =
        events.filter(event =>
            getStatus(event) === "pending_approval"
        ).length;

    document.getElementById("publishedEvents").textContent =
        events.filter(event => getStatus(event) === "published").length;
}

function formatDate(value) {
    if (!value) return "Date not set";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric"
    });
}

function createElement(tag, className, text) {
    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    if (text !== undefined && text !== null) {
        element.textContent = String(text);
    }

    return element;
}

function renderEvents(events) {
    const container = document.getElementById("eventsList");
    const empty = document.getElementById("noEvents");

    container.replaceChildren();

    if (events.length === 0) {
        empty.classList.remove("d-none");
        return;
    }

    empty.classList.add("d-none");

    events.forEach(event => {
        const column = createElement("div", "col-12 col-md-6 col-xl-4");
        const card = createElement("div", "card h-100 shadow-sm border-0");
        const body = createElement("div", "card-body d-flex flex-column");

        const title = createElement(
            "h3",
            "h5 fw-bold mb-2",
            event.title || "Untitled Event"
        );

        const status = String(event.status || "unknown").toLowerCase();

        const statusClass = {
            draft: "bg-secondary",
            pending_approval: "bg-warning text-dark",
            published: "bg-success",
            cancelled: "bg-danger",
            completed: "bg-info text-dark"
        }[status] || "bg-secondary";

        const statusBadge = createElement(
            "span",
            `badge ${statusClass} align-self-start mb-3`,
            status.replaceAll("_", " ")
        );

        const date = createElement(
            "p",
            "text-muted small mb-2",
            `Date: ${formatDate(event.event_date)}`
        );

        const category = createElement(
            "p",
            "text-muted small mb-2",
            `Category: ${event.category || "Not specified"}`
        );

        const venue = createElement(
            "p",
            "text-muted small mb-3",
            `Venue: ${event.venue || event.mode || "Not specified"}`
        );

        const actions = createElement(
            "div",
            "d-flex flex-wrap gap-2 mt-auto"
        );

        const detailsLink = createElement(
            "a",
            "btn btn-outline-primary btn-sm",
            "View Details"
        );
        detailsLink.href = `event-details.html?id=${encodeURIComponent(event.id)}`;

        const editLink = createElement(
            "a",
            "btn btn-outline-secondary btn-sm",
            "Edit"
        );
        editLink.href = `create-event.html?edit=${encodeURIComponent(event.id)}`;

        const participantsLink = createElement(
            "a",
            "btn btn-outline-success btn-sm",
            "Participants"
        );
        participantsLink.href =
            `participants.html?event_id=${encodeURIComponent(event.id)}`;

        actions.append(detailsLink, editLink, participantsLink);

        body.append(title, statusBadge, date, category, venue, actions);
        card.append(body);
        column.append(card);
        container.append(column);
    });
}
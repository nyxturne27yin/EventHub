
"use strict";

const DASHBOARD_API_URL = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", loadStudentDashboard);

async function loadStudentDashboard() {
    const token = sessionStorage.getItem("access_token");
    const loading = document.getElementById("dashboardLoading");
    const errorBox = document.getElementById("dashboardError");
    const retryButton = document.getElementById("dashboardRetry");
    const content = document.getElementById("dashboardContent");

    if (!token) {
        window.location.href = "login.html";
        return;
    }

    loading.classList.remove("d-none");
    errorBox.classList.add("d-none");
    retryButton.classList.add("d-none");
    content.classList.add("d-none");

    try {
        const headers = { Authorization: `Bearer ${token}` };

        const userResponse = await fetch(`${DASHBOARD_API_URL}/auth/me`, {
            headers
        });

        if (userResponse.status === 401 || userResponse.status === 403) {
            sessionStorage.removeItem("access_token");
            window.location.href = "login.html";
            return;
        }

        if (!userResponse.ok) {
            throw new Error("Could not verify your account. Please try again.");
        }

        const user = await userResponse.json();
        const role = typeof user.role === "object"
            ? user.role?.name
            : user.role;

        if (String(role || "").toLowerCase() !== "student") {
            errorBox.textContent =
                "This dashboard is available to student accounts only.";
            errorBox.classList.remove("d-none");
            return;
        }

        const registrationsResponse = await fetch(
            `${DASHBOARD_API_URL}/registrations/me`,
            { headers }
        );

        if (!registrationsResponse.ok) {
            if (
                registrationsResponse.status === 401 ||
                registrationsResponse.status === 403
            ) {
                sessionStorage.removeItem("access_token");
                window.location.href = "login.html";
                return;
            }

            throw new Error("Could not load your registrations.");
        }

        const registrations = await registrationsResponse.json();

        if (!Array.isArray(registrations)) {
            throw new Error(
                "The registrations response was not in the expected format."
            );
        }

        document.getElementById("dashboardWelcome").textContent =
            user.name ? `Welcome, ${user.name}!` : "Welcome back!";

        renderRegistrations(registrations);
        content.classList.remove("d-none");

        await loadDashboardCertificates(headers);
    } catch (error) {
        errorBox.textContent =
            error.message ||
            "Something went wrong while loading your dashboard.";

        errorBox.classList.remove("d-none");
        retryButton.classList.remove("d-none");
    } finally {
        loading.classList.add("d-none");
    }
}

function renderRegistrations(registrations) {
    const now = new Date();

    const isPast = (registration) => {
        const date = registration.event_date;
        const endTime = registration.end_time || "23:59:59";

        if (!date) return false;

        const eventEnd = new Date(`${date}T${endTime}`);

        return !Number.isNaN(eventEnd.getTime()) && eventEnd < now;
    };

    const isCompleted = (registration) => {
        const registrationStatus = String(
            registration.registration_status || ""
        ).toLowerCase();

        const eventStatus = String(registration.status || "").toLowerCase();

        return registrationStatus === "registered" &&
            (
                eventStatus === "completed" ||
                (eventStatus !== "cancelled" && isPast(registration))
            );
    };

    // Treat registration and event statuses case-insensitively.
    const upcoming = registrations.filter((registration) =>
        String(registration.registration_status || "").toLowerCase() ===
            "registered" &&
        String(registration.status || "").toLowerCase() === "published" &&
        !isCompleted(registration)
    );

    const completed = registrations.filter(isCompleted);

    document.getElementById("totalRegistrations").textContent =
        registrations.length;

    document.getElementById("upcomingCount").textContent =
        upcoming.length;

    document.getElementById("completedCount").textContent =
        completed.length;

    const upcomingContainer = document.getElementById("upcomingEvents");
    upcomingContainer.replaceChildren();

    upcoming.forEach((registration) => {
        upcomingContainer.appendChild(createRegistrationCard(registration));
    });

    document.getElementById("upcomingEmpty").classList.toggle(
        "d-none",
        upcoming.length > 0
    );

    // EV-77: Show only completed registrations in event history.
    const historyContainer = document.getElementById("registrationHistory");
    historyContainer.replaceChildren();

    completed.forEach((registration) => {
        historyContainer.appendChild(createRegistrationCard(registration));
    });

    document.getElementById("historyEmpty").classList.toggle(
        "d-none",
        completed.length > 0
    );
}

function createRegistrationCard(registration) {
    const column = document.createElement("div");
    column.className = "col-12 col-md-6 col-xl-4";

    const card = document.createElement("article");
    card.className = "card h-100 shadow-sm";

    const body = document.createElement("div");
    body.className = "card-body d-flex flex-column";

    const title = document.createElement("h3");
    title.className = "h5 card-title";
    title.textContent = registration.title || "Untitled event";

    const category = document.createElement("p");
    category.className = "text-secondary mb-2";
    category.textContent = registration.category || "University event";

    const date = document.createElement("p");
    date.className = "mb-1";
    date.textContent = `Date: ${formatDate(registration.event_date)}`;

    const time = document.createElement("p");
    time.className = "mb-1";
    time.textContent = `Time: ${formatTime(registration.start_time)}${
        registration.end_time
            ? ` - ${formatTime(registration.end_time)}`
            : ""
    }`;

    const location = document.createElement("p");
    location.className = "mb-2";

    const mode = String(registration.mode || "").trim().toLowerCase();
    const isOnline = mode === "online";
    const meetingLink = String(registration.meeting_link || "").trim();

    if (isOnline) {
        location.textContent = "Online event";

        if (/^https?:\/\//i.test(meetingLink)) {
            const link = document.createElement("a");
            link.href = meetingLink;
            link.textContent = "Join meeting";
            link.target = "_blank";
            link.rel = "noopener noreferrer";

            location.append(
                document.createTextNode(" - "),
                link
            );
        } else {
            location.append(
                document.createTextNode(" - Meeting link not available")
            );
        }
    } else {
        location.textContent =
            `Offline event - Venue: ${registration.venue || "Venue not specified"}`;
    }

    const status = document.createElement("span");
    status.className = "badge align-self-start mb-3";

    const registrationStatus =
        registration.registration_status || "Unknown";

    status.textContent = registrationStatus;

    status.classList.add(
        registrationStatus === "Registered"
            ? "text-bg-success"
            : registrationStatus === "Cancelled"
                ? "text-bg-danger"
                : "text-bg-secondary"
    );

    const eventStatus = document.createElement("p");
    eventStatus.className = "small text-secondary mb-3";
    eventStatus.textContent =
        `Event status: ${registration.status || "Unknown"}`;

    const detailsLink = document.createElement("a");
    detailsLink.className =
        "btn btn-outline-primary btn-sm mt-auto";

    detailsLink.href =
        `event-details.html?id=${encodeURIComponent(registration.event_id)}`;

    detailsLink.textContent = "View event details";

    body.append(
        title,
        category,
        date,
        time,
        location,
        status,
        eventStatus,
        detailsLink
    );

    card.appendChild(body);
    column.appendChild(card);

    return column;
}

async function loadDashboardCertificates(headers) {
    const container = document.getElementById("dashboardCertificates");
    const emptyMessage = document.getElementById("certificatesEmpty");
    const errorMessage = document.getElementById("certificateError");

    container.replaceChildren();
    errorMessage.classList.add("d-none");

    try {
        const response = await fetch(
            `${DASHBOARD_API_URL}/certificates/me`,
            { headers }
        );

        if (!response.ok) {
            throw new Error(
                "Certificate information is currently unavailable."
            );
        }

        const certificates = await response.json();

        if (!Array.isArray(certificates)) {
            throw new Error(
                "Certificate data was not in the expected format."
            );
        }

        document.getElementById("certificateCount").textContent =
            certificates.length;

        emptyMessage.classList.toggle(
            "d-none",
            certificates.length > 0
        );

        certificates.forEach((certificate) => {
            const column = document.createElement("div");
            column.className = "col-12 col-md-6 col-xl-4";

            const card = document.createElement("div");
            card.className = "card h-100";

            const body = document.createElement("div");
            body.className = "card-body";

            const title = document.createElement("h3");
            title.className = "h6 card-title";
            title.textContent =
                certificate.title ||
                certificate.event_title ||
                "Event certificate";

            const category = document.createElement("p");
            category.className = "text-secondary mb-2";
            category.textContent = certificate.category || "Certificate";

            const issued = document.createElement("p");
            issued.className = "small mb-0";
            issued.textContent =
                `Issued: ${formatDate(certificate.issued_at)}`;

            body.append(title, category, issued);

            if (certificate.verification_path) {
                const link = document.createElement("a");
                link.className =
                    "btn btn-sm btn-outline-primary mt-3";

                link.href =
                    `${DASHBOARD_API_URL}${certificate.verification_path}`;

                link.target = "_blank";
                link.rel = "noopener noreferrer";
                link.textContent = "Verify certificate";

                body.appendChild(link);
            }

            card.appendChild(body);
            column.appendChild(card);
            container.appendChild(column);
        });
    } catch (error) {
        document.getElementById("certificateCount").textContent = "—";
        emptyMessage.classList.add("d-none");

        errorMessage.textContent =
            error.message || "Could not load certificates.";

        errorMessage.classList.remove("d-none");
    }
}

function formatDate(value) {
    if (!value) return "Not specified";

    const dateValue = String(value);
    const datePart = dateValue.includes("T")
        ? dateValue.split("T")[0]
        : dateValue;

    const date = new Date(`${datePart}T00:00:00`);

    if (Number.isNaN(date.getTime())) return dateValue;

    return date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric"
    });
}

function formatTime(value) {
    if (!value) return "Not specified";

    const match = String(value).match(/^(\d{2}):(\d{2})/);
    if (!match) return String(value);

    const hours = Number(match[1]);
    const minutes = match[2];
    const suffix = hours >= 12 ? "PM" : "AM";
    const displayHours = hours % 12 || 12;

    return `${displayHours}:${minutes} ${suffix}`;
}

document.getElementById("dashboardRetry")?.addEventListener(
    "click",
    loadStudentDashboard
);

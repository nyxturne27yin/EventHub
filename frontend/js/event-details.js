const EVENTS_API_URL = "http://127.0.0.1:8000/events/";

const params = new URLSearchParams(window.location.search);
const rawId = params.get("id");
const eventId = rawId && /^[1-9]\d*$/.test(rawId) ? rawId : null;

const loading = document.getElementById("detailsLoading");
const errorBox = document.getElementById("detailsError");
const retryButton = document.getElementById("retryDetails");
const details = document.getElementById("eventDetails");

function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}

function formatDate(value) {
    if (!value) return "Not specified";

    const parsed = new Date(value + "T00:00:00");

    return Number.isNaN(parsed.getTime())
        ? value
        : new Intl.DateTimeFormat(undefined, {
              dateStyle: "long"
          }).format(parsed);
}

function formatTime(value) {
    if (!value) return "Not specified";

    const parts = value.split(":");

    if (parts.length < 2) return value;

    const parsed = new Date();
    parsed.setHours(Number(parts[0]), Number(parts[1]), 0, 0);

    return Number.isNaN(parsed.getTime())
        ? value
        : new Intl.DateTimeFormat(undefined, {
              hour: "numeric",
              minute: "2-digit"
          }).format(parsed);
}

function getAvailability(event) {
    if ((event.status || "").toLowerCase() === "cancelled") {
        return "Cancelled - registration is unavailable.";
    }
    if (event.registration_deadline && new Date(event.registration_deadline) <= new Date()) {
        return "Registration closed - the deadline has passed.";
    }
    if (Number(event.capacity) > 0 && Number(event.registered_count || 0) >= Number(event.capacity)) {
        return "Full - participant capacity has been reached.";
    }
    return "Registration open.";
}

async function loadDetails() {
    if (!loading || !errorBox || !retryButton || !details) {
        console.error(
            "Event details page is missing one or more required HTML elements."
        );
        return;
    }

    loading.classList.remove("d-none");
    errorBox.classList.add("d-none");
    retryButton.classList.add("d-none");
    details.classList.add("d-none");

    if (!eventId) {
        loading.classList.add("d-none");
        errorBox.textContent =
            "The event link is invalid. Return to the event listing and select an event.";
        errorBox.classList.remove("d-none");
        return;
    }

    try {
        const response = await fetch(
            EVENTS_API_URL + encodeURIComponent(eventId),
            {
                headers: {
                    Accept: "application/json"
                }
            }
        );

        const data = await response.json().catch(() => null);

        if (!response.ok) {
            if (response.status === 404) {
                throw new Error(
                    "This event does not exist or is not publicly available."
                );
            }

            throw new Error(
                "Unable to load event details. Please try again."
            );
        }

        if (!data || typeof data !== "object" || !data.id) {
            throw new Error(
                "The server returned an unexpected event response."
            );
        }

        setText("detailTitle", data.title || "Untitled Event");
        setText("detailCategory", data.category || "General");
        setText("detailMode", data.mode || "Mode not specified");

        setText(
            "detailStatus",
            (data.status || "unknown").replace(/^./, c => c.toUpperCase())
        );

        setText(
            "detailDescription",
            data.description || "No description available."
        );

        // Organizer club / organization and department
        setText(
            "detailOrganization",
            data.organization_name || "Not specified"
        );
        setText(
            "detailDepartment",
            data.department || "Not specified"
        );

        setText("detailDate", formatDate(data.event_date));

        setText(
            "detailTime",
            formatTime(data.start_time) + " – " + formatTime(data.end_time)
        );

        setText(
            "detailLocation",
            (data.mode || "").toLowerCase() === "online"
                ? "Online event. Meeting details are not exposed on the public discovery page."
                : data.venue || "Venue not specified"
        );

        setText(
            "detailCapacity",
            data.capacity == null ? "Not specified" : String(data.capacity)
        );

        setText(
            "detailDeadline",
            data.registration_deadline
                ? new Date(data.registration_deadline).toLocaleString()
                : "No deadline specified"
        );

        setText("detailAvailability", getAvailability(data));

        const status = (data.status || "").toLowerCase();
        const badge = document.getElementById("detailStatus");

        if (badge) {
            badge.className =
                "badge " +
                (status === "cancelled"
                    ? "text-bg-danger"
                    : "text-bg-success");
        }

        loading.classList.add("d-none");
        details.classList.remove("d-none");
    } catch (error) {
        loading.classList.add("d-none");

        errorBox.textContent =
            error.message || "Cannot connect to EventHub API.";

        errorBox.classList.remove("d-none");
        retryButton.classList.remove("d-none");

        console.error("Failed to load event details:", error);
    }
}

if (retryButton) {
    retryButton.addEventListener("click", loadDetails);
}

loadDetails();

// Event registration
const registerButton = document.getElementById("registerForEvent");
const registrationMessage = document.getElementById("registrationMessage");

if (registerButton) {
    registerButton.addEventListener("click", async function () {
        if (!eventId) return;

        const token = sessionStorage.getItem("access_token");

        if (!token) {
            if (registrationMessage) {
                registrationMessage.textContent = "Please log in before registering for an event.";
                registrationMessage.className = "alert alert-warning mt-4";
            }
            return;
        }

        registerButton.disabled = true;
        registerButton.textContent = "Registering...";

        try {
            const response = await fetch(
                EVENTS_API_URL + encodeURIComponent(eventId) + "/registrations",
                {
                    method: "POST",
                    headers: {
                        "Authorization": "Bearer " + token,
                        "Accept": "application/json"
                    }
                }
            );

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(
                    typeof data.detail === "string"
                        ? data.detail
                        : "Registration failed. Please try again."
                );
            }

            if (registrationMessage) {
                registrationMessage.textContent = "Registration successful! Your registration ID is " + data.id + ".";
                registrationMessage.className = "alert alert-success mt-4";
            }

            registerButton.textContent = "Registered";
        } catch (error) {
            if (registrationMessage) {
                registrationMessage.textContent = error.message || "Could not complete registration.";
                registrationMessage.className = "alert alert-danger mt-4";
            }
            registerButton.disabled = false;
            registerButton.textContent = "Register for Event";
        }
    });
}

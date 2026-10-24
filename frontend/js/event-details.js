
const EVENTS_API_URL = "http://127.0.0.1:8000/events/";

const params = new URLSearchParams(window.location.search);
const rawId = params.get("id");
const eventId = rawId && /^[1-9]\d*$/.test(rawId) ? rawId : null;

const loading = document.getElementById("detailsLoading");
const errorBox = document.getElementById("detailsError");
const retryButton = document.getElementById("retryDetails");
const details = document.getElementById("eventDetails");
const registerButton = document.getElementById("registerForEvent");
const registrationMessage = document.getElementById("registrationMessage");

let currentEventData = null;

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
    const status = (event.status || "").trim().toLowerCase();

    if (status === "cancelled") {
        return "Cancelled - registration is unavailable.";
    }

    if (status === "completed") {
        return "Completed - registration is unavailable.";
    }

    if (
        event.registration_deadline &&
        new Date(event.registration_deadline) <= new Date()
    ) {
        return "Registration closed - the deadline has passed.";
    }

    if (
        Number(event.capacity) > 0 &&
        Number(event.registered_count || 0) >= Number(event.capacity)
    ) {
        return "Full - participant capacity has been reached.";
    }

    return "Registration open.";
}

function updateRegistrationButton(event) {
    if (!registerButton) return;

    if (!event) {
        registerButton.disabled = true;
        return;
    }

    const status = (event.status || "").trim().toLowerCase();

    const isCancelled = status === "cancelled";
    const isCompleted = status === "completed";

    const deadlinePassed =
        Boolean(event.registration_deadline) &&
        !Number.isNaN(new Date(event.registration_deadline).getTime()) &&
        new Date(event.registration_deadline) <= new Date();

    const isFull =
        Number(event.capacity) > 0 &&
        Number(event.registered_count || 0) >= Number(event.capacity);

    if (isCancelled) {
        registerButton.disabled = true;
        registerButton.textContent = "Event Cancelled";
    } else if (isCompleted) {
        registerButton.disabled = true;
        registerButton.textContent = "Event Completed";
    } else if (deadlinePassed) {
        registerButton.disabled = true;
        registerButton.textContent = "Registration Closed";
    } else if (isFull) {
        registerButton.disabled = true;
        registerButton.textContent = "Event Full";
    } else {
        registerButton.disabled = false;
        registerButton.textContent = "Register for Event";
    }
}

async function loadMyRegistrationStatus() {
    if (!registrationMessage) return;

    const token = sessionStorage.getItem("access_token");

    if (!token || !eventId) return;

    try {
        const response = await fetch("http://127.0.0.1:8000/registrations/me", {
            headers: {
                Authorization: "Bearer " + token,
                Accept: "application/json"
            }
        });

        if (!response.ok) return;

        const registrations = await response.json();
        const registration = registrations.find(
            item => String(item.event_id) === String(eventId)
        );

        if (!registration) return;

        const status = registration.registration_status;

        registrationMessage.textContent = "Your registration status: " + status;
        registrationMessage.className =
            "alert mt-4 " +
            (status === "Registered" ? "alert-success" : "alert-danger");
    } catch (error) {
        console.error("Could not load registration status:", error);
    }
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

    if (registerButton) {
        registerButton.disabled = true;
    }

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

        currentEventData = data;

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
            `${formatTime(data.start_time)} - ${formatTime(data.end_time)}`
        );

        // Display the venue for offline events and a safe, clickable
        // meeting link for online events.
        const locationElement = document.getElementById("detailLocation");
        const isOnline = (data.mode || "").trim().toLowerCase() === "online";

        if (locationElement) {
            locationElement.replaceChildren();

            if (isOnline) {
                locationElement.append(document.createTextNode("Online event"));

                const meetingLink = (data.meeting_link || "").trim();

                if (/^https?:\/\//i.test(meetingLink)) {
                    const link = document.createElement("a");
                    link.href = meetingLink;
                    link.textContent = "Join meeting";
                    link.target = "_blank";
                    link.rel = "noopener noreferrer";

                    locationElement.append(
                        document.createTextNode(" — "),
                        link
                    );
                } else {
                    locationElement.append(
                        document.createTextNode(" — Meeting link not available")
                    );
                }
            } else {
                locationElement.textContent =
                    `Offline event — Venue: ${data.venue || "Venue not specified"}`;
            }
        }

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

        const status = (data.status || "").trim().toLowerCase();
        const badge = document.getElementById("detailStatus");

        if (badge) {
            let badgeStyle = "text-bg-success";

            if (status === "cancelled") {
                badgeStyle = "text-bg-danger";
            } else if (status === "completed") {
                badgeStyle = "text-bg-secondary";
            }

            badge.className = "badge " + badgeStyle;
        }

        // Disable registration when the event cannot accept registrations.
        updateRegistrationButton(data);
        await loadMyRegistrationStatus();

        loading.classList.add("d-none");
        details.classList.remove("d-none");
    } catch (error) {
        loading.classList.add("d-none");

        errorBox.textContent =
            error.message || "Cannot connect to EventHub API.";

        errorBox.classList.remove("d-none");
        retryButton.classList.remove("d-none");

        if (registerButton) {
            registerButton.disabled = true;
        }

        console.error("Failed to load event details:", error);
    }
}

if (retryButton) {
    retryButton.addEventListener("click", loadDetails);
}

loadDetails();

// Event registration
if (registerButton) {
    registerButton.addEventListener("click", async function () {
        if (!eventId || registerButton.disabled) return;

        const status = (currentEventData?.status || "").trim().toLowerCase();

        if (status === "cancelled") {
            if (registrationMessage) {
                registrationMessage.textContent =
                    "This event has been cancelled. Registration is unavailable.";
                registrationMessage.className = "alert alert-danger mt-4";
            }

            updateRegistrationButton(currentEventData);
            return;
        }

        if (status === "completed") {
            if (registrationMessage) {
                registrationMessage.textContent =
                    "This event has been completed. Registration is unavailable.";
                registrationMessage.className = "alert alert-danger mt-4";
            }

            updateRegistrationButton(currentEventData);
            return;
        }

        const token = sessionStorage.getItem("access_token");

        if (!token) {
            if (registrationMessage) {
                registrationMessage.textContent =
                    "Please log in before registering for an event.";
                registrationMessage.className = "alert alert-warning mt-4";
            }
            return;
        }

        registerButton.disabled = true;
        registerButton.textContent = "Registering...";

        try {
            const response = await fetch(
                EVENTS_API_URL +
                    encodeURIComponent(eventId) +
                    "/registrations",
                {
                    method: "POST",
                    headers: {
                        Authorization: "Bearer " + token,
                        Accept: "application/json"
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

            registerButton.disabled = true;
            registerButton.textContent = "Registered";

            if (registrationMessage) {
                const status = data.status || "Registered";
                registrationMessage.textContent =
                    "Your registration status: " + status;
                registrationMessage.className = "alert mt-4 alert-success";
            }

            await loadMyRegistrationStatus();
        } catch (error) {
            if (registrationMessage) {
                registrationMessage.textContent =
                    error.message || "Could not complete registration.";
                registrationMessage.className = "alert alert-danger mt-4";
            }

            // Restore the correct state instead of always enabling the button.
            updateRegistrationButton(currentEventData);
        }
    });
}

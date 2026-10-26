
const API_BASE_URL = "http://127.0.0.1:8000";

const form = document.getElementById("createEventForm");
const messageBox = document.getElementById("pageMessage");
const modeInput = document.getElementById("mode");
const venueInput = document.getElementById("venue");
const meetingLinkInput = document.getElementById("meeting_link");
const submitButton = document.getElementById("submitButton");
const postCreateActions = document.getElementById("postCreateActions");

function showMessage(message, type = "danger") {
    messageBox.textContent = message;
    messageBox.className = `alert alert-${type}`;
}

function updateModeFields() {
    const isOnline = modeInput.value === "Online";

    document.getElementById("venueGroup").classList.toggle("d-none", isOnline);
    document.getElementById("meetingLinkGroup").classList.toggle("d-none", !isOnline);

    venueInput.required = !isOnline;
    meetingLinkInput.required = isOnline;
}

async function checkOrganizerAccess() {
    const token = sessionStorage.getItem("access_token");

    if (!token) {
        showMessage("Please log in before creating an event.");
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });

        if (!response.ok) {
            sessionStorage.removeItem("access_token");
            showMessage("Session expired. Please log in again.");
            return;
        }

        const user = await response.json();
        const role = typeof user.role === "string"
            ? user.role
            : user.role?.name;

        if (String(role || "").toLowerCase() !== "organizer") {
            showMessage("Access denied. Only organizers can create events.");
            return;
        }

        messageBox.classList.add("d-none");
        form.classList.remove("d-none");
        updateModeFields();

    } catch (error) {
        showMessage("Cannot connect to the backend. Please try again.");
    }
}

modeInput.addEventListener("change", updateModeFields);

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!form.reportValidity()) return;

    const token = sessionStorage.getItem("access_token");

    if (!token) {
        showMessage("Please log in again.");
        return;
    }

    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());

    payload.capacity = Number(payload.capacity);

    if (!Number.isInteger(payload.capacity) || payload.capacity <= 0) {
        showMessage("Capacity must be a positive whole number.");
        return;
    }

    if (payload.end_time <= payload.start_time) {
        showMessage("End time must be after start time.");
        return;
    }

    if (payload.mode === "Offline") {
        payload.meeting_link = null;
    } else {
        payload.venue = null;
    }

    submitButton.disabled = true;
    submitButton.setAttribute("aria-busy", "true");
    submitButton.textContent = "Creating…";

    try {
        const response = await fetch(`${API_BASE_URL}/events/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json().catch(() => ({}));

        if (!response.ok) {
            const detail = result.detail;
            const errorMessage = Array.isArray(detail)
                ? detail.map(item => item.msg).join(", ")
                : typeof detail === "string"
                    ? detail
                    : "Could not create the event.";

            throw new Error(errorMessage);
        }

        const createdEvent = result.event;
        showMessage("Event created successfully as a draft.", "success");
        postCreateActions.replaceChildren();
        postCreateActions.classList.remove("d-none");

        if (createdEvent && createdEvent.id) {
            const publishButton = document.createElement("button");
            publishButton.type = "button";
            publishButton.className = "btn btn-success";
            publishButton.textContent = "Submit for approval";
            publishButton.addEventListener("click", async () => {
                publishButton.disabled = true;
                publishButton.textContent = "Publishing...";
                try {
                    const publishResponse = await fetch(
                        `${API_BASE_URL}/events/${encodeURIComponent(createdEvent.id)}/publish`,
                        { method: "POST", headers: { Authorization: `Bearer ${token}`, Accept: "application/json" } }
                    );
                    const publishResult = await publishResponse.json().catch(() => null);
                    if (!publishResponse.ok) {
                        const detail = publishResult?.detail;
                        throw new Error(Array.isArray(detail)
                            ? detail.map(item => item.msg).join(", ")
                            : (detail || "Could not publish the event."));
                    }
                    showMessage("Event submitted for approval. It will appear in Event Discovery after an administrator approves it.", "success");
                    publishButton.textContent = "Submitted for approval";
                    publishButton.classList.remove("btn-success");
                    publishButton.classList.add("btn-outline-success");
                    publishButton.disabled = true;
                } catch (publishError) {
                    showMessage(publishError.message || "Could not publish the event.");
                    publishButton.disabled = false;
                    publishButton.textContent = "Retry publishing";
                }
            });
            postCreateActions.append(publishButton);
            const dashboardLink = document.createElement("a");
            dashboardLink.className = "btn btn-outline-primary ms-2 mt-2 mt-sm-0";
            dashboardLink.href = "profile.html";
            dashboardLink.textContent = "View profile";
            postCreateActions.append(dashboardLink);
        }
        form.reset();
        updateModeFields();

    } catch (error) {
        showMessage(error.message || "Could not connect to the server.");
    } finally {
        submitButton.disabled = false;
        submitButton.removeAttribute("aria-busy");
        submitButton.textContent = "Create Event";
    }
});

checkOrganizerAccess();

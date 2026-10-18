const EVENTS_API_URL = "http://127.0.0.1:8000/events/";
const params = new URLSearchParams(window.location.search);
const rawId = params.get("id");
const eventId = rawId && /^[1-9]\d*$/.test(rawId) ? rawId : null;

const loading = document.getElementById("detailsLoading");
const errorBox = document.getElementById("detailsError");
const retryButton = document.getElementById("retryDetails");
const details = document.getElementById("eventDetails");

function setText(id, value) {
    document.getElementById(id).textContent = value;
}

function formatDate(value) {
    if (!value) return "Not specified";
    const parsed = new Date(`${value}T00:00:00`);
    return Number.isNaN(parsed.getTime())
        ? value
        : new Intl.DateTimeFormat(undefined, { dateStyle: "long" }).format(parsed);
}

function formatTime(value) {
    if (!value) return "Not specified";
    const parts = value.split(":");
    if (parts.length < 2) return value;
    const parsed = new Date();
    parsed.setHours(Number(parts[0]), Number(parts[1]), 0, 0);
    return Number.isNaN(parsed.getTime())
        ? value
        : new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(parsed);
}

function getAvailability(event) {
    if ((event.status || "").toLowerCase() === "cancelled") return "Cancelled — registration is unavailable.";
    if (event.registration_deadline && new Date(event.registration_deadline) < new Date()) {
        return "Registration closed — the deadline has passed.";
    }
    // The current API does not expose active registration counts, so capacity
    // alone cannot prove that places remain or that the event is full.
    return "Unable to confirm. Active registration counts are not currently available.";
}

async function loadDetails() {
    loading.classList.remove("d-none");
    errorBox.classList.add("d-none");
    retryButton.classList.add("d-none");
    details.classList.add("d-none");

    if (!eventId) {
        loading.classList.add("d-none");
        errorBox.textContent = "The event link is invalid. Return to the event listing and select an event.";
        errorBox.classList.remove("d-none");
        return;
    }

    try {
        const response = await fetch(`${EVENTS_API_URL}${encodeURIComponent(eventId)}`, {
            headers: { "Accept": "application/json" }
        });
        const data = await response.json().catch(() => null);
        if (!response.ok) {
            if (response.status === 404) throw new Error("This event does not exist or is not publicly available.");
            throw new Error("Unable to load event details. Please try again.");
        }
        if (!data || typeof data !== "object" || !data.id) {
            throw new Error("The server returned an unexpected event response.");
        }

        setText("detailTitle", data.title || "Untitled Event");
        setText("detailCategory", data.category || "General");
        setText("detailMode", data.mode || "Mode not specified");
        setText("detailStatus", (data.status || "unknown").replace(/^./, c => c.toUpperCase()));
        setText("detailDescription", data.description || "No description available.");
        setText("detailDate", formatDate(data.event_date));
        setText("detailTime", `${formatTime(data.start_time)} – ${formatTime(data.end_time)}`);
        setText("detailLocation", (data.mode || "").toLowerCase() === "online"
            ? "Online event. Meeting details are not exposed on the public discovery page."
            : (data.venue || "Venue not specified"));
        setText("detailCapacity", data.capacity == null ? "Not specified" : String(data.capacity));
        setText("detailDeadline", data.registration_deadline
            ? new Date(data.registration_deadline).toLocaleString()
            : "No deadline specified");
        setText("detailAvailability", getAvailability(data));

        const status = (data.status || "").toLowerCase();
        const badge = document.getElementById("detailStatus");
        badge.className = `badge ${status === "cancelled" ? "text-bg-danger" : "text-bg-success"}`;
        loading.classList.add("d-none");
        details.classList.remove("d-none");
    } catch (error) {
        loading.classList.add("d-none");
        errorBox.textContent = error.message || "Cannot connect to EventHub API.";
        errorBox.classList.remove("d-none");
        retryButton.classList.remove("d-none");
    }
}

retryButton.addEventListener("click", loadDetails);
loadDetails();

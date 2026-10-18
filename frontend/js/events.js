const EVENTS_API_URL = "http://127.0.0.1:8000/events/";

const searchForm = document.getElementById("eventSearchForm");
const searchInput = document.getElementById("eventSearchInput");
const clearButton = document.getElementById("clearEventSearch");
const retryButton = document.getElementById("retryEventSearch");
const loadingMessage = document.getElementById("eventSearchLoading");
const errorMessage = document.getElementById("eventSearchError");
const emptyMessage = document.getElementById("eventSearchEmpty");
const resultsContainer = document.getElementById("eventSearchResults");

function hideSearchStates() {
    loadingMessage.classList.add("d-none");
    errorMessage.classList.add("d-none");
    retryButton.classList.add("d-none");
    emptyMessage.classList.add("d-none");
    resultsContainer.replaceChildren();
}

function formatDate(value) {
    if (!value) return "Date not specified";
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime())
        ? value
        : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

function formatTime(value) {
    if (!value) return "Time not specified";
    const parts = value.split(":");
    if (parts.length < 2) return value;
    const date = new Date();
    date.setHours(Number(parts[0]), Number(parts[1]), 0, 0);
    return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
}

function getAvailability(event) {
    if ((event.status || "").toLowerCase() === "cancelled") {
        return { label: "Cancelled", style: "text-bg-danger" };
    }
    if (event.registration_deadline && new Date(event.registration_deadline) < new Date()) {
        return { label: "Registration closed", style: "text-bg-secondary" };
    }
    return { label: "Availability unconfirmed", style: "text-bg-warning" };
}

function showEvent(event) {
    const column = document.createElement("div");
    column.className = "col-12 col-md-6 col-xl-4";

    const card = document.createElement("article");
    card.className = "card event-card h-100 shadow-sm";

    const body = document.createElement("div");
    body.className = "card-body d-flex flex-column";

    const badges = document.createElement("div");
    badges.className = "d-flex flex-wrap gap-2 mb-3";
    const category = document.createElement("span");
    category.className = "badge text-bg-secondary";
    category.textContent = event.category || "General";
    const mode = document.createElement("span");
    const isOnline = (event.mode || "").toLowerCase() === "online";
    mode.className = `badge ${isOnline ? "text-bg-info" : "text-bg-primary"}`;
    mode.textContent = isOnline ? "Online" : (event.mode || "Mode not specified");
    const availability = getAvailability(event);
    const availabilityBadge = document.createElement("span");
    availabilityBadge.className = `badge ${availability.style}`;
    availabilityBadge.textContent = availability.label;
    badges.append(category, mode, availabilityBadge);

    const title = document.createElement("h3");
    title.className = "h5 card-title event-card-title";
    title.textContent = event.title || "Untitled Event";

    const description = document.createElement("p");
    description.className = "card-text event-card-description";
    description.textContent = event.description || "No description available.";

    const dateAndTime = document.createElement("p");
    dateAndTime.className = "small mb-2";
    dateAndTime.textContent = `${formatDate(event.event_date)} · ${formatTime(event.start_time)}–${formatTime(event.end_time)}`;

    const location = document.createElement("p");
    location.className = "small text-muted";
    location.textContent = isOnline
        ? "Online event · meeting details provided through the event workflow"
        : `Venue: ${event.venue || "Not specified"}`;

    const capacity = document.createElement("p");
    capacity.className = "small text-muted";
    capacity.textContent = event.capacity == null
        ? "Capacity not specified"
        : `Maximum capacity: ${event.capacity}`;

    const deadline = document.createElement("p");
    deadline.className = "small text-muted";
    deadline.textContent = event.registration_deadline
        ? `Registration deadline: ${new Date(event.registration_deadline).toLocaleString()}`
        : "No registration deadline specified";

    const action = document.createElement("a");
    action.className = "btn btn-outline-primary mt-auto align-self-start";
    action.href = `event-details.html?id=${encodeURIComponent(event.id)}`;
    action.textContent = "View event details";
    action.setAttribute("aria-label", `View details for ${event.title || "event"}`);

    body.append(badges, title, description, dateAndTime, location, capacity, deadline, action);
    card.append(body);
    column.append(card);
    resultsContainer.append(column);
}

async function loadEvents(searchText = "") {
    hideSearchStates();
    loadingMessage.classList.remove("d-none");

    const params = new URLSearchParams();
    const normalizedSearch = searchText.trim();
    if (normalizedSearch) params.set("search", normalizedSearch);
    const requestUrl = params.toString()
        ? `${EVENTS_API_URL}?${params.toString()}`
        : EVENTS_API_URL;

    try {
        const response = await fetch(requestUrl, { headers: { "Accept": "application/json" } });
        const data = await response.json().catch(() => null);
        if (!response.ok) {
            throw new Error(response.status === 422
                ? "Search must be 100 characters or fewer."
                : "Unable to load events. Please try again.");
        }
        if (!Array.isArray(data)) throw new Error("The server returned an unexpected response.");

        // Defensive client filtering complements the API's public/upcoming query.
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const upcoming = data.filter(event => {
            if (!event || (event.status || "").toLowerCase() !== "published") return false;
            if (!event.event_date) return false;
            const eventDate = new Date(`${event.event_date}T00:00:00`);
            return !Number.isNaN(eventDate.getTime()) && eventDate >= today;
        });

        loadingMessage.classList.add("d-none");
        if (upcoming.length === 0) {
            emptyMessage.classList.remove("d-none");
            return;
        }
        upcoming.forEach(showEvent);
    } catch (error) {
        loadingMessage.classList.add("d-none");
        errorMessage.textContent = error.message || "Cannot connect to EventHub API.";
        errorMessage.classList.remove("d-none");
        retryButton.classList.remove("d-none");
    }
}

searchForm.addEventListener("submit", event => {
    event.preventDefault();
    loadEvents(searchInput.value);
});

clearButton.addEventListener("click", () => {
    searchInput.value = "";
    loadEvents();
});

retryButton.addEventListener("click", () => loadEvents(searchInput.value));
loadEvents();

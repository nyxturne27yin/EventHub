const EVENTS_API_URL = "http://127.0.0.1:8000/events/";

const searchForm = document.getElementById("eventSearchForm");
const searchInput = document.getElementById("eventSearchInput");
const clearButton = document.getElementById("clearEventSearch");
const loadingMessage = document.getElementById("eventSearchLoading");
const errorMessage = document.getElementById("eventSearchError");
const emptyMessage = document.getElementById("eventSearchEmpty");
const resultsContainer = document.getElementById("eventSearchResults");

function hideSearchStates() {
    loadingMessage.classList.add("d-none");
    errorMessage.classList.add("d-none");
    emptyMessage.classList.add("d-none");
    resultsContainer.replaceChildren();
}

function showEvent(event) {
    const column = document.createElement("div");
    column.className = "col-12 col-md-6";

    const card = document.createElement("article");
    card.className = "card h-100 shadow-sm";

    const cardBody = document.createElement("div");
    cardBody.className = "card-body";

    const title = document.createElement("h3");
    title.className = "h5 card-title";
    title.textContent = event.title || "Untitled Event";

    const category = document.createElement("p");
    category.className = "text-muted mb-2";
    category.textContent = event.category || "General";

    const description = document.createElement("p");
    description.className = "card-text";
    description.textContent = event.description || "No description available.";

    const dateAndTime = document.createElement("p");
    dateAndTime.className = "small";
    dateAndTime.textContent =
        `Date: ${event.event_date || "Not specified"} | Start: ${event.start_time || "Not specified"} | End: ${event.end_time || "Not specified"}`;

    const mode = document.createElement("p");
    mode.className = "small";
    mode.textContent = `Mode: ${event.mode || "Not specified"}`;

    const location = document.createElement("p");
    location.className = "small mb-0";
    location.textContent = event.mode === "Online"
        ? `Meeting link: ${event.meeting_link || "Not available"}`
        : `Venue: ${event.venue || "Not specified"}`;

    cardBody.append(title, category, description, dateAndTime, mode, location);
    card.append(cardBody);
    column.append(card);
    resultsContainer.append(column);
}

async function loadEvents(searchText = "") {
    hideSearchStates();
    loadingMessage.classList.remove("d-none");

    const params = new URLSearchParams();
    const normalizedSearch = searchText.trim();

    if (normalizedSearch) {
        params.set("search", normalizedSearch);
    }

    const queryString = params.toString();
    const requestUrl = queryString
        ? `${EVENTS_API_URL}?${queryString}`
        : EVENTS_API_URL;

    try {
        const response = await fetch(requestUrl);
        const data = await response.json().catch(() => null);

        if (!response.ok) {
            throw new Error(
                response.status === 422
                    ? "Search must be 100 characters or fewer."
                    : "Unable to load events. Please try again."
            );
        }

        if (!Array.isArray(data)) {
            throw new Error("The server returned an unexpected response.");
        }

        loadingMessage.classList.add("d-none");

        if (data.length === 0) {
            emptyMessage.classList.remove("d-none");
            return;
        }

        data.forEach(showEvent);
    } catch (error) {
        loadingMessage.classList.add("d-none");
        errorMessage.textContent = error.message;
        errorMessage.classList.remove("d-none");
    }
}

searchForm.addEventListener("submit", function (event) {
    event.preventDefault();
    loadEvents(searchInput.value);
});

clearButton.addEventListener("click", function () {
    searchInput.value = "";
    loadEvents();
});

loadEvents();
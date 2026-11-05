const CLUB_DETAIL_API = `${window.EVENTHUB_API_BASE_URL}/organizer-profiles/clubs`;

const clubParams = new URLSearchParams(window.location.search);
const rawClubId = clubParams.get("id");
const clubId = rawClubId && /^[1-9]\d*$/.test(rawClubId)
    ? rawClubId
    : null;

const detailLoading = document.getElementById("clubDetailLoading");
const detailError = document.getElementById("clubDetailError");
const detailRetry = document.getElementById("clubDetailRetry");
const detailContent = document.getElementById("clubDetailContent");

function detailText(value, fallback = "Not provided") {
    return typeof value === "string" && value.trim()
        ? value.trim()
        : fallback;
}

function detailLogoUrl(value) {
    if (
        typeof value !== "string" ||
        !value.startsWith("/uploads/club-logos/")
    ) {
        return null;
    }

    return `${window.EVENTHUB_API_BASE_URL}${value}`;
}

function setClubText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function formatClubDate(value) {
    if (!value) return "Date to be announced";

    const date = new Date(`${value}T00:00:00`);

    return Number.isNaN(date.getTime())
        ? value
        : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

function formatClubTime(value) {
    if (!value) return "Time to be announced";

    const parts = value.split(":");
    if (parts.length < 2) return value;

    const date = new Date();
    date.setHours(Number(parts[0]), Number(parts[1]), 0, 0);

    return new Intl.DateTimeFormat(undefined, {
        hour: "numeric",
        minute: "2-digit"
    }).format(date);
}

function createClubEventCard(event) {
    const column = document.createElement("div");
    column.className = "col-md-6 col-lg-4";

    const card = document.createElement("article");
    card.className = "club-event-card h-100";

    if (
        typeof event.cover_image_url === "string" &&
        event.cover_image_url.startsWith("/uploads/event-covers/")
    ) {
        const image = document.createElement("img");
        image.className = "club-event-cover";
        image.src = `${window.EVENTHUB_API_BASE_URL}${event.cover_image_url}`;
        image.alt = `${detailText(event.title, "Event")} cover`;
        image.onerror = () => image.classList.add("d-none");
        card.append(image);
    }

    const body = document.createElement("div");
    body.className = "club-event-body";

    const category = document.createElement("span");
    category.className = "club-department";
    category.textContent = detailText(event.category, "Club event");

    const title = document.createElement("h3");
    title.className = "h5 mt-2";
    title.textContent = detailText(event.title, "Untitled event");

    const date = document.createElement("p");
    date.className = "club-event-meta";
    date.textContent = `Date: ${formatClubDate(event.event_date)}`;

    const time = document.createElement("p");
    time.className = "club-event-meta";
    time.textContent =
        `Time: ${formatClubTime(event.start_time)} – ${formatClubTime(event.end_time)}`;

    const mode = document.createElement("p");
    mode.className = "club-event-meta";
    mode.textContent = `Mode: ${detailText(event.mode, "Not specified")}`;

    const link = document.createElement("a");
    link.className = "club-card-link";
    link.href = `event-details.html?id=${encodeURIComponent(event.id)}`;
    link.textContent = "View event";

    body.append(category, title, date, time, mode, link);
    card.append(body);
    column.append(card);

    return column;
}

function renderClubProfile(club) {
    const name = detailText(club.organization_name, "Unnamed club");

    setClubText("clubDetailName", name);
    setClubText("clubDetailDepartment", detailText(club.department, "UNIVERSITY CLUB"));
    setClubText("clubDetailBio", detailText(club.bio, "Discover this student organization."));
    setClubText("clubDetailAbout", detailText(club.bio, "No club description has been provided."));
    setClubText(
        "clubDetailContact",
        club.contact_phone ? `Contact phone: ${club.contact_phone}` : "Contact information has not been provided."
    );

    document.title = `${name} | EventHub`;

    const initial = document.getElementById("clubDetailInitial");
    initial.textContent = name.charAt(0).toUpperCase();

    const logo = document.getElementById("clubDetailLogo");
    const logoUrl = detailLogoUrl(club.logo_url);

    if (logoUrl) {
        logo.src = logoUrl;
        logo.alt = `${name} logo`;
        logo.classList.remove("d-none");
        initial.classList.add("d-none");

        logo.onerror = () => {
            logo.classList.add("d-none");
            initial.classList.remove("d-none");
        };
    } else {
        logo.classList.add("d-none");
        initial.classList.remove("d-none");
    }

    const events = Array.isArray(club.events) ? club.events : [];
    const eventsGrid = document.getElementById("clubEventsGrid");
    eventsGrid.replaceChildren();

    events.forEach(event => eventsGrid.append(createClubEventCard(event)));

    document.getElementById("clubEventCount").textContent =
        `${events.length} ${events.length === 1 ? "event" : "events"}`;

    document.getElementById("clubEventsEmpty")
        .classList.toggle("d-none", events.length !== 0);
}

async function loadClubProfile() {
    detailLoading.classList.remove("d-none");
    detailError.classList.add("d-none");
    detailRetry.classList.add("d-none");
    detailContent.classList.add("d-none");

    if (!clubId) {
        detailLoading.classList.add("d-none");
        detailError.textContent = "This club link is invalid. Return to the clubs directory.";
        detailError.classList.remove("d-none");
        return;
    }

    try {
        const response = await fetch(
            `${CLUB_DETAIL_API}/${encodeURIComponent(clubId)}`,
            { headers: { Accept: "application/json" } }
        );

        const data = await response.json().catch(() => null);

        if (!response.ok) {
            throw new Error(
                response.status === 404
                    ? "This club could not be found."
                    : data?.detail || "Unable to load this club profile."
            );
        }

        if (!data || typeof data !== "object" || !data.user_id) {
            throw new Error("The server returned an unexpected club profile.");
        }

        renderClubProfile(data);
        detailContent.classList.remove("d-none");
    } catch (error) {
        detailError.textContent = error.message || "Cannot connect to EventHub.";
        detailError.classList.remove("d-none");
        detailRetry.classList.remove("d-none");
        console.error("Could not load club profile:", error);
    } finally {
        detailLoading.classList.add("d-none");
    }
}

detailRetry.addEventListener("click", loadClubProfile);

loadClubProfile();

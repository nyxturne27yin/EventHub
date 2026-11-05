const CLUBS_API_URL = `${window.EVENTHUB_API_BASE_URL}/organizer-profiles/clubs`;

const clubsGrid = document.getElementById("clubsGrid");
const clubsLoading = document.getElementById("clubsLoading");
const clubsError = document.getElementById("clubsError");
const clubsRetry = document.getElementById("clubsRetry");
const clubsEmpty = document.getElementById("clubsEmpty");
const clubSearch = document.getElementById("clubSearch");
const clubCount = document.getElementById("clubCount");

let allClubs = [];

function clubText(value, fallback = "Not provided") {
    return typeof value === "string" && value.trim()
        ? value.trim()
        : fallback;
}

function clubLogoUrl(value) {
    if (
        typeof value !== "string" ||
        !value.startsWith("/uploads/club-logos/")
    ) {
        return null;
    }

    return `${window.EVENTHUB_API_BASE_URL}${value}`;
}

function createClubCard(club) {
    const column = document.createElement("div");
    column.className = "col-sm-6 col-lg-4";

    const card = document.createElement("article");
    card.className = "club-card h-100";

    const visual = document.createElement("div");
    visual.className = "club-card-visual";

    const logo = document.createElement("img");
    logo.className = "club-card-logo";
    logo.alt = `${clubText(club.organization_name, "Club")} logo`;

    const fallback = document.createElement("div");
    fallback.className = "club-card-initial";
    fallback.textContent = clubText(club.organization_name, "C")
        .charAt(0).toUpperCase();

    const logoUrl = clubLogoUrl(club.logo_url);

    if (logoUrl) {
        logo.src = logoUrl;
        logo.addEventListener("error", () => {
            logo.classList.add("d-none");
            fallback.classList.remove("d-none");
        });
        fallback.classList.add("d-none");
    } else {
        logo.classList.add("d-none");
    }

    visual.append(logo, fallback);

    const content = document.createElement("div");
    content.className = "club-card-body";

    const department = document.createElement("span");
    department.className = "club-department";
    department.textContent = clubText(club.department, "University club");

    const title = document.createElement("h3");
    title.className = "club-card-title";
    title.textContent = clubText(club.organization_name, "Unnamed club");

    const description = document.createElement("p");
    description.className = "club-card-description";
    description.textContent = clubText(
        club.bio,
        "Discover this student organization and explore its activities."
    );

    const link = document.createElement("a");
    link.className = "club-card-link";
    link.href = `club-details.html?id=${encodeURIComponent(club.user_id)}`;
    link.textContent = "Explore club";

    content.append(department, title, description, link);
    card.append(visual, content);
    column.append(card);

    return column;
}

function renderClubs() {
    const query = (clubSearch.value || "").trim().toLowerCase();

    const filtered = allClubs.filter(club => {
        const name = clubText(club.organization_name, "").toLowerCase();
        const department = clubText(club.department, "").toLowerCase();
        const description = clubText(club.bio, "").toLowerCase();

        return (
            name.includes(query) ||
            department.includes(query) ||
            description.includes(query)
        );
    });

    clubsGrid.replaceChildren();

    filtered.forEach(club => {
        clubsGrid.append(createClubCard(club));
    });

    clubCount.textContent =
        `${filtered.length} ${filtered.length === 1 ? "club" : "clubs"}`;

    clubsEmpty.classList.toggle("d-none", filtered.length !== 0);
}

async function loadClubs() {
    clubsLoading.classList.remove("d-none");
    clubsError.classList.add("d-none");
    clubsRetry.classList.add("d-none");
    clubsEmpty.classList.add("d-none");

    try {
        const response = await fetch(CLUBS_API_URL, {
            headers: { Accept: "application/json" }
        });

        const data = await response.json().catch(() => null);

        if (!response.ok) {
            throw new Error(
                data?.detail || "Unable to load clubs. Please try again."
            );
        }

        if (!Array.isArray(data)) {
            throw new Error("The server returned an unexpected clubs response.");
        }

        allClubs = data;
        renderClubs();
    } catch (error) {
        clubsGrid.replaceChildren();
        clubCount.textContent = "Clubs unavailable";
        clubsError.textContent =
            error.message || "Cannot connect to EventHub.";
        clubsError.classList.remove("d-none");
        clubsRetry.classList.remove("d-none");
        console.error("Could not load clubs:", error);
    } finally {
        clubsLoading.classList.add("d-none");
    }
}

clubSearch.addEventListener("input", renderClubs);
clubsRetry.addEventListener("click", loadClubs);

loadClubs();

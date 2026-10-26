
const NOTIFICATION_API_URL = "http://127.0.0.1:8000/notifications";

const notificationLoading = document.getElementById("notificationLoading");
const notificationError = document.getElementById("notificationError");
const notificationErrorMessage = document.getElementById("notificationErrorMessage");
const notificationEmpty = document.getElementById("notificationEmpty");
const notificationList = document.getElementById("notificationList");
const refreshButton = document.getElementById("refreshNotifications");
const retryButton = document.getElementById("retryNotifications");
let notificationRequestInProgress = false;

function showNotificationState(state) {
    notificationLoading.classList.toggle("d-none", state !== "loading");
    notificationError.classList.toggle("d-none", state !== "error");
    notificationEmpty.classList.toggle("d-none", state !== "empty");
    notificationList.classList.toggle("d-none", state !== "success");
}

function getNotificationType(title, message) {
    const text = `${title} ${message}`.toLowerCase();

    if (text.includes("cancel")) return "Cancellation";
    if (text.includes("reminder") || text.includes("upcoming")) return "Reminder";
    if (text.includes("change") || text.includes("updated") || text.includes("rescheduled")) {
        return "Event update";
    }
    if (text.includes("registration") || text.includes("registered") || text.includes("confirm")) {
        return "Registration";
    }

    return "Event notification";
}

function formatNotificationDate(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "Date unavailable";
    }

    return date.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short"
    });
}

function createNotificationCard(notification) {
    const card = document.createElement("article");
    card.className = `card shadow-sm ${notification.is_read ? "" : "border-primary"}`;

    const body = document.createElement("div");
    body.className = "card-body";

    const heading = document.createElement("div");
    heading.className = "d-flex flex-wrap justify-content-between gap-2";

    const title = document.createElement("h2");
    title.className = "h5 mb-1";
    title.textContent = notification.title || "Event notification";

    const status = document.createElement("span");
    status.className = notification.is_read
        ? "badge text-bg-secondary"
        : "badge text-bg-primary";
    status.textContent = notification.is_read ? "Read" : "Unread";

    heading.append(title, status);

    const type = document.createElement("span");
    type.className = "badge text-bg-light border mt-2";
    type.textContent = getNotificationType(
        notification.title || "",
        notification.message || ""
    );

    const message = document.createElement("p");
    message.className = "card-text mt-3 mb-2";
    message.textContent = notification.message || "";

    const eventTitle = document.createElement("p");
    eventTitle.className = "text-muted small mb-2";
    eventTitle.textContent = notification.event_title
        ? `Event: ${notification.event_title}`
        : "";

    const date = document.createElement("time");
    date.className = "text-muted small";
    date.dateTime = notification.created_at || "";
    date.textContent = formatNotificationDate(notification.created_at);

    body.append(heading, type, message, eventTitle, date);
    card.append(body);

    return card;
}

async function loadNotifications() {
    if (notificationRequestInProgress) return;
    notificationRequestInProgress = true;
    if (refreshButton) { refreshButton.disabled = true; refreshButton.setAttribute("aria-busy", "true"); }
    if (retryButton) retryButton.disabled = true;
    showNotificationState("loading");
    notificationList.replaceChildren();

    const token = sessionStorage.getItem("access_token");

    if (!token) {
        notificationRequestInProgress = false;
        if (refreshButton) { refreshButton.disabled = false; refreshButton.removeAttribute("aria-busy"); }
        if (retryButton) retryButton.disabled = false;
        window.location.href = "login.html";
        return;
    }

    try {
        const response = await fetch(NOTIFICATION_API_URL, {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });

        if (response.status === 401 || response.status === 403) {
            sessionStorage.removeItem("access_token");
            window.location.href = "login.html";
            return;
        }

        if (!response.ok) {
            throw new Error("Unable to retrieve notifications. Please try again.");
        }

        const notifications = await response.json();

        if (!Array.isArray(notifications) || notifications.length === 0) {
            showNotificationState("empty");
            return;
        }

        notifications.sort(
            (a, b) => new Date(b.created_at) - new Date(a.created_at)
        );

        notifications.forEach((notification) => {
            notificationList.appendChild(createNotificationCard(notification));
        });

        showNotificationState("success");
    } catch (error) {
        notificationErrorMessage.textContent =
            error.message || "Unable to load notifications. Check your connection.";
        showNotificationState("error");
    } finally {
        notificationRequestInProgress = false;
        if (refreshButton) { refreshButton.disabled = false; refreshButton.removeAttribute("aria-busy"); }
        if (retryButton) retryButton.disabled = false;
    }
}

refreshButton?.addEventListener("click", loadNotifications);
retryButton?.addEventListener("click", loadNotifications);

loadNotifications();

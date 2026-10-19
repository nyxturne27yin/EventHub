
const API_BASE = "http://127.0.0.1:8000";

const token = sessionStorage.getItem("access_token");

const pageMessage = document.getElementById("pageMessage");
const loadingMessage = document.getElementById("loadingMessage");
const dashboardContent = document.getElementById("dashboardContent");

function showMessage(message, type = "danger") {
    pageMessage.textContent = message;
    pageMessage.className = `alert alert-${type}`;
}

function hideMessage() {
    pageMessage.textContent = "";
    pageMessage.className = "d-none";
}

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            ...options.headers,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(
            error.detail || `Request failed (${response.status})`
        );
    }

    return response.json();
}

function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value ?? 0;
    }
}

function formatDate(value) {
    if (!value) return "Not specified";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleDateString();
}

function createCell(value) {
    const cell = document.createElement("td");
    cell.textContent = value ?? "—";
    return cell;
}

function createSelect(options, selectedValue) {
    const select = document.createElement("select");
    select.className = "form-select form-select-sm";

    options.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        option.selected = value === selectedValue;
        select.appendChild(option);
    });

    return select;
}

function createButton(label, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-sm btn-primary";
    button.textContent = label;
    button.addEventListener("click", onClick);
    return button;
}

function renderStats(containerId, stats) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.replaceChildren();

    const entries = Object.entries(stats || {});

    if (entries.length === 0) {
        container.textContent = "No data available.";
        return;
    }

    entries.forEach(([name, count]) => {
        const item = document.createElement("span");
        item.className = "badge text-bg-secondary me-2 mb-2";
        item.textContent = `${name}: ${count}`;
        container.appendChild(item);
    });
}

async function loadDashboard() {
    const data = await apiRequest("/admin/dashboard");

    setText("totalUsers", data.total_users);
    setText("activeUsers", data.active_users);
    setText("inactiveUsers", data.inactive_users);
    setText("totalEvents", data.total_events);

    renderStats("roleStats", data.users_by_role);
    renderStats("eventStats", data.events_by_status);
}

async function loadUsers() {
    const users = await apiRequest("/admin/users");
    const table = document.getElementById("usersTable");
    const emptyMessage = document.getElementById("usersEmpty");

    table.replaceChildren();

    if (emptyMessage) {
        emptyMessage.classList.toggle("d-none", users.length > 0);
    }

    users.forEach((user) => {
        const row = document.createElement("tr");

        row.appendChild(createCell(user.name));
        row.appendChild(createCell(user.email));

        const roleCell = document.createElement("td");
        const roleSelect = createSelect(
            ["student", "organizer", "administrator"],
            user.role
        );
        roleCell.appendChild(roleSelect);
        row.appendChild(roleCell);

        const accountCell = document.createElement("td");
        const accountSelect = createSelect(
            ["active", "inactive"],
            user.is_active ? "active" : "inactive"
        );
        accountCell.appendChild(accountSelect);
        row.appendChild(accountCell);

        const actionCell = document.createElement("td");

        const saveButton = createButton("Save", async () => {
            saveButton.disabled = true;
            saveButton.textContent = "Saving...";

            try {
                await apiRequest(`/admin/users/${user.id}`, {
                    method: "PATCH",
                    body: JSON.stringify({
                        role: roleSelect.value,
                        is_active: accountSelect.value === "active",
                    }),
                });

                showMessage(
                    `Updated ${user.name} successfully.`,
                    "success"
                );

                await Promise.all([loadUsers(), loadDashboard()]);
            } catch (error) {
                showMessage(`Could not update user: ${error.message}`);
            } finally {
                saveButton.disabled = false;
                saveButton.textContent = "Save";
            }
        });

        actionCell.appendChild(saveButton);
        row.appendChild(actionCell);
        table.appendChild(row);
    });
}

async function loadEvents() {
    const events = await apiRequest("/admin/events");
    const table = document.getElementById("eventsTable");
    const emptyMessage = document.getElementById("eventsEmpty");

    table.replaceChildren();

    if (emptyMessage) {
        emptyMessage.classList.toggle("d-none", events.length > 0);
    }

    events.forEach((event) => {
        const row = document.createElement("tr");

        row.appendChild(createCell(event.title));
        row.appendChild(createCell(formatDate(event.event_date)));
        row.appendChild(createCell(event.organizer_name));
        row.appendChild(createCell(event.status));

        const actionCell = document.createElement("td");
        const statusSelect = createSelect(
            ["draft", "published", "cancelled", "completed"],
            event.status
        );

        const saveButton = createButton("Update", async () => {
            saveButton.disabled = true;
            saveButton.textContent = "Updating...";

            try {
                await apiRequest(
                    `/admin/events/${event.id}/status`,
                    {
                        method: "PATCH",
                        body: JSON.stringify({
                            status: statusSelect.value,
                        }),
                    }
                );

                showMessage(
                    `Updated "${event.title}" successfully.`,
                    "success"
                );

                await Promise.all([loadEvents(), loadDashboard()]);
            } catch (error) {
                showMessage(
                    `Could not update event: ${error.message}`
                );
            } finally {
                saveButton.disabled = false;
                saveButton.textContent = "Update";
            }
        });

        actionCell.appendChild(statusSelect);
        actionCell.appendChild(saveButton);
        row.appendChild(actionCell);
        table.appendChild(row);
    });
}

async function initializeDashboard() {
    if (!token) {
        window.location.href = "login.html";
        return;
    }

    try {
        const currentUser = await apiRequest("/auth/me");
        const role =
            typeof currentUser.role === "string"
                ? currentUser.role.toLowerCase()
                : currentUser.role?.name?.toLowerCase();

        if (role !== "administrator") {
            showMessage("Access denied. Administrator permission is required.");
            loadingMessage.classList.add("d-none");
            return;
        }

        await Promise.all([
            loadDashboard(),
            loadUsers(),
            loadEvents(),
        ]);

        hideMessage();
        dashboardContent.classList.remove("d-none");
    } catch (error) {
        showMessage(`Could not load dashboard: ${error.message}`);

        if (loadingMessage) {
            loadingMessage.classList.add("d-none");
        }
    } finally {
        if (loadingMessage) {
            loadingMessage.classList.add("d-none");
        }
    }
}

document.getElementById("logoutButton")?.addEventListener("click", () => {
    sessionStorage.removeItem("access_token");
    window.location.href = "login.html";
});

document.getElementById("refreshUsers")?.addEventListener("click", async () => {
    try {
        hideMessage();
        await loadUsers();
        showMessage("User list refreshed.", "success");
    } catch (error) {
        showMessage(`Could not refresh users: ${error.message}`);
    }
});

document.getElementById("refreshEvents")?.addEventListener("click", async () => {
    try {
        hideMessage();
        await loadEvents();
        showMessage("Event list refreshed.", "success");
    } catch (error) {
        showMessage(`Could not refresh events: ${error.message}`);
    }
});

initializeDashboard();


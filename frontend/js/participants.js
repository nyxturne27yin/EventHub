const API_BASE_URL = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("participantsRetry")?.addEventListener("click", loadParticipants);
    loadParticipants();
});

async function loadParticipants() {
    const loading = document.getElementById("participantsLoading");
    const error = document.getElementById("participantsError");
    const empty = document.getElementById("participantsEmpty");
    const list = document.getElementById("participantsList");
    const items = document.getElementById("participantItems");
    const retry = document.getElementById("participantsRetry");
    const token = sessionStorage.getItem("access_token");
    const eventId = new URLSearchParams(window.location.search).get("event_id");

    if (retry) retry.classList.add("d-none");
    error.classList.add("d-none");
    empty.classList.add("d-none");
    list.classList.add("d-none");
    if (!token || !eventId || !/^[1-9]\d*$/.test(eventId)) {
        loading.classList.add("d-none");
        error.textContent = !token
            ? "Please log in to view participants."
            : (!eventId ? "Event ID is missing from the URL." : "The event ID in this link is invalid.");
        error.classList.remove("d-none");
        return;
    }

    loading.classList.remove("d-none");
    try {
        const response = await fetch(
            `${API_BASE_URL}/events/${eventId}/participants`,
            { headers: { Authorization: `Bearer ${token}` } }
        );

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || "Unable to load participants.");
        }

        items.replaceChildren();

        if (data.length === 0) {
            empty.classList.remove("d-none");
            return;
        }

        data.forEach(participant => {
            const item = document.createElement("li");
            item.className = "list-group-item d-flex flex-wrap justify-content-between align-items-center gap-3";

            const details = document.createElement("div");
            const name = document.createElement("strong");
            name.textContent = participant.participant_name;
            const email = document.createElement("div");
            email.className = "text-muted small";
            email.textContent = participant.participant_email;
            const statusText = document.createElement("div");
            statusText.className = "small mt-1";
            statusText.textContent = `Status: ${participant.status}`;
            details.append(name, email, statusText);

            const controls = document.createElement("div");
            controls.className = "d-flex flex-wrap gap-2 w-100";

            const select = document.createElement("select");
            select.className = "form-select form-select-sm flex-grow-1";
            ["Registered", "Cancelled"].forEach(value => {
                const option = document.createElement("option");
                option.value = value;
                option.textContent = value;
                select.appendChild(option);
            });
            select.value = participant.status;

            const button = document.createElement("button");
            button.type = "button";
            button.className = "btn btn-sm btn-primary";
            button.textContent = "Update";

            button.addEventListener("click", async () => {
                button.disabled = true;
                button.setAttribute("aria-busy", "true");
                button.textContent = "Saving…";
                try {
                    const updateResponse = await fetch(
                        `${API_BASE_URL}/events/${eventId}/registrations/${participant.id}/status`,
                        {
                            method: "PATCH",
                            headers: {
                                Authorization: `Bearer ${token}`,
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({ status: select.value })
                        }
                    );

                    const result = await updateResponse.json().catch(() => ({}));
                    if (!updateResponse.ok) {
                        throw new Error(result.detail || "Could not update status.");
                    }

                    statusText.textContent = `Status: ${result.status}`;
                    error.classList.add("d-none");
                } catch (err) {
                    error.textContent = err.message;
                    error.classList.remove("d-none");
                } finally {
                    button.disabled = false;
                    button.removeAttribute("aria-busy");
                    button.textContent = "Update";
                }
            });

            controls.append(select, button);
            item.append(details, controls);
            items.appendChild(item);
        });

        list.classList.remove("d-none");
    } catch (err) {
        error.textContent = err.message || "Unable to load participants.";
        error.classList.remove("d-none");
        if (retry) retry.classList.remove("d-none");
    } finally {
        loading.classList.add("d-none");
    }
}

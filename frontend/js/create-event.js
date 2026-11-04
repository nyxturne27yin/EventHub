
const API_BASE_URL = window.EVENTHUB_API_BASE_URL;
const requestedEditId = new URLSearchParams(window.location.search).get("edit");
const editEventId = requestedEditId && /^[1-9]\d*$/.test(requestedEditId) ? requestedEditId : null;
let existingCoverImageUrl = null;
let removeExistingCover = false;

const form = document.getElementById("createEventForm");
const messageBox = document.getElementById("pageMessage");
const modeInput = document.getElementById("mode");
const venueInput = document.getElementById("venue");
const meetingLinkInput = document.getElementById("meeting_link");
const submitButton = document.getElementById("submitButton");
const postCreateActions = document.getElementById("postCreateActions");
const coverInput = document.getElementById("coverImage");
const coverDropZone = document.getElementById("coverDropZone");
const coverPreviewWrap = document.getElementById("coverImagePreviewWrap");
const coverPreview = document.getElementById("coverImagePreview");
const coverImageName = document.getElementById("coverImageName");
const removeCoverButton = document.getElementById("removeCoverImage");
const MAX_COVER_IMAGE_SIZE = 5 * 1024 * 1024;
const ALLOWED_COVER_TYPES = ["image/jpeg", "image/png", "image/webp"];
let selectedCoverImage = null;
let coverPreviewUrl = null;

function showMessage(message, type = "danger") {
    messageBox.textContent = message;
    messageBox.className = `alert alert-${type}`;
}

function clearCoverPreview() {
    selectedCoverImage = null;
    existingCoverImageUrl = null;
    removeExistingCover = false;
    coverInput.value = "";
    if (coverPreviewUrl) URL.revokeObjectURL(coverPreviewUrl);
    coverPreviewUrl = null;
    coverPreview.removeAttribute("src");
    coverPreviewWrap.classList.add("d-none");
    coverDropZone.classList.remove("has-image");
}

function showExistingCover(imageUrl) {
    existingCoverImageUrl = imageUrl || null;
    selectedCoverImage = null;
    removeExistingCover = false;
    if (coverPreviewUrl) URL.revokeObjectURL(coverPreviewUrl);
    coverPreviewUrl = null;
    coverInput.value = "";
    coverPreview.src = `${API_BASE_URL}${imageUrl}`;
    coverImageName.textContent = "Current event cover image";
    coverPreviewWrap.classList.remove("d-none");
    coverDropZone.classList.add("has-image");
}

function removeCoverSelection() {
    if (selectedCoverImage) {
        selectedCoverImage = null;
        coverInput.value = "";
        if (coverPreviewUrl) URL.revokeObjectURL(coverPreviewUrl);
        coverPreviewUrl = null;
        if (existingCoverImageUrl) {
            showExistingCover(existingCoverImageUrl);
        } else {
            coverPreview.removeAttribute("src");
            coverPreviewWrap.classList.add("d-none");
            coverDropZone.classList.remove("has-image");
        }
        return;
    }
    if (existingCoverImageUrl) {
        removeExistingCover = true;
        existingCoverImageUrl = null;
    }
    coverPreview.removeAttribute("src");
    coverPreviewWrap.classList.add("d-none");
    coverDropZone.classList.remove("has-image");
}

function setCoverImage(file) {
    if (!file) return;
    if (!ALLOWED_COVER_TYPES.includes(file.type)) {
        showMessage("Choose a JPG, PNG, or WebP image.");
        coverInput.value = "";
        return;
    }
    if (file.size > MAX_COVER_IMAGE_SIZE) {
        showMessage("The cover image must be 5 MB or smaller.");
        coverInput.value = "";
        return;
    }
    selectedCoverImage = file;
    removeExistingCover = false;
    if (coverPreviewUrl) URL.revokeObjectURL(coverPreviewUrl);
    coverPreviewUrl = URL.createObjectURL(file);
    coverPreview.src = coverPreviewUrl;
    coverImageName.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB`;
    coverPreviewWrap.classList.remove("d-none");
    coverDropZone.classList.add("has-image");
    messageBox.classList.add("d-none");
}

async function uploadCoverImage(eventId, token) {
    if (!selectedCoverImage) return null;
    const uploadData = new FormData();
    uploadData.append("image", selectedCoverImage);
    const response = await fetch(`${API_BASE_URL}/events/${encodeURIComponent(eventId)}/cover-image`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: uploadData
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
        const detail = result.detail;
        throw new Error(Array.isArray(detail) ? detail.map(item => item.msg).join(", ") : (detail || "The event was created, but its cover image could not be uploaded."));
    }
    return result.cover_image_url;
}

function updateModeFields() {
    const isOnline = modeInput.value === "Online";

    document.getElementById("venueGroup").classList.toggle("d-none", isOnline);
    document.getElementById("meetingLinkGroup").classList.toggle("d-none", !isOnline);

    venueInput.required = !isOnline;
    meetingLinkInput.required = isOnline;
}

async function loadEventForEditing(eventId, token) {
    try {
        const response = await fetch(`${API_BASE_URL}/events/${encodeURIComponent(eventId)}/manage`, {
            headers: { Authorization: `Bearer ${token}`, Accept: "application/json" }
        });
        const event = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(event.detail || "Unable to load this event for editing.");

        ["title", "description", "category", "event_date", "start_time", "end_time", "mode", "capacity", "venue", "meeting_link"].forEach(name => {
            const field = form.elements.namedItem(name);
            if (field) field.value = event[name] ?? "";
        });
        const deadline = event.registration_deadline ? String(event.registration_deadline).slice(0, 16) : "";
        document.getElementById("registration_deadline").value = deadline;
        updateModeFields();
        if (event.cover_image_url) showExistingCover(event.cover_image_url);
        document.querySelector("main h1").textContent = "Edit event";
        submitButton.textContent = "Save Changes";
        document.querySelector("main .card-body > p").textContent = "Update your event details and save your changes.";
    } catch (error) {
        form.classList.add("d-none");
        showMessage(error.message || "Unable to load this event.");
    }
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
        if (editEventId) await loadEventForEditing(editEventId, token);

    } catch (error) {
        showMessage("Cannot connect to the backend. Please try again.");
    }
}

modeInput.addEventListener("change", updateModeFields);
coverInput.addEventListener("change", () => setCoverImage(coverInput.files[0]));
removeCoverButton.addEventListener("click", removeCoverSelection);
["dragenter", "dragover"].forEach(type => coverDropZone.addEventListener(type, event => {
    event.preventDefault();
    coverDropZone.classList.add("is-dragging");
}));
["dragleave", "drop"].forEach(type => coverDropZone.addEventListener(type, event => {
    event.preventDefault();
    coverDropZone.classList.remove("is-dragging");
}));
coverDropZone.addEventListener("drop", event => setCoverImage(event.dataTransfer.files[0]));

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

    payload.capacity = payload.capacity === "" ? null : Number(payload.capacity);

    if (payload.capacity !== null && (!Number.isInteger(payload.capacity) || payload.capacity <= 0)) {
        showMessage("Capacity must be a positive whole number, or leave it blank for unlimited capacity.");
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
    submitButton.textContent = editEventId ? "Saving…" : "Creating…";

    try {
        const response = await fetch(editEventId ? `${API_BASE_URL}/events/${encodeURIComponent(editEventId)}` : `${API_BASE_URL}/events/`, {
            method: editEventId ? "PATCH" : "POST",
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

        const savedEvent = result.event || result;
        const savedEventId = savedEvent.id || editEventId;
        let imageUploadFailed = false;
        if (savedEventId && selectedCoverImage) {
            try {
                const uploadedUrl = await uploadCoverImage(savedEventId, token);
                if (editEventId && uploadedUrl) showExistingCover(uploadedUrl);
                else clearCoverPreview();
            } catch (imageError) {
                imageUploadFailed = true;
                showMessage(`The event details were saved, but the cover image upload failed: ${imageError.message}`, "warning");
            }
        } else if (savedEventId && editEventId && removeExistingCover) {
            try {
                const removeResponse = await fetch(`${API_BASE_URL}/events/${encodeURIComponent(savedEventId)}/cover-image`, {
                    method: "DELETE",
                    headers: { Authorization: `Bearer ${token}` }
                });
                const removeResult = await removeResponse.json().catch(() => ({}));
                if (!removeResponse.ok) throw new Error(removeResult.detail || "Could not remove the cover image.");
                clearCoverPreview();
            } catch (removeError) {
                imageUploadFailed = true;
                showMessage(removeError.message || "The event was saved, but its image could not be removed.", "warning");
            }
        }
        if (!imageUploadFailed) {
            showMessage(editEventId ? "Event updated successfully." : "Event created successfully as a draft.", "success");
        }
        postCreateActions.replaceChildren();
        postCreateActions.classList.remove("d-none");

        if (savedEventId) {
            if (editEventId) {
                const profileLink = document.createElement("a");
                profileLink.className = "btn btn-outline-primary";
                profileLink.href = "profile.html";
                profileLink.textContent = "Back to profile";
                postCreateActions.append(profileLink);
            } else if (imageUploadFailed && selectedCoverImage) {
                const retryImageButton = document.createElement("button");
                retryImageButton.type = "button";
                retryImageButton.className = "btn btn-outline-primary me-2 mb-2";
                retryImageButton.textContent = "Retry cover image upload";
                retryImageButton.addEventListener("click", async () => {
                    retryImageButton.disabled = true;
                    retryImageButton.textContent = "Uploading...";
                    try {
                        await uploadCoverImage(savedEventId, token);
                        clearCoverPreview();
                        showMessage("Cover image uploaded successfully.", "success");
                        retryImageButton.textContent = "Cover image uploaded";
                    } catch (retryError) {
                        showMessage(retryError.message || "Could not upload the cover image.", "warning");
                        retryImageButton.disabled = false;
                        retryImageButton.textContent = "Retry cover image upload";
                    }
                });
                postCreateActions.append(retryImageButton);
            }

            if (!editEventId) {
            const publishButton = document.createElement("button");
            publishButton.type = "button";
            publishButton.className = "btn btn-success";
            publishButton.textContent = "Submit for approval";
            publishButton.addEventListener("click", async () => {
                publishButton.disabled = true;
                publishButton.textContent = "Publishing...";
                try {
                    const publishResponse = await fetch(
                        `${API_BASE_URL}/events/${encodeURIComponent(savedEventId)}/publish`,
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
        }
        if (!editEventId) {
            form.reset();
            if (!imageUploadFailed) clearCoverPreview();
            updateModeFields();
        }

    } catch (error) {
        showMessage(error.message || "Could not connect to the server.");
    } finally {
        submitButton.disabled = false;
        submitButton.removeAttribute("aria-busy");
        submitButton.textContent = editEventId ? "Save Changes" : "Create Event";
    }
});

checkOrganizerAccess();

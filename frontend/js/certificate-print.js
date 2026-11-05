document.addEventListener("DOMContentLoaded", async () => {
    const api = window.EVENTHUB_API_BASE_URL;
    const id = new URLSearchParams(window.location.search).get("id");
    const error = document.getElementById("certificateError");

    document.getElementById("printButton").addEventListener("click", () => {
        window.print();
    });

    if (!id || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
        error.textContent = "A valid certificate ID is required.";
        error.classList.remove("d-none");
        return;
    }

    try {
        const response = await fetch(
            `${api}/certificates/verify/${encodeURIComponent(id)}`
        );

        const data = await response.json().catch(() => ({}));

        if (!response.ok || !data.valid) {
            throw new Error(data.detail || "Certificate could not be verified.");
        }

        document.getElementById("studentName").textContent =
            data.student_name || "Student";

        document.getElementById("eventTitle").textContent =
            data.event_title || "Event";

        document.getElementById("category").textContent =
            data.category || "Academic";

        document.getElementById("issuedDate").textContent =
            data.issued_at
                ? new Date(data.issued_at).toLocaleDateString()
                : "Not available";

        document.getElementById("certificateId").textContent =
            `Certificate ID: ${id}`;

        const qr = document.getElementById("qrImage");
        qr.src = `${api}/certificates/verify/${encodeURIComponent(id)}/qr`;

        qr.addEventListener("error", () => {
            qr.alt = "QR code unavailable. Check PUBLIC_API_BASE_URL.";
        });
    } catch (err) {
        error.textContent = err.message || "Unable to load certificate.";
        error.classList.remove("d-none");
        document.getElementById("certificate").classList.add("d-none");
    }
});
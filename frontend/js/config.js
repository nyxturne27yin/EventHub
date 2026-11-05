/*
 * Central frontend configuration.
 * Local development uses localhost.
 * Deployed frontend uses the Render backend.
 */
(() => {
    const isLocalDevelopment = [
        "localhost",
        "127.0.0.1"
    ].includes(window.location.hostname);

    const configuredOrigin = window.EVENTHUB_API_BASE_URL
        || document.querySelector('meta[name="eventhub-api-base"]')?.content
        || (
            isLocalDevelopment
                ? "http://127.0.0.1:8000"
                : "https://eventhub-backend-1xye.onrender.com"
        );

    window.EVENTHUB_API_BASE_URL = String(configuredOrigin).replace(/\/+$/, "");
})();

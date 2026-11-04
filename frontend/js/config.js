/*
 * Central frontend configuration.
 * Set this one value to the deployed FastAPI origin before publishing the frontend.
 */
(() => {
    const configuredOrigin = window.EVENTHUB_API_BASE_URL
        || document.querySelector('meta[name="eventhub-api-base"]')?.content
        || "http://127.0.0.1:8000";
    window.EVENTHUB_API_BASE_URL = String(configuredOrigin).replace(/\/+$/, "");
})();

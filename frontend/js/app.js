// EventHub API configuration
const API_BASE_URL = "http://127.0.0.1:8000";

// Make a GET request to an EventHub API endpoint
async function getFromApi(endpoint) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);

    if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
    }

    return response.json();
}

console.log("EventHub frontend JavaScript loaded successfully.");
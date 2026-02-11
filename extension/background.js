const GEMINI_URL = "https://gemini.google.com/";

// Alarm to check cookies every 5 minutes
chrome.alarms.create("syncCookies", { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === "syncCookies") {
        syncCookies();
    }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "sync") {
        syncCookies();
        sendResponse({ status: "sync_started" });
    }
});

async function syncCookies() {
    const settings = await chrome.storage.local.get(["serverUrl", "apiKey"]);
    if (!settings.serverUrl || !settings.apiKey) {
        console.log("Probaho Sync: Settings not configured.");
        return;
    }

    // Search for cookies across .google.com to be sure
    const cookies = await chrome.cookies.getAll({ domain: ".google.com" });
    const psid = cookies.find(c => c.name === "__Secure-1PSID")?.value;
    const psidts = cookies.find(c => c.name === "__Secure-1PSIDTS")?.value;

    console.log("Probaho Sync: Found cookies?", !!psid, !!psidts);

    if (psid && psidts) {
        try {
            const response = await fetch(`${settings.serverUrl}/admin/sync-cookies`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-Key": settings.apiKey
                },
                body: JSON.stringify({ psid, psidts })
            });
            const data = await response.json();
            console.log("Probaho Sync:", data.message);
        } catch (error) {
            console.error("Probaho Sync Error:", error);
        }
    }
}

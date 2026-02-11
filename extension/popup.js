document.getElementById('save').addEventListener('click', async () => {
    const serverUrl = document.getElementById('serverUrl').value.replace(/\/$/, "");
    const apiKey = document.getElementById('apiKey').value;

    await chrome.storage.local.set({ serverUrl, apiKey });

    const status = document.getElementById('status');
    status.textContent = "Saving and syncing...";

    // Trigger background sync
    chrome.runtime.getBackgroundPage ?
        chrome.runtime.getBackgroundPage(bg => bg.syncCookies()) :
        chrome.runtime.sendMessage({ action: "sync" }); // V3 workaround

    setTimeout(() => {
        status.textContent = "Settings saved! Syncing in background.";
    }, 1500);
});

// Load existing settings
chrome.storage.local.get(['serverUrl', 'apiKey'], (data) => {
    if (data.serverUrl) document.getElementById('serverUrl').value = data.serverUrl;
    if (data.apiKey) document.getElementById('apiKey').value = data.apiKey;
});

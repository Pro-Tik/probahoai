const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadList = document.getElementById('uploadList');
const generateBtn = document.getElementById('generateBtn');
const statusCard = document.getElementById('statusCard');
const progressBar = document.getElementById('progressBar');
const statusMessage = document.getElementById('statusMessage');
const gallery = document.getElementById('gallery');

let uploadedFiles = [];
let pollingInterval = null;

dropZone.onclick = () => fileInput.click();

fileInput.onchange = (e) => handleFiles(e.target.files);

dropZone.ondragover = (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
};

dropZone.ondragleave = () => dropZone.classList.remove('dragover');

dropZone.ondrop = (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
};

function handleFiles(files) {
    for (const file of files) {
        if (!file.type.startsWith('image/')) continue;

        const reader = new FileReader();
        reader.onload = (e) => {
            const item = document.createElement('div');
            item.className = 'upload-item';
            item.innerHTML = `
                <img src="${e.target.result}" alt="preview">
                <span>${file.name}</span>
            `;
            uploadList.appendChild(item);
            uploadedFiles.push(file);
            generateBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }
}

generateBtn.onclick = async () => {
    if (uploadedFiles.length === 0) return;

    generateBtn.disabled = true;
    statusCard.style.display = 'block';
    statusMessage.textContent = 'Uploading files...';
    progressBar.style.width = '0%';
    gallery.innerHTML = '';

    const formData = new FormData();
    uploadedFiles.forEach(file => formData.append('files', file));

    // Try to get API key from localStorage or use default for development
    const apiKey = localStorage.getItem('PROBAHO_API_KEY') || 'probaho_master_secret';

    try {
        showLoader();
        const response = await fetch('/upload', {
            method: 'POST',
            headers: {
                'X-API-Key': apiKey
            },
            body: formData
        });

        if (response.status === 401) {
            throw new Error("Unauthorized: Invalid API Key");
        }

        const data = await response.json();
        const jobId = data.job_id;

        startPolling(jobId, apiKey);
    } catch (error) {
        statusMessage.textContent = 'Upload failed: ' + error.message;
        generateBtn.disabled = false;
        setTimeout(() => hideLoader(), 3000);
    }
};

function startPolling(jobId, apiKey) {
    if (pollingInterval) clearInterval(pollingInterval);

    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/status/${jobId}`, {
                headers: {
                    'X-API-Key': apiKey
                }
            });
            if (!response.ok) {
                // If the job is missing (e.g., server restart), stop polling
                if (response.status === 404) {
                    throw new Error("Job not found (Server might have restarted).");
                }
                throw new Error("Failed to fetch status.");
            }
            const data = await response.json();

            statusMessage.textContent = data.message;
            progressBar.style.width = (data.progress || 0) + '%';

            if (data.results && data.results.length > 0) {
                updateGallery(data.results);
            }

            if (data.status === 'completed' || data.status === 'failed') {
                clearInterval(pollingInterval);
                generateBtn.disabled = false;

                if (data.status === 'failed') {
                    statusCard.classList.add('failed'); // We can add some CSS for this
                }

                // Notify the game that generation is complete
                const iframe = document.getElementById('loaderIframe');
                if (iframe && iframe.contentWindow) {
                    iframe.contentWindow.postMessage('generationComplete', '*');
                }

                // Automatically hide after 5 seconds so user can see their score
                // and any final error message if it failed
                setTimeout(() => {
                    hideLoader();
                }, 5000);
            }
        } catch (error) {
            console.error('Polling error:', error);
            clearInterval(pollingInterval);
            statusMessage.textContent = "Error: " + error.message;
            generateBtn.disabled = false;

            // Still hide the loader so user isn't stuck
            setTimeout(() => {
                hideLoader();
            }, 3000);
        }
    }, 2000);
}

const shotNameMap = {
    'Front_View': 'Front View',
    'Back_View': 'Back View',
    'Side_View': 'Side View',
    'Three_Quarter': 'Hero Shot (45°)',
    'Detail_Shot': 'Detail Close-up',
    'Lifestyle': 'Lifestyle Scene'
};

function updateGallery(results) {
    if (results.length > gallery.children.length) {
        const newResults = results.slice(gallery.children.length);
        newResults.forEach(url => {
            const fileName = url.split('/').pop();
            // Extract shot name from filename (e.g., photo_Front_View_v1.png)
            let displayName = fileName;
            for (const [key, value] of Object.entries(shotNameMap)) {
                if (fileName.includes(key)) {
                    displayName = value;
                    break;
                }
            }

            const item = document.createElement('div');
            item.className = 'gallery-item';
            item.innerHTML = `
                <img src="${url}" alt="generated">
                <div class="gallery-item-info">
                    <span>${displayName}</span>
                    <button class="download-btn" onclick="downloadImage('${url}', '${fileName}')">
                        <i class="fa-solid fa-download"></i>
                    </button>
                </div>
            `;
            gallery.appendChild(item);
        });
    }
}

function showLoader() {
    const loaderContent = document.getElementById('loaderContent');
    loaderContent.style.display = 'flex';
    const iframe = document.getElementById('loaderIframe');
    iframe.src = 'loader.html';
}

function hideLoader() {
    const loaderContent = document.getElementById('loaderContent');
    loaderContent.style.display = 'none';
    const iframe = document.getElementById('loaderIframe');
    iframe.src = 'about:blank';
}

// Handle messages from the loader game iframe
window.addEventListener('message', (event) => {
    if (event.data === 'hideLoader') {
        hideLoader();
    }
});

function downloadImage(url, name) {
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// Add this at the beginning of your script.js file
// Use the configuration from config.js
const API_BASE_URL = CONFIG.apiBaseUrl;
const WS_URL = CONFIG.wsUrl;

// Update any existing fetch calls to use the API_BASE_URL
// Example:
// Instead of fetch('/api/readers')
// Use fetch(`${API_BASE_URL}/readers`)

// Function to log to backend
function logToBackend(level, message, context = {}) {
    if (!CONFIG.features.enableLogging) return;
    
    fetch(`${API_BASE_URL}/log`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            level: level,
            message: message,
            context: context
        })
    }).catch(error => {
        console.error('Error sending log to backend:', error);
    });
}

// WebSocket connection setup
function setupWebSocket() {
    const socket = new WebSocket(WS_URL);
    
    socket.onopen = function(e) {
        console.log("WebSocket connection established");
        logToBackend('info', 'WebSocket connection established');
    };
    
    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log("WebSocket message received:", data);
        
        // Handle different message types
        if (data.type === 'card_inserted') {
            handleCardEvent(data);
        } else if (data.type === 'card_removed') {
            updateCardStatus(null);
        }
    };
    
    socket.onclose = function(event) {
        if (event.wasClean) {
            console.log(`WebSocket connection closed cleanly, code=${event.code}, reason=${event.reason}`);
        } else {
            console.error('WebSocket connection died');
            logToBackend('error', 'WebSocket connection died');
        }
        // Try to reconnect after a delay
        setTimeout(setupWebSocket, 5000);
    };
    
    socket.onerror = function(error) {
        console.error(`WebSocket error: ${error.message}`);
        logToBackend('error', `WebSocket error: ${error.message}`);
    };
    
    return socket;
}

document.addEventListener('DOMContentLoaded', function() {
    const socket = setupWebSocket();
    console.log('DOM loaded, Bootstrap:', typeof bootstrap !== 'undefined' ? 'Loaded' : 'Not loaded');

    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap not loaded. Tab functionality will fail.');
        return;
    }

    // Tab initialization with error handling
    document.addEventListener('DOMContentLoaded', function() {
        let tabTriggerList = document.querySelectorAll('.nav-link[data-bs-toggle="tab"]');
        tabTriggerList.forEach(tabTriggerEl => {
            tabTriggerEl.addEventListener('click', function(event) {
                event.preventDefault();
                let tab = new bootstrap.Tab(this);
                tab.show();
            });
        });
    });

    document.querySelectorAll('.nav-link[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', (e) => {
            const targetId = e.target.getAttribute('href');
            console.log('Tab shown:', targetId);
            if (targetId === '#smartcard') {
                listReaders();
            } else if (targetId === '#nfc') {
                document.getElementById('discover-nfc')?.click();
            } else if (targetId === '#mifare-classic') {
                populateMifareSelectors();
                createMemoryMap();
            } else if (targetId === '#mifare-desfire') {
                fetchDESFireApplications();
            } else if (targetId === '#javacard') {
                loadJavaCardApplets();
            } else if (targetId === '#emv') {
                loadEMVPresets();
            }
        });
    });

    // Core functions
    function fadeIn(element) {
        element.classList.add('fade-in');
    }

    function displayResult(elementId, data) {
        const element = document.getElementById(elementId);
        element.classList.remove('fade-in');
        setTimeout(() => {
            element.innerHTML = data.status === 'error' ? 
                `<span class="text-danger">${escapeHtml(data.message)}</span>` : 
                `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            fadeIn(element);
        }, 50);
    }

    function addToHistory(listId, command) {
        const list = document.getElementById(listId);
        const item = document.createElement('li');
        item.className = 'list-group-item command-item';
        item.textContent = command;
        item.addEventListener('click', () => document.getElementById('apdu-command').value = command);
        list.insertBefore(item, list.firstChild);
        while (list.children.length > 10) list.removeChild(list.lastChild);
        saveHistory(listId);
    }

    function saveHistory(listId) {
        const commands = Array.from(document.getElementById(listId).children).map(item => item.textContent);
        localStorage.setItem(listId, JSON.stringify(commands));
    }

    function loadHistory(listId) {
        const list = document.getElementById(listId);
        JSON.parse(localStorage.getItem(listId) || '[]').forEach(command => {
            const item = document.createElement('li');
            item.className = 'list-group-item command-item';
            item.textContent = command;
            item.addEventListener('click', () => document.getElementById('apdu-command').value = command);
            list.appendChild(item);
        });
    }

    loadHistory('sc-command-history');

    function listReaders() {
        fetch(`${API_BASE_URL}/smartcard/readers`)
            .then(response => response.json())
            .then(response => {
                displayResult('smartcard-result', response);
                updateReaderSelect(response.data);
            })
            .catch(error => {
                displayResult('smartcard-result', { status: 'error', message: error.message });
            });
    }

    function updateReaderSelect(data) {
        console.log('Updating reader dropdown with:', data);
        const readerSelect = document.getElementById('reader-select');
        readerSelect.innerHTML = ''; // Clear existing options
    
        if (data && data.readers && Array.isArray(data.readers)) {
            data.readers.forEach(reader => {
                let option = document.createElement('option');
                option.value = reader.name;
                option.textContent = `${reader.name} (${reader.type})`;
                readerSelect.appendChild(option);
            });
        } else {
            readerSelect.innerHTML = '<option>No readers found</option>';
        }
    }

    function escapeHtml(string) {
        const entityMap = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '/': '&#x2F;'};
        return String(string).replace(/[&<>"'/]/g, s => entityMap[s]);
    }

    // Expose functions globally for inline handlers
    window.toggleSimulationMode = function() {
        const simulationMode = document.getElementById('simulation-mode').checked;
        fetch(`${API_BASE_URL}/toggle_simulation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: simulationMode })
        })
            .then(response => response.json())
            .then(data => {
                alert(`Simulation mode ${simulationMode ? 'enabled' : 'disabled'}. Please restart the application for changes to take effect.`);
            })
            .catch(error => {
                console.error('Error toggling simulation mode:', error);
            });
    };

    window.loadApduTemplate = function() {
        const template = document.getElementById('apdu-template').value;
        if (template) {
            document.getElementById('apdu-command').value = template.replace(/(.{2})/g, "$1 ").trim();
        }
    };

    // Event listeners
    document.getElementById('smartcard-tab')?.addEventListener('shown.bs.tab', function() {
        listReaders();
    });

    document.getElementById('list-readers')?.addEventListener('click', listReaders);

    document.getElementById('get-atr')?.addEventListener('click', async () => {
        const readerIndex = document.getElementById('reader-select').value;
        try {
            const response = await fetch(`${API_BASE_URL}/smartcard/atr?reader=${readerIndex}`);
            const data = await response.json();
            displayResult('smartcard-result', data);
        } catch (error) {
            displayResult('smartcard-result', { status: 'error', message: error.message });
        }
    });

    document.getElementById('card-status')?.addEventListener('click', async () => {
        const readerIndex = document.getElementById('reader-select').value;
        try {
            const response = await fetch(`${API_BASE_URL}/smartcard/detect?reader=${readerIndex}`);
            const data = await response.json();
            displayCardStatus(data);
        } catch (error) {
            displayResult('smartcard-result', { status: 'error', message: error.message });
        }
    });

    function displayCardStatus(data) {
        const cardStatusDisplay = document.getElementById('card-status-display');
        if (data.status === 'success') {
            cardStatusDisplay.innerHTML = data.data.present ? 
                '<span class="text-success">Card Present</span>' : 
                '<span class="text-warning">No Card Present</span>';
        } else {
            cardStatusDisplay.innerHTML = `<span class="text-danger">${escapeHtml(data.message)}</span>`;
        }
    }

    document.getElementById('send-apdu')?.addEventListener('click', async () => {
        const readerIndex = document.getElementById('reader-select').value;
        const apdu = document.getElementById('apdu-command').value;
        try {
            const response = await fetch(`${API_BASE_URL}/smartcard/transmit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reader: readerIndex, apdu: apdu })
            });
            const data = await response.json();
            displayResult('smartcard-result', data);
        } catch (error) {
            displayResult('smartcard-result', { status: 'error', message: error.message });
        }
    });

    document.getElementById('discover-nfc')?.addEventListener('click', async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/nfc/discover`);
            const data = await response.json();
            displayResult('nfc-result', data);
        } catch (error) {
            displayResult('nfc-result', { status: 'error', message: error.message });
        }
    });

    document.getElementById('read-nfc')?.addEventListener('click', async () => {
        displayResult('nfc-result', { status: 'info', message: 'Waiting for tag...' });
        try {
            const response = await fetch(`${API_BASE_URL}/nfc/read`);
            const data = await response.json();
            displayResult('nfc-result', data);
        } catch (error) {
            displayResult('nfc-result', { status: 'error', message: error.message });
        }
    });

    document.getElementById('write-nfc-text')?.addEventListener('click', async () => {
        const text = document.getElementById('nfc-text').value;
        displayResult('nfc-result', { status: 'info', message: 'Waiting for tag...' });
        try {
            const response = await fetch(`${API_BASE_URL}/nfc/write_text`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            const data = await response.json();
            displayResult('nfc-result', data);
        } catch (error) {
            displayResult('nfc-result', { status: 'error', message: error.message });
        }
    });

    document.getElementById('write-nfc-uri')?.addEventListener('click', async () => {
        const uri = document.getElementById('nfc-uri').value;
        displayResult('nfc-result', { status: 'info', message: 'Waiting for tag...' });
        try {
            const response = await fetch(`${API_BASE_URL}/nfc/write_uri`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ uri })
            });
            const data = await response.json();
            displayResult('nfc-result', data);
        } catch (error) {
            displayResult('nfc-result', { status: 'error', message: error.message });
        }
    });

    // Poll for card detection
    let lastActiveReader = null; // Store the last detected reader
    let autoDetectEnabled = document.getElementById('autodetect-reader').checked;
    
    setInterval(async () => {
        if (!autoDetectEnabled) return; // Skip polling if auto-detect is off
    
        try {
            const response = await fetch(`${API_BASE_URL}/smartcard/detect`);
            const data = await response.json();
    
            if (data.data && data.data.active_reader !== null && data.data.active_reader !== lastActiveReader) {
                lastActiveReader = data.data.active_reader;
                document.getElementById('reader-select').value = lastActiveReader; 
                console.log(`Auto-selected reader: ${lastActiveReader}`);
            }
        } catch (error) {
            console.error('Smartcard detect error:', error);
        }
    }, 2000);
    // Copy result to clipboard
    document.getElementById('copy-result')?.addEventListener('click', function() {
        const resultText = document.getElementById('smartcard-result').innerText;
        copyToClipboard(resultText);
        showToast('Result copied to clipboard');
    });

    document.getElementById('copy-nfc-result')?.addEventListener('click', function() {
        const resultText = document.getElementById('nfc-result').innerText;
        copyToClipboard(resultText);
        showToast('Result copied to clipboard');
    });

    // Clear result boxes
    document.getElementById('clear-result')?.addEventListener('click', function() {
        document.getElementById('smartcard-result').innerText = 'Results will appear here...';
    });

    document.getElementById('clear-nfc-result')?.addEventListener('click', function() {
        document.getElementById('nfc-result').innerText = 'Results will appear here...';
    });

    // Clear command history
    document.getElementById('clear-history')?.addEventListener('click', function() {
        const list = document.getElementById('sc-command-history');
        list.innerHTML = '';
        saveHistory('sc-command-history');
    });

    // Format switching for results
    document.querySelectorAll('input[name="result-format"]')?.forEach(radio => {
        radio.addEventListener('change', function() {
            const resultElement = document.getElementById('smartcard-result');
            const resultText = resultElement.innerText;
            try {
                const resultData = JSON.parse(resultText);
                
                if (this.id === 'format-json') {
                    resultElement.innerText = JSON.stringify(resultData, null, 2);
                } else if (this.id === 'format-hex') {
                    if (resultData.response) {
                        resultElement.innerText = resultData.response.replace(/\s/g, '');
                    }
                } else if (this.id === 'format-ascii') {
                    if (resultData.response) {
                        const hexStr = resultData.response.replace(/\s/g, '');
                        resultElement.innerText = hexToAscii(hexStr);
                    }
                }
            } catch (e) {
                console.error('Error formatting result:', e);
            }
        });
    });

    function copyToClipboard(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
    }

    function showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.innerText = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => {
                    document.body.removeChild(toast);
                }, 300);
            }, 2000);
        }, 100);
    }

    function hexToAscii(hexString) {
        let ascii = '';
        for (let i = 0; i < hexString.length; i += 2) {
            const hex = hexString.substr(i, 2);
            const decimal = parseInt(hex, 16);
            ascii += (decimal >= 32 && decimal <= 126) ? String.fromCharCode(decimal) : '.';
        }
        return ascii;
    }

    // APDU Script execution
    document.getElementById('run-script')?.addEventListener('click', async function() {
        const script = document.getElementById('apdu-script').value;
        const readerIndex = document.getElementById('reader-select').value;
        
        document.getElementById('smartcard-result').innerText = 'Running script...';
        
        const commands = script
            .split('\n')
            .map(line => line.trim())
            .filter(line => line && !line.startsWith('#'));
        
        let results = [];
        
        for (const command of commands) {
            try {
                const response = await fetch(`${API_BASE_URL}/smartcard/transmit`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reader: readerIndex, apdu: command })
                });
                
                const data = await response.json();
                results.push({ command, response: data });
                addToHistory('sc-command-history', command);
            } catch (error) {
                results.push({ command, error: error.message });
            }
        }
        
        displayResult('smartcard-result', { 
            status: 'success', 
            script_results: results 
        });
    });

    // Save APDU script
    document.getElementById('save-script')?.addEventListener('click', function() {
        const script = document.getElementById('apdu-script').value;
        const scriptName = prompt('Enter a name for this script:');
        
        if (scriptName) {
            const scripts = JSON.parse(localStorage.getItem('apdu-scripts') || '{}');
            scripts[scriptName] = script;
            localStorage.setItem('apdu-scripts', JSON.stringify(scripts));
            showToast(`Script saved as "${scriptName}"`);
        }
    });

    // Load APDU script
    document.getElementById('load-script')?.addEventListener('click', function() {
        const scripts = JSON.parse(localStorage.getItem('apdu-scripts') || '{}');
        const scriptNames = Object.keys(scripts);
        
        if (scriptNames.length === 0) {
            alert('No saved scripts found');
            return;
        }
        
        const select = document.createElement('select');
        select.className = 'form-select mb-3';
        
        scriptNames.forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            select.appendChild(option);
        });
        
        const div = document.createElement('div');
        div.appendChild(select);
        
        const loadDialog = confirm => {
            const selectedScript = scripts[select.value];
            if (selectedScript && confirm) {
                document.getElementById('apdu-script').value = selectedScript;
                showToast(`Loaded script "${select.value}"`);
            }
        };
        
        const modal = createModal('Load Script', div, loadDialog);
        document.body.appendChild(modal);
        modal.style.display = 'block';
    });

    function createModal(title, content, callback) {
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        
        const dialog = document.createElement('div');
        dialog.className = 'modal-dialog';
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        
        const modalHeader = document.createElement('div');
        modalHeader.className = 'modal-header';
        
        const modalTitle = document.createElement('h5');
        modalTitle.className = 'modal-title';
        modalTitle.textContent = title;
        
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        modalHeader.appendChild(modalTitle);
        modalHeader.appendChild(closeButton);
        
        const modalBody = document.createElement('div');
        modalBody.className = 'modal-body';
        modalBody.appendChild(content);
        
        const modalFooter = document.createElement('div');
        modalFooter.className = 'modal-footer';
        
        const cancelButton = document.createElement('button');
        cancelButton.type = 'button';
        cancelButton.className = 'btn btn-secondary';
        cancelButton.textContent = 'Cancel';
        cancelButton.addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        const confirmButton = document.createElement('button');
        confirmButton.type = 'button';
        confirmButton.className = 'btn btn-primary';
        confirmButton.textContent = 'Load';
        confirmButton.addEventListener('click', () => {
            callback(true);
            document.body.removeChild(modal);
        });
        
        modalFooter.appendChild(cancelButton);
        modalFooter.appendChild(confirmButton);
        
        modalContent.appendChild(modalHeader);
        modalContent.appendChild(modalBody);
        modalContent.appendChild(modalFooter);
        
        dialog.appendChild(modalContent);
        modal.appendChild(dialog);
        
        return modal;
    }

    // NFC vCard writing
    document.getElementById('write-nfc-vcard')?.addEventListener('click', async function() {
        const name = document.getElementById('vcard-name').value;
        const org = document.getElementById('vcard-org').value;
        const email = document.getElementById('vcard-email').value;
        const phone = document.getElementById('vcard-phone').value;
        
        if (!name) {
            alert('Please enter at least a name');
            return;
        }
        
        displayResult('nfc-result', { status: 'info', message: 'Waiting for tag...' });
        
        try {
            const response = await fetch(`${API_BASE_URL}/nfc/write_vcard`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, org, email, phone })
            });
            
            const data = await response.json();
            displayResult('nfc-result', data);
        } catch (error) {
            displayResult('nfc-result', { status: 'error', message: error.message });
        }
    });

    // NFC raw record writing
    document.getElementById('write-nfc-raw')?.addEventListener('click', async function() {
        const recordType = document.getElementById('nfc-raw-type').value;
        const payload = document.getElementById('nfc-raw-payload').value;
        
        if (!recordType || !payload) {
            alert('Please enter both record type and payload');
            return;
        }
        
        displayResult('nfc-result', { status: 'info', message: 'Waiting for tag...' });
        
        try {
            const response = await fetch(`${API_BASE_URL}/nfc/write_raw`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ record_type: recordType, payload: payload })
            });
            
            const data = await response.json();
            displayResult('nfc-result', data);
        } catch (error) {
            displayResult('nfc-result', { status: 'error', message: error.message });
        }
    });

    // Tag emulation mode
    document.getElementById('emulate-tag')?.addEventListener('click', async function() {
        try {
            const response = await fetch(`${API_BASE_URL}/nfc/emulate`, {
                method: 'POST'
            });
            
            const data = await response.json();
            displayResult('nfc-result', data);
        } catch (error) {
            displayResult('nfc-result', { status: 'error', message: error.message });
        }
    });

    // P2P mode
    document.getElementById('p2p-mode')?.addEventListener('click', async function() {
        try {
            const response = await fetch(`${API_BASE_URL}/nfc/p2p`, {
                method: 'POST'
            });
            
            const data = await response.json();
            displayResult('nfc-result', data);
        } catch (error) {
            displayResult('nfc-result', { status: 'error', message: error.message });
        }
    });

    // Save and load tag data
    document.getElementById('save-tag-data')?.addEventListener('click', function() {
        const tagData = {
            type: document.getElementById('tag-type').textContent,
            uid: document.getElementById('tag-uid').textContent,
            size: document.getElementById('tag-size').textContent,
            tech: document.getElementById('tag-tech').textContent,
            result: document.getElementById('nfc-result').innerText
        };
        
        const tagName = prompt('Enter a name for this tag data:');
        
        if (tagName) {
            const savedTags = JSON.parse(localStorage.getItem('saved-nfc-tags') || '{}');
            savedTags[tagName] = tagData;
            localStorage.setItem('saved-nfc-tags', JSON.stringify(savedTags));
            showToast(`Tag data saved as "${tagName}"`);
        }
    });

    document.getElementById('load-tag-data')?.addEventListener('click', function() {
        const savedTags = JSON.parse(localStorage.getItem('saved-nfc-tags') || '{}');
        const tagNames = Object.keys(savedTags);
        
        if (tagNames.length === 0) {
            alert('No saved tag data found');
            return;
        }
        
        const select = document.createElement('select');
        select.className = 'form-select mb-3';
        
        tagNames.forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            select.appendChild(option);
        });
        
        const div = document.createElement('div');
        div.appendChild(select);
        
        const loadDialog = confirm => {
            if (confirm) {
                const tagData = savedTags[select.value];
                document.getElementById('tag-type').textContent = tagData.type;
                document.getElementById('tag-uid').textContent = tagData.uid;
                document.getElementById('tag-size').textContent = tagData.size;
                document.getElementById('tag-tech').textContent = tagData.tech;
                document.getElementById('nfc-result').innerText = tagData.result;
                showToast(`Loaded tag data "${select.value}"`);
            }
        };
        
        const modal = createModal('Load Tag Data', div, loadDialog);
        document.body.appendChild(modal);
        modal.style.display = 'block';
    });

    // Populate MIFARE sector and block dropdowns
    function populateMifareSelectors() {
        const sectorSelect = document.getElementById('mifare-sector');
        const blockSelect = document.getElementById('mifare-block');
        
        sectorSelect.innerHTML = '';
        
        for (let i = 0; i < 16; i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = `Sector ${i}`;
            sectorSelect.appendChild(option);
        }
        
        updateMifareBlockSelector();
        
        sectorSelect.addEventListener('change', updateMifareBlockSelector);
    }

    function updateMifareBlockSelector() {
        const sectorSelect = document.getElementById('mifare-sector');
        const blockSelect = document.getElementById('mifare-block');
        const sector = parseInt(sectorSelect.value);
        
        blockSelect.innerHTML = '';
        
        const startBlock = sector * 4;
        for (let i = 0; i < 4; i++) {
            const blockNumber = startBlock + i;
            const option = document.createElement('option');
            option.value = blockNumber;
            option.textContent = `Block ${blockNumber}${i === 3 ? ' (Trailer)' : ''}`;
            blockSelect.appendChild(option);
        }
    }

    // MIFARE operations
    document.getElementById('mifare-auth')?.addEventListener('click', async function() {
        const sector = document.getElementById('mifare-sector').value;
        const keyType = document.getElementById('mifare-key-type').value;
        const key = document.getElementById('mifare-key').value;
        
        if (!key || key.length !== 12) {
            alert('Please enter a valid 6-byte key (12 hex characters)');
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/mifare/auth`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sector, key_type: keyType, key })
            });
            
            const data = await response.json();
            displayResult('smartcard-result', data);
        } catch (error) {
            displayResult('smartcard-result', { status: 'error', message: error.message });
        }
    });

    document.getElementById('mifare-read')?.addEventListener('click', async function() {
        const block = document.getElementById('mifare-block').value;
        
        try {
            const response = await fetch(`${API_BASE_URL}/mifare/read_block?block=${block}`);
            const data = await response.json();
            displayResult('smartcard-result', data);
            
            if (data.status === 'success' && data.data) {
                document.getElementById('mifare-data').value = data.data.replace(/\s/g, '');
                updateMemoryMapDisplay(block, data.data);
            }
        } catch (error) {
            displayResult('smartcard-result', { status: 'error', message: error.message });
        }
    });

    document.getElementById('mifare-write')?.addEventListener('click', async function() {
        const block = document.getElementById('mifare-block').value;
        const data = document.getElementById('mifare-data').value;
        
        if (!data || data.length !== 32) {
            alert('Please enter valid 16-byte data (32 hex characters)');
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/mifare/write_block`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ block, data })
            });
            
            const result = await response.json();
            displayResult('smartcard-result', result);
            
            if (result.status === 'success') {
                updateMemoryMapDisplay(block, data);
            }
        } catch (error) {
            displayResult('smartcard-result', { status: 'error', message: error.message });
        }
    });

    // Create MIFARE memory map display
    function createMemoryMap() {
        const container = document.getElementById('mifare-memory-map');
        container.innerHTML = '';
        
        for (let sector = 0; sector < 16; sector++) {
            const sectorDiv = document.createElement('div');
            sectorDiv.className = 'memory-sector';
            
            const sectorHeader = document.createElement('div');
            sectorHeader.className = 'sector-header';
            sectorHeader.textContent = `Sector ${sector}`;
            sectorDiv.appendChild(sectorHeader);
            
            const startBlock = sector * 4;
            for (let i = 0; i < 4; i++) {
                const blockNumber = startBlock + i;
                const blockDiv = document.createElement('div');
                blockDiv.className = 'memory-block';
                blockDiv.id = `block-${blockNumber}`;
                blockDiv.innerHTML = `<span class="block-number">Block ${blockNumber}:</span> <span class="block-data">????????????????????????????????</span>`;
                
                if (i === 3) {
                    blockDiv.classList.add('sector-trailer');
                }
                
                blockDiv.addEventListener('click', () => {
                    document.getElementById('mifare-sector').value = sector;
                    updateMifareBlockSelector();
                    document.getElementById('mifare-block').value = blockNumber;
                });
                
                sectorDiv.appendChild(blockDiv);
            }
            
            container.appendChild(sectorDiv);
        }
    }

    function updateMemoryMapDisplay(block, data) {
        const blockElement = document.getElementById(`block-${block}`);
        if (blockElement) {
            const dataDisplay = blockElement.querySelector('.block-data');
            dataDisplay.textContent = data.replace(/\s/g, '').match(/.{2}/g).join(' ');
            
            blockElement.classList.add('updated');
            setTimeout(() => blockElement.classList.remove('updated'), 1000);
        }
    }

    // Placeholder functions for other card types
    function fetchDESFireApplications() {
        console.log('Fetching DESFire applications...');
    }

    function loadJavaCardApplets() {
        console.log('Loading JavaCard applets...');
    }

    function loadEMVPresets() {
        console.log('Loading EMV presets...');
    }

    // Test reader connection
    function testReaderConnection() {
        const readerIndex = document.getElementById('reader-select').value;
        fetch(`${API_BASE_URL}/smartcard/test_reader?reader=${readerIndex}`)
            .then(response => response.json())
            .then(data => {
                displayResult('smartcard-result', data);
                if (data.status === 'success') {
                    showToast(`Reader ${readerIndex} is functional`);
                } else {
                    showToast(`Reader ${readerIndex} test failed: ${data.message}`);
                }
            })
            .catch(error => {
                displayResult('smartcard-result', { status: 'error', message: error.message });
            });
    }

    document.getElementById('test-reader')?.addEventListener('click', testReaderConnection);

    // Socket.IO error handling
    socket.on('connect_error', (error) => {
        console.error('Socket.IO connection error:', error);
        showToast('Failed to connect to server. Please check if it’s running.');
    });

     // Add CSS styles (previously in a separate DOMContentLoaded listener)
     const style = document.createElement('style');
     style.textContent = `
         .modal {
             position: fixed;
             top: 0;
             left: 0;
             width: 100%;
             height: 100%;
             z-index: 1050;
             display: none;
         }
         .toast-notification {
             position: fixed;
             bottom: 20px;
             right: 20px;
             background: rgba(0,0,0,0.8);
             color: white;
             padding: 10px 20px;
             border-radius: 4px;
             z-index: 1100;
             transform: translateY(100px);
             opacity: 0;
             transition: transform 0.3s, opacity 0.3s;
         }
         .toast-notification.show {
             transform: translateY(0);
             opacity: 1;
         }
         .memory-sector {
             margin-bottom: 10px;
             border: 1px solid #dee2e6;
             border-radius: 4px;
         }
         .sector-header {
             background-color: #f8f9fa;
             padding: 5px 10px;
             font-weight: bold;
             border-bottom: 1px solid #dee2e6;
         }
         .memory-block {
             padding: 5px 10px;
             cursor: pointer;
             transition: background-color 0.2s;
         }
         .memory-block:hover {
             background-color: #f1f3f5;
         }
         .sector-trailer {
             background-color: #fff3cd;
         }
         .memory-block.updated .block-data {
             color: #28a745;
             font-weight: bold;
         }
         .block-number {
             display: inline-block;
             width: 70px;
         }
         .block-data {
             font-family: monospace;
         }
         .fade-in {
             animation: fadeIn 0.3s;
         }
         @keyframes fadeIn {
             from { opacity: 0; }
             to { opacity: 1; }
         }
         .command-item {
             cursor: pointer;
             transition: background-color 0.2s;
         }
         .command-item:hover {
             background-color: #f8f9fa;
         }
     `;
     document.head.appendChild(style);
 
     // Socket.IO event listeners for real-time updates (if applicable)
     socket.on('smartcard_event', (data) => {
         console.log('Smartcard event received:', data);
         displayResult('smartcard-result', data);
     });
 
     socket.on('nfc_event', (data) => {
         console.log('NFC event received:', data);
         displayResult('nfc-result', data);
     });
 
     // Cleanup on page unload (optional)
     window.addEventListener('beforeunload', () => {
         socket.disconnect();
     });

     // Autodetect toggle
     document.getElementById('autodetect-reader').addEventListener('change', function() {
         const autodetectEnabled = this.checked;
         if (autodetectEnabled) {
             startAutodetection();
         } else {
             stopAutodetection();
         }
     });
 
     let autodetectionInterval;
 
     function startAutodetection() {
         console.log('Autodetection started');
         autodetectionInterval = setInterval(checkCardStatus, 2000); // Check every 2 seconds
     }
 
     function stopAutodetection() {
         console.log('Autodetection stopped');
         clearInterval(autodetectionInterval);
     }
 
     async function checkCardStatus() {
         const readerIndex = document.getElementById('reader-select').value;
         try {
             const response = await fetch(`${API_BASE_URL}/smartcard/card_status?reader=${readerIndex}`);
             const data = await response.json();
             if (data.status === 'success') {
                 if (data.present) {
                     console.log('Card detected in reader ' + readerIndex);
                     showToast('Card detected in reader ' + readerIndex);
                 } else {
                     console.log('Card removed from reader ' + readerIndex);
                     showToast('Card removed from reader ' + readerIndex);
                 }
             } else {
                 console.error('Error checking card status:', data.message);
             }
         } catch (error) {
             console.error('Error checking card status:', error);
         }
     }

     document.getElementById('refresh-readers').addEventListener('click', listReaders);

     // Load autodetect state from local storage
     const autodetectState = localStorage.getItem('autodetect');
     const autodetectCheckbox = document.getElementById('autodetect-reader');
 
     if (autodetectState === 'true') {
         autodetectCheckbox.checked = true;
         startAutodetection();
     } else {
         autodetectCheckbox.checked = false;
     }
 
     autodetectCheckbox.addEventListener('change', function() {
         const autodetectEnabled = this.checked;
         localStorage.setItem('autodetect', autodetectEnabled); // Save state to local storage
         if (autodetectEnabled) {
             startAutodetection();
         } else {
             stopAutodetection();
         }
     });
 });

window.onerror = function(message, source, lineno, colno, error) {
    logToBackend('error', message, source, lineno, colno, error);
};

console.error = (function(original) {
    return function(message) {
        logToBackend('console.error', message);
        original.apply(console, arguments);
    }
})(console.error);

console.warn = (function(original) {
    return function(message) {
        logToBackend('console.warn', message);
        original.apply(console, arguments);
    }
})(console.warn);

function logToBackend(type, message, source = null, lineno = null, colno = null, error = null) {
    fetch(`${API_BASE_URL}/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            type: type,
            message: message,
            source: source,
            lineno: lineno,
            colno: colno,
            error: error ? error.stack : null
        })
    }).catch(error => console.error('Failed to send log to backend:', error));
}

let selectedReader = null;
let autodetectEnabled = false;

// Function to update the reader select dropdown
document.getElementById('list-readers').addEventListener('click', async function() {
    try {
        const response = await fetch(`${API_BASE_URL}/smartcard/readers`);
        const data = await response.json();
        updateReaderSelect(data.data);
    } catch (error) {
        console.error('Error refreshing readers:', error);
    }
});

function updateReaderSelect(data) {
    const readerSelect = document.getElementById('reader-select');
    readerSelect.innerHTML = ''; // Clear existing entries

    if (data && data.readers && Array.isArray(data.readers)) {
        data.readers.forEach(reader => {
            const option = document.createElement('option');
            option.value = reader.name;
            option.textContent = `${reader.name} (${reader.type})`;
            readerSelect.appendChild(option);
        });
    } else {
        const noReaderOption = document.createElement('option');
        noReaderOption.textContent = 'No readers found';
        readerSelect.appendChild(noReaderOption);
    }
}

// Function to fetch the list of readers from the backend
async function fetchReaders() {
    try {
        const response = await fetch(`${API_BASE_URL}/readers`);
        const data = await response.json();
        if (data.status === 'success') {
            updateReaderSelect(data.readers);
            selectedReader = data.selected_reader;
            if (selectedReader) {
                document.getElementById('reader-select').value = selectedReader;
            }
        } else {
            console.error('Error fetching readers:', data.message);
        }
    } catch (error) {
        console.error('Error fetching readers:', error);
    }
}

// Function to handle manual reader selection
function selectReader() {
    const readerSelect = document.getElementById('reader-select');
    const readerName = readerSelect.value;
    fetch(`${API_BASE_URL}/select_reader`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reader: readerName })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            selectedReader = readerName;
            console.log('Selected reader:', selectedReader);
        } else {
            console.error('Error selecting reader:', data.message);
        }
    })
    .catch(error => {
        console.error('Error selecting reader:', error);
    });
}

// Event listener for manual reader selection
document.getElementById('reader-select')?.addEventListener('change', function() {
    fetch(`${API_BASE_URL}/smartcard/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reader: this.value })
    }).then(response => response.json())
      .then(data => console.log(`Reader selected: ${data.message}`))
      .catch(error => console.error('Error selecting reader:', error));
});


// Function to handle card detection events
function handleCardEvent(readerName) {
    fetch(`${API_BASE_URL}/card_event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reader: readerName })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            selectedReader = data.selected_reader;
            document.getElementById('reader-select').value = selectedReader;
            console.log('Card detected on reader:', selectedReader);
        } else {
            console.error('Error handling card event:', data.message);
        }
    })
    .catch(error => {
        console.error('Error handling card event:', error);
    });
}

// Autodetect toggle
document.getElementById('autodetect-reader').addEventListener('change', function() {
    autodetectEnabled = this.checked;
    if (autodetectEnabled) {
        startAutodetection();
    } else {
        stopAutodetection();
    }
});

let autodetectionInterval;

function startAutodetection() {
    console.log('Autodetection started');
    autodetectionInterval = setInterval(checkCardStatus, 2000); // Check every 2 seconds
}

function stopAutodetection() {
    console.log('Autodetection stopped');
    clearInterval(autodetectionInterval);
}

async function checkCardStatus() {
    if (selectedReader && !autodetectEnabled) {
        return; // Do not check if a reader is manually selected and autodetect is disabled
    }
    try {
        const response = await fetch(`${API_BASE_URL}/readers`);
        const data = await response.json();
        if (data.status === 'success') {
            const readers = data.readers;
            if (readers && readers.length > 0) {
                for (const reader of readers) {
                    const readerName = reader.name;
                    const cardStatusResponse = await fetch(`${API_BASE_URL}/smartcard/card_status?reader=${readerName}`);
                    const cardStatusData = await cardStatusResponse.json();
                    if (cardStatusData.status === 'success') {
                        if (cardStatusData.present) {
                            handleCardEvent(readerName);
                            stopAutodetection(); // Stop autodetect after card is detected
                            break; // Exit loop after detecting a card
                        }
                    } else {
                        console.error('Error checking card status:', cardStatusData.message);
                    }
                }
            }
        } else {
            console.error('Error fetching readers:', data.message);
        }
    } catch (error) {
        console.error('Error checking card status:', error);
    }
}

// Event listener for refresh readers button
document.getElementById('refresh-readers').addEventListener('click', fetchReaders);

// Initial fetch of readers on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    fetchReaders();
});
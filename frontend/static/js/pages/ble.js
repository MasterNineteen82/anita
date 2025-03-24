// ble.js
document.addEventListener('DOMContentLoaded', () => {
    console.log("BLE Manager initializing...");

    // DOM element references
    const scanBtn = document.getElementById('scan-btn');
    const deviceList = document.getElementById('device-list');
    const statusIndicatorContainer = document.getElementById('status-indicator-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const disconnectBtn = document.getElementById('disconnect-btn');
    const logContainer = document.getElementById('ble-log-container');
    const clearLogBtn = document.getElementById('clear-log-btn');
    const showDebugBtn = document.getElementById('show-debug');
    const debugPanel = document.getElementById('debug-panel');
    const debugToggleBtn = document.getElementById('debug-toggle');
    const debugSendBtn = document.getElementById('debug-send');
    const debugEndpointSelect = document.getElementById('debug-endpoint');
    const debugResponseContainer = document.getElementById('debug-response');
    const scanStatus = document.getElementById('scan-status');
    const servicesList = document.getElementById('services-list');
    const characteristicsList = document.getElementById('characteristics-list');
    const notificationsContainer = document.getElementById('notifications-container');

    // Connection state
    let connectedDevice = null;
    let websocket = null;
    let subscribedCharacteristics = new Set();

    // WebSocket connection
    let socket;

    function connectWebSocket() {
        try {
            socket = new WebSocket(`ws://${window.location.host}/api/ble/ws/ble`);
            
            socket.onopen = () => {
                logMessage('WebSocket connected', 'success');
                console.log('WebSocket connected');
            };
            
            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                    logMessage(`Error parsing WebSocket message: ${error.message}`, 'error');
                }
            };
            
            socket.onclose = () => {
                logMessage('WebSocket disconnected', 'info');
                console.log('WebSocket disconnected');
                // Try to reconnect after a delay
                setTimeout(connectWebSocket, 5000);
            };
            
            socket.onerror = (error) => {
                logMessage(`WebSocket error: ${error.message}`, 'error');
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('Error connecting to WebSocket:', error);
            logMessage(`Error connecting to WebSocket: ${error.message}`, 'error');
        }
    }

    function handleWebSocketMessage(data) {
        console.log('WebSocket message received:', data);
        
        switch (data.type) {
            case 'ble.characteristic':
                handleCharacteristicNotification(data);
                break;
            case 'ble.characteristic_subscription':
                handleSubscriptionStatus(data);
                break;
            case 'error':
                logMessage(`WebSocket Error: ${data.message}`, 'error');
                break;
            default:
                console.log('Unknown WebSocket message type:', data.type);
        }
    }

    function handleCharacteristicNotification(data) {
        // Display the notification in the UI
        const { characteristic, value, value_hex } = data;
        
        // Create notification element
        const notificationEl = document.createElement('div');
        notificationEl.className = 'notification-item bg-gray-700 p-2 rounded mb-2';
        notificationEl.innerHTML = `
            <div class="flex justify-between items-center">
                <span class="text-xs font-mono text-cyan">${characteristic}</span>
                <span class="text-xs text-gray-400">${new Date().toLocaleTimeString()}</span>
            </div>
            <div class="mt-1 text-sm font-mono break-all">${value_hex}</div>
        `;
        
        // Add to notifications container
        if (notificationsContainer) {
            notificationsContainer.prepend(notificationEl);
            
            // Limit number of displayed notifications to prevent UI clutter
            if (notificationsContainer.children.length > 10) {
                notificationsContainer.removeChild(notificationsContainer.lastChild);
            }
        }
        
        // Also log to console
        logMessage(`Notification from ${characteristic}: ${value_hex}`, 'info');
    }

    function handleSubscriptionStatus(data) {
        const { char_uuid, status } = data;
        logMessage(`Characteristic ${char_uuid} ${status}`, status === 'subscribed' ? 'success' : 'info');
        
        // Update UI to show subscription status
        updateSubscriptionStatus(char_uuid, status === 'subscribed');
    }

    // Toggle notifications for a characteristic
    async function toggleNotification(charUuid, button) {
        try {
            const isSubscribed = button.dataset.subscribed === 'true';
            
            if (isSubscribed) {
                // Unsubscribe
                socket.send(JSON.stringify({
                    action: 'unsubscribe_from_characteristic',
                    data: { char_uuid: charUuid }
                }));
            } else {
                // Subscribe
                socket.send(JSON.stringify({
                    action: 'subscribe_to_characteristic',
                    data: { char_uuid: charUuid }
                }));
            }
            
            // The UI update will happen when the server confirms the subscription
        } catch (error) {
            console.error('Error toggling notification:', error);
            logMessage(`Error toggling notification: ${error.message}`, 'error');
        }
    }

    // Update subscription status in UI
    function updateSubscriptionStatus(charUuid, isSubscribed) {
        const button = document.querySelector(`[data-char-uuid="${charUuid}"]`);
        if (button) {
            button.dataset.subscribed = isSubscribed.toString();
            button.innerHTML = isSubscribed 
                ? '<i class="fas fa-bell-slash"></i>' 
                : '<i class="fas fa-bell"></i>';
            button.title = isSubscribed ? 'Unsubscribe from notifications' : 'Subscribe to notifications';
        }
    }

    // Unsubscribe from a characteristic
    async function unsubscribeFromCharacteristic(charUuid) {
        try {
            logMessage(`Unsubscribing from characteristic ${charUuid}...`, 'info');
            socket.send(JSON.stringify({
                action: 'unsubscribe_from_characteristic',
                data: { char_uuid: charUuid }
            }));
            // Remove from our subscribed set
            subscribedCharacteristics.delete(charUuid);
            return true;
        } catch (error) {
            console.error('Unsubscribe error:', error);
            logMessage(`Failed to unsubscribe from characteristic: ${error.message}`, 'error');
            throw error;
        }
    }

    // Logging function with timestamp and color coding
    function logMessage(message, type = 'info') {
        if (!logContainer) return;
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type === 'error' ? 'text-red-400' : 
                                          type === 'success' ? 'text-green-400' : 
                                          type === 'warning' ? 'text-yellow-400' : 'text-gray-400'}`;
        logEntry.innerHTML = `[${timestamp}] ${message}`;
        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    // Loading indicator with customizable message
    function setLoading(isLoading, message = 'Loading...') {
        if (!loadingIndicator) return;
        if (isLoading) {
            loadingIndicator.classList.remove('hidden');
            const messageEl = loadingIndicator.querySelector('span');
            if (messageEl) messageEl.textContent = message;
        } else {
            loadingIndicator.classList.add('hidden');
        }
    }

    // Update status with visual feedback
    function updateStatus(status, message) {
        if (!statusIndicatorContainer) return;
        const statusText = status.charAt(0).toUpperCase() + status.slice(1);
        statusIndicatorContainer.innerHTML = `
            <div class="alert-component ble-status-alert rounded-md p-4 mb-4" role="alert" data-status="${status}">
                <div class="flex items-center">
                    <div class="flex-shrink-0 mr-3">
                        ${status === 'connected' ? '<i class="fab fa-bluetooth-b text-green-500"></i>' : 
                          status === 'connecting' ? '<i class="fab fa-bluetooth-b text-yellow-500 animate-pulse"></i>' :
                          status === 'scanning' ? '<i class="fas fa-search text-blue-500 animate-pulse"></i>' :
                          status === 'error' ? '<i class="fab fa-bluetooth-b text-red-500"></i>' :
                          '<i class="fab fa-bluetooth-b text-gray-500"></i>'}
                    </div>
                    <div class="flex-1">
                        <div class="flex items-center">
                            <span class="text-sm font-medium mr-2">BLE Status:</span>
                            <span class="text-sm px-2 py-0.5 rounded-full 
                                ${status === 'connected' ? 'bg-green-100 text-green-800' : 
                                  status === 'connecting' || status === 'scanning' ? 'bg-yellow-100 text-yellow-800' :
                                  status === 'error' ? 'bg-red-100 text-red-800' : 
                                  'bg-gray-100 text-gray-800'}">
                                ${statusText}
                            </span>
                        </div>
                        <p class="text-sm mt-1">${message}</p>
                    </div>
                </div>
            </div>
        `;
    }

    // Update scan status indicator
    function updateScanStatus(status, message) {
        if (!scanStatus) return;
        scanStatus.innerHTML = `
            <span class="w-3 h-3 rounded-full ${status === 'scanning' ? 'bg-blue-500 animate-pulse' : 
                                                  status === 'active' ? 'bg-green-500' : 'bg-gray-500'} mr-2"></span>
            <span class="text-gray-400">${message}</span>
        `;
    }

    // Scan for BLE devices
    async function scanDevices() {
        try {
            console.log("Starting BLE scan...");
            logMessage('Initiating device scan...', 'info');
            setLoading(true, 'Scanning for devices...');
            updateStatus('scanning', 'Scanning for BLE devices...');
            updateScanStatus('scanning', 'Scanning');

            deviceList.innerHTML = '<div class="text-gray-500 animate-pulse">Scanning for devices...</div>';

            const response = await fetch('/api/ble/scan', { method: 'GET' });
            if (!response.ok) throw new Error(`Scan failed: ${response.statusText}`);

            const devices = await response.json();
            console.log('Devices found:', devices);

            deviceList.innerHTML = '';
            if (!Array.isArray(devices) || devices.length === 0) {
                deviceList.innerHTML = '<div class="text-gray-500">No devices found</div>';
                logMessage('No BLE devices detected', 'warning');
                updateScanStatus('active', 'No devices found');
                return;
            }

            logMessage(`Discovered ${devices.length} BLE device${devices.length > 1 ? 's' : ''}`, 'success');
            updateScanStatus('active', 'Scan complete');

            devices.forEach(device => {
                const deviceEl = document.createElement('div');
                deviceEl.className = 'bg-gray-700 p-3 rounded mb-2 flex justify-between items-center hover:bg-gray-600 transition-colors';
                deviceEl.innerHTML = `
                    <div>
                        <div class="font-medium text-white">${device.name || 'Unknown Device'}</div>
                        <div class="text-xs text-gray-400">${device.address}</div>
                        ${device.rssi ? `<div class="text-xs text-gray-400">RSSI: ${device.rssi} dBm</div>` : ''}
                    </div>
                    <button class="connect-btn bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition-colors"
                            data-address="${device.address}" data-name="${device.name || 'Unknown Device'}">
                        Connect
                    </button>
                `;
                deviceList.appendChild(deviceEl);
            });

            document.querySelectorAll('.connect-btn').forEach(button => {
                button.addEventListener('click', (e) => {
                    const address = e.target.dataset.address;
                    const name = e.target.dataset.name;
                    connectToDevice(address, name);
                });
            });

        } catch (error) {
            console.error('Scan error:', error);
            logMessage(`Scan failed: ${error.message}`, 'error');
            deviceList.innerHTML = `<div class="text-red-500">Error: ${error.message}</div>`;
            updateStatus('error', `Scan failed: ${error.message}`);
            updateScanStatus('active', 'Scan failed');
        } finally {
            setLoading(false);
        }
    }

    // Connect to a BLE device
    async function connectToDevice(address, name) {
        try {
            logMessage(`Attempting to connect to ${name} (${address})...`, 'info');
            setLoading(true, `Connecting to ${name}...`);
            updateStatus('connecting', `Connecting to ${name}...`);

            const response = await fetch(`/api/ble/connect/${address}`, { method: 'POST' });
            if (!response.ok) throw new Error(`Connection failed: ${response.statusText}`);

            connectedDevice = { address, name };
            logMessage(`Successfully connected to ${name}`, 'success');
            updateStatus('connected', `Connected to ${name}`);

            disconnectBtn.classList.remove('hidden');
            document.getElementById('device-info-content').innerHTML = `
                <div class="flex flex-col space-y-2">
                    <div class="font-semibold text-white">${name}</div>
                    <div class="text-sm text-gray-400">Address: ${address}</div>
                </div>
            `;

            await getServices();

        } catch (error) {
            console.error('Connection error:', error);
            logMessage(`Connection failed: ${error.message}`, 'error');
            updateStatus('error', `Connection failed: ${error.message}`);
        } finally {
            setLoading(false);
        }
    }

    // Disconnect from device
    async function disconnectFromDevice() {
        if (!connectedDevice) {
            logMessage('No device currently connected', 'warning');
            return;
        }
        try {
            logMessage(`Disconnecting from ${connectedDevice.name}...`, 'info');
            setLoading(true, 'Disconnecting...');
            updateStatus('disconnecting', 'Disconnecting...');

            // Unsubscribe from all characteristics
            for (const charUuid of subscribedCharacteristics) {
                await unsubscribeFromCharacteristic(charUuid);
            }

            const response = await fetch('/api/ble/disconnect', { method: 'POST' });
            if (!response.ok) throw new Error(`Disconnection failed: ${response.statusText}`);

            logMessage('Successfully disconnected', 'success');
            updateStatus('disconnected', 'Disconnected');
            disconnectBtn.classList.add('hidden');
            document.getElementById('device-info-content').innerHTML = '<div class="text-gray-500">No device connected</div>';
            servicesList.innerHTML = '<div class="text-gray-500">Connect to a device to view services</div>';
            characteristicsList.innerHTML = '<div class="text-gray-500">Select a service to view characteristics</div>';
            notificationsContainer.innerHTML = '<div class="text-gray-500">Subscribe to receive characteristic updates</div>';
            connectedDevice = null;

        } catch (error) {
            console.error('Disconnection error:', error);
            logMessage(`Disconnection failed: ${error.message}`, 'error');
            updateStatus('error', `Disconnection failed: ${error.message}`);
        } finally {
            setLoading(false);
        }
    }

    // Get services for connected device
    async function getServices() {
        if (!connectedDevice) return;
        if (!servicesList) return;

        try {
            logMessage('Fetching BLE services...', 'info');
            servicesList.innerHTML = '<div class="text-gray-500 animate-pulse">Loading services...</div>';

            const response = await fetch('/api/ble/services');
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to get services: ${errorText}`);
            }

            const services = await response.json();
            servicesList.innerHTML = '';

            if (!services.length) {
                servicesList.innerHTML = '<div class="text-gray-500">No services found</div>';
                logMessage('No services detected on device', 'warning');
                return;
            }

            logMessage(`Found ${services.length} services`, 'success');
            services.forEach(service => {
                const serviceEl = document.createElement('div');
                serviceEl.className = 'bg-gray-700 p-3 rounded mb-2 hover:bg-gray-600 transition-colors';
                serviceEl.innerHTML = `
                    <div class="font-medium text-white">${service.description || 'Unknown Service'}</div>
                    <div class="text-xs text-gray-400">${service.uuid}</div>
                    <button class="get-chars-btn mt-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition-colors"
                            data-uuid="${service.uuid}">
                        Get Characteristics
                    </button>
                    <div class="chars-container mt-2 hidden" id="chars-${service.uuid.replace(/[^a-z0-9]/gi, '')}"></div>
                `;
                servicesList.appendChild(serviceEl);
            });

            document.querySelectorAll('.get-chars-btn').forEach(button => {
                button.addEventListener('click', (e) => {
                    const uuid = e.target.dataset.uuid;
                    getCharacteristics(uuid);
                });
            });

        } catch (error) {
            console.error('Service fetch error:', error);
            logMessage(`Failed to fetch services: ${error.message}`, 'error');
            servicesList.innerHTML = `
                <div class="text-red-500">Error: ${error.message}</div>
                <button class="retry-services-btn mt-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition-colors">
                    Retry
                </button>
            `;
            const retryButton = document.querySelector('.retry-services-btn');
            if (retryButton) {
                retryButton.addEventListener('click', getServices);
            }
        }
    }

    // Get characteristics for a service
    async function getCharacteristics(serviceUuid) {
        if (!connectedDevice) return;
        const charsContainer = document.getElementById(`chars-${serviceUuid.replace(/[^a-z0-9]/gi, '')}`);
        if (!charsContainer) return;

        try {
            logMessage(`Fetching characteristics for service ${serviceUuid}...`, 'info');
            charsContainer.innerHTML = '<div class="text-gray-500 animate-pulse">Loading characteristics...</div>';

            const response = await fetch(`/api/ble/services/${serviceUuid}/characteristics`);
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to get characteristics: ${errorText}`);
            }

            const characteristics = await response.json();
            charsContainer.innerHTML = '';
            characteristicsList.innerHTML = '';

            if (!characteristics.length) {
                charsContainer.innerHTML = '<div class="text-gray-500">No characteristics found</div>';
                characteristicsList.innerHTML = '<div class="text-gray-500">No characteristics found for this service</div>';
                logMessage('No characteristics found for this service', 'warning');
                return;
            }

            logMessage(`Found ${characteristics.length} characteristics`, 'success');
            characteristics.forEach(char => {
                const charEl = document.createElement('div');
                charEl.className = 'bg-gray-700 p-3 rounded mb-2';
                charEl.innerHTML = `
                    <div class="font-medium text-white">${char.description || 'Unknown Characteristic'}</div>
                    <div class="text-xs text-gray-400">${char.uuid}</div>
                    <div class="text-xs text-gray-400 mt-1">Properties: ${char.properties.join(', ')}</div>
                    <div class="mt-2 flex space-x-2">
                        ${char.properties.includes('read') ? `
                            <button class="read-char-btn bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition-colors"
                                    data-uuid="${char.uuid}">
                                Read
                            </button>
                        ` : ''}
                        ${char.properties.includes('write') ? `
                            <button class="write-char-btn bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-sm transition-colors"
                                    data-uuid="${char.uuid}">
                                Write
                            </button>
                        ` : ''}
                        ${char.properties.includes('notify') ? `
                            <button class="notify-char-btn bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm transition-colors"
                                    data-uuid="${char.uuid}">
                                Subscribe
                            </button>
                        ` : ''}
                    </div>
                    <div class="char-value mt-2 text-sm text-gray-300" id="value-${char.uuid.replace(/[^a-z0-9]/gi, '')}"></div>
                `;
                characteristicsList.appendChild(charEl.cloneNode(true));
                charsContainer.appendChild(charEl);
            });

            charsContainer.classList.remove('hidden');

            // Add event listeners for read/write/notify buttons
            document.querySelectorAll('.read-char-btn').forEach(button => {
                button.addEventListener('click', async (e) => {
                    const uuid = e.target.dataset.uuid;
                    await readCharacteristic(uuid);
                });
            });

            document.querySelectorAll('.write-char-btn').forEach(button => {
                button.addEventListener('click', async (e) => {
                    const uuid = e.target.dataset.uuid;
                    const value = prompt('Enter value to write (hex string, e.g., "FF"):', 'FF');
                    if (value) await writeCharacteristic(uuid, value);
                });
            });

            document.querySelectorAll('.notify-char-btn').forEach(button => {
                button.addEventListener('click', (e) => {
                    const uuid = e.target.dataset.uuid;
                    toggleNotification(uuid, button);
                });
            });

        } catch (error) {
            console.error('Characteristics fetch error:', error);
            logMessage(`Failed to fetch characteristics: ${error.message}`, 'error');
            charsContainer.innerHTML = `<div class="text-red-500">Error: ${error.message}</div>`;
            characteristicsList.innerHTML = `<div class="text-red-500">Error: ${error.message}</div>`;
        }
    }

    // Read characteristic value
    async function readCharacteristic(charUuid) {
        try {
            logMessage(`Reading characteristic ${charUuid}...`, 'info');
            const response = await fetch(`/api/ble/read/${charUuid}`);
            if (!response.ok) throw new Error(`Read failed: ${await response.text()}`);
            const data = await response.json();
            logMessage(`Read value from ${charUuid}: ${data.value}`, 'success');
            const valueEl = document.getElementById(`value-${charUuid.replace(/[^a-z0-9]/gi, '')}`);
            if (valueEl) valueEl.textContent = `Value: ${data.value}`;
        } catch (error) {
            console.error('Read error:', error);
            logMessage(`Failed to read characteristic: ${error.message}`, 'error');
        }
    }

    // Write characteristic value
    async function writeCharacteristic(charUuid, value) {
        try {
            logMessage(`Writing to characteristic ${charUuid}...`, 'info');
            const response = await fetch(`/api/ble/write/${charUuid}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(value)
            });
            if (!response.ok) throw new Error(`Write failed: ${await response.text()}`);
            logMessage(`Successfully wrote ${value} to ${charUuid}`, 'success');
        } catch (error) {
            console.error('Write error:', error);
            logMessage(`Failed to write characteristic: ${error.message}`, 'error');
        }
    }

    // Clear log
    function clearLog() {
        if (logContainer) logContainer.innerHTML = '';
    }

    // Toggle debug panel
    function toggleDebugPanel() {
        if (debugPanel) debugPanel.classList.toggle('hidden');
    }

    // Send debug request
    async function sendDebugRequest() {
        if (!debugEndpointSelect || !debugResponseContainer) return;
        const endpoint = debugEndpointSelect.value;
        try {
            const response = await fetch(endpoint);
            const data = await response.json();
            debugResponseContainer.textContent = JSON.stringify(data, null, 2);
        } catch (error) {
            debugResponseContainer.textContent = `Error: ${error.message}`;
        }
    }

    // Event listeners
    if (scanBtn) {
        scanBtn.addEventListener('click', () => {
            console.log("Scan button clicked");
            scanDevices();
        });
    } else {
        console.error("Scan button not found!");
    }

    if (disconnectBtn) disconnectBtn.addEventListener('click', disconnectFromDevice);
    if (clearLogBtn) clearLogBtn.addEventListener('click', clearLog);
    if (showDebugBtn) showDebugBtn.addEventListener('click', toggleDebugPanel);
    if (debugToggleBtn) debugToggleBtn.addEventListener('click', toggleDebugPanel);
    if (debugSendBtn) debugSendBtn.addEventListener('click', sendDebugRequest);

    // Initial setup
    updateStatus('disconnected', 'Not connected to any device');
    updateScanStatus('active', 'Inactive');
    logMessage('BLE Manager initialized', 'success');
    console.log("BLE Manager initialization complete");

    // Connect to WebSocket
    connectWebSocket();
});
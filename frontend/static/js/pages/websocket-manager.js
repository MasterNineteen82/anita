import UI from '/static/js/utils/ui.js';
import Logger from '/static/js/utils/logger.js';

document.addEventListener('DOMContentLoaded', () => {
    // Constants
    const MAX_RECONNECT_ATTEMPTS = 5;
    const AUTO_RECONNECT_DELAY = 2000;
    const TOKEN_STORAGE_KEY = 'ws_auth_token';

    // WebSocket connection configurations
    const connections = {
        uwb: {
            endpoint: '/ws/uwb',
            label: 'UWB',
            socket: null,
            isConnected: false,
            reconnectAttempts: 0,
            statusElement: null
        },
        biometric: {
            endpoint: '/ws/biometric',
            label: 'Biometric',
            socket: null,
            isConnected: false,
            reconnectAttempts: 0,
            statusElement: null
        },
        card: {
            endpoint: '/ws/card',
            label: 'Card',
            socket: null,
            isConnected: false,
            reconnectAttempts: 0,
            statusElement: null
        },
        ble: {
            endpoint: '/ws/ble',
            label: 'BLE',
            socket: null,
            isConnected: false,
            reconnectAttempts: 0,
            statusElement: null
        },
        mqtt: {
            endpoint: '/ws/mqtt',
            label: 'MQTT',
            socket: null,
            isConnected: false,
            reconnectAttempts: 0,
            statusElement: null
        }
    };

    // DOM Elements
    const logContainer = document.getElementById('log-container');
    const eventContainer = document.getElementById('event-container');
    const messageTypeInput = document.getElementById('message-type');
    const messagePayloadTextarea = document.getElementById('message-payload');
    const wsEndpointSelect = document.getElementById('ws-endpoint');
    const filterLogInput = document.getElementById('filter-log');
    const filterEndpointSelect = document.getElementById('filter-endpoint');
    const filterDirectionSelect = document.getElementById('filter-direction');
    const autoUpdateEventsCheckbox = document.getElementById('auto-update-events');
    const authTokenInput = document.getElementById('auth-token') || createAuthTokenInput();
    const saveTokenCheckbox = document.getElementById('save-token') || createSaveTokenCheckbox();
    const connectionStatsElement = document.getElementById('connection-stats') || createConnectionStatsElement();

    // Function to create authentication token input if it doesn't exist
    function createAuthTokenInput() {
        const container = document.createElement('div');
        container.className = 'space-y-3';
        const label = document.createElement('label');
        label.setAttribute('for', 'auth-token');
        label.className = 'block mb-1 text-sm text-gray-300';
        label.textContent = 'Auth Token (optional)';
        const input = document.createElement('input');
        input.type = 'password';
        input.id = 'auth-token';
        input.className = 'w-full bg-gray-700 border border-gray-600 rounded py-2 px-3 text-white';
        input.placeholder = 'Enter WebSocket auth token';
        // Load saved token if available
        const savedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
        if (savedToken) {
            input.value = savedToken;
        }
        container.appendChild(label);
        container.appendChild(input);
        const messageComposer = document.getElementById('message-composer');
        if (messageComposer) {
            messageComposer.appendChild(container);
        }
        return input;
    }

    // Function to create save token checkbox
    function createSaveTokenCheckbox() {
        const container = document.createElement('div');
        container.className = 'flex items-center mt-2';
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.id = 'save-token';
        input.className = 'mr-2';
        const label = document.createElement('label');
        label.setAttribute('for', 'save-token');
        label.className = 'text-sm text-gray-300';
        label.textContent = 'Save token locally';
        // Check if token is already saved
        if (localStorage.getItem(TOKEN_STORAGE_KEY)) {
            input.checked = true;
        }
        container.appendChild(input);
        container.appendChild(label);
        const messageComposer = document.getElementById('message-composer');
        if (messageComposer) {
            const authContainer = authTokenInput.parentElement;
            messageComposer.insertBefore(container, authContainer.nextSibling);
        }
        // Add event listener to save or remove token
        input.addEventListener('change', function() {
            if (this.checked) {
                localStorage.setItem(TOKEN_STORAGE_KEY, authTokenInput.value);
            } else {
                localStorage.removeItem(TOKEN_STORAGE_KEY);
            }
        });
        // Update saved token when it changes
        authTokenInput.addEventListener('input', function() {
            if (input.checked) {
                localStorage.setItem(TOKEN_STORAGE_KEY, this.value);
            }
        });
        return input;
    }

    // Function to create connection statistics element
    function createConnectionStatsElement() {
        const container = document.createElement('div');
        container.id = 'connection-stats';
        container.className = 'mt-4 p-3 bg-gray-800 rounded text-sm text-gray-300';
        container.innerHTML = `
            <h3 class="font-bold mb-2">Connection Statistics</h3>
            <div id="stats-content" class="grid grid-cols-2 gap-2"></div>
        `;
        const connectionController = document.getElementById('connection-controller');
        if (connectionController) {
            connectionController.parentNode.insertBefore(container, connectionController.nextSibling);
        }
        return container;
    }

    // Function to update connection statistics
    function updateConnectionStats() {
        const statsContent = document.getElementById('stats-content');
        if (!statsContent) return;
        
        let statsHTML = '';
        let connectedCount = 0;
        let totalCount = Object.keys(connections).length;
        
        Object.entries(connections).forEach(([type, config]) => {
            statsHTML += `
                <div>
                    <span class="font-medium">${config.label}:</span>
                    <span class="${config.isConnected ? 'text-green-500' : 'text-red-500'}">${config.isConnected ? 'Connected' : 'Disconnected'}</span>
                    ${!config.isConnected && config.reconnectAttempts > 0 ? `<span class="text-yellow-500">(Retry ${config.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})</span>` : ''}
                </div>
            `;
            if (config.isConnected) {
                connectedCount++;
            }
        });
        
        statsHTML = `<div><span class="font-medium">Overall:</span> <span class="${connectedCount === totalCount ? 'text-green-500' : connectedCount > 0 ? 'text-yellow-500' : 'text-red-500'}">${connectedCount}/${totalCount} Connected</span></div>` + statsHTML;
        
        statsContent.innerHTML = statsHTML;
    }

    // Connect to a specific WebSocket endpoint
    function connectWebSocket(type) {
        if (connections[type].isConnected) {
            console.log(`${type} WebSocket already connected`);
            return;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let wsUrl = `${protocol}//${window.location.host}${connections[type].endpoint}`;
        const authToken = authTokenInput.value.trim();
        
        // Always add token if available (required for authenticated endpoints)
        if (authToken) {
            wsUrl += (wsUrl.includes('?') ? '&' : '?') + `token=${encodeURIComponent(authToken)}`;
            
            // Save token if checkbox is checked
            if (saveTokenCheckbox && saveTokenCheckbox.checked) {
                localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
            }
        }
        
        console.log(`Attempting to connect to WebSocket at: ${wsUrl}`);
        
        try {
            updateConnectionStatus(type, 'connecting');
            connections[type].socket = new WebSocket(wsUrl);
            
            // Set a connection timeout
            const connectionTimeout = setTimeout(() => {
                if (connections[type].socket && connections[type].socket.readyState !== WebSocket.OPEN) {
                    console.error(`Connection timeout for ${type} WebSocket`);
                    connections[type].socket.close();
                    updateConnectionStatus(type, 'error');
                    addLogEntry(`Connection timeout for ${type} WebSocket`, 'error', type, 'system');
                }
            }, 10000); // 10 second timeout
            
            connections[type].socket.onopen = () => {
                clearTimeout(connectionTimeout);
                connections[type].isConnected = true;
                connections[type].reconnectAttempts = 0;
                updateConnectionStatus(type, 'connected');
                addLogEntry(`Connected to ${type} WebSocket`, 'success', type, 'system');
                updateConnectionStats();
                
                // Send a ping to test the connection
                sendPing(type);
            };
            
            connections[type].socket.onmessage = (event) => {
                let message;
                try {
                    // Try to parse as JSON if it's a string
                    if (typeof event.data === 'string') {
                        // If it's a plain string like "ping" or "pong", handle directly
                        if (event.data === 'ping') {
                            connections[type].socket.send('pong');
                            addLogEntry('Received ping, sent pong', 'info', type, 'received');
                            return;
                        } else if (event.data === 'pong') {
                            addLogEntry('Received pong', 'info', type, 'received');
                            return;
                        }
                        
                        // Try to parse as JSON
                        try {
                            message = JSON.parse(event.data);
                        } catch (e) {
                            // If not JSON, treat as text message
                            addLogEntry(`Received text message: ${event.data}`, 'info', type, 'received');
                            return;
                        }
                    } else {
                        // Blob or ArrayBuffer handling
                        const reader = new FileReader();
                        reader.onload = () => {
                            addLogEntry(`Received binary data: ${reader.result.byteLength} bytes`, 'info', type, 'received');
                        };
                        reader.readAsArrayBuffer(event.data);
                        return;
                    }
                    
                    // Log the received message
                    addLogEntry(`Received message: ${JSON.stringify(message)}`, 'info', type, 'received');
                    
                    // Handle different message types
                    handleWebSocketMessage(type, message);
                } catch (error) {
                    console.error(`Error processing ${type} WebSocket message:`, error);
                    addLogEntry(`Error processing message: ${error.message}`, 'error', type, 'system');
                }
            };
            
            connections[type].socket.onclose = (event) => {
                clearTimeout(connectionTimeout);
                connections[type].isConnected = false;
                updateConnectionStatus(type, 'disconnected');
                
                // Log the close event
                let closeReason = 'Connection closed';
                if (event.code !== 1000) {
                    closeReason += ` (Code: ${event.code}, Reason: ${event.reason || 'Unknown'})`;
                }
                addLogEntry(closeReason, 'warning', type, 'system');
                
                // Try to reconnect if not a clean close
                if (!event.wasClean && connections[type].reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                    connections[type].reconnectAttempts++;
                    const delay = Math.min(30000, Math.pow(2, connections[type].reconnectAttempts) * 1000);
                    addLogEntry(`Reconnecting in ${Math.round(delay/1000)} seconds (attempt ${connections[type].reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`, 'info', type, 'system');
                    
                    setTimeout(() => {
                        if (!connections[type].isConnected) {
                            connectWebSocket(type);
                        }
                    }, delay);
                } else if (connections[type].reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
                    addLogEntry(`Maximum reconnection attempts reached (${MAX_RECONNECT_ATTEMPTS})`, 'error', type, 'system');
                }
                
                updateConnectionStats();
            };
            
            connections[type].socket.onerror = (error) => {
                console.error(`${type} WebSocket error:`, error);
                addLogEntry(`WebSocket error occurred`, 'error', type, 'system');
                updateConnectionStats();
            };
            
        } catch (error) {
            console.error(`Error connecting to ${type} WebSocket:`, error);
            addLogEntry(`Connection error: ${error.message}`, 'error', type, 'system');
            updateConnectionStatus(type, 'error');
            updateConnectionStats();
        }
    }

    // Disconnect from a specific WebSocket endpoint
    function disconnectWebSocket(type) {
        if (!connections[type].isConnected) {
            console.log(`${type} WebSocket already disconnected`);
            return;
        }
        
        if (connections[type].socket) {
            connections[type].socket.close();
            connections[type].isConnected = false;
            connections[type].reconnectAttempts = 0; // Reset reconnect attempts
            updateConnectionStatus(type, 'disconnected');
            addLogEntry(`Disconnected from ${type} WebSocket`, 'info', type, 'system');
            updateConnectionStats();
        }
    }

    // Connect to all WebSocket endpoints
    function connectAll() {
        Object.keys(connections).forEach(type => {
            connectWebSocket(type);
        });
    }

    // Disconnect from all WebSocket endpoints
    function disconnectAll() {
        Object.keys(connections).forEach(type => {
            disconnectWebSocket(type);
        });
    }

    // Toggle connection for a specific endpoint
    function toggleConnection(type) {
        if (connections[type].isConnected) {
            disconnectWebSocket(type);
        } else {
            connectWebSocket(type);
        }
    }

    // Update connection status UI
    function updateConnectionStatus(type, status) {
        const statusElement = connections[type].statusElement || document.getElementById(`${type}-connection-status`);
        if (!statusElement) return;
        
        connections[type].statusElement = statusElement;
        
        // Update status text and color
        switch(status) {
            case 'connected':
                statusElement.innerHTML = '<span class="text-green-500">Connected</span>';
                break;
            case 'connecting':
                statusElement.innerHTML = '<span class="text-yellow-500">Connecting...</span>';
                break;
            case 'disconnected':
                statusElement.innerHTML = '<span class="text-red-500">Disconnected</span>';
                break;
            case 'error':
                statusElement.innerHTML = '<span class="text-red-500">Error</span>';
                break;
            default:
                statusElement.innerHTML = '<span class="text-gray-500">Unknown</span>';
        }
        updateConnectionStats();
    }

    // Handle incoming WebSocket messages
    function handleWebSocketMessage(type, message) {
        // Check if the message is an error
        if (message.type === 'error') {
            addLogEntry(`Error from ${type}: ${message.message}`, 'error', type, 'incoming');
            return;
        }
        
        // Handle specific message types
        switch(type) {
            case 'ble':
                handleBleMessage(message);
                break;
            case 'uwb':
                handleUwbMessage(message);
                break;
            case 'biometric':
                handleBiometricMessage(message);
                break;
            case 'card':
                handleCardMessage(message);
                break;
            case 'mqtt':
                handleMqttMessage(message);
                break;
            default:
                console.log('Unhandled message type:', type, message);
        }
    }

    // Handler for BLE messages
    function handleBleMessage(message) {
        switch(message.type) {
            case 'ble_scan_started':
                addEventEntry('BLE Scan Started', JSON.stringify(message.data, null, 2), 'ble');
                break;
            case 'ble_devices':
                addEventEntry('BLE Devices Discovered', JSON.stringify(message.data.devices, null, 2), 'ble');
                break;
            case 'ble_device_connection':
                addEventEntry('BLE Device Connected', JSON.stringify(message.data, null, 2), 'ble');
                break;
            case 'ble_device_disconnection':
                addEventEntry('BLE Device Disconnected', JSON.stringify(message.data, null, 2), 'ble');
                break;
            case 'ble_device_services':
                addEventEntry('BLE Device Services', JSON.stringify(message.data.services, null, 2), 'ble');
                break;
            case 'ble_characteristic_value':
                addEventEntry('BLE Characteristic Value', JSON.stringify(message.data, null, 2), 'ble');
                break;
            default:
                addEventEntry(`BLE: ${message.type}`, JSON.stringify(message.data || message, null, 2), 'ble');
        }
    }

    // Handler for UWB messages
    function handleUwbMessage(message) {
        addEventEntry(`UWB: ${message.type}`, JSON.stringify(message.data || message, null, 2), 'uwb');
    }

    // Handler for Biometric messages
    function handleBiometricMessage(message) {
        addEventEntry(`Biometric: ${message.type}`, JSON.stringify(message.data || message, null, 2), 'biometric');
    }

    // Handler for Card messages
    function handleCardMessage(message) {
        addEventEntry(`Card: ${message.type}`, JSON.stringify(message.data || message, null, 2), 'card');
    }

    // Handler for MQTT messages
    function handleMqttMessage(message) {
        addEventEntry(`MQTT: ${message.type}`, JSON.stringify(message.data || message, null, 2), 'mqtt');
    }

    // Add log entry to UI
    function addLogEntry(message, level, endpoint, direction) {
        if (!logContainer) return;
        
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry p-2 rounded mb-1 text-sm font-mono ${getLogLevelClass(level)}`;
        logEntry.dataset.endpoint = endpoint;
        logEntry.dataset.direction = direction;
        logEntry.dataset.level = level;
        
        const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
        logEntry.innerHTML = `<span class="text-gray-400">[${timestamp}]</span> <span class="font-bold">[${endpoint.toUpperCase()}]</span> ${message}`;
        
        logContainer.appendChild(logEntry);
        
        // Auto-scroll if at bottom
        if (logContainer.scrollTop + logContainer.clientHeight >= logContainer.scrollHeight - 10) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        applyLogFilters();
    }

    // Add event entry to UI
    function addEventEntry(title, details, category) {
        if (!eventContainer) return;
        if (!autoUpdateEventsCheckbox.checked) return;
        
        const eventEntry = document.createElement('div');
        eventEntry.className = 'event-entry p-3 bg-gray-800 rounded mb-2 text-sm';
        eventEntry.dataset.category = category;
        
        eventEntry.innerHTML = `
            <div class="font-bold text-white mb-1">${title}</div>
            <pre class="whitespace-pre-wrap text-xs font-mono bg-gray-900 p-2 rounded overflow-x-auto">${details}</pre>
        `;
        
        eventContainer.insertBefore(eventEntry, eventContainer.firstChild);
        
        // Limit to last 20 events
        while (eventContainer.children.length > 20) {
            eventContainer.removeChild(eventContainer.lastChild);
        }
    }

    // Apply log filters
    function applyLogFilters() {
        if (!logContainer) return;
        
        const searchText = filterLogInput.value.toLowerCase();
        const endpointFilter = filterEndpointSelect.value;
        const directionFilter = filterDirectionSelect.value;
        
        Array.from(logContainer.children).forEach(entry => {
            const matchesSearch = searchText === '' || entry.textContent.toLowerCase().includes(searchText);
            const matchesEndpoint = endpointFilter === 'all' || entry.dataset.endpoint === endpointFilter;
            const matchesDirection = directionFilter === 'all' || entry.dataset.direction === directionFilter;
            
            entry.style.display = matchesSearch && matchesEndpoint && matchesDirection ? 'block' : 'none';
        });
    }

    // Get log level class
    function getLogLevelClass(level) {
        switch(level) {
            case 'success':
                return 'bg-green-900 text-green-300';
            case 'error':
                return 'bg-red-900 text-red-300';
            case 'info':
                return 'bg-blue-900 text-blue-300';
            case 'warning':
                return 'bg-yellow-900 text-yellow-300';
            default:
                return 'bg-gray-800 text-gray-300';
        }
    }

    // Send a message to a WebSocket endpoint
    function sendMessage() {
        const type = wsEndpointSelect.value;
        const messageType = messageTypeInput.value.trim();
        let payload = messagePayloadTextarea.value.trim();
        
        if (!type || !messageType) {
            addLogEntry('Endpoint and message type are required', 'error', 'system', 'outgoing');
            return;
        }
        
        try {
            // Parse payload if it's JSON
            if (payload.startsWith('{') || payload.startsWith('[')) {
                payload = JSON.parse(payload);
            }
        } catch (e) {
            addLogEntry(`Invalid JSON payload: ${e.message}`, 'error', 'system', 'outgoing');
            return;
        }
        
        const message = {
            type: messageType,
            data: payload
        };
        
        if (connections[type].socket && connections[type].isConnected) {
            try {
                connections[type].socket.send(JSON.stringify(message));
                addLogEntry(`Sent: ${JSON.stringify(message, null, 2)}`, 'info', type, 'outgoing');
            } catch (error) {
                addLogEntry(`Failed to send message: ${error.message}`, 'error', type, 'system');
            }
        } else {
            addLogEntry(`Cannot send message: ${type} WebSocket is not connected`, 'error', type, 'system');
        }
    }

    // Clear log entries
    function clearLogs() {
        if (logContainer) {
            logContainer.innerHTML = '';
        }
    }

    // Clear event entries
    function clearEvents() {
        if (eventContainer) {
            eventContainer.innerHTML = '';
        }
    }

    // Send a ping message to test the connection
    function sendPing(type) {
        if (!connections[type] || !connections[type].isConnected) {
            console.warn(`Cannot send ping: ${type} WebSocket not connected`);
            return;
        }
        
        try {
            connections[type].socket.send(JSON.stringify({
                type: 'ping',
                data: { timestamp: Date.now() }
            }));
            addLogEntry('Sent ping', 'info', type, 'sent');
        } catch (error) {
            console.error(`Error sending ping to ${type} WebSocket:`, error);
            addLogEntry(`Error sending ping: ${error.message}`, 'error', type, 'system');
        }
    }

    // Initialize UI when DOM is loaded
    function initializeUI() {
        console.log('Initializing WebSocket Manager UI...');
        // Initialize connection status elements
        Object.keys(connections).forEach(type => {
            connections[type].statusElement = document.getElementById(`${type}-connection-status`);
            if (!connections[type].statusElement) {
                console.error(`Status element for ${type} not found`);
            }
            updateConnectionStatus(type, 'disconnected');
        });
        
        // Initialize buttons
        Object.keys(connections).forEach(type => {
            const connectButton = document.getElementById(`connect-${type}-btn`);
            const disconnectButton = document.getElementById(`disconnect-${type}-btn`);
            
            if (connectButton) {
                connectButton.addEventListener('click', () => {
                    console.log(`Connect ${type} button clicked`);
                    connectWebSocket(type);
                });
            } else {
                console.error(`Connect button for ${type} not found`);
            }
            
            if (disconnectButton) {
                disconnectButton.addEventListener('click', () => {
                    console.log(`Disconnect ${type} button clicked`);
                    disconnectWebSocket(type);
                });
            } else {
                console.error(`Disconnect button for ${type} not found`);
            }
        });
        
        // Connect/Disconnect all buttons
        const connectAllButton = document.getElementById('connect-all-btn');
        const disconnectAllButton = document.getElementById('disconnect-all-btn');
        
        if (connectAllButton) {
            connectAllButton.addEventListener('click', () => {
                console.log('Connect all button clicked');
                connectAll();
            });
        } else {
            console.error('Connect all button not found');
        }
        
        if (disconnectAllButton) {
            disconnectAllButton.addEventListener('click', () => {
                console.log('Disconnect all button clicked');
                disconnectAll();
            });
        } else {
            console.error('Disconnect all button not found');
        }
        
        // Message composer
        const sendMessageButton = document.getElementById('send-message-btn');
        const clearMessageButton = document.getElementById('clear-message-btn');
        
        if (sendMessageButton) {
            sendMessageButton.addEventListener('click', () => {
                console.log('Send message button clicked');
                sendMessage();
            });
        } else {
            console.error('Send message button not found');
        }
        
        if (clearMessageButton) {
            clearMessageButton.addEventListener('click', () => {
                console.log('Clear message button clicked');
                if (messageTypeInput) messageTypeInput.value = '';
                if (messagePayloadTextarea) messagePayloadTextarea.value = '{}';
            });
        } else {
            console.error('Clear message button not found');
        }
        
        // Log and event controls
        const clearLogButton = document.getElementById('clear-log-btn');
        const clearEventsButton = document.getElementById('clear-events-btn');
        const exportLogButton = document.getElementById('export-log-btn');
        
        if (clearLogButton) {
            clearLogButton.addEventListener('click', clearLogs);
        }
        
        if (clearEventsButton) {
            clearEventsButton.addEventListener('click', clearEvents);
        }
        
        if (exportLogButton) {
            exportLogButton.addEventListener('click', () => {
                // Export logs as JSON
                const logs = Array.from(logContainer.children).map(entry => {
                    return {
                        message: entry.querySelector('.log-message').textContent,
                        level: entry.dataset.level,
                        endpoint: entry.dataset.endpoint,
                        direction: entry.dataset.direction,
                        timestamp: entry.dataset.timestamp
                    };
                });
                
                const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `websocket-logs-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            });
        }
        
        // Filters
        if (filterLogInput) {
            filterLogInput.addEventListener('input', applyLogFilters);
        }
        
        if (filterEndpointSelect) {
            filterEndpointSelect.addEventListener('change', applyLogFilters);
        }
        
        if (filterDirectionSelect) {
            filterDirectionSelect.addEventListener('change', applyLogFilters);
        }
        
        // Initial update of UI elements
        updateConnectionStats();
        
        console.log('WebSocket Manager UI initialized');
    }

    // Run initialization when DOM is fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeUI);
    } else {
        // DOM already loaded, run initialization now
        initializeUI();
    }
});
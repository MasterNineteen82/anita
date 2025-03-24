import UI from '/static/js/utils/ui.js';
import Logger from '/static/js/utils/logger.js';

document.addEventListener('DOMContentLoaded', () => {
    // WebSocket connection management
    const connections = {
        uwb: {
            socket: null,
            endpoint: '/ws/uwb',
            isConnected: false,
            reconnectAttempts: 0,
        },
        biometric: {
            socket: null,
            endpoint: '/ws/biometric',
            isConnected: false,
            reconnectAttempts: 0,
        },
        card: {
            socket: null,
            endpoint: '/ws/card',
            isConnected: false,
            reconnectAttempts: 0,
        }
    };
    
    const MAX_RECONNECT_ATTEMPTS = 5;
    const AUTO_RECONNECT_DELAY = 2000; // milliseconds
    
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
    
    // Connect to a specific WebSocket endpoint
    function connectWebSocket(type) {
        if (connections[type].isConnected) {
            console.log(`${type} WebSocket already connected`);
            return;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${connections[type].endpoint}`;
        
        try {
            updateConnectionStatus(type, 'connecting');
            connections[type].socket = new WebSocket(wsUrl);
            
            connections[type].socket.onopen = () => {
                connections[type].isConnected = true;
                connections[type].reconnectAttempts = 0;
                updateConnectionStatus(type, 'connected');
                addLogEntry(`Connected to ${type} WebSocket`, 'success', type, 'system');
            };
            
            connections[type].socket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(type, message);
                addLogEntry(`Received: ${JSON.stringify(message)}`, 'info', type, 'incoming');
            };
            
            connections[type].socket.onclose = () => {
                connections[type].isConnected = false;
                updateConnectionStatus(type, 'disconnected');
                addLogEntry(`Disconnected from ${type} WebSocket`, 'error', type, 'system');
                
                // Auto-reconnect logic
                if (connections[type].reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                    connections[type].reconnectAttempts++;
                    const delay = AUTO_RECONNECT_DELAY * connections[type].reconnectAttempts;
                    
                    addLogEntry(`Attempting to reconnect in ${delay/1000}s (attempt ${connections[type].reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`, 'info', type, 'system');
                    
                    setTimeout(() => {
                        connectWebSocket(type);
                    }, delay);
                } else {
                    addLogEntry(`Failed to reconnect after ${MAX_RECONNECT_ATTEMPTS} attempts`, 'error', type, 'system');
                }
            };
            
            connections[type].socket.onerror = (error) => {
                addLogEntry(`WebSocket error: ${error.message || 'Unknown error'}`, 'error', type, 'system');
            };
        } catch (error) {
            addLogEntry(`Failed to connect to ${type} WebSocket: ${error.message}`, 'error', type, 'system');
            updateConnectionStatus(type, 'error');
        }
    }
    
    // Disconnect from a specific WebSocket endpoint
    function disconnectWebSocket(type) {
        if (!connections[type].isConnected || !connections[type].socket) {
            console.log(`${type} WebSocket not connected`);
            return;
        }
        
        try {
            connections[type].socket.close(1000, "User initiated disconnect");
            connections[type].isConnected = false;
            updateConnectionStatus(type, 'disconnected');
        } catch (error) {
            addLogEntry(`Error disconnecting from ${type} WebSocket: ${error.message}`, 'error', type, 'system');
        }
    }
    
    // Update the UI connection status
    function updateConnectionStatus(type, status) {
        const statusEl = document.getElementById(`${type}-connection-status`);
        if (!statusEl) return;
        
        statusEl.className = 'flex items-center text-sm';
        
        switch(status) {
            case 'connected':
                statusEl.innerHTML = '<span class="w-2 h-2 bg-green-500 rounded-full mr-2"></span> Connected';
                statusEl.classList.add('text-green-400');
                break;
            case 'disconnected':
                statusEl.innerHTML = '<span class="w-2 h-2 bg-red-500 rounded-full mr-2"></span> Disconnected';
                statusEl.classList.add('text-red-400');
                break;
            case 'connecting':
                statusEl.innerHTML = '<span class="w-2 h-2 bg-yellow-500 rounded-full mr-2"></span> Connecting...';
                statusEl.classList.add('text-yellow-400');
                break;
            case 'error':
                statusEl.innerHTML = '<span class="w-2 h-2 bg-red-500 rounded-full mr-2"></span> Error';
                statusEl.classList.add('text-red-400');
                break;
            default:
                statusEl.innerHTML = '<span class="w-2 h-2 bg-gray-500 rounded-full mr-2"></span> Unknown';
                statusEl.classList.add('text-gray-400');
        }
    }
    
    // Send a message to the specified WebSocket
    function sendMessage(type, messageType, payload) {
        if (!connections[type].isConnected || !connections[type].socket) {
            UI.toast(`Cannot send message: ${type} WebSocket not connected`, 'error');
            return false;
        }
        
        try {
            const message = {
                type: messageType,
                payload: payload
            };
            
            connections[type].socket.send(JSON.stringify(message));
            addLogEntry(`Sent: ${JSON.stringify(message)}`, 'info', type, 'outgoing');
            return true;
        } catch (error) {
            addLogEntry(`Error sending message: ${error.message}`, 'error', type, 'system');
            UI.toast(`Failed to send message: ${error.message}`, 'error');
            return false;
        }
    }
    
    // Handle incoming WebSocket messages
    function handleWebSocketMessage(type, message) {
        // Process message based on type and add to event monitor
        if (message.type && message.payload) {
            addEventEntry(type, message.type, message.payload);
        }
    }
    
    // Add entry to the message log
    function addLogEntry(message, level = 'info', endpoint = 'system', direction = 'system') {
        if (!logContainer) return;
        
        const entry = document.createElement('div');
        entry.className = 'py-1 mb-1';
        
        // Apply styling based on message level
        if (level === 'error') {
            entry.classList.add('border-l-2', 'border-red-500', 'pl-2');
        } else if (level === 'success') {
            entry.classList.add('border-l-2', 'border-green-500', 'pl-2');
        } else if (direction === 'incoming') {
            entry.classList.add('border-l-2', 'border-blue-500', 'pl-2');
        } else if (direction === 'outgoing') {
            entry.classList.add('border-l-2', 'border-purple-500', 'pl-2');
        } else {
            entry.classList.add('border-l-2', 'border-gray-500', 'pl-2');
        }
        
        // Create the timestamp and endpoint tag
        const timestamp = new Date().toLocaleTimeString();
        const header = document.createElement('div');
        header.className = 'text-gray-400';
        header.textContent = `[${timestamp}] [${endpoint.toUpperCase()}] [${direction.toUpperCase()}]`;
        
        // Create the message content
        const content = document.createElement('div');
        if (level === 'error') {
            content.className = 'text-red-400';
        } else if (level === 'success') {
            content.className = 'text-green-400';
        } else if (direction === 'incoming') {
            content.className = 'text-blue-400';
        } else if (direction === 'outgoing') {
            content.className = 'text-purple-400';
        } else {
            content.className = 'text-gray-300';
        }
        content.textContent = message;
        
        // Add elements to the entry
        entry.appendChild(header);
        entry.appendChild(content);
        
        // Add entry to log container
        logContainer.appendChild(entry);
        logContainer.scrollTop = logContainer.scrollHeight;
        
        // Also log to console
        if (level === 'error') {
            Logger.error(`[${endpoint}] ${message}`);
        } else {
            Logger.info(`[${endpoint}] ${message}`);
        }
    }
    
    // Add entry to the event monitor
    function addEventEntry(endpoint, eventType, data) {
        if (!eventContainer || !autoUpdateEventsCheckbox.checked) return;
        
        const entry = document.createElement('div');
        entry.className = 'py-1 mb-2 border-l-2 border-cyan-500 pl-2';
        
        // Create the timestamp and endpoint tag
        const timestamp = new Date().toLocaleTimeString();
        const header = document.createElement('div');
        header.className = 'text-gray-400';
        header.textContent = `[${timestamp}] [${endpoint.toUpperCase()}] Event: ${eventType}`;
        
        // Create the data content
        const content = document.createElement('div');
        content.className = 'text-cyan-400';
        try {
            content.textContent = data !== null && typeof data === 'object' ? JSON.stringify(data, null, 2) : String(data || '');
        } catch (error) {
            content.textContent = `Error processing data: ${error.message}`;
        }
        
        // Add elements to the entry
        entry.appendChild(header);
        entry.appendChild(content);
        
        // Add entry to event container
        eventContainer.appendChild(entry);
        eventContainer.scrollTop = eventContainer.scrollHeight;
    }
    
    // Filter log entries
    function filterLogEntries() {
        const filterText = filterLogInput.value.toLowerCase();
        const filterEndpoint = filterEndpointSelect.value;
        const filterDirection = filterDirectionSelect.value;
        
        const entries = logContainer.querySelectorAll('div');
        
        entries.forEach(entry => {
            const headerText = entry.querySelector('div')?.textContent?.toLowerCase() || '';
            const contentText = entry.querySelector('div:nth-child(2)')?.textContent?.toLowerCase() || '';
            const fullText = headerText + ' ' + contentText;
            
            // Text filter
            const matchesText = filterText === '' || fullText.includes(filterText);
            
            // Endpoint filter
            const matchesEndpoint = filterEndpoint === 'all' || 
                                  headerText.includes(`[${filterEndpoint.toUpperCase()}]`);
            
            // Direction filter
            const matchesDirection = filterDirection === 'all' || 
                                   headerText.includes(`[${filterDirection.toUpperCase()}]`);
            
            entry.style.display = (matchesText && matchesEndpoint && matchesDirection) ? 'block' : 'none';
        });
    }
    
    // Clear log container
    function clearLogContainer() {
        if (logContainer) {
            logContainer.innerHTML = '';
            addLogEntry('Log cleared', 'info', 'system', 'system');
        }
    }
    
    // Clear event container
    function clearEventContainer() {
        if (eventContainer) {
            eventContainer.innerHTML = '';
        }
    }
    
    // Export log to file
    function exportLog() {
        if (!logContainer || !logContainer.textContent) {
            UI.toast('No log entries to export', 'error');
            return;
        }
        
        try {
            // Gather log entries
            const entries = Array.from(logContainer.querySelectorAll('div')).map(entry => {
                const header = entry.querySelector('div')?.textContent || '';
                const content = entry.querySelector('div:nth-child(2)')?.textContent || '';
                return `${header}\n${content}\n`;
            }).join('\n');
            
            // Create file
            const blob = new Blob([entries], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            
            // Trigger download
            const a = document.createElement('a');
            a.href = url;
            a.download = `websocket-log-${new Date().toISOString().split('T')[0]}.txt`;
            document.body.appendChild(a);
            a.click();
            
            // Cleanup
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            UI.toast('Log exported successfully', 'success');
        } catch (error) {
            UI.toast(`Failed to export log: ${error.message}`, 'error');
        }
    }
    
    // Event Listeners
    
    // Message sending
    const sendMessageBtn = document.getElementById('send-message-btn');
    if (sendMessageBtn) {
        sendMessageBtn.addEventListener('click', () => {
            const endpoint = wsEndpointSelect.value;
            const messageType = messageTypeInput.value.trim();
            let payload = {};
            
            if (!messageType) {
                UI.toast('Please enter a message type', 'error');
                return;
            }
            
            try {
                // Parse payload as JSON if not empty
                if (messagePayloadTextarea.value.trim()) {
                    payload = JSON.parse(messagePayloadTextarea.value);
                }
                
                if (!connections[endpoint].isConnected) {
                    UI.toast(`Cannot send message: ${endpoint} WebSocket not connected. Connect first.`, 'error');
                    return;
                }
                
                if (sendMessage(endpoint, messageType, payload)) {
                    UI.toast('Message sent successfully', 'success');
                }
            } catch (error) {
                UI.toast(`Invalid JSON payload: ${error.message}`, 'error');
            }
        });
    }
    
    // Clear message composer
    const clearMessageBtn = document.getElementById('clear-message-btn');
    if (clearMessageBtn) {
        clearMessageBtn.addEventListener('click', () => {
            messageTypeInput.value = '';
            messagePayloadTextarea.value = '';
        });
    }
    
    // Connect button handlers
    const connectUwbBtn = document.getElementById('connect-uwb-btn');
    if (connectUwbBtn) {
        connectUwbBtn.addEventListener('click', () => connectWebSocket('uwb'));
    }
    
    const connectBiometricBtn = document.getElementById('connect-biometric-btn');
    if (connectBiometricBtn) {
        connectBiometricBtn.addEventListener('click', () => connectWebSocket('biometric'));
    }
    
    const connectCardBtn = document.getElementById('connect-card-btn');
    if (connectCardBtn) {
        connectCardBtn.addEventListener('click', () => connectWebSocket('card'));
    }
    
    // Disconnect button handlers
    const disconnectUwbBtn = document.getElementById('disconnect-uwb-btn');
    if (disconnectUwbBtn) {
        disconnectUwbBtn.addEventListener('click', () => disconnectWebSocket('uwb'));
    }
    
    const disconnectBiometricBtn = document.getElementById('disconnect-biometric-btn');
    if (disconnectBiometricBtn) {
        disconnectBiometricBtn.addEventListener('click', () => disconnectWebSocket('biometric'));
    }
    
    const disconnectCardBtn = document.getElementById('disconnect-card-btn');
    if (disconnectCardBtn) {
        disconnectCardBtn.addEventListener('click', () => disconnectWebSocket('card'));
    }
    
    // Connect all button
    const connectAllBtn = document.getElementById('connect-all-btn');
    if (connectAllBtn) {
        connectAllBtn.addEventListener('click', () => {
            Object.keys(connections).forEach(type => connectWebSocket(type));
        });
    }
    
    // Disconnect all button
    const disconnectAllBtn = document.getElementById('disconnect-all-btn');
    if (disconnectAllBtn) {
        disconnectAllBtn.addEventListener('click', () => {
            Object.keys(connections).forEach(type => disconnectWebSocket(type));
        });
    }
    
    // Log controls
    const clearLogBtn = document.getElementById('clear-log-btn');
    if (clearLogBtn) {
        clearLogBtn.addEventListener('click', clearLogContainer);
    }
    
    const exportLogBtn = document.getElementById('export-log-btn');
    if (exportLogBtn) {
        exportLogBtn.addEventListener('click', exportLog);
    }
    
    // Event controls
    const clearEventsBtn = document.getElementById('clear-events-btn');
    if (clearEventsBtn) {
        clearEventsBtn.addEventListener('click', clearEventContainer);
    }
    
    const toggleAutofollowBtn = document.getElementById('toggle-autofollow-btn');
    if (toggleAutofollowBtn) {
        toggleAutofollowBtn.addEventListener('click', () => {
            autoUpdateEventsCheckbox.checked = !autoUpdateEventsCheckbox.checked;
        });
    }
    
    // Log filtering
    if (filterLogInput) {
        filterLogInput.addEventListener('input', filterLogEntries);
    }
    
    if (filterEndpointSelect) {
        filterEndpointSelect.addEventListener('change', filterLogEntries);
    }
    
    if (filterDirectionSelect) {
        filterDirectionSelect.addEventListener('change', filterLogEntries);
    }
    
    // Set page title dynamically
    document.title = "WebSocket Manager | ANITA";
    
    // Initialize
    addLogEntry('WebSocket Manager initialized', 'success', 'system', 'system');
});
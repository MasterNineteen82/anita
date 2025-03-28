import { logMessage, updateSubscriptionStatus } from './ble-ui.js';
import { formatCharacteristicValue } from './ble-services.js';
import { updateDeviceList } from './ble-device-list.js';
import { updateStatus } from './ble-ui.js';
import { updateAdapterInfo } from './ble-ui.js';



let retryCount = 0;
const maxRetries = 5;

/**
 * BLE WebSocket connection management module
 * Handles WebSocket connections for real-time BLE notifications
 */

/**
 * Establish a WebSocket connection to the BLE notification endpoint
 * @param {Object} state - The shared BLE state object
 * @returns {Promise} Promise that resolves when connected, rejects on error
 */
export function connectWebSocket(state) {
    // Check if WebSocket is supported
    if (!window.WebSocket) {
        console.error('WebSocket is not supported by this browser');
        logMessage('WebSocket not supported by your browser. Some features may not work.', 'error');
        return null;
    }
    
    try {
        // Determine WebSocket URL based on window location
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/ble`;
        
        // Create and configure WebSocket
        const socket = new WebSocket(wsUrl);
        
        // Configure WebSocket event handlers
        socket.onopen = () => {
            console.log('WebSocket connection established');
            logMessage('WebSocket connected', 'info');
            state.socketConnected = true;
            retryCount = 0; // Reset retry count on successful connection
        };
        
        socket.onclose = (event) => {
            state.socketConnected = false;
            console.log(`WebSocket connection closed: ${event.code}`);
            
            // Don't try to reconnect for normal close events (1000, 1001)
            if (event.code !== 1000 && event.code !== 1001) {
                logMessage('WebSocket disconnected. Reconnecting...', 'warning');
                scheduleReconnection(state);
            } else {
                // Normal closure - still reconnect if we're not navigating away
                // Add a small delay to check if we're navigating away
                setTimeout(() => {
                    if (document.visibilityState === 'visible') {
                        scheduleReconnection(state);
                    }
                }, 500);
            }
        };
        
        socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            logMessage('WebSocket error', 'error');
        };
        
        socket.onmessage = (event) => {
            try {
                console.log('WebSocket message received:', event.data);
                const data = JSON.parse(event.data);
                handleWebSocketMessage(state, data);
            } catch (error) {
                console.error('Error handling WebSocket message:', error);
            }
        };
        
        return socket;
    } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        logMessage(`WebSocket connection error: ${error.message}`, 'error');
        scheduleReconnection(state);
        return null;
    }
}
/**
 * Schedule WebSocket reconnection with exponential backoff
 * @param {Object} state - The shared BLE state object
 */
export function scheduleReconnection(state) {
    if (state.reconnectAttempts === undefined) {
        state.reconnectAttempts = 0;
    }
    
    // Exponential backoff: 1s, 2s, 4s, 8s, etc. up to 30s
    const delay = Math.min(30000, Math.pow(2, state.reconnectAttempts) * 1000);
    state.reconnectAttempts++;
    
    console.log(`Scheduling WebSocket reconnection in ${delay/1000}s (attempt ${state.reconnectAttempts})`);
    
    setTimeout(() => {
        if (!state.socketConnected) {
            console.log(`Attempting to reconnect WebSocket (attempt ${state.reconnectAttempts})`);
            connectWebSocket(state)
                .then(() => {
                    console.log("WebSocket reconnected successfully");
                    state.reconnectAttempts = 0;
                })
                .catch(error => {
                    console.error("WebSocket reconnection failed:", error);
                    scheduleReconnection(state);
                });
        }
    }, delay);
}

/**
 * Start ping interval to keep WebSocket connection alive
 * @param {WebSocket} socket - The WebSocket instance
 */
export function startPingInterval(socket) {
    const PING_INTERVAL = 30000; // 30 seconds
    
    // Clear any existing interval
    if (socket.pingInterval) {
        clearInterval(socket.pingInterval);
    }
    
    // Setup new ping interval
    socket.pingInterval = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
            // Send a ping message
            socket.send(JSON.stringify({ type: "ping" }));
        } else {
            // If socket is not open, clear interval
            clearInterval(socket.pingInterval);
        }
    }, PING_INTERVAL);
}

// Update the message handler to properly handle invalid JSON
export function handleWebSocketMessage(event) {
    try {
        if (!event.data || event.data.trim() === '') {
            console.warn('Received empty WebSocket message');
            return;
        }
        
        const message = JSON.parse(event.data);
        console.log('Received WebSocket message:', message);

        // Handle different message types
        switch (message.type) {
            case 'log':
                logMessage(message.content, message.level || 'info');
                break;
            case 'device_update':
                if (typeof updateDeviceList === 'function') {
                    updateDeviceList(message.devices);
                } else {
                    console.error('updateDeviceList function not available');
                }
                break;
            case 'status_update':
                updateStatus(message.status);
                break;
            case 'adapter_info':
                updateAdapterInfo(message.info);
                break;
            case 'ble.notification':
                // Handle characteristic notification
                console.log(`Notification received from ${message.char_uuid}: ${message.decoded_value}`);
                break;
            default:
                console.warn('Unknown message type:', message.type);
        }
    } catch (error) {
        console.error('Error handling WebSocket message:', error);
        console.error('Raw message data:', event.data); // Log the raw message data
        logMessage(`WebSocket error: ${error.message}`, 'error');
    }
}

export function handleDeviceUpdate(data) {
    console.log("Device update:", data);
}

/**
 * Handle characteristic notification messages
 * @param {Object} state - The shared BLE state object
 * @param {Object} data - The notification data
 */
export function handleCharacteristicNotification(state, data) {
    // Update the UI with the notification data
    const characteristicId = data.characteristic;
    const value = data.value_hex;
    
    console.log(`Notification for ${characteristicId}: ${value}`);
    
    // If you have UI elements for notifications, update them here
    const notificationElement = document.getElementById(`notification-${characteristicId}`);
    if (notificationElement) {
        notificationElement.textContent = value;
        notificationElement.classList.add('notification-highlight');
        
        // Remove highlight after animation completes
        setTimeout(() => {
            notificationElement.classList.remove('notification-highlight');
        }, 1000);
    }
}

/**
 * Handle subscription status updates
 * @param {Object} state - The shared BLE state object
 * @param {Object} data - The subscription data
 */
export function handleSubscriptionUpdate(state, data) {
    const characteristicId = data.char_uuid;
    const status = data.status;
    
    // Update subscribed characteristics set
    if (status === "subscribed") {
        state.subscribedCharacteristics.add(characteristicId);
    } else if (status === "unsubscribed") {
        state.subscribedCharacteristics.delete(characteristicId);
    }
    
    console.log(`Characteristic ${characteristicId} ${status}`);
}

/**
 * Handle connection status updates
 * @param {Object} state - The shared BLE state object
 * @param {Object} data - The connection data
 */
export function handleConnectionUpdate(state, data) {
    console.log("Connection update:", data);
    
    // You may want to update UI elements based on connection status here
}

/**
 * Close the WebSocket connection cleanly
 * @param {Object} state - The shared BLE state object
 */
export function closeWebSocket(state) {
    if (state.socket) {
        // Clear ping interval
        if (state.socket.pingInterval) {
            clearInterval(state.socket.pingInterval);
        }
        
        // Close socket with normal closure code
        state.socket.close(1000, "Normal closure");
        state.socket = null;
        state.socketConnected = false;
    }
}

/**
 * Handle connection events
 * @param {Object} state - Application state
 * @param {Object} data - Connection event data
 */
export async function handleConnectionEvent(state, data) {
    if (data.status === 'disconnected' && state.connectedDevice) {
        logMessage("Device disconnected unexpectedly", 'warning');
        try {
            const { updateStatus } = await import('./ble-ui.js');
            const { disconnectFromDevice } = await import('./ble-connection.js');
            updateStatus(state, 'disconnected', 'Device disconnected unexpectedly');
            disconnectFromDevice(state);
        } catch (error) {
            console.error('Error handling disconnection:', error);
            logMessage(`Error handling disconnection: ${error.message}`, 'error');
        }
    }
}

/**
 * Add a notification to the notifications container
 * @param {Object} state - Application state
 * @param {String} characteristic - Characteristic UUID
 * @param {String} value_hex - Hex value
 */
export function addNotification(state, characteristic, value_hex) {
    const { notificationsContainer } = state.domElements;
    if (!notificationsContainer) return;

    const formattedValue = formatCharacteristicValue(value_hex);
    const timestamp = new Date().toLocaleTimeString();
    const notificationEl = document.createElement('div');
    notificationEl.className = 'bg-gray-800 p-3 rounded mb-2 border border-gray-700';
    notificationEl.innerHTML = `
        <div class="flex justify-between">
            <div class="text-xs text-gray-400">${timestamp}</div>
            <div class="text-xs text-blue-400">${characteristic.substring(0, 8)}...</div>
        </div>
        <div class="mt-1 font-mono text-sm text-white">${formattedValue}</div>
    `;

    if (notificationsContainer.firstChild) {
        notificationsContainer.insertBefore(notificationEl, notificationsContainer.firstChild);
    } else {
        notificationsContainer.appendChild(notificationEl);
    }

    const MAX_NOTIFICATIONS = 20;
    while (notificationsContainer.children.length > MAX_NOTIFICATIONS) {
        notificationsContainer.removeChild(notificationsContainer.lastChild);
    }
}

/**
 * Send a command through the WebSocket connection
 * @param {Object} state - The shared BLE state object
 * @param {String} command - The command type
 * @param {Object} data - The command payload
 * @returns {Boolean} - Success status of sending the command
 */
export function sendWebSocketCommand(state, command, data = {}) {
    if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
        console.error('WebSocket not connected. Cannot send command:', command);
        logMessage('Cannot send command: WebSocket not connected', 'error');
        return false;
    }
    
    try {
        const message = {
            type: command,
            ...data
        };
        
        state.socket.send(JSON.stringify(message));
        return true;
    } catch (error) {
        console.error('Error sending WebSocket command:', error);
        logMessage(`Failed to send command: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Reconnect the WebSocket
 * @param {Object} state - The shared BLE state object
 * @returns {Promise} - Resolves when reconnected
 */
export async function reconnectWebSocket(state) {
    if (state.socket) {
        closeWebSocket(state);
    }
    
    logMessage('Reconnecting WebSocket...', 'info');
    
    try {
        state.socket = connectWebSocket(state);
        if (state.socket) {
            return new Promise((resolve, reject) => {
                state.socket.onopen = () => {
                    logMessage('WebSocket reconnected successfully', 'success');
                    state.reconnectAttempts = 0;
                    resolve(true);
                };
                
                state.socket.onerror = (error) => {
                    reject(error);
                };
                
                // Add timeout for connection attempt
                setTimeout(() => {
                    if (!state.socketConnected) {
                        reject(new Error('WebSocket reconnection timeout'));
                    }
                }, 5000);
            });
        } else {
            throw new Error('Failed to create WebSocket connection');
        }
    } catch (error) {
        console.error('Error reconnecting WebSocket:', error);
        logMessage(`WebSocket reconnection failed: ${error.message}`, 'error');
        scheduleReconnection(state);
        throw error;
    }
}

/**
 * Disconnect the WebSocket
 * @param {Object} state - The shared BLE state object
 */
export function disconnectWebSocket(state) {
    closeWebSocket(state);
    logMessage('WebSocket disconnected', 'info');
}

/**
 * Get the current state of the WebSocket connection
 * @param {Object} state - The shared BLE state object
 * @returns {Object} - Connection state information
 */
export function getWebSocketState(state) {
    if (!state.socket) {
        return {
            connected: false,
            readyState: 'CLOSED',
            reconnectAttempts: state.reconnectAttempts || 0
        };
    }
    
    const readyStateMap = {
        [WebSocket.CONNECTING]: 'CONNECTING',
        [WebSocket.OPEN]: 'OPEN',
        [WebSocket.CLOSING]: 'CLOSING',
        [WebSocket.CLOSED]: 'CLOSED'
    };
    
    return {
        connected: state.socketConnected,
        readyState: readyStateMap[state.socket.readyState],
        reconnectAttempts: state.reconnectAttempts || 0,
        url: state.socket.url
    };
}

/**
 * Setup heartbeat mechanism to detect disconnections
 * @param {Object} state - The shared BLE state object
 */
export function setupWebSocketHeartbeat(state) {
    if (!state.socket) return;
    
    // Clear any existing heartbeat
    if (state.heartbeatInterval) {
        clearInterval(state.heartbeatInterval);
        clearTimeout(state.heartbeatTimeout);
    }
    
    const HEARTBEAT_INTERVAL = 15000; // 15 seconds
    const HEARTBEAT_TIMEOUT = 10000; // 10 seconds
    
    state.heartbeatInterval = setInterval(() => {
        if (state.socket && state.socket.readyState === WebSocket.OPEN) {
            // Send heartbeat and expect response
            state.socket.send(JSON.stringify({ type: 'heartbeat' }));
            
            // Set timeout for response
            state.heartbeatTimeout = setTimeout(() => {
                console.warn('Heartbeat timeout - no response received');
                logMessage('Connection problem detected', 'warning');
                
                // Force reconnection
                reconnectWebSocket(state);
            }, HEARTBEAT_TIMEOUT);
        }
    }, HEARTBEAT_INTERVAL);
}

/**
 * Handle WebSocket errors
 * @param {Object} state - The shared BLE state object
 * @param {Error} error - The error object
 */
export function handleWebSocketError(state, error) {
    console.error('WebSocket error:', error);
    logMessage(`WebSocket error: ${error.message || 'Unknown error'}`, 'error');
    
    // Increment error count
    state.wsErrorCount = (state.wsErrorCount || 0) + 1;
    
    // If too many errors, force reconnection
    if (state.wsErrorCount > 3) {
        console.warn('Too many WebSocket errors, forcing reconnection');
        logMessage('Too many connection errors, reconnecting...', 'warning');
        state.wsErrorCount = 0;
        reconnectWebSocket(state);
    }
}

/**
 * Parse WebSocket data
 * @param {String} data - Raw WebSocket data
 * @returns {Object|null} - Parsed data or null if parsing failed
 */
export function parseWebSocketData(data) {
    try {
        if (typeof data === 'string') {
            return JSON.parse(data);
        } else if (data instanceof Blob) {
            // Handle binary data if needed
            console.warn('Received binary WebSocket data');
            return null;
        } else {
            console.warn('Received unknown WebSocket data type:', typeof data);
            return null;
        }
    } catch (error) {
        console.error('Error parsing WebSocket data:', error);
        console.error('Raw data:', data);
        return null;
    }
}
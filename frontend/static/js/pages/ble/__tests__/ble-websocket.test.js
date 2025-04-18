import { logMessage, updateSubscriptionStatus } from './ble-ui.js';
import { formatCharacteristicValue } from './ble-services.js';

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
            
            // Set up ping interval to keep connection alive
            if (state.pingInterval) clearInterval(state.pingInterval);
            state.pingInterval = setInterval(() => {
                if (socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify({ type: 'ping' }));
                }
            }, 30000); // Send ping every 30 seconds
        };
        
        socket.onclose = (event) => {
            console.log('WebSocket connection closed', event);
            logMessage(`WebSocket disconnected (${event.code})`, 'warning');
            state.socketConnected = false;
            
            // Clear ping interval
            if (state.pingInterval) {
                clearInterval(state.pingInterval);
                state.pingInterval = null;
            }
            
            // Attempt to reconnect after a delay
            setTimeout(() => {
                logMessage('Attempting to reconnect WebSocket...', 'info');
                state.socket = connectWebSocket(state);
            }, 5000);
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
        console.error('Error creating WebSocket:', error);
        logMessage(`Failed to create WebSocket: ${error.message}`, 'error');
        return null;
    }
}

/**
 * Schedule WebSocket reconnection with exponential backoff
 * @param {Object} state - The shared BLE state object
 */
function scheduleReconnection(state) {
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
function startPingInterval(socket) {
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

/**
 * Handle incoming WebSocket messages
 * @param {Object} state - The shared BLE state object
 * @param {MessageEvent} event - The WebSocket message event
 */
export function handleWebSocketMessage(state, event) {
    try {
        const data = JSON.parse(event.data);
        console.log("WebSocket message received:", data);
        
        // Handle different message types
        switch (data.type) {
            case "ble.characteristic":
                handleCharacteristicNotification(state, data);
                break;
            case "ble.characteristic_subscription":
                handleSubscriptionUpdate(state, data);
                break;
            case "ble.connection":
                handleConnectionUpdate(state, data);
                break;
            case "error":
                console.error("WebSocket error message:", data.message);
                break;
            case "pong":
                // Received response to our ping
                break;
            case 'ping': // Add this case
                console.log('Ping received');
                break;
            default:
                console.warn("Unknown WebSocket message type:", data.type);
        }
        
        // Broadcast the message via the event system if available
        if (window.bleEvents) {
            window.bleEvents.emit('WEBSOCKET_MESSAGE', data);
        }
    } catch (error) {
        console.error("Error handling WebSocket message:", error);
    }
}

/**
 * Handle characteristic notification messages
 * @param {Object} state - The shared BLE state object
 * @param {Object} data - The notification data
 */
function handleCharacteristicNotification(state, data) {
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
function handleSubscriptionUpdate(state, data) {
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
function handleConnectionUpdate(state, data) {
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
async function handleConnectionEvent(state, data) {
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
function addNotification(state, characteristic, value_hex) {
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
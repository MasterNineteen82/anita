import { BleEvents, BLE_EVENTS } from './ble-events.js';
import { BleUI } from './ble-ui.js';
import { MessageType } from './ble-constants.js';
import { BleLogger } from './ble-logger.js';

/**
 * Singleton instance for global access
 */
let instance = null;

/**
 * Handles WebSocket communication for BLE functionality
 */
export class BleWebSocket {
    constructor(endpoint = '/api/ble/ws') {
        this.endpoint = endpoint;
        this.socket = null;
        this.isConnecting = false;
        this.retryCount = 0;
        this.pingInterval = null;
        this.maxRetries = 5;
    }
    
    /**
     * Initialize the WebSocket connection
     */
    async initialize() {
        console.log('Initializing BLE WebSocket connection');
        try {
            return await this.connect();
        } catch (error) {
            console.error('WebSocket initialization failed:', error);
            throw error;
        }
    }
    
    /**
     * Connect to the WebSocket server
     */
    async connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return this.socket;
        }
        
        if (this.isConnecting) {
            console.log('WebSocket connection already in progress');
            return null;
        }
        
        this.isConnecting = true;
        
        try {
            // Use consistent WebSocket URL format
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}${this.endpoint}`;
            
            console.log(`Connecting to WebSocket: ${wsUrl}`);
            
            return new Promise((resolve, reject) => {
                const socket = new WebSocket(wsUrl);
                
                socket.onopen = () => {
                    console.log('WebSocket connection established');
                    this.socket = socket;
                    this.isConnecting = false;
                    this.retryCount = 0;
                    this.startPingInterval();
                    
                    // Emit connection event
                    if (window.BleEvents) {
                        window.BleEvents.emit(BleEvents.WEBSOCKET_CONNECTED, { timestamp: Date.now() });
                    }
                    
                    resolve(socket);
                };
                
                socket.onerror = (error) => {
                    console.error('WebSocket connection error:', error);
                    this.isConnecting = false;
                    
                    // Emit error event
                    if (window.BleEvents) {
                        window.BleEvents.emit(BleEvents.WEBSOCKET_ERROR, { error, timestamp: Date.now() });
                    }
                    
                    reject(error);
                };
                
                socket.onclose = (event) => {
                    console.log(`WebSocket connection closed: ${event.code} ${event.reason}`);
                    this.isConnecting = false;
                    this.socket = null;
                    
                    // Clear ping interval
                    if (this.pingInterval) {
                        clearInterval(this.pingInterval);
                        this.pingInterval = null;
                    }
                    
                    // Emit disconnection event
                    if (window.BleEvents) {
                        window.BleEvents.emit(BleEvents.WEBSOCKET_DISCONNECTED, { 
                            code: event.code,
                            reason: event.reason,
                            timestamp: Date.now()
                        });
                    }
                    
                    // Schedule reconnection if not manually closed
                    if (event.code !== 1000) {
                        this.scheduleReconnect();
                    }
                };
                
                socket.onmessage = this.handleMessage.bind(this);
            });
        } catch (error) {
            console.error('Error creating WebSocket connection:', error);
            this.isConnecting = false;
            throw error;
        }
    }
    
    /**
     * Schedule a reconnection attempt
     */
    scheduleReconnect() {
        if (this.retryCount >= this.maxRetries) {
            console.log('Max reconnect attempts reached');
            return;
        }
        
        this.retryCount++;
        const delay = Math.min(30000, 1000 * Math.pow(1.5, this.retryCount - 1));
        
        console.log(`Scheduling reconnect attempt ${this.retryCount} in ${delay}ms`);
        
        setTimeout(() => {
            console.log(`Attempting reconnect ${this.retryCount}/${this.maxRetries}`);
            this.connect().catch(error => {
                console.error('Reconnection failed:', error);
            });
        }, delay);
    }
    
    /**
     * Clean up WebSocket resources
     */
    cleanup() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
        
        if (this.socket) {
            // Remove all event listeners
            this.socket.onopen = null;
            this.socket.onmessage = null;
            this.socket.onclose = null;
            this.socket.onerror = null;
            
            // Close the socket if it's still open
            if (this.socket.readyState === WebSocket.OPEN) {
                this.socket.close();
            }
            
            this.socket = null;
        }
        
        this.isConnecting = false;
    }
    
    /**
     * Start the ping interval to keep the connection alive
     */
    startPingInterval() {
        // Clear any existing interval
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
        }
        
        // Send a ping every 30 seconds
        this.pingInterval = setInterval(() => {
            this.sendCommand('ping', { timestamp: Date.now() });
        }, 30000);
    }
    
    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            
            if (!message || !message.type) {
                console.warn('Invalid WebSocket message format', message);
                return;
            }
            
            // Log incoming message for debugging
            console.log('WebSocket message received:', message);
            
            // Handle different message types
            switch (message.type) {
                case 'ping':
                    console.log('ping received');
                    // Respond with pong
                    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                        this.socket.send(JSON.stringify({
                            type: 'pong',
                            timestamp: Date.now()
                        }));
                    }
                    break;
                    
                case 'pong':
                    console.log('pong received');
                    // Update connection health metrics
                    if (this.lastPingSent) {
                        const latency = Date.now() - this.lastPingSent;
                        this.lastPingLatency = latency;
                        
                        if (window.BleEvents) {
                            window.BleEvents.emit('websocket.latency', { latency });
                        }
                    }
                    this.lastPingSent = null;
                    break;
                    
                case 'scan':
                    this.handleScanMessage(message);
                    break;
                    
                case 'device':
                    this.handleDeviceMessage(message);
                    break;
                    
                case 'service':
                    this.handleServiceMessage(message);
                    break;
                    
                case 'characteristic':
                    this.handleCharacteristicMessage(message);
                    break;
                    
                case 'notification':
                    this.handleNotificationMessage(message);
                    break;
                    
                case 'error':
                    this.handleErrorMessage(message);
                    break;
                    
                default:
                    console.warn('Unknown message type:', message.type);
                    if (window.BleLogger) {
                        window.BleLogger.warn('WebSocket', 'message', `Unknown message type: ${message.type}`);
                    }
            }
            
            // Emit general message event
            if (window.BleEvents) {
                window.BleEvents.emit('websocket.message', { message });
            }
            
        } catch (error) {
            console.error('Error handling WebSocket message:', error);
            if (window.BleLogger) {
                window.BleLogger.error('WebSocket', 'message', 'Error parsing message', { 
                    error: error.message,
                    data: event.data
                });
            }
        }
    }
    
    /**
     * Handle scan status updates
     */
    handleScanStatus(data) {
        switch (data.status) {
            case 'starting':
                BleEvents.emit(BLE_EVENTS.SCAN_STARTED, {
                    timestamp: data.timestamp,
                    config: data.config || {}
                });
                break;
                
            case 'scanning':
                // Handle ongoing scan status, e.g. for progress updates
                BleEvents.emit(BLE_EVENTS.SCAN_PROGRESS, {
                    progress: data.progress || 0,
                    discoveredDevices: data.discovered_devices || 0,
                    timestamp: data.timestamp
                });
                break;
                
            case 'error':
                BleEvents.emit(BLE_EVENTS.SCAN_ERROR, {
                    error: data.message || 'Unknown scan error',
                    timestamp: data.timestamp
                });
                break;
                
            default:
                console.log('Unknown scan status:', data.status);
                BleEvents.emit(BLE_EVENTS.SCAN_STATUS, {
                    status: data.status,
                    timestamp: data.timestamp
                });
                break;
        }
    }
    
    /**
     * Handle scan results
     */
    handleScanResults(data) {
        BleEvents.emit(BLE_EVENTS.SCAN_COMPLETED, {
            devices: data.devices || [],
            count: data.count || 0,
            timestamp: data.timestamp
        });
    }
    
    /**
     * Handle connection status updates
     */
    handleConnectStatus(data) {
        if (data.status === 'connected') {
            BleEvents.emit(BLE_EVENTS.DEVICE_CONNECTED, {
                device: data.device,
                timestamp: data.timestamp
            });
        } else if (data.status === 'disconnected') {
            BleEvents.emit(BLE_EVENTS.DEVICE_DISCONNECTED, {
                device: data.device,
                reason: data.reason,
                timestamp: data.timestamp
            });
        } else if (data.status === 'services_discovered') {
            BleEvents.emit(BLE_EVENTS.DEVICE_SERVICES_DISCOVERED, {
                device: data.device,
                services: data.services,
                timestamp: data.timestamp
            });
        }
    }
    
    /**
     * Handle device notifications
     */
    handleDeviceNotification(data) {
        BleEvents.emit(BLE_EVENTS.CHARACTERISTIC_NOTIFICATION, {
            deviceId: data.device_id,
            serviceUuid: data.service_uuid,
            characteristicUuid: data.characteristic_uuid,
            value: data.value,
            timestamp: data.timestamp
        });
    }
    
    /**
     * Handle error messages
     */
    handleError(data) {
        console.error('WebSocket error:', data.message, data.context);
        
        BleEvents.emit(BLE_EVENTS.ERROR, {
            message: data.message,
            context: data.context,
            timestamp: data.timestamp
        });
        
        // Show error toast
        BleUI.showToast(data.message, 'error');
    }
    
    /**
     * Handle adapter status updates
     */
    handleAdapterStatus(data) {
        BleEvents.emit(BLE_EVENTS.ADAPTER_CHANGED, {
            adapter: data.adapter,
            status: data.status
        });
    }
    
    /**
     * Handle adapter information
     */
    handleAdapterInfo(data) {
        BleEvents.emit(BLE_EVENTS.ADAPTER_INFO, {
            adapters: data.adapters,
            count: data.count
        });
    }
    
    /**
     * Send a command to the WebSocket server
     */
    sendCommand(command, payload = {}) {
        const message = {
            type: command,
            ...payload,
            timestamp: Date.now()
        };
        
        return this.sendMessage(message);
    }
    
    /**
     * Send a command and wait for a response
     */
    async sendCommandWithResponse(command, payload = {}, timeout = 10000) {
        const commandId = Date.now() + '-' + (this.commandCounter++);
        
        const message = {
            type: command,
            command_id: commandId,
            ...payload,
            timestamp: Date.now()
        };
        
        // Create a promise that will be resolved when the response is received
        const responsePromise = new Promise((resolve, reject) => {
            // Store the resolve and reject functions
            this.commandCallbacks.set(commandId, { resolve, reject });
            
            // Set a timeout to reject the promise if no response is received
            setTimeout(() => {
                if (this.commandCallbacks.has(commandId)) {
                    this.commandCallbacks.delete(commandId);
                    reject(new Error(`Command ${command} timed out`));
                }
            }, timeout);
        });
        
        // Send the message
        this.sendMessage(message);
        
        // Return the promise
        return responsePromise;
    }
    
    /**
     * Send a message to the WebSocket server
     */
    sendMessage(message) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.log('WebSocket not connected, queueing message');
            this.messageQueue.push(message);
            
            // Try to reconnect
            if (!this.connected && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.connect().catch(error => {
                    console.error('WebSocket connection error:', error);
                });
            }
            
            return false;
        }
        
        try {
            this.socket.send(JSON.stringify(message));
            return true;
        } catch (error) {
            console.error('Error sending WebSocket message:', error);
            this.messageQueue.push(message);
            return false;
        }
    }
    
    /**
     * Flush the message queue
     */
    flushMessageQueue() {
        if (!this.connected || !this.socket || this.socket.readyState !== WebSocket.OPEN) {
            return;
        }
        
        console.log(`Flushing ${this.messageQueue.length} queued messages`);
        
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            try {
                this.socket.send(JSON.stringify(message));
            } catch (error) {
                console.error('Error sending queued message:', error);
                // Put the message back in the queue
                this.messageQueue.unshift(message);
                break;
            }
        }
    }
    
    /**
     * Check if the WebSocket is connected
     */
    isConnected() {
        return this.connected && this.socket && this.socket.readyState === WebSocket.OPEN;
    }
    
    /**
     * Disconnect the WebSocket
     */
    disconnect() {
        this.cleanup();
    }

    // Add stub methods for each message type handler
    handleScanMessage(message) {
        console.log('Scan message received:', message);
        // Implement scan message handling
    }

    handleDeviceMessage(message) {
        console.log('Device message received:', message);
        // Implement device message handling
    }

    handleServiceMessage(message) {
        console.log('Service message received:', message);
        // Implement service message handling
    }

    handleCharacteristicMessage(message) {
        console.log('Characteristic message received:', message);
        // Implement characteristic message handling
    }

    handleNotificationMessage(message) {
        console.log('Notification message received:', message);
        // Implement notification message handling
    }

    handleErrorMessage(message) {
        console.error('Error message from server:', message.error || message);
        if (window.BleLogger) {
            window.BleLogger.error('WebSocket', 'error', message.error || 'Server error', message);
        }
        
        // Display error in UI
        if (window.BleUI && window.BleUI.showToast) {
            window.BleUI.showToast(message.error || 'Server error', 'error');
        }
    }
}

// Create singleton instance
const bleWebSocketInstance = new BleWebSocket();

/**
 * Static methods that forward to the singleton instance
 * This allows both patterns:
 * - BleWebSocket.staticMethod()
 * - const ws = new BleWebSocket(); ws.instanceMethod()
 */

/**
 * Initialize the WebSocket connection (static method)
 */
BleWebSocket.initialize = async function () {
    return await bleWebSocketInstance.initialize();
};

/**
 * Connect to the WebSocket server (static method)
 */
BleWebSocket.connect = async function () {
    return await bleWebSocketInstance.connect();
};

/**
 * Send a command to the WebSocket server (static method)
 */
BleWebSocket.sendCommand = function (command, payload = {}) {
    return bleWebSocketInstance.sendCommand(command, payload);
};

/**
 * Send a command and wait for a response (static method)
 */
BleWebSocket.sendCommandWithResponse = async function (command, payload = {}, timeout = 10000) {
    return await bleWebSocketInstance.sendCommandWithResponse(command, payload, timeout);
};

/**
 * Get connection status (static method)
 */
BleWebSocket.isConnected = function () {
    return bleWebSocketInstance.isConnected();
};

/**
 * Disconnect the WebSocket (static method)
 */
BleWebSocket.disconnect = function () {
    return bleWebSocketInstance.disconnect();
};

/**
 * Send a WebSocket command with the given type and data
 * @param {string} type The command type
 * @param {object} data The command data
 * @param {number} timeout Timeout in milliseconds
 * @returns {Promise<object>} The response from the server
 */
export async function sendWebSocketCommand(type, data = {}, timeout = 10000) {
    if (!window.bleWebSocket) {
        throw new Error('WebSocket not initialized');
    }
    
    try {
        const result = await window.bleWebSocket.sendCommand(type, data, timeout);
        return result;
    } catch (error) {
        console.error(`Error sending WebSocket command ${type}:`, error);
        throw error;
    }
}

// Export the BleWebSocket class
export default BleWebSocket;
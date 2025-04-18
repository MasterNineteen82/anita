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
        this.maxRetries = 10;  // Increased from 5
        this.connectionHealth = 100;
        this.lastPingSent = null;
        this.lastPongReceived = null;
        this.pingTimeout = null;
        this.heartbeatInterval = null;
        this.connectionStatus = 'disconnected'; // disconnected, connecting, connected
        this.messageQueue = [];  // Queue for messages during disconnection
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 3000;
    }
    
    /**
     * Initialize the WebSocket connection
     */
    async initialize() {
        console.log('Initializing BLE WebSocket connection');
        this.setupHeartbeat();
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
        if (this.socket && this.socket.readyState === WebSocket.CONNECTING) {
            console.log('WebSocket is already connecting');
            return new Promise((resolve, reject) => {
                // Wait for connection to complete or fail
                const checkConnection = setInterval(() => {
                    if (this.socket.readyState === WebSocket.OPEN) {
                        clearInterval(checkConnection);
                        resolve(this.socket);
                    } else if (this.socket.readyState === WebSocket.CLOSED) {
                        clearInterval(checkConnection);
                        reject(new Error('WebSocket connection closed during connection attempt'));
                    }
                }, 100);
            });
        }
        
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            console.log('WebSocket is already connected');
            return Promise.resolve(this.socket);
        }
        
        this.isConnecting = true;
        this.connectionStatus = 'connecting';
        this.emitStatusChange();
        console.log(`Connecting to WebSocket at ${this.endpoint}`);
        
        return new Promise((resolve, reject) => {
            try {
                // Calculate backoff with jitter
                const backoff = this.retryCount === 0 ? 0 : 
                    Math.min(30000, (Math.pow(2, this.retryCount) * 1000) + (Math.random() * 1000));
                
                if (this.retryCount > 0) {
                    console.log(`Retrying connection (attempt ${this.retryCount}) after ${Math.round(backoff)}ms delay`);
                    BleUI.showToast(`Retrying WebSocket Connection (Attempt ${this.retryCount})`, 'info');
                }
                
                // Wait for backoff time before connecting
                setTimeout(() => {
                    try {
                        // Set protocol to match page protocol
                        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                        const host = window.location.host;
                        // Determine full WebSocket URL
                        const wsUrl = this.endpoint.startsWith('ws') ? 
                            this.endpoint : 
                            `${protocol}//${host}${this.endpoint.startsWith('/') ? this.endpoint : '/' + this.endpoint}`;
                        
                        this.socket = new WebSocket(wsUrl);
                        
                        this.socket.onopen = (event) => {
                            this.isConnecting = false;
                            this.connectionStatus = 'connected';
                            this.retryCount = 0;
                            this.reconnectAttempts = 0; // Reset reconnection attempts
                            this.connectionHealth = 100;
                            
                            console.log('WebSocket connection established');
                            
                            // Start ping interval
                            this.startPingInterval();
                            
                            // Process any queued messages
                            this.processQueuedMessages();
                            
                            BleEvents.emit('WS_CONNECTED', { status: 'connected' });
                            BleUI.showToast('WebSocket Connected', 'success');
                            this.emitStatusChange();
                            
                            resolve(this.socket);
                        };
                        
                        this.socket.onmessage = (event) => {
                            // Handle different message types
                            try {
                                // Handle string ping messages
                                if (typeof event.data === 'string' && !event.data.startsWith('{')) {
                                    if (event.data.trim() === 'ping') {
                                        this.sendPong();
                                        return;
                                    }
                                    return;
                                }
                                
                                // Parse JSON messages
                                const message = JSON.parse(event.data);
                                
                                // Handle ping messages
                                if (message.type === 'ping') {
                                    this.sendPong();
                                    return;
                                }
                                
                                // Handle other message types
                                this.handleMessage(message);
                            } catch (error) {
                                console.error('Error handling WebSocket message:', error);
                                BleUI.showToast('WebSocket Message Error', 'error');
                            }
                        };
                        
                        this.socket.onclose = (event) => {
                            this.isConnecting = false;
                            this.connectionStatus = 'disconnected';
                            console.log(`WebSocket connection closed: code=${event.code}, reason=${event.reason}`);
                            BleUI.showToast(`WebSocket Closed: ${event.reason || 'Unknown reason'}`, 'error');
                            
                            // Clear ping interval
                            this.clearPingInterval();
                            
                            // Attempt reconnection if not closed cleanly
                            if (!event.wasClean && this.retryCount < this.maxRetries) {
                                this.retryCount++;
                                console.log(`Scheduling reconnection attempt ${this.retryCount}/${this.maxRetries}`);
                                setTimeout(() => this.connect(), this.getBackoffDelay());
                            } else {
                                this.handleReconnect();
                            }
                            this.emitStatusChange();
                        };
                        
                        this.socket.onerror = (error) => {
                            this.isConnecting = false;
                            console.error('WebSocket error:', error);
                            this.connectionHealth = Math.max(0, this.connectionHealth - 20);
                            BleUI.showToast('WebSocket Error', 'error');
                            this.emitStatusChange();
                            // Don't reject here, let onclose handle reconnection
                        };
                    } catch (error) {
                        this.isConnecting = false;
                        console.error('Error creating WebSocket connection:', error);
                        BleUI.showToast('WebSocket Connection Error', 'error');
                        reject(error);
                    }
                }, backoff);
            } catch (error) {
                this.isConnecting = false;
                console.error('Error in connect method:', error);
                BleUI.showToast('WebSocket Connection Error', 'error');
                reject(error);
            }
        });
    }
    
    /**
     * Emit a status change event
     */
    emitStatusChange() {
        if (typeof BleEvents !== 'undefined') {
            BleEvents.emit('websocket.status', {
                status: this.connectionStatus,
                health: this.connectionHealth,
                retryCount: this.retryCount
            });
        }
    }
    
    /**
     * Setup heartbeat monitoring for health checking
     */
    setupHeartbeat() {
        // Clear existing heartbeat
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }
        
        // Check connection health every 10 seconds
        this.heartbeatInterval = setInterval(() => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                // Check if we've received a pong recently
                if (this.lastPingSent && !this.lastPongReceived) {
                    // No pong received since last ping
                    this.connectionHealth -= 10;
                    this.connectionHealth = Math.max(0, this.connectionHealth);
                    
                    if (this.connectionHealth === 0) {
                        console.warn('WebSocket connection appears to be dead, forcing reconnect');
                        // Force close and reconnect
                        this.socket.close();
                        this.scheduleReconnect();
                    }
                } else {
                    // Got a pong, improve health
                    this.connectionHealth = Math.min(100, this.connectionHealth + 5);
                }
                
                this.emitStatusChange();
            }
        }, 10000);
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
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.lastPingSent = Date.now();
                this.lastPongReceived = null;
                
                this.send(JSON.stringify({
                    type: 'ping',
                    timestamp: this.lastPingSent
                }));
                
                // Set a timeout to detect missed pongs
                if (this.pingTimeout) {
                    clearTimeout(this.pingTimeout);
                }
                
                this.pingTimeout = setTimeout(() => {
                    if (!this.lastPongReceived) {
                        console.warn('No pong received within timeout');
                        this.connectionHealth -= 15;
                        this.connectionHealth = Math.max(0, this.connectionHealth);
                        this.emitStatusChange();
                    }
                }, 5000); // 5 second timeout for pong
            }
        }, 30000);
    }
    
    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(message) {
        try {
            // Log incoming messages for debugging
            console.log('Received WebSocket message:', message);
            
            // Handle different message types
            switch (message.type) {
                case MessageType.ADAPTERS_DISCOVERED:
                    BleEvents.emit(BLE_EVENTS.ADAPTERS_DISCOVERED, message.data);
                    BleUI.showToast('Bluetooth Adapters Discovered', 'info');
                    break;
                case MessageType.ADAPTER_SELECTED:
                    BleEvents.emit(BLE_EVENTS.ADAPTER_SELECTED, message.data);
                    BleUI.showToast(`Adapter Selected: ${message.data.adapter_name || message.data.adapter_id}`, 'success');
                    break;
                case MessageType.ADAPTER_STATUS:
                    BleEvents.emit(BLE_EVENTS.ADAPTER_STATUS, message.data);
                    break;
                default:
                    // Forward other messages to appropriate handlers
                    BleEvents.emit('WS_MESSAGE', message);
                    break;
            }
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
        }
    }
    
    /**
     * Send command to discover Bluetooth adapters
     */
    sendDiscoverAdaptersCommand() {
        const command = {
            type: 'discover_adapters',
            data: {}
        };
        this.send(JSON.stringify(command));
        BleUI.showToast('Discovering Bluetooth Adapters...', 'info');
        console.log('Sent discover adapters command');
    }
    
    /**
     * Send command to select a specific Bluetooth adapter
     * @param {string} adapterId - ID of the adapter to select
     */
    sendSelectAdapterCommand(adapterId) {
        const command = {
            type: 'select_adapter',
            data: {
                id: adapterId
            }
        };
        this.send(JSON.stringify(command));
        BleUI.showToast(`Selecting Adapter: ${adapterId}`, 'info');
        console.log(`Sent select adapter command for ID: ${adapterId}`);
    }
    
    /**
     * Send command to get information about a specific adapter or the current one
     * @param {string} adapterId - ID of the adapter (optional)
     */
    sendGetAdapterInfoCommand(adapterId = null) {
        const command = {
            type: 'get_adapter_info',
            data: adapterId ? { id: adapterId } : {}
        };
        this.send(JSON.stringify(command));
        console.log(`Sent get adapter info command${adapterId ? ' for ID: ' + adapterId : ''}`);
    }
    
    /**
     * Schedule reconnection with exponential backoff
     */
    scheduleReconnect() {
        if (this.retryCount >= this.maxRetries) {
            console.error(`Max reconnection attempts (${this.maxRetries}) reached`);
            BleLogger.error('WebSocket', 'reconnect', 'Maximum reconnection attempts reached', {
                attempts: this.retryCount,
                maxRetries: this.maxRetries
            });
            return;
        }
        
        // Calculate delay with exponential backoff and jitter
        // Base: 1000ms * 2^retry with a max of 30 seconds plus random jitter
        const baseDelay = Math.min(30000, 1000 * Math.pow(2, this.retryCount));
        const jitter = Math.random() * 1000; // Add up to 1 second of jitter
        const delay = baseDelay + jitter;
        
        this.retryCount++;
        
        console.log(`Scheduling reconnect attempt ${this.retryCount}/${this.maxRetries} in ${Math.round(delay/1000)}s`);
        BleLogger.info('WebSocket', 'reconnect', `Reconnecting in ${Math.round(delay/1000)}s`, {
            attempt: this.retryCount,
            maxRetries: this.maxRetries,
            delay: delay
        });
        
        setTimeout(() => {
            console.log(`Attempting reconnect ${this.retryCount}/${this.maxRetries}`);
            this.connect().catch(error => {
                console.error('Reconnection failed:', error);
            });
        }, delay);
    }
    
    /**
     * Send a message through the WebSocket
     */
    send(message) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.warn('WebSocket not connected, queueing message');
            // Queue message for when connection is restored
            this.messageQueue.push(message);
            return false;
        }
        
        try {
            this.socket.send(message);
            return true;
        } catch (error) {
            console.error('Error sending WebSocket message:', error);
            BleLogger.error('WebSocket', 'message', 'Failed to send WebSocket message', {
                error: error.message
            });
            return false;
        }
    }
    
    /**
     * Process any queued messages after reconnection
     */
    processQueuedMessages() {
        if (this.messageQueue.length === 0) {
            return;
        }
        
        console.log(`Processing ${this.messageQueue.length} queued messages`);
        BleUI.showToast(`Processing ${this.messageQueue.length} Queued Messages`, 'info');
        
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            try {
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    this.socket.send(JSON.stringify(message));
                    console.log('Sent queued message:', message);
                } else {
                    console.error('Cannot send queued message, WebSocket is not open:', message);
                    this.messageQueue.unshift(message); // Put it back in the queue
                    break;
                }
            } catch (error) {
                console.error('Error sending queued message:', error);
                this.messageQueue.unshift(message); // Put it back in the queue
                break;
            }
        }
    }
    
    /**
     * Queue a message to be sent when connection is restored
     * @param {Object} message - The message to queue
     */
    queueMessage(message) {
        this.messageQueue.push(message);
        console.log(`Queued message, queue length: ${this.messageQueue.length}`);
        BleUI.showToast(`Message Queued (${this.messageQueue.length} in queue)`, 'info');
        
        // If not already connecting, attempt to reconnect
        if (!this.isConnecting && this.connectionStatus !== 'connected') {
            console.log('Triggering reconnection due to queued message');
            this.connect().catch(error => {
                console.error('Reconnection for queued message failed:', error);
            });
        }
    }
    
    /**
     * Clean up WebSocket resources
     */
    cleanup() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
        
        if (this.pingTimeout) {
            clearTimeout(this.pingTimeout);
            this.pingTimeout = null;
        }
        
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
        
        if (this.socket) {
            // Remove all event listeners
            this.socket.onopen = null;
            this.socket.onclose = null;
            this.socket.onerror = null;
            this.socket.onmessage = null;
            
            // Close the socket if it's not already closed
            if (this.socket.readyState !== WebSocket.CLOSED) {
                try {
                    this.socket.close();
                } catch (e) {
                    console.error('Error closing WebSocket:', e);
                }
            }
            
            this.socket = null;
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
    
    /**
     * Send a pong response
     */
    sendPong() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            try {
                this.socket.send(JSON.stringify({ 
                    type: 'pong',
                    timestamp: Date.now()
                }));
                this.lastPongReceived = Date.now();
            } catch (error) {
                console.error('Error sending pong message:', error);
            }
        }
    }
    
    /**
     * Process any messages queued during disconnection
     */
    processQueuedMessages() {
        if (this.messageQueue.length === 0) {
            return;
        }
        
        console.log(`Processing ${this.messageQueue.length} queued messages`);
        BleUI.showToast(`Processing ${this.messageQueue.length} Queued Messages`, 'info');
        
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            try {
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    this.socket.send(JSON.stringify(message));
                    console.log('Sent queued message:', message);
                } else {
                    console.error('Cannot send queued message, WebSocket is not open:', message);
                    this.messageQueue.unshift(message); // Put it back in the queue
                    break;
                }
            } catch (error) {
                console.error('Error sending queued message:', error);
                this.messageQueue.unshift(message); // Put it back in the queue
                break;
            }
        }
    }
    
    /**
     * Queue a message to be sent when connection is restored
     * @param {Object} message - The message to queue
     */
    queueMessage(message) {
        this.messageQueue.push(message);
        console.log(`Queued message, queue length: ${this.messageQueue.length}`);
        BleUI.showToast(`Message Queued (${this.messageQueue.length} in queue)`, 'info');
        
        // If not already connecting, attempt to reconnect
        if (!this.isConnecting && this.connectionStatus !== 'connected') {
            console.log('Triggering reconnection due to queued message');
            this.connect().catch(error => {
                console.error('Reconnection for queued message failed:', error);
            });
        }
    }
    
    /**
     * Handle WebSocket reconnection
     */
    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            BleUI.showToast(`Reconnecting WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, 'info');
            setTimeout(() => {
                this.connect().catch(error => {
                    console.error(`Reconnection attempt ${this.reconnectAttempts} failed:`, error);
                    BleUI.showToast(`Reconnection Failed (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, 'error');
                    this.handleReconnect();
                });
            }, this.reconnectInterval);
        } else {
            console.error('Maximum reconnection attempts reached. Giving up.');
            BleUI.showToast('WebSocket Reconnection Failed: Max Attempts Reached', 'error');
            BleEvents.emit('WS_DISCONNECTED', { status: 'disconnected', reason: 'max attempts reached' });
            this.connectionStatus = 'disconnected';
            this.emitStatusChange();
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
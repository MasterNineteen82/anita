// Event constants
export const BLE_EVENTS = {
    // Adapter events
    ADAPTER_CHANGED: 'ADAPTER_CHANGED',
    ADAPTER_READY: 'ADAPTER_READY',
    ADAPTER_ERROR: 'ADAPTER_ERROR',
    ADAPTER_SELECTED: 'ADAPTER_SELECTED',
    ADAPTERS_DISCOVERED: 'ADAPTERS_DISCOVERED',
    ADAPTER_STATUS: 'ADAPTER_STATUS',

    // Scan events
    SCAN_STARTED: 'SCAN_STARTED',
    SCAN_RESULT: 'SCAN_RESULT',
    SCAN_COMPLETED: 'SCAN_COMPLETED',
    SCAN_ERROR: 'SCAN_ERROR',
    SCAN_PROGRESS: 'SCAN_PROGRESS',

    // Device events
    DEVICE_CONNECTED: 'DEVICE_CONNECTED',
    DEVICE_DISCONNECTED: 'DEVICE_DISCONNECTED',
    DEVICE_SERVICES_DISCOVERED: 'DEVICE_SERVICES_DISCOVERED',
    CONNECT_REQUEST: 'CONNECT_REQUEST',

    // Characteristic events
    CHARACTERISTIC_READ: 'CHARACTERISTIC_READ',
    CHARACTERISTIC_WRITTEN: 'CHARACTERISTIC_WRITTEN',
    CHARACTERISTIC_NOTIFICATION: 'CHARACTERISTIC_NOTIFICATION',
    NOTIFICATION_SUBSCRIBED: 'NOTIFICATION_SUBSCRIBED',
    NOTIFICATION_UNSUBSCRIBED: 'NOTIFICATION_UNSUBSCRIBED',

    // Error events
    ERROR: 'ERROR',

    // WebSocket events
    WEBSOCKET_CONNECTED: 'WEBSOCKET_CONNECTED',
    WEBSOCKET_DISCONNECTED: 'WEBSOCKET_DISCONNECTED',
    WEBSOCKET_MESSAGE: 'WEBSOCKET_MESSAGE',
    WEBSOCKET_ERROR: 'WEBSOCKET_ERROR',
    RECONNECTING: 'RECONNECTING',
    CONNECTION_STATUS_UPDATED: 'CONNECTION_STATUS_UPDATED',
    WS_CONNECTED: 'WS_CONNECTED',
    WS_DISCONNECTED: 'WS_DISCONNECTED',
    WS_RECONNECTING: 'WS_RECONNECTING',
    WS_RECONNECT_FAILED: 'WS_RECONNECT_FAILED',
    WS_MESSAGE: 'WS_MESSAGE'
};

/**
 * BLE Events class - handles event registration and emission for the BLE system
 */
export class BleEvents {
    constructor() {
        console.log('Creating BLE Events instance');
        
        // Event handlers
        this.handlers = {};
        this.characteristicHandlers = {};
        
        // WebSocket connection
        this.socket = null;
        this.pingInterval = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectBackoff = 1000; // Start with 1 second, will increase
        this.isConnected = false;
        
        // Initialize WebSocket connection
        this.connectWebSocket();
        
        // Store instance in window for singleton pattern
        if (!window.bleEventsInstance) {
            window.bleEventsInstance = this;
            console.log('BLE Events instance stored in window.bleEventsInstance');
        }
    }
    
    /**
     * Get the singleton instance
     * @returns {BleEvents} The singleton instance
     */
    static getInstance() {
        if (!window.bleEventsInstance) {
            window.bleEventsInstance = new BleEvents();
        }
        return window.bleEventsInstance;
    }
    
    /**
     * Register a handler for an event
     * @param {string} eventType - The event type
     * @param {Function} callback - The callback function
     * @returns {Function} A function to remove this specific handler
     */
    on(eventType, callback) {
        if (!this.handlers[eventType]) {
            this.handlers[eventType] = [];
        }
        
        this.handlers[eventType].push(callback);
        console.log(`Registered handler for ${eventType}, total handlers: ${this.handlers[eventType].length}`);
        
        // Return a function that will remove this specific handler
        return () => this.off(eventType, callback);
    }
    
    /**
     * Unregister a handler for an event
     * @param {string} eventType - The event type
     * @param {Function} callback - The callback function
     */
    off(eventType, callback) {
        if (!this.handlers[eventType]) return;
        
        const initialLength = this.handlers[eventType].length;
        this.handlers[eventType] = this.handlers[eventType].filter(h => h !== callback);
        console.log(`Removed handler for ${eventType}, handlers before: ${initialLength}, after: ${this.handlers[eventType].length}`);
    }
    
    /**
     * Emit an event
     * @param {string} eventType - The event type
     * @param {any} data - The event data
     */
    emit(eventType, data) {
        this.withGuard(eventType, () => {
            if (!this.handlers[eventType]) return;
            
            console.log(`Emitting event: ${eventType}`, data ? data : '');
            this.handlers[eventType].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in handler for event ${eventType}:`, error);
                }
            });
        });
    }
    
    /**
     * Add a handler for a characteristic notification
     * @param {string} uuid - The characteristic UUID
     * @param {Function} callback - The callback function
     */
    addCharacteristicHandler(uuid, callback) {
        if (!this.characteristicHandlers[uuid]) {
            this.characteristicHandlers[uuid] = [];
        }
        
        this.characteristicHandlers[uuid].push(callback);
        console.log(`Added characteristic handler for ${uuid}`);
    }
    
    /**
     * Remove a handler for a characteristic notification
     * @param {string} uuid - The characteristic UUID
     * @param {Function} callback - The callback function
     */
    removeCharacteristicHandler(uuid, callback) {
        if (!this.characteristicHandlers[uuid]) return;
        
        if (callback) {
            this.characteristicHandlers[uuid] = this.characteristicHandlers[uuid].filter(h => h !== callback);
        } else {
            delete this.characteristicHandlers[uuid];
        }
        
        console.log(`Removed characteristic handler for ${uuid}`);
    }
    
    /**
     * Handle a message from the WebSocket
     * @param {Object} message - The message object
     */
    handleWebSocketMessage(message) {
        if (!message || !message.type) {
            console.warn('Received invalid message from WebSocket', message);
            return;
        }
        
        // Handle different message types
        switch (message.type) {
            case 'notification':
                this.handleNotification(message);
                break;
            case 'adapter':
                this.emit(BLE_EVENTS.ADAPTER_CHANGED, message.data);
                break;
            case 'scan_result':
                this.emit(BLE_EVENTS.SCAN_RESULT, message.data);
                break;
            case 'scan_completed':
                this.emit(BLE_EVENTS.SCAN_COMPLETED, message.data);
                break;
            case 'device_connected':
                this.emit(BLE_EVENTS.DEVICE_CONNECTED, message.data);
                break;
            case 'device_disconnected':
                this.emit(BLE_EVENTS.DEVICE_DISCONNECTED, message.data);
                break;
            case 'error':
                this.emit(BLE_EVENTS.ERROR, message.data);
                break;
            case 'connection_established':
                console.log('WebSocket connection established with message:', message.message || 'Connection successful');
                this.emit(BLE_EVENTS.WEBSOCKET_CONNECTED, {
                    message: message.message || 'Connection established',
                    timestamp: Date.now()
                });
                break;
            case 'connection_status':
                console.log('WebSocket connection status:', message.status || 'Unknown');
                const isConnected = message.status === 'connected';
                this.emit(BLE_EVENTS.CONNECTION_STATUS_UPDATED, {
                    connected: isConnected,
                    status: message.status,
                    message: message.message || '',
                    timestamp: Date.now()
                });
                break;
            case 'pong':
                // Heartbeat response, no action needed
                break;
            default:
                console.log('Unhandled WebSocket message type:', message.type, message.data);
                // Emit a generic message event with the raw message
                this.emit(BLE_EVENTS.WEBSOCKET_MESSAGE, message);
        }
    }
    
    /**
     * Handle a notification message
     * @param {Object} message - The notification message
     */
    handleNotification(message) {
        if (!message.data || !message.data.uuid) {
            console.warn('Invalid notification message', message);
            return;
        }
        
        const { uuid, value } = message.data;
        
        // Emit generic notification event
        this.emit(BLE_EVENTS.CHARACTERISTIC_NOTIFICATION, {
            uuid,
            value,
            timestamp: Date.now()
        });
        
        // Call specific handlers for this characteristic
        if (this.characteristicHandlers[uuid]) {
            this.characteristicHandlers[uuid].forEach(handler => {
                try {
                    handler(value);
                } catch (error) {
                    console.error(`Error in characteristic handler for ${uuid}:`, error);
                }
            });
        }
    }
    
    /**
     * Connect to the WebSocket server
     */
    connectWebSocket() {
        // Only attempt to connect if we're not already connected
        if (this.socket && (this.socket.readyState === WebSocket.CONNECTING || 
                           this.socket.readyState === WebSocket.OPEN)) {
            console.log('WebSocket already connected or connecting');
            return;
        }
        
        // Determine WebSocket URL from current location
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        // Use the correct WebSocket endpoint for BLE notifications
        const wsUrl = `${protocol}//${host}/api/ble/ws`;
        
        console.log(`Connecting to WebSocket at ${wsUrl}`);
        
        try {
            this.socket = new WebSocket(wsUrl);
            
            // Set up event handlers
            this.socket.onopen = this.handleSocketOpen.bind(this);
            this.socket.onmessage = this.handleSocketMessage.bind(this);
            this.socket.onclose = this.handleSocketClose.bind(this);
            this.socket.onerror = this.handleSocketError.bind(this);
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.emit(BLE_EVENTS.WEBSOCKET_ERROR, { 
                error: error.message || 'Failed to create WebSocket connection' 
            });
            
            // Schedule a reconnection attempt
            this.scheduleReconnect();
        }
    }
    
    /**
     * Handle WebSocket open event
     * @param {Event} event - The open event
     */
    handleSocketOpen(event) {
        console.log('WebSocket connection established');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        // Set up ping interval to keep connection alive
        this.pingInterval = setInterval(() => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000); // Send ping every 30 seconds
        
        // Emit connection event
        this.emit(BLE_EVENTS.WEBSOCKET_CONNECTED, {
            timestamp: Date.now()
        });
        
        // Emit connection status update
        this.emit(BLE_EVENTS.CONNECTION_STATUS_UPDATED, {
            connected: true,
            reconnectAttempts: this.reconnectAttempts
        });
    }
    
    /**
     * Handle WebSocket message event
     * @param {MessageEvent} event - The message event
     */
    handleSocketMessage(event) {
        try {
            // Check if it's a simple string message (common for ping)
            if (typeof event.data === 'string' && !event.data.startsWith('{')) {
                if (event.data.trim() === 'ping') {
                    // Handle ping message directly
                    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                        this.socket.send('pong');
                    }
                    return;
                }
            }
            
            // Parse the message
            const message = JSON.parse(event.data);
            
            // Handle ping message in JSON format
            if (message.type === 'ping') {
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    this.socket.send(JSON.stringify({
                        type: 'pong',
                        timestamp: Date.now()
                    }));
                }
                return;
            }
            
            // Handle notification message
            if (message.type === 'notification') {
                this.handleNotification(message);
                return;
            }
            
            // Emit the event for other message types
            if (message.type) {
                this.emit(message.type, message);
            } else {
                console.warn('Unhandled WebSocket message:', message);
            }
        } catch (error) {
            console.error('Error handling WebSocket message:', error, event.data);
        }
    }
    
    /**
     * Handle WebSocket close event
     * @param {CloseEvent} event - The close event
     */
    handleSocketClose(event) {
        console.log(`WebSocket connection closed: ${event.code} ${event.reason}`);
        this.isConnected = false;
        
        // Clear ping interval
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
        
        // Emit disconnection event
        this.emit(BLE_EVENTS.WEBSOCKET_DISCONNECTED, {
            code: event.code,
            reason: event.reason,
            timestamp: Date.now()
        });
        
        // Emit connection status update
        this.emit(BLE_EVENTS.CONNECTION_STATUS_UPDATED, {
            connected: false,
            code: event.code,
            reason: event.reason
        });
        
        // Schedule a reconnection attempt
        this.scheduleReconnect();
    }
    
    /**
     * Handle WebSocket error event
     * @param {Event} error - The error event
     */
    handleSocketError(error) {
        console.error('WebSocket error:', error);
        
        // Emit error event
        this.emit(BLE_EVENTS.WEBSOCKET_ERROR, {
            error: error.message || 'WebSocket error',
            timestamp: Date.now()
        });
    }
    
    /**
     * Schedule a reconnection attempt
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.warn(`Maximum reconnect attempts (${this.maxReconnectAttempts}) reached, giving up`);
            return;
        }
        
        // Calculate backoff time
        const backoffTime = this.reconnectBackoff * Math.pow(2, this.reconnectAttempts);
        this.reconnectAttempts++;
        
        console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${backoffTime}ms`);
        
        // Emit reconnecting event
        this.emit(BLE_EVENTS.RECONNECTING, {
            attempt: this.reconnectAttempts,
            maxAttempts: this.maxReconnectAttempts,
            delay: backoffTime,
            timestamp: Date.now()
        });
        
        // Schedule reconnection
        setTimeout(() => {
            console.log(`Attempting to reconnect (attempt ${this.reconnectAttempts})`);
            this.connectWebSocket();
        }, backoffTime);
    }
    
    /**
     * Guard against recursive event emission
     * @param {string} eventName - The name of the event
     * @param {Function} callback - The function to execute with guard
     */
    withGuard(eventName, callback) {
        // Create a recursion guard key
        const guardKey = `_handling_${eventName}`;
        
        // Check if we're already handling this event
        if (this[guardKey]) {
            console.warn(`Prevented recursive emission of ${eventName}`);
            return;
        }
        
        try {
            // Set the guard flag
            this[guardKey] = true;
            
            // Execute the callback
            callback();
        } finally {
            // Always clear the guard flag
            this[guardKey] = false;
        }
    }
    
    /**
     * Initialize the events system
     */
    static initialize() {
        console.log('Initializing BLE Events system...');
        const instance = BleEvents.getInstance();
        console.log('BLE Events system initialized');
        return instance;
    }
}

// Initialize the events system
try {
    console.log('Setting up BLE Events system...');
    const bleEvents = BleEvents.initialize();
    console.log('BLE Events system initialized successfully');
    
    // Make it available globally
    window.bleEvents = bleEvents;
} catch (error) {
    console.error('Failed to initialize BLE Events system:', error);
}

export default BleEvents;
// Event constants
export const BLE_EVENTS = {
    // Adapter events
    ADAPTER_CHANGED: 'ADAPTER_CHANGED',
    ADAPTER_READY: 'ADAPTER_READY',
    ADAPTER_ERROR: 'ADAPTER_ERROR',
    
    // Scan events
    SCAN_STARTED: 'SCAN_STARTED',
    SCAN_RESULT: 'SCAN_RESULT',
    SCAN_COMPLETED: 'SCAN_COMPLETED',
    
    // Device events
    DEVICE_CONNECTED: 'DEVICE_CONNECTED',
    DEVICE_DISCONNECTED: 'DEVICE_DISCONNECTED',
    DEVICE_SERVICES_DISCOVERED: 'DEVICE_SERVICES_DISCOVERED',
    
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
    WEBSOCKET_MESSAGE: 'WEBSOCKET_MESSAGE'
};

// Make sure this is in your existing BleEvents class
export class BleEvents {
    // Your existing code...

    // Add the event constants as static properties
    static get ADAPTER_CHANGED() { return BLE_EVENTS.ADAPTER_CHANGED; }
    static get ADAPTER_READY() { return BLE_EVENTS.ADAPTER_READY; }
    static get ADAPTER_ERROR() { return BLE_EVENTS.ADAPTER_ERROR; }
    static get SCAN_STARTED() { return BLE_EVENTS.SCAN_STARTED; }
    static get SCAN_RESULT() { return BLE_EVENTS.SCAN_RESULT; }
    static get SCAN_COMPLETED() { return BLE_EVENTS.SCAN_COMPLETED; }
    static get DEVICE_CONNECTED() { return BLE_EVENTS.DEVICE_CONNECTED; }
    static get DEVICE_DISCONNECTED() { return BLE_EVENTS.DEVICE_DISCONNECTED; }
    static get DEVICE_SERVICES_DISCOVERED() { return BLE_EVENTS.DEVICE_SERVICES_DISCOVERED; }
    static get CHARACTERISTIC_READ() { return BLE_EVENTS.CHARACTERISTIC_READ; }
    static get CHARACTERISTIC_WRITTEN() { return BLE_EVENTS.CHARACTERISTIC_WRITTEN; }
    static get CHARACTERISTIC_NOTIFICATION() { return BLE_EVENTS.CHARACTERISTIC_NOTIFICATION; }
    static get NOTIFICATION_SUBSCRIBED() { return BLE_EVENTS.NOTIFICATION_SUBSCRIBED; }
    static get NOTIFICATION_UNSUBSCRIBED() { return BLE_EVENTS.NOTIFICATION_UNSUBSCRIBED; }
    static get ERROR() { return BLE_EVENTS.ERROR; }
    static get WEBSOCKET_CONNECTED() { return BLE_EVENTS.WEBSOCKET_CONNECTED; }
    static get WEBSOCKET_DISCONNECTED() { return BLE_EVENTS.WEBSOCKET_DISCONNECTED; }
    static get WEBSOCKET_MESSAGE() { return BLE_EVENTS.WEBSOCKET_MESSAGE; }

    
    // Singleton pattern
    static #instance;
    
    /**
     * Get the singleton instance
     * @returns {BleEventsImpl} The singleton instance
     */
    static getInstance() {
        if (!this.#instance) {
            this.#instance = new BleEventsImpl();
        }
        return this.#instance;
    }
    
    /**
     * Initialize the events system
     */
    static initialize() {
        this.getInstance(); // Ensure instance is created
        console.log('BLE Events system initialized');
        return this;
    }
    
    /**
     * Register a handler for an event
     * @param {string} eventType - The event type
     * @param {Function} callback - The callback function
     */
    static on(eventType, callback) {
        return this.getInstance().on(eventType, callback);
    }
    
    /**
     * Unregister a handler for an event
     * @param {string} eventType - The event type
     * @param {Function} callback - The callback function
     */
    static off(eventType, callback) {
        return this.getInstance().off(eventType, callback);
    }
    
    /**
     * Emit an event
     * @param {string} eventType - The event type
     * @param {any} data - The event data
     */
    static emit(eventType, data) {
        return this.getInstance().emit(eventType, data);
    }
    
    /**
     * Add a handler for a characteristic notification
     * @param {string} uuid - The characteristic UUID
     * @param {Function} callback - The callback function
     */
    static addCharacteristicHandler(uuid, callback) {
        return this.getInstance().addCharacteristicHandler(uuid, callback);
    }
    
    /**
     * Remove a handler for a characteristic notification
     * @param {string} uuid - The characteristic UUID
     */
    static removeCharacteristicHandler(uuid) {
        return this.getInstance().removeCharacteristicHandler(uuid);
    }
    
    /**
     * Handle a message from the WebSocket
     * @param {Object} message - The message object
     */
    static handleWebSocketMessage(message) {
        return this.getInstance().handleWebSocketMessage(message);
    }
    
    /**
     * Connect to the WebSocket server
     */
    static connectWebSocket() {
        return this.getInstance().connectWebSocket();
    }
}

/**
 * Implementation of BLE events system
 * @private
 */
class BleEventsImpl {
    constructor() {
        this.handlers = {};
        this.characteristicHandlers = {};
        this.socket = null;
        this.pingInterval = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectBackoff = 1000; // Start with 1 second, will increase
        
        // Initialize WebSocket connection
        this.connectWebSocket();
        
        console.log('BLE Events implementation initialized');
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
        
        this.handlers[eventType] = this.handlers[eventType].filter(h => h !== callback);
    }
    
    /**
     * Emit an event
     * @param {string} eventType - The event type
     * @param {any} data - The event data
     */
    emit(eventType, data) {
        if (!this.handlers[eventType]) return;
        
        const augmentedData = {
            ...data,
            timestamp: data.timestamp || Date.now(),
            eventType
        };
        
        this.handlers[eventType].forEach(callback => {
            try {
                callback(augmentedData);
            } catch (error) {
                console.error(`Error in BLE event handler for ${eventType}:`, error);
            }
        });
    }
    
    /**
     * Add a handler for a characteristic notification
     * @param {string} uuid - The characteristic UUID
     * @param {Function} callback - The callback function
     */
    addCharacteristicHandler(uuid, callback) {
        // Convert UUID to lowercase for consistent matching
        const lowerUuid = uuid.toLowerCase();
        this.characteristicHandlers[lowerUuid] = callback;
        
        // If WebSocket is connected, send subscribe message
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'subscribe',
                characteristic: lowerUuid
            }));
        }
        
        // Emit subscription event
        this.emit(BleEvents.NOTIFICATION_SUBSCRIBED, {
            characteristic: lowerUuid
        });
    }
    
    /**
     * Remove a handler for a characteristic notification
     * @param {string} uuid - The characteristic UUID
     */
    removeCharacteristicHandler(uuid) {
        // Convert UUID to lowercase for consistent matching
        const lowerUuid = uuid.toLowerCase();
        
        // If WebSocket is connected, send unsubscribe message
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'unsubscribe',
                characteristic: lowerUuid
            }));
        }
        
        delete this.characteristicHandlers[lowerUuid];
        
        // Emit unsubscription event
        this.emit(BleEvents.NOTIFICATION_UNSUBSCRIBED, {
            characteristic: lowerUuid
        });
    }
    
    /**
     * Handle a message from the WebSocket
     * @param {Object} message - The message object
     */
    handleWebSocketMessage(message) {
        try {
            // Handle different message types
            switch (message.type) {
                case 'ble.notification':
                    this.handleNotification(message);
                    break;
                    
                case 'ble.connection':
                    this.emit(BleEvents.DEVICE_CONNECTED, {
                        device: message.device,
                        timestamp: message.timestamp
                    });
                    break;
                    
                case 'ble.disconnect':
                    this.emit(BleEvents.DEVICE_DISCONNECTED, {
                        device: message.device,
                        timestamp: message.timestamp
                    });
                    break;
                    
                case 'ble.scan.start':
                    this.emit(BleEvents.SCAN_STARTED, {
                        timestamp: message.timestamp,
                        config: message.config
                    });
                    break;
                    
                case 'ble.scan.result':
                    this.emit(BleEvents.SCAN_RESULT, {
                        device: message.device,
                        timestamp: message.timestamp
                    });
                    break;
                    
                case 'ble.scan.complete':
                    this.emit(BleEvents.SCAN_COMPLETED, {
                        devices: message.devices,
                        timestamp: message.timestamp,
                        duration: message.duration
                    });
                    break;
                    
                case 'ble.error':
                    this.emit(BleEvents.ERROR, {
                        message: message.message,
                        context: message.context,
                        timestamp: message.timestamp
                    });
                    break;
                    
                case 'pong':
                    // WebSocket keep-alive, no action needed
                    break;
                    
                default:
                    console.warn('Unknown WebSocket message type:', message.type);
            }
        } catch (error) {
            console.error('Error handling WebSocket message:', error);
        }
    }
    
    /**
     * Handle a notification message
     * @param {Object} message - The notification message
     */
    handleNotification(message) {
        // Extract notification details
        const { characteristic, value, encoding, device } = message;
        
        // Convert UUID to lowercase for consistent matching
        const lowerUuid = characteristic.toLowerCase();
        
        // Call the specific handler for this characteristic
        if (this.characteristicHandlers[lowerUuid]) {
            try {
                this.characteristicHandlers[lowerUuid](value, encoding);
            } catch (error) {
                console.error(`Error in characteristic handler for ${characteristic}:`, error);
            }
        }
        
        // Also emit a general notification event
        this.emit(BleEvents.NOTIFICATION, { characteristic, value, encoding, device });
    }
    
    /**
     * Connect to the WebSocket server
     */
    connectWebSocket() {
        try {
            // Close existing socket if any
            if (this.socket) {
                this.socket.close();
            }
            
            // Determine WebSocket URL based on current page URL
            const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
            const wsUrl = `${protocol}://${window.location.host}/api/ws/ble`;
            
            console.log(`Connecting to WebSocket at ${wsUrl}`);
            
            // Create new WebSocket
            this.socket = new WebSocket(wsUrl);
            
            // Set up event handlers
            this.socket.addEventListener('open', this.handleSocketOpen.bind(this));
            this.socket.addEventListener('message', this.handleSocketMessage.bind(this));
            this.socket.addEventListener('close', this.handleSocketClose.bind(this));
            this.socket.addEventListener('error', this.handleSocketError.bind(this));
            
            // Set up ping interval to keep the connection alive
            this.pingInterval = setInterval(() => {
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    this.socket.send(JSON.stringify({ type: 'ping' }));
                }
            }, 30000); // Send a ping every 30 seconds
        } catch (error) {
            console.error('Error connecting to WebSocket:', error);
            this.emit(BleEvents.WEBSOCKET_ERROR, {
                message: `WebSocket connection error: ${error.message}`,
                context: { wsError: true }
            });
        }
    }
    
    /**
     * Handle WebSocket open event
     */
    handleSocketOpen(event) {
        console.log('WebSocket connection established');
        this.reconnectAttempts = 0;
        
        // Emit websocket connected event
        this.emit(BleEvents.WEBSOCKET_CONNECTED, {
            timestamp: Date.now()
        });
        
        // Re-subscribe to all characteristics
        Object.keys(this.characteristicHandlers).forEach(uuid => {
            this.socket.send(JSON.stringify({
                type: 'subscribe',
                characteristic: uuid
            }));
        });
    }
    
    /**
     * Handle WebSocket message event
     */
    handleSocketMessage(event) {
        try {
            const message = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }
    
    /**
     * Handle WebSocket close event
     */
    handleSocketClose(event) {
        console.log(`WebSocket connection closed: ${event.code} ${event.reason}`);
        
        // Emit websocket disconnected event
        this.emit(BleEvents.WEBSOCKET_DISCONNECTED, {
            code: event.code,
            reason: event.reason,
            timestamp: Date.now()
        });
        
        // Clear ping interval
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
        
        // Attempt to reconnect with exponential backoff
        this.reconnectAttempts++;
        
        if (this.reconnectAttempts <= this.maxReconnectAttempts) {
            const delay = Math.min(30000, this.reconnectBackoff * Math.pow(2, this.reconnectAttempts - 1));
            
            // Emit reconnecting event
            this.emit(BleEvents.RECONNECTING, {
                attempt: this.reconnectAttempts,
                maxAttempts: this.maxReconnectAttempts,
                delay,
                timestamp: Date.now()
            });
            
            console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, delay);
        } else {
            console.error(`Maximum reconnection attempts (${this.maxReconnectAttempts}) reached. Giving up.`);
            
            // Emit final error
            this.emit(BleEvents.ERROR, {
                message: 'WebSocket connection failed after maximum attempts',
                context: { wsError: true, reconnect: false },
                timestamp: Date.now()
            });
        }
    }
    
    /**
     * Handle WebSocket error event
     */
    handleSocketError(error) {
        console.error('WebSocket error:', error);
        
        this.emit(BleEvents.WEBSOCKET_ERROR, {
            message: 'WebSocket connection error',
            error,
            context: { wsError: true },
            timestamp: Date.now()
        });
    }
}
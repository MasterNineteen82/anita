/**
 * Event types for BLE operations
 * @enum {string}
 */
export const BLE_EVENTS = {
    // Connection events
    DEVICE_CONNECTING: 'ble.device.connecting',
    DEVICE_CONNECTED: 'ble.device.connected',
    DEVICE_DISCONNECTED: 'ble.device.disconnected',
    DEVICE_RECOVERED: 'ble.device.recovered',
    
    // Error events
    CONNECTION_ERROR: 'ble.error.connection',
    SCAN_ERROR: 'ble.error.scan',
    SERVICE_ERROR: 'ble.error.service',
    
    // Notification events
    CHARACTERISTIC_NOTIFICATION: 'ble.characteristic.notification',
    
    // Lifecycle events
    ADAPTER_RESET: 'ble.adapter.reset',
    RECOVERY_ATTEMPT: 'ble.recovery.attempt',
    RECOVERY_SUCCESS: 'ble.recovery.success',
    RECOVERY_FAILURE: 'ble.recovery.failure'
};

/**
 * Simple event emitter for BLE events
 */
export class BLEEventEmitter {
    constructor() {
        this.listeners = {};
    }
    
    /**
     * Register a callback for an event
     * @param {string} event - Event type 
     * @param {Function} callback - Callback function
     */
    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }
    
    /**
     * Remove a callback for an event
     * @param {string} event - Event type
     * @param {Function} callback - Callback to remove
     */
    off(event, callback) {
        if (!this.listeners[event]) return;
        this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
    
    /**
     * Emit an event with data
     * @param {string} event - Event type
     * @param {Object} data - Event data
     */
    emit(event, data = {}) {
        if (!this.listeners[event]) return;
        
        // Add timestamp to all events
        const eventData = {
            ...data,
            timestamp: Date.now()
        };
        
        // Log all events to console for debugging
        console.debug(`BLE Event: ${event}`, eventData);
        
        this.listeners[event].forEach(callback => {
            try {
                callback(eventData);
            } catch (error) {
                console.error(`Error in BLE event listener for ${event}:`, error);
            }
        });
    }
    
    /**
     * Remove all listeners
     */
    clear() {
        this.listeners = {};
    }
}

// Create and export the event emitter instance
export const bleEventEmitter = new BLEEventEmitter();
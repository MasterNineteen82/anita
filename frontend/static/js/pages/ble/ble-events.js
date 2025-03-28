/**
 * BLE Events module - provides a simple event system for BLE-related events
 */

// Define event names as constants
export const BLE_EVENTS = {
    // Connection events
    DEVICE_CONNECTING: 'ble.device.connecting',
    DEVICE_CONNECTED: 'ble.device.connected',
    DEVICE_DISCONNECTING: 'ble.device.disconnecting',
    DEVICE_DISCONNECTED: 'ble.device.disconnected',
    CONNECTION_FAILED: 'ble.connection.failed',
    CONNECTION_TIMEOUT: 'ble.connection.timeout',
    CONNECTION_CANCELLED: 'ble.connection.cancelled',
    CONNECTION_STATE_CHANGED: 'ble.connection.state_changed',
    
    // Scan events
    SCAN_STARTED: 'ble.scan.start',
    SCAN_RESULT: 'ble.scan.result',
    SCAN_COMPLETE: 'ble.scan.complete',
    SCAN_FAILED: 'ble.scan.failed',
    
    // Service events
    SERVICES_DISCOVERED: 'ble.services.discovered',
    SERVICE_CHANGED: 'ble.service.changed',
    
    // Characteristic events
    CHARACTERISTIC_READ: 'ble.characteristic.read',
    CHARACTERISTIC_WRITE: 'ble.characteristic.write',
    CHARACTERISTIC_NOTIFY: 'ble.characteristic.notify',
    CHARACTERISTIC_CHANGED: 'ble.characteristic.changed',
    CHARACTERISTIC_NOTIFICATION: 'ble.characteristic.notification',
    
    // Notification events
    NOTIFICATION_SUBSCRIBED: 'ble.notification.subscribed',
    NOTIFICATION_UNSUBSCRIBED: 'ble.notification.unsubscribed',
    
    // Error events
    ERROR_SCAN: 'ble.error.scan',
    ERROR_CONNECT: 'ble.error.connect',
    ERROR_DISCONNECT: 'ble.error.disconnect',
    ERROR_READ: 'ble.error.read',
    ERROR_WRITE: 'ble.error.write',
    ERROR_NOTIFY: 'ble.error.notify',
    
    // Adapter events
    ADAPTER_STATE_CHANGED: 'ble.adapter.state_changed'
};

// Event registry for internal use
const eventRegistry = {};

// Export the BleEvents object
export const BleEvents = {
    _listeners: {},
    
    /**
     * Register an event listener
     * @param {string} eventName - Name of the event
     * @param {Function} callback - Callback function
     * @returns {Function} Unsubscribe function
     */
    on(eventName, callback) {
        if (!this._listeners[eventName]) {
            this._listeners[eventName] = [];
        }
        this._listeners[eventName].push(callback);
        
        return () => this.off(eventName, callback); // Return unsubscribe function
    },
    
    /**
     * Remove an event listener
     * @param {string} eventName - Name of the event
     * @param {Function} callback - Callback function to remove
     */
    off(eventName, callback) {
        if (this._listeners[eventName]) {
            this._listeners[eventName] = this._listeners[eventName].filter(
                cb => cb !== callback
            );
        }
    },
    
    /**
     * Emit an event
     * @param {string} eventName - Name of the event
     * @param {*} data - Event data
     */
    emit(eventName, data) {
        // Add timestamp to all events
        const eventData = {
            ...data,
            timestamp: Date.now()
        };
        
        // Log all events for debugging
        console.log(`BLE Event: ${eventName}`, eventData);
        
        if (this._listeners[eventName]) {
            this._listeners[eventName].forEach(callback => {
                try {
                    callback(eventData);
                } catch (error) {
                    console.error(`Error in event listener for ${eventName}:`, error);
                }
            });
        }
        
        // Also dispatch as DOM event for legacy support
        emitCustomEvent(eventName, eventData);
    },
    
    /**
     * Register multiple event listeners at once
     * @param {Object} listeners - Object with event names as keys and callbacks as values
     * @returns {Function} Unsubscribe function for all registered listeners
     */
    onMany(listeners) {
        const unsubscribeFunctions = [];
        
        // Register each listener
        for (const [eventName, callback] of Object.entries(listeners)) {
            const unsubscribe = this.on(eventName, callback);
            unsubscribeFunctions.push(unsubscribe);
        }
        
        // Return a function that unsubscribes all listeners
        return () => {
            unsubscribeFunctions.forEach(unsubscribe => unsubscribe());
        };
    },
    
    /**
     * Register a one-time event listener
     * @param {string} eventName - Name of the event
     * @param {Function} callback - Callback function
     */
    once(eventName, callback) {
        const wrappedCallback = (data) => {
            // Unsubscribe immediately
            this.off(eventName, wrappedCallback);
            // Call the original callback
            callback(data);
        };
        
        return this.on(eventName, wrappedCallback);
    },
    
    /**
     * Check if an event has any listeners
     * @param {string} eventName - Name of the event
     * @returns {boolean} Whether the event has listeners
     */
    hasListeners(eventName) {
        return !!this._listeners[eventName] && this._listeners[eventName].length > 0;
    },
    
    /**
     * Get all registered event names
     * @returns {string[]} Array of event names
     */
    getRegisteredEvents() {
        return Object.keys(this._listeners);
    },
    
    /**
     * Clear all listeners for a specific event
     * @param {string} eventName - Name of the event
     */
    clearEvent(eventName) {
        this._listeners[eventName] = [];
    },
    
    /**
     * Clear all listeners for all events
     */
    clearAll() {
        this._listeners = {};
    }
};

/**
 * Register an event handler (legacy method)
 * @param {string} eventName - Event name
 * @param {Function} handlerFn - Handler function
 * @returns {Function} - Unregister function
 */
export function registerEventHandler(eventName, handlerFn) {
    return BleEvents.on(eventName, handlerFn);
}

/**
 * Unregister an event handler (legacy method)
 * @param {string} eventName - Event name
 * @param {Function} handlerFn - Handler function
 */
export function unregisterEventHandler(eventName, handlerFn) {
    BleEvents.off(eventName, handlerFn);
}

/**
 * Emit a custom DOM event
 * @param {string} eventName - Event name
 * @param {Object} detail - Event details
 */
export function emitCustomEvent(eventName, detail) {
    // Create and dispatch a custom event
    const event = new CustomEvent(eventName, {
        detail,
        bubbles: true,
        cancelable: true
    });
    
    document.dispatchEvent(event);
}

// Legacy event handlers - use these for backward compatibility
export const BLE_EVENT_HANDLERS = {
    onScanStart: (callback) => BleEvents.on(BLE_EVENTS.SCAN_STARTED, callback),
    onScanComplete: (callback) => BleEvents.on(BLE_EVENTS.SCAN_COMPLETE, callback),
    onScanError: (callback) => BleEvents.on(BLE_EVENTS.ERROR_SCAN, callback),
    onDeviceConnecting: (callback) => BleEvents.on(BLE_EVENTS.DEVICE_CONNECTING, callback),
    onDeviceConnected: (callback) => BleEvents.on(BLE_EVENTS.DEVICE_CONNECTED, callback),
    onConnectionFailed: (callback) => BleEvents.on(BLE_EVENTS.CONNECTION_FAILED, callback),
    onDeviceDisconnected: (callback) => BleEvents.on(BLE_EVENTS.DEVICE_DISCONNECTED, callback),
    onCharacteristicNotification: (callback) => BleEvents.on(BLE_EVENTS.CHARACTERISTIC_NOTIFICATION, callback),
    onNotificationSubscribed: (callback) => BleEvents.on(BLE_EVENTS.NOTIFICATION_SUBSCRIBED, callback),
    onNotificationUnsubscribed: (callback) => BleEvents.on(BLE_EVENTS.NOTIFICATION_UNSUBSCRIBED, callback)
};

// For backward compatibility
// Create a global reference to BleEvents
window.bleEvents = BleEvents;

// Initialize event listeners when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('BLE Events module initialized');
    
    // Register global event listeners for debugging
    if (window.BLE_DEBUG) {
        document.addEventListener('ble.device.connected', function(event) {
            console.log('[DOM Event] Device connected:', event.detail);
        });
        
        document.addEventListener('ble.device.disconnected', function(event) {
            console.log('[DOM Event] Device disconnected:', event.detail);
        });
        
        document.addEventListener('ble.characteristic.notification', function(event) {
            console.log('[DOM Event] Notification received:', event.detail);
        });
    }
});

// Export default for convenience
export default BleEvents;
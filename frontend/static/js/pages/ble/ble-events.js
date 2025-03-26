// frontend/static/js/pages/ble/ble-events.js
export class BLEEventEmitter {
    constructor() {
        this.events = {};
    }
    
    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
        return this; // For chaining
    }
    
    off(event, callback) {
        if (!this.events[event]) return this;
        
        if (callback) {
            this.events[event] = this.events[event].filter(cb => cb !== callback);
        } else {
            delete this.events[event];
        }
        return this;
    }
    
    emit(event, ...args) {
        if (!this.events[event]) return;
        
        this.events[event].forEach(callback => {
            try {
                callback(...args);
            } catch (err) {
                console.error(`Error in ${event} event handler:`, err);
            }
        });
    }
}

// BLE lifecycle events
export const BLE_EVENTS = {
    SCAN_START: 'scan:start',
    SCAN_COMPLETE: 'scan:complete',
    SCAN_ERROR: 'scan:error',
    DEVICE_FOUND: 'device:found',
    DEVICE_CONNECTING: 'device:connecting',
    DEVICE_CONNECTED: 'device:connected',
    DEVICE_DISCONNECTED: 'device:disconnected',
    CONNECTION_ERROR: 'connection:error',
    SERVICES_DISCOVERED: 'services:discovered',
    CHARACTERISTIC_READ: 'characteristic:read',
    CHARACTERISTIC_WRITE: 'characteristic:write',
    NOTIFICATION_STARTED: 'notification:started',
    NOTIFICATION_RECEIVED: 'notification:received',
    NOTIFICATION_STOPPED: 'notification:stopped'
};

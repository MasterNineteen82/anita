/**
 * BLE constants used throughout the application
 */

/**
 * Message types for WebSocket communication
 * @enum {string}
 */
export const MessageType = {
    // Command messages
    SCAN_REQUEST: 'scan_request',
    CONNECT_REQUEST: 'connect_request',
    DISCONNECT_REQUEST: 'disconnect_request',
    READ_REQUEST: 'read_request',
    WRITE_REQUEST: 'write_request',
    SUBSCRIBE_REQUEST: 'subscribe_request',
    UNSUBSCRIBE_REQUEST: 'unsubscribe_request',
    
    // Response messages
    SCAN_RESULT: 'scan_result',
    DEVICE_CONNECTED: 'device_connected',
    DEVICE_DISCONNECTED: 'device_disconnected',
    CHARACTERISTIC_VALUE: 'characteristic_value',
    NOTIFICATION: 'notification',
    ERROR: 'error',
    
    // System messages
    PING: 'ping',
    PONG: 'pong'
};

/**
 * Connection status values
 * @enum {string}
 */
export const ConnectionStatus = {
    DISCONNECTED: 'disconnected',
    CONNECTING: 'connecting',
    CONNECTED: 'connected',
    DISCONNECTING: 'disconnecting',
    FAILED: 'failed'
};

/**
 * Standard Bluetooth service UUIDs and descriptions
 * @type {Object}
 */
export const BleServices = {
    GENERIC_ACCESS: '1800',
    GENERIC_ATTRIBUTE: '1801',
    IMMEDIATE_ALERT: '1802',
    LINK_LOSS: '1803',
    TX_POWER: '1804',
    CURRENT_TIME: '1805',
    HEART_RATE: '180D',
    BATTERY: '180F',
    DEVICE_INFORMATION: '180A'
};
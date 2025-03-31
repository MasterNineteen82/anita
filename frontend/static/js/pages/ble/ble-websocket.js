import { BleEvents } from './ble-events.js';
import { BleUI } from './ble-ui.js';
import { MessageType } from './ble-constants.js';

/**
 * Singleton instance for global access
 */
let instance = null;

/**
 * Handles WebSocket communication for BLE functionality
 */
export class BleWebSocket {
    constructor() {
        if (instance) {
            return instance;
        }
        
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this.heartbeatInterval = null;
        this.pendingPings = 0;
        this.maxPendingPings = 5; // Increased max pending pings
        
        instance = this;
    }

    /**
     * Initialize the WebSocket connection
     */
    async initialize() {
        console.log('Initializing BLE WebSocket');
        
        try {
            await this.connect();
            return true;
        } catch (error) {
            console.error('WebSocket initialization failed:', error);
            return false;
        }
    }

    /**
     * Connect to the WebSocket server
     */
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
                    console.log('WebSocket already connected or connecting');
                    resolve(true);
                    return;
                }
                
                // Create WebSocket URL based on current location
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/api/ws/ble`;
                
                console.log(`Connecting to WebSocket at ${wsUrl}`);
                
                this.socket = new WebSocket(wsUrl);
                
                // Setup event handlers
                this.socket.onopen = () => {
                    console.log('WebSocket connected');
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    
                    // Start heartbeat
                    this.startHeartbeat();
                    
                    // Emit connection event
                    BleEvents.emit(BleEvents.WEBSOCKET_CONNECTED, { timestamp: Date.now() });
                    
                    BleUI.showToast('Connected to BLE service', 'success');
                    resolve(true);
                };
                
                this.socket.onmessage = (event) => {
                    // Parse message data
                    try {
                        const data = JSON.parse(event.data);
                        this.handleMessage(data);
                    } catch (error) {
                        console.error('Error parsing WebSocket message:', error);
                    }
                };

                this.socket.onclose = (event) => {
                    console.log('WebSocket disconnected:', event.code, event.reason);
                    this.isConnected = false;
                    clearInterval(this.heartbeatInterval);
                    this.heartbeatInterval = null;
                    
                    // Emit disconnection event
                    BleEvents.emit(BleEvents.WEBSOCKET_DISCONNECTED, { timestamp: Date.now() });
                    
                    BleUI.showToast('Disconnected from BLE service', 'warning');
                    
                    // Attempt to reconnect
                    if (this.reconnectAttempts < this.maxReconnectAttempts) {
                        this.reconnectAttempts++;
                        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
                        setTimeout(() => this.connect().then(resolve).catch(reject), this.reconnectDelay);
                    } else {
                        console.error('Max reconnect attempts reached. Giving up.');
                        BleUI.showToast('Connection to BLE service lost', 'error');
                        reject(new Error('WebSocket disconnected'));
                    }
                };

                this.socket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.isConnected = false;
                    clearInterval(this.heartbeatInterval);
                    this.heartbeatInterval = null;
                    
                    // Emit disconnection event
                    BleEvents.emit(BleEvents.WEBSOCKET_DISCONNECTED, { timestamp: Date.now() });
                    
                    BleUI.showToast('Error in BLE service', 'error');
                    reject(error);
                };
            } catch (error) {
                console.error('WebSocket connection error:', error);
                reject(error);
            }
        });
    }

    /**
     * Start the heartbeat to keep the connection alive
     */
    startHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }
        
        this.heartbeatInterval = setInterval(() => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                // Send ping
                this.sendPing();
            } else {
                // Clear interval if socket is not open
                clearInterval(this.heartbeatInterval);
                this.heartbeatInterval = null;
            }
        }, 10000); // Increased interval to 10 seconds
    }

    /**
     * Send a ping message to the server
     */
    sendPing() {
        if (this.pendingPings >= this.maxPendingPings) {
            console.warn('Too many pending pings. Closing connection.');
            this.socket.close(4000, 'Too many pings without response');
            return;
        }
        
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.pendingPings++;
            this.socket.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
        }
    }

    /**
     * Handle incoming messages from the WebSocket server
     * @param {Object} data - Message data
     */
    handleMessage(data) {
        // Handle different message types from the new backend
        console.log('WebSocket message received:', data);
        
        try {
            // Emit general websocket message event
            BleEvents.emit(BleEvents.WEBSOCKET_MESSAGE, data);
            
            switch (data.type) {
                case MessageType.SCAN_RESULT:
                    // Handle scan results
                    BleEvents.emit(BleEvents.SCAN_RESULT, {
                        device: data.device,
                        timestamp: data.timestamp
                    });
                    break;
                    
                case MessageType.NOTIFICATION:
                    // Handle notifications with new CharacteristicValue format
                    BleEvents.emit(BleEvents.CHARACTERISTIC_NOTIFICATION, {
                        characteristic: data.characteristic,
                        value: data.value,
                        timestamp: data.timestamp
                    });
                    break;
                    
                case MessageType.DEVICE_CONNECTED:
                    // Handle device connected event
                    BleEvents.emit(BleEvents.DEVICE_CONNECTED, {
                        device: data.device,
                        services: data.services || [],
                        timestamp: data.timestamp
                    });
                    break;
                    
                case MessageType.DEVICE_DISCONNECTED:
                    // Handle device disconnected event
                    BleEvents.emit(BleEvents.DEVICE_DISCONNECTED, {
                        device: data.device,
                        reason: data.reason,
                        timestamp: data.timestamp
                    });
                    break;
                    
                case MessageType.ERROR:
                    // Handle error messages
                    BleEvents.emit(BleEvents.ERROR, {
                        message: data.message,
                        type: data.error_type,
                        details: data.details,
                        timestamp: data.timestamp
                    });
                    
                    BleUI.showToast(`BLE Error: ${data.message}`, 'error');
                    break;
                    
                case 'pong':
                    // Handle pong response (heartbeat)
                    this.lastPongTime = Date.now();
                    break;
                    
                default:
                    console.log('Unknown message type:', data.type);
            }
        } catch (error) {
            console.error('Error handling WebSocket message:', error);
        }
    }

    /**
     * Send a command to the WebSocket server
     * @param {string} command - Command to send
     * @param {object} payload - Command payload
     */
    sendCommand(command, payload = {}) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            const message = {
                type: command,
                payload: payload,
                timestamp: Date.now()
            };
            this.socket.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected. Cannot send command:', command);
            BleUI.showToast('Not connected to BLE service', 'warning');
        }
    }
    
    /**
     * Get connection status
     * @returns {boolean} Whether WebSocket is connected
     */
    isWebSocketConnected() {
        return this.isConnected;
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
BleWebSocket.initialize = async function() {
    return await bleWebSocketInstance.initialize();
};

/**
 * Connect to the WebSocket server (static method)
 */
BleWebSocket.connect = async function() {
    return await bleWebSocketInstance.connect();
};

/**
 * Send a command to the WebSocket server (static method)
 */
BleWebSocket.sendCommand = function(command, payload = {}) {
    return bleWebSocketInstance.sendCommand(command, payload);
};

/**
 * Get connection status (static method)
 */
BleWebSocket.isConnected = function() {
    return bleWebSocketInstance.isConnected;
};

// Add static property for compatibility
Object.defineProperty(BleWebSocket, 'isConnected', {
    get: function() {
        return bleWebSocketInstance.isConnected;
    }
});

/**
 * Send a command to the WebSocket server (convenience function)
 * @param {string} command - Command to send
 * @param {object} payload - Command payload
 */
export const sendWebSocketCommand = (command, payload = {}) => {
    return bleWebSocketInstance.sendCommand(command, payload);
};

// Initialize WebSocket when module is loaded
bleWebSocketInstance.initialize().catch(error => {
    console.error('Failed to initialize WebSocket on module load:', error);
});

// Export singleton instance directly
export const bleWebSocket = bleWebSocketInstance;
import { BleEvents } from './ble-events.js';
import { BleUI } from './ble-ui.js';

/**
 * Handles WebSocket communication for BLE functionality
 */
export class BleWebSocket {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this.heartbeatInterval = null;
        this.pendingPings = 0;
        this.maxPendingPings = 5; // Increased max pending pings
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
        switch (data.type) {
            case 'pong':
                // Handle pong
                this.pendingPings = Math.max(0, this.pendingPings - 1);
                break;
            default:
                // Handle other messages
                BleEvents.handleWebSocketMessage(data);
                break;
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
}

/**
 * Send a command to the WebSocket server
 * @param {string} command - Command to send
 * @param {object} payload - Command payload
 */
export const sendWebSocketCommand = (command, payload = {}) => {
    const bleWebSocket = new BleWebSocket();
    bleWebSocket.sendCommand(command, payload);
};
/**
 * Main BLE Module
 * Core functionality for Bluetooth Low Energy operations
 */

class BLECore {
    constructor() {
        this.state = {};
        this.isConnected = false;
        this.currentDevice = null;
        this.baseUrl = '/api/ble';
        this.socket = null;
        this.eventHandlers = {};

        console.log('BLE Core module initialized');
    }

    /**
     * Initialize the BLE core module
     */
    async initialize() {
        console.log('BLE Core module initialized');
    }

    /**
     * Initialize the WebSocket connection
     */
    async initWebSocket() {
        if (this.socket) {
            console.log('WebSocket already initialized');
            return;
        }

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Update to use the correct path
        const wsUrl = `${wsProtocol}//${window.location.host}/api/ble/ws`;

        console.log(`Connecting to WebSocket at ${wsUrl}`);

        try {
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = this._handleSocketOpen.bind(this);
            this.socket.onmessage = this._handleSocketMessage.bind(this);
            this.socket.onclose = this._handleSocketClose.bind(this);
            this.socket.onerror = this._handleSocketError.bind(this);

            return new Promise((resolve, reject) => {
                // Add temporary handlers for connection resolution
                const onOpenHandler = () => {
                    this.socket.removeEventListener('open', onOpenHandler);
                    this.socket.removeEventListener('error', onErrorHandler);
                    resolve();
                };

                const onErrorHandler = (error) => {
                    this.socket.removeEventListener('open', onOpenHandler);
                    this.socket.removeEventListener('error', onErrorHandler);
                    reject(error);
                };

                this.socket.addEventListener('open', onOpenHandler);
                this.socket.addEventListener('error', onErrorHandler);

                // Add a timeout for the connection
                setTimeout(() => {
                    this.socket.removeEventListener('open', onOpenHandler);
                    this.socket.removeEventListener('error', onErrorHandler);
                    reject(new Error('WebSocket connection timeout'));
                }, 5000);
            });
        } catch (error) {
            console.error('Error initializing WebSocket:', error);
            throw error;
        }
    }

    /**
     * Handle WebSocket open event
     */
    _handleSocketOpen(event) {
        console.log('WebSocket connection established');
        this._triggerEvent('websocket.connected', {});
    }

    /**
     * Handle WebSocket message event
     */
    _handleSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('WebSocket message received:', data);

            if (data.type) {
                this._triggerEvent(`ble.${data.type}`, data);
                this._triggerEvent('websocket.message', data);
            }
        } catch (error) {
            console.error('Error handling WebSocket message:', error);
        }
    }

    /**
     * Handle WebSocket close event
     */
    _handleSocketClose(event) {
        if (event.wasClean) {
            console.log(`WebSocket connection closed cleanly, code=${event.code}, reason=${event.reason}`);
        } else {
            console.error('WebSocket connection died');
        }

        this._triggerEvent('websocket.disconnected', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
        });

        // Try to reconnect after a delay
        setTimeout(() => {
            if (this.socket && this.socket.readyState === WebSocket.CLOSED) {
                console.log('Attempting to reconnect WebSocket...');
                this.initWebSocket().catch(error => {
                    console.error('Failed to reconnect WebSocket:', error);
                });
            }
        }, 5000);
    }

    /**
     * Handle WebSocket error event
     */
    _handleSocketError(error) {
        console.error('WebSocket error:', error);
        this._triggerEvent('websocket.error', { error });
    }

    /**
     * Subscribe to BLE characteristic notifications
     */
    subscribeToCharacteristic(characteristicUuid) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return false;
        }

        try {
            this.socket.send(JSON.stringify({
                type: 'subscribe',
                characteristic: characteristicUuid
            }));
            return true;
        } catch (error) {
            console.error('Error subscribing to characteristic:', error);
            return false;
        }
    }

    /**
     * Unsubscribe from BLE characteristic notifications
     */
    unsubscribeFromCharacteristic(characteristicUuid) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return false;
        }

        try {
            this.socket.send(JSON.stringify({
                type: 'unsubscribe',
                characteristic: characteristicUuid
            }));
            return true;
        } catch (error) {
            console.error('Error unsubscribing from characteristic:', error);
            return false;
        }
    }

    /**
     * Send ping message to keep WebSocket connection alive
     */
    ping() {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return false;
        }

        try {
            this.socket.send(JSON.stringify({
                type: 'ping'
            }));
            return true;
        } catch (error) {
            console.error('Error sending ping:', error);
            return false;
        }
    }

    /**
     * Register an event handler
     */
    on(eventName, handler) {
        if (!this.eventHandlers[eventName]) {
            this.eventHandlers[eventName] = [];
        }

        this.eventHandlers[eventName].push(handler);
    }

    /**
     * Unregister an event handler
     */
    off(eventName, handler) {
        if (!this.eventHandlers[eventName]) {
            return;
        }

        this.eventHandlers[eventName] = this.eventHandlers[eventName].filter(h => h !== handler);
    }

    /**
     * Trigger an event
     */
    _triggerEvent(eventName, data) {
        if (!this.eventHandlers[eventName]) {
            return;
        }

        for (const handler of this.eventHandlers[eventName]) {
            try {
                handler(data);
            } catch (error) {
                console.error(`Error in event handler for ${eventName}:`, error);
            }
        }
    }

    /**
     * Make an API request
     * @param {string} endpoint - API endpoint
     * @param {object} options - Request options
     * @returns {Promise<any>} - Response data
     */
    async request(endpoint, options = {}) {
        try {
            // Use URL constructor to properly join the base URL and endpoint
            const baseUrl = window.location.origin; // Get the base URL from the current location
            const url = new URL(`${this.baseUrl}${endpoint}`, baseUrl).href;

            const defaultOptions = {
                method: 'GET', // Default method is GET
                headers: {
                    'Content-Type': 'application/json'
                }
            };

            const mergedOptions = { ...defaultOptions, ...options };

            const response = await fetch(url, mergedOptions);

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Error in API request to ${endpoint}: ${error}`);
            throw error;
        }
    }
}

// Export a singleton instance
export const BLE = new BLECore();
import logger from '../core/logger.js';
import CONFIG from '../core/config.js';

/**
 * Enhanced WebSocket client for real-time communication
 */

class WebSocketClient {
    constructor(url, options = {}) {
        this.url = url;
        this.options = {
            reconnectInterval: 1000, // Start with 1 second
            maxReconnectInterval: 30000, // Max 30 seconds
            reconnectDecay: 1.5, // Exponential factor
            maxReconnectAttempts: 50,
            timeout: 10000, // Connection timeout
            heartbeatInterval: 30000, // Heartbeat interval
            heartbeatMessage: JSON.stringify({ type: 'ping' }),
            queueOfflineMessages: true,
            autoReconnect: true,
            debug: false,
            ...options
        };
        
        this.socket = null;
        this.reconnectTimeout = null;
        this.heartbeatTimeout = null;
        this.connectionTimeout = null;
        this.eventHandlers = {};
        this.reconnectAttempts = 0;
        this.currentReconnectInterval = this.options.reconnectInterval;
        this.messageQueue = [];
        this.connectionState = 'disconnected'; // disconnected, connecting, connected, reconnecting
        
        // Bind methods to maintain context
        this.handleOpen = this.handleOpen.bind(this);
        this.handleMessage = this.handleMessage.bind(this);
        this.handleClose = this.handleClose.bind(this);
        this.handleError = this.handleError.bind(this);
    }
    
    /**
     * Get current connection state
     * @returns {string} - Current state
     */
    getState() {
        return this.connectionState;
    }
    
    /**
     * Connect to WebSocket server
     * @returns {Promise} - Resolves when connected
     */
    connect() {
        return new Promise((resolve, reject) => {
            if (this.socket && this.connectionState === 'connected') {
                resolve();
                return;
            }
            
            // If we're currently trying to connect, wait for that attempt
            if (this.connectionState === 'connecting') {
                this.once('connect', () => resolve());
                this.once('error', (error) => reject(error));
                return;
            }
            
            // Clean up any existing socket
            this.cleanup();
            
            this.connectionState = 'connecting';
            this.log('Connecting to WebSocket server');
            this.triggerEvent('connecting');
            
            try {
                this.socket = new WebSocket(this.url);
                
                // Set up connection timeout
                this.connectionTimeout = setTimeout(() => {
                    if (this.connectionState === 'connecting') {
                        this.log('Connection timeout', 'error');
                        this.socket.close();
                        reject(new Error('Connection timeout'));
                    }
                }, this.options.timeout);
                
                // Set up event handlers
                this.socket.addEventListener('open', (event) => {
                    this.handleOpen(event);
                    resolve();
                });
                
                this.socket.addEventListener('message', this.handleMessage);
                this.socket.addEventListener('close', this.handleClose);
                this.socket.addEventListener('error', (error) => {
                    this.handleError(error);
                    if (this.connectionState === 'connecting') {
                        reject(error);
                    }
                });
            } catch (error) {
                this.log(`Error creating WebSocket: ${error.message}`, 'error');
                this.connectionState = 'disconnected';
                this.triggerEvent('error', error);
                
                if (this.options.autoReconnect) {
                    this.scheduleReconnect();
                }
                
                reject(error);
            }
        });
    }
    
    /**
     * Handle WebSocket open event
     * @param {Event} event - Open event
     */
    handleOpen(event) {
        clearTimeout(this.connectionTimeout);
        this.connectionState = 'connected';
        this.reconnectAttempts = 0;
        this.currentReconnectInterval = this.options.reconnectInterval;
        
        this.log('WebSocket connection established');
        this.triggerEvent('connect', event);
        
        // Send any queued messages
        this.flushQueue();
        
        // Start heartbeat
        this.startHeartbeat();
    }
    
    /**
     * Handle WebSocket message event
     * @param {MessageEvent} event - Message event
     */
    handleMessage(event) {
        try {
            // Reset heartbeat timer on any message
            this.resetHeartbeat();
            
            // Parse message if it's JSON
            let data;
            try {
                data = JSON.parse(event.data);
                
                // Handle heartbeat responses
                if (data.type === 'pong') {
                    this.log('Received heartbeat response');
                    return;
                }
                
                // Trigger specific event if type exists
                if (data.type) {
                    this.triggerEvent(data.type, data);
                }
            } catch (e) {
                // Not JSON, use raw data
                data = event.data;
            }
            
            // Trigger general message event
            this.triggerEvent('message', data);
        } catch (error) {
            this.log('Error handling WebSocket message', 'error');
            this.triggerEvent('error', error);
        }
    }
    
    /**
     * Handle WebSocket close event
     * @param {CloseEvent} event - Close event
     */
    handleClose(event) {
        this.cleanup();
        
        if (event.wasClean) {
            this.log(`WebSocket connection closed cleanly, code=${event.code}, reason=${event.reason}`);
            this.connectionState = 'disconnected';
        } else {
            this.log('WebSocket connection died unexpectedly', 'error');
            this.connectionState = 'reconnecting';
        }
        
        this.triggerEvent('disconnect', event);
        
        // Reconnect after delay if auto reconnect is enabled
        if (this.options.autoReconnect && event.code !== 1000) {
            this.scheduleReconnect();
        }
    }
    
    /**
     * Handle WebSocket error event
     * @param {Event} error - Error event
     */
    handleError(error) {
        this.log(`WebSocket error: ${error.message || 'Unknown error'}`, 'error');
        this.triggerEvent('error', error);
    }
    
    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            this.log(`Maximum reconnect attempts (${this.options.maxReconnectAttempts}) reached`, 'error');
            this.connectionState = 'disconnected';
            this.triggerEvent('reconnect_failed');
            return;
        }
        
        clearTimeout(this.reconnectTimeout);
        
        this.reconnectTimeout = setTimeout(() => {
            this.reconnectAttempts++;
            this.log(`Reconnecting... Attempt ${this.reconnectAttempts}/${this.options.maxReconnectAttempts}`);
            this.triggerEvent('reconnecting', { attempt: this.reconnectAttempts });
            
            this.connect().catch(() => {
                // Connect failed, exponential backoff for next attempt
                this.currentReconnectInterval = Math.min(
                    this.currentReconnectInterval * this.options.reconnectDecay,
                    this.options.maxReconnectInterval
                );
            });
        }, this.currentReconnectInterval);
    }
    
    /**
     * Start heartbeat mechanism
     */
    startHeartbeat() {
        if (!this.options.heartbeatInterval) return;
        
        this.heartbeatTimeout = setInterval(() => {
            if (this.connectionState === 'connected') {
                this.log('Sending heartbeat');
                this.send(this.options.heartbeatMessage);
            }
        }, this.options.heartbeatInterval);
    }
    
    /**
     * Reset heartbeat timer
     */
    resetHeartbeat() {
        if (!this.options.heartbeatInterval) return;
        
        clearInterval(this.heartbeatTimeout);
        this.startHeartbeat();
    }
    
    /**
     * Clean up resources
     */
    cleanup() {
        clearTimeout(this.connectionTimeout);
        clearTimeout(this.reconnectTimeout);
        clearInterval(this.heartbeatTimeout);
        
        if (this.socket) {
            // Remove event listeners to avoid memory leaks
            this.socket.removeEventListener('open', this.handleOpen);
            this.socket.removeEventListener('message', this.handleMessage);
            this.socket.removeEventListener('close', this.handleClose);
            this.socket.removeEventListener('error', this.handleError);
            
            // Close socket if it's still open
            if (this.socket.readyState === WebSocket.OPEN) {
                this.socket.close();
            }
            
            this.socket = null;
        }
    }
    
    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        this.options.autoReconnect = false; // Disable auto reconnect
        this.cleanup();
        this.connectionState = 'disconnected';
        this.triggerEvent('disconnect', { manual: true });
    }
    
    /**
     * Send data through WebSocket
     * @param {Object|string} data - Data to send
     * @returns {boolean} - Success status
     */
    send(data) {
        if (this.connectionState !== 'connected') {
            if (this.options.queueOfflineMessages) {
                this.queueMessage(data);
                return false;
            } else {
                this.log('Attempted to send message while disconnected', 'warn');
                return false;
            }
        }
        
        try {
            const message = typeof data === 'string' ? data : JSON.stringify(data);
            this.socket.send(message);
            return true;
        } catch (error) {
            this.log('Error sending WebSocket message', 'error');
            this.triggerEvent('error', error);
            return false;
        }
    }
    
    /**
     * Queue a message for later sending
     * @param {Object|string} data - Message to queue
     */
    queueMessage(data) {
        this.log('Queueing message for later delivery');
        this.messageQueue.push(data);
        
        // Limit queue size
        if (this.messageQueue.length > 100) {
            this.messageQueue.shift();
        }
    }
    
    /**
     * Send all queued messages
     */
    flushQueue() {
        if (this.messageQueue.length === 0) return;
        
        this.log(`Sending ${this.messageQueue.length} queued messages`);
        
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.send(message);
        }
    }
    
    /**
     * Subscribe to an event
     * @param {string} eventName - Event name
     * @param {Function} callback - Event handler
     * @returns {Function} - Unsubscribe function
     */
    on(eventName, callback) {
        if (!this.eventHandlers[eventName]) {
            this.eventHandlers[eventName] = [];
        }
        this.eventHandlers[eventName].push(callback);
        
        // Return unsubscribe function
        return () => this.off(eventName, callback);
    }
    
    /**
     * Subscribe to an event for a single execution
     * @param {string} eventName - Event name
     * @param {Function} callback - Event handler
     * @returns {Function} - Unsubscribe function
     */
    once(eventName, callback) {
        const onceHandler = (data) => {
            this.off(eventName, onceHandler);
            callback(data);
        };
        
        return this.on(eventName, onceHandler);
    }
    
    /**
     * Unsubscribe from an event
     * @param {string} eventName - Event name
     * @param {Function} callback - Event handler to remove
     */
    off(eventName, callback) {
        if (this.eventHandlers[eventName]) {
            this.eventHandlers[eventName] = this.eventHandlers[eventName].filter(
                handler => handler !== callback
            );
        }
    }
    
    /**
     * Unsubscribe from all events
     * @param {string} [eventName] - Optional event name to clear
     */
    offAll(eventName = null) {
        if (eventName) {
            this.eventHandlers[eventName] = [];
        } else {
            this.eventHandlers = {};
        }
    }
    
    /**
     * Trigger an event
     * @param {string} eventName - Event name
     * @param {*} data - Event data
     */
    triggerEvent(eventName, data) {
        const handlers = this.eventHandlers[eventName] || [];
        
        handlers.forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                this.log(`Error in WebSocket ${eventName} handler: ${error.message}`, 'error');
            }
        });
    }
    
    /**
     * Log a message based on debug setting
     * @param {string} message - Message to log
     * @param {string} level - Log level
     */
    log(message, level = 'info') {
        if (!this.options.debug && level !== 'error') return;
        
        if (level === 'error') {
            logger.error(`WebSocket: ${message}`);
        } else if (level === 'warn') {
            logger.warn(`WebSocket: ${message}`);
        } else {
            logger.info(`WebSocket: ${message}`);
        }
    }
}

// Create and export the WebSocket client instance
const wsUrl = CONFIG.wsUrl || `ws://${window.location.host}/ws`;
const ws = new WebSocketClient(wsUrl, {
    debug: CONFIG.debug || false,
    queueOfflineMessages: true
});

export default ws;
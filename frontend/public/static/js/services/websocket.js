/**
 * WebSocket service for live updates
 */
import logger from '../core/logger.js';

class WebSocketService {
    constructor(config) {
        this.config = config;
        this.socket = null;
        this.isConnected = false;
        this.reconnectTimer = null;
        this.reconnectInterval = 5000; // 5 seconds
        this.handlers = {};
        
        // Initialize connection if configured
        if (this.config.wsUrl) {
            this.connect();
        }
    }
    
    connect() {
        if (this.socket) this.disconnect();
        
        try {
            this.socket = new WebSocket(this.config.wsUrl);
            
            this.socket.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.triggerEvent('connect');
                
                if (this.reconnectTimer) {
                    clearTimeout(this.reconnectTimer);
                    this.reconnectTimer = null;
                }
            };
            
            this.socket.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.triggerEvent('disconnect');
                
                // Attempt to reconnect
                if (!this.reconnectTimer) {
                    this.reconnectTimer = setTimeout(() => {
                        this.connect();
                    }, this.reconnectInterval);
                }
            };
            
            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Error processing WebSocket message:', error);
                }
            };
            
            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.triggerEvent('error', error);
            };
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            
            // Schedule reconnect
            if (!this.reconnectTimer) {
                this.reconnectTimer = setTimeout(() => {
                    this.connect();
                }, this.reconnectInterval);
            }
        }
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
    }
    
    handleMessage(data) {
        // Handle different message types
        if (data.type && this.handlers[data.type]) {
            this.handlers[data.type](data);
        }
        
        // Also trigger a general message event
        this.triggerEvent('message', data);
    }
    
    registerHandler(type, callback) {
        this.handlers[type] = callback;
    }
    
    on(event, callback) {
        if (!this.eventHandlers) this.eventHandlers = {};
        if (!this.eventHandlers[event]) this.eventHandlers[event] = [];
        this.eventHandlers[event].push(callback);
    }
    
    off(event, callback) {
        if (!this.eventHandlers || !this.eventHandlers[event]) return;
        
        if (callback) {
            this.eventHandlers[event] = this.eventHandlers[event].filter(
                handler => handler !== callback
            );
        } else {
            delete this.eventHandlers[event];
        }
    }
    
    triggerEvent(event, data) {
        if (!this.eventHandlers || !this.eventHandlers[event]) return;
        
        this.eventHandlers[event].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`Error in WebSocket ${event} handler:`, error);
            }
        });
    }
}

export default WebSocketService;
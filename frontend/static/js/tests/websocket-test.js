/**
 * Test script for WebSocket functionality
 * Run this in the browser console to diagnose WebSocket issues
 */

function testWebSockets() {
    console.log("Starting WebSocket connection tests...");
    
    // Test variables
    const TOKEN = localStorage.getItem('ws_auth_token') || 'test_token';
    const ENDPOINTS = [
        { type: 'ble', endpoint: '/ws/ble' },
        { type: 'uwb', endpoint: '/ws/uwb' },
        { type: 'biometric', endpoint: '/ws/biometric' },
        { type: 'card', endpoint: '/ws/card' },
        { type: 'mqtt', endpoint: '/ws/mqtt' }
    ];
    
    // Test each endpoint
    ENDPOINTS.forEach(({ type, endpoint }) => {
        testEndpoint(type, endpoint, TOKEN);
    });
}

function testEndpoint(type, endpoint, token) {
    console.log(`Testing ${type} WebSocket connection...`);
    
    // Create WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let wsUrl = `${protocol}//${window.location.host}${endpoint}`;
    
    // Add authentication token
    if (token) {
        wsUrl += (wsUrl.includes('?') ? '&' : '?') + `token=${encodeURIComponent(token)}`;
    }
    
    // Create connection
    const socket = new WebSocket(wsUrl);
    
    // Set timeout
    const connectionTimeout = setTimeout(() => {
        if (socket.readyState !== WebSocket.OPEN) {
            console.error(`[${type}] Connection timeout`);
        }
    }, 5000);
    
    // Connection opened
    socket.onopen = () => {
        clearTimeout(connectionTimeout);
        console.log(`[${type}] Connection established`);
        
        // Send a ping message
        socket.send(JSON.stringify({
            type: 'ping',
            data: { timestamp: Date.now() }
        }));
        console.log(`[${type}] Sent ping message`);
    };
    
    // Listen for messages
    socket.onmessage = (event) => {
        try {
            // Try to parse as JSON
            const message = typeof event.data === 'string' ? 
                (event.data.startsWith('{') ? JSON.parse(event.data) : event.data) : 
                'binary data';
            console.log(`[${type}] Received:`, message);
            
            // If we got a pong, connection is working
            if (typeof message === 'object' && message.type === 'pong') {
                console.log(`[${type}] WebSocket ping-pong successful!`);
                
                // Close the connection after successful test
                setTimeout(() => {
                    socket.close(1000, "Test completed");
                }, 1000);
            }
        } catch (error) {
            console.error(`[${type}] Error parsing message:`, error);
        }
    };
    
    // Connection closed
    socket.onclose = (event) => {
        clearTimeout(connectionTimeout);
        console.log(`[${type}] Connection closed:`, {
            clean: event.wasClean,
            code: event.code,
            reason: event.reason
        });
    };
    
    // Connection error
    socket.onerror = (error) => {
        clearTimeout(connectionTimeout);
        console.error(`[${type}] WebSocket error:`, error);
    };
}

// Expose function globally
window.testWebSockets = testWebSockets;

console.log("WebSocket test script loaded. Run testWebSockets() to begin testing.");

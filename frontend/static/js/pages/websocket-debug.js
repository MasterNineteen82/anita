/**
 * Debug tool for WebSocket Manager
 * This will help identify issues with DOM elements and event listeners
 */

function debugWebSocketManager() {
    console.group('WebSocket Manager Debug');
    console.log('Running WebSocket Manager debug tool...');
    
    // Check all DOM elements referenced in websocket-manager.js
    const elements = {
        // Connection status elements
        'uwb-connection-status': document.getElementById('uwb-connection-status'),
        'biometric-connection-status': document.getElementById('biometric-connection-status'),
        'card-connection-status': document.getElementById('card-connection-status'),
        'ble-connection-status': document.getElementById('ble-connection-status'),
        'mqtt-connection-status': document.getElementById('mqtt-connection-status'),
        
        // Connection buttons
        'connect-uwb-btn': document.getElementById('connect-uwb-btn'),
        'disconnect-uwb-btn': document.getElementById('disconnect-uwb-btn'),
        'connect-biometric-btn': document.getElementById('connect-biometric-btn'),
        'disconnect-biometric-btn': document.getElementById('disconnect-biometric-btn'),
        'connect-card-btn': document.getElementById('connect-card-btn'),
        'disconnect-card-btn': document.getElementById('disconnect-card-btn'),
        'connect-ble-btn': document.getElementById('connect-ble-btn'),
        'disconnect-ble-btn': document.getElementById('disconnect-ble-btn'),
        'connect-mqtt-btn': document.getElementById('connect-mqtt-btn'),
        'disconnect-mqtt-btn': document.getElementById('disconnect-mqtt-btn'),
        
        // Global connection buttons
        'connect-all-btn': document.getElementById('connect-all-btn'),
        'disconnect-all-btn': document.getElementById('disconnect-all-btn'),
        
        // Message composer elements
        'ws-endpoint': document.getElementById('ws-endpoint'),
        'message-type': document.getElementById('message-type'),
        'message-payload': document.getElementById('message-payload'),
        'auth-token': document.getElementById('auth-token'),
        'save-token': document.getElementById('save-token'),
        
        // Message composer buttons
        'send-message-btn': document.getElementById('send-message-btn'),
        'clear-message-btn': document.getElementById('clear-message-btn'),
        
        // Log and event elements
        'log-container': document.getElementById('log-container'),
        'event-container': document.getElementById('event-container'),
        'activity-log': document.getElementById('activity-log'),
        
        // Filter elements
        'filter-log': document.getElementById('filter-log'),
        'filter-endpoint': document.getElementById('filter-endpoint'),
        'filter-direction': document.getElementById('filter-direction'),
        
        // Log and event buttons
        'clear-log-btn': document.getElementById('clear-log-btn'),
        'clear-events-btn': document.getElementById('clear-events-btn'),
        'export-log-btn': document.getElementById('export-log-btn'),
        
        // Connection stats
        'connection-stats': document.getElementById('connection-stats'),
        'stats-content': document.getElementById('stats-content')
    };
    
    // Check which elements are missing
    const missingElements = [];
    
    for (const [id, element] of Object.entries(elements)) {
        if (!element) {
            missingElements.push(id);
            console.error(`Element #${id} not found in DOM`);
        } else {
            console.log(`Element #${id} found in DOM`);
        }
    }
    
    if (missingElements.length > 0) {
        console.error(`Found ${missingElements.length} missing elements`, missingElements);
    } else {
        console.log('All elements found in DOM');
    }
    
    // Check for script errors
    const scriptErrors = window.onerror;
    if (scriptErrors) {
        console.error('Script errors detected:', scriptErrors);
    }
    
    // Test WebSocket CORS
    console.log('Testing WebSocket connection...');
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const testUrl = `${protocol}//${window.location.host}/ws/ble`;
        console.log(`Attempting test connection to ${testUrl}`);
        
        const testSocket = new WebSocket(testUrl);
        testSocket.onopen = () => {
            console.log('Test WebSocket connection successful!');
            testSocket.close();
        };
        
        testSocket.onerror = (error) => {
            console.error('Test WebSocket connection failed:', error);
        };
    } catch (error) {
        console.error('Error creating test WebSocket:', error);
    }
    
    console.log('Debug complete');
    console.groupEnd();
    
    return {
        missingElements,
        elements
    };
}

// Add debug function to window for console access
window.debugWebSocketManager = debugWebSocketManager;

// Auto-run when loaded in a script tag
console.log('WebSocket debug tool loaded. Run debugWebSocketManager() in console to diagnose issues.');

// Export function for module usage
export default debugWebSocketManager;

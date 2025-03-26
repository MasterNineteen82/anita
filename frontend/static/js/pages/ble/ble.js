import { initializeUI, updateStatus, updateScanStatus, logMessage, setLoading, updateSubscriptionStatus } from './ble-ui.js';
import { connectToDevice as connectToDeviceOriginal, disconnectFromDevice, pairWithDevice } from './ble-connection.js';
import { scanDevices, scanDevicesWithErrorHandling } from './ble-scanning.js';
import { getServices, getCharacteristics, readCharacteristic, writeCharacteristic, toggleNotification } from './ble-services.js';
import { connectWebSocket, handleWebSocketMessage } from './ble-websocket.js';
import { initializeDebugPanel, initializeDebugShortcuts } from './ble-debug.js';
import { createErrorBoundary } from '../../components/error_boundary.js';
import { BLEEventEmitter, BLE_EVENTS } from './ble-events.js';
import { getBatteryLevel, powerEfficientScan } from './ble-power.js';
import { getDeviceInformation } from './ble-device-info.js';
import { initializeAdvancedFeatures } from './ble-advanced.js';

// Initialize event system and make globally available
const bleEvents = new BLEEventEmitter();
window.bleEvents = bleEvents;

// Set up event handlers
bleEvents.on(BLE_EVENTS.DEVICE_CONNECTED, (device) => {
    updateStatus(state, 'connected', `Connected to ${device.name || 'device'}`);
    
    // Check device battery after connection
    setTimeout(() => {
        getBatteryLevel(state)
            .catch(err => logMessage(`Unable to check battery: ${err.message}`, 'warning'));
        
        getDeviceInformation(state)
            .catch(err => logMessage(`Unable to get device info: ${err.message}`, 'warning'));
    }, 1000);
});

bleEvents.on(BLE_EVENTS.DEVICE_DISCONNECTED, () => {
    // Handle disconnect events
    updateStatus(state, 'disconnected', 'Device disconnected');
    
    // Hide battery indicator when disconnected
    if (state.domElements.batteryContainer) {
        state.domElements.batteryContainer.classList.add('hidden');
    }
});

// Enhanced state object
const state = {
    connectedDevice: null,
    subscribedCharacteristics: new Set(),
    socketConnected: false,
    socket: null,
    scanningActive: false,
    connectionInProgress: false,
    lastConnectionAttempt: null,
    deviceInfo: null,
    batteryLevel: null,
    reconnectAttempts: 0,
    domElements: {},
    eventBus: {
        listeners: {},
        on(event, callback) {
            if (!this.listeners[event]) {
                this.listeners[event] = [];
            }
            this.listeners[event].push(callback);
        },
        emit(event, data) {
            if (this.listeners[event]) {
                this.listeners[event].forEach(callback => callback(data));
            }
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    console.log("BLE Manager initializing...");
    initializeDomReferences();
    initializeUI(state);
    initializeDebugPanel(state);
    initializeDebugShortcuts(state);
    
    setupEventListeners();
    setupErrorBoundaries();
    
    updateStatus(state, 'disconnected', 'Not connected to any device');
    updateScanStatus(state, 'idle', 'Inactive');
    logMessage('BLE Manager initialized', 'success');
    
    // Connect to WebSocket with retry
    connectWebSocketWithRetry();
    
    // Try to reconnect to last device if auto-reconnect is enabled
    tryAutoReconnect();
    
    // Initialize advanced features
    initializeAdvancedFeatures(state);
    
    console.log("BLE Manager initialization complete");
});

function setupEventListeners() {
    if (state.domElements.clearLogBtn) {
        state.domElements.clearLogBtn.addEventListener('click', () => {
            if (state.domElements.logContainer) {
                state.domElements.logContainer.innerHTML = '';
            }
        });
    }
    
    // Add battery refresh button handler
    if (state.domElements.refreshBatteryBtn) {
        state.domElements.refreshBatteryBtn.addEventListener('click', () => {
            getBatteryLevel(state)
                .catch(err => logMessage(`Unable to refresh battery: ${err.message}`, 'warning'));
        });
    }
}

function initializeDomReferences() {
    const elements = {
        scanBtn: document.getElementById('scan-btn'),
        deviceList: document.getElementById('device-list'),
        statusIndicatorContainer: document.getElementById('status-indicator-container'),
        loadingIndicator: document.getElementById('loading-indicator'),
        disconnectBtn: document.getElementById('disconnect-btn'),
        logContainer: document.getElementById('ble-log-container'),
        clearLogBtn: document.getElementById('clear-log-btn'),
        showDebugBtn: document.getElementById('show-debug'),
        debugPanel: document.getElementById('debug-panel'),
        debugToggleBtn: document.getElementById('debug-toggle'),
        debugSendBtn: document.getElementById('debug-send'),
        debugEndpointSelect: document.getElementById('debug-endpoint'),
        debugResponseContainer: document.getElementById('debug-response'),
        scanStatus: document.getElementById('scan-status'),
        servicesList: document.getElementById('services-list'),
        characteristicsList: document.getElementById('characteristics-list'),
        notificationsContainer: document.getElementById('notifications-container'),
        scanContainer: document.getElementById('scan-container'),
        // Add battery-related elements
        batteryLevel: document.getElementById('battery-level'),
        batteryIcon: document.getElementById('battery-icon'),
        batteryContainer: document.getElementById('battery-container'),
        refreshBatteryBtn: document.getElementById('refresh-battery-btn'),
        // Add device info elements
        deviceInfoContainer: document.getElementById('device-info-container')
    };
    
    state.domElements = Object.fromEntries(
        Object.entries(elements).map(([key, value]) => {
            if (!value) console.warn(`DOM element "${key}" not found`);
            return [key, value];
        })
    );
}

// Enhanced connect to device function that uses event system
async function connectToDevice(state, deviceId, deviceName) {
    // Prevent multiple simultaneous connection attempts
    if (state.connectionInProgress) {
        logMessage('Connection already in progress, please wait', 'warning');
        return false;
    }
    
    state.connectionInProgress = true;
    state.lastConnectionAttempt = Date.now();
    
    try {
        bleEvents.emit(BLE_EVENTS.DEVICE_CONNECTING, { id: deviceId, name: deviceName });
        
        // Call the original connection function
        const result = await connectToDeviceOriginal(state, deviceId, deviceName);
        
        if (result) {
            // Save to connection history
            saveToConnectionHistory(deviceId, deviceName);
            
            // Emit connected event with device data
            bleEvents.emit(BLE_EVENTS.DEVICE_CONNECTED, { 
                address: deviceId, 
                name: deviceName 
            });
            
            // Emit connection state change event
            state.eventBus.emit('CONNECTION_STATE_CHANGED', true);
            state.eventBus.emit('DEVICE_SELECTED', { address: deviceId, name: deviceName });
        }
        
        return result;
    } catch (error) {
        logMessage(`Connection error: ${error.message}`, 'error');
        bleEvents.emit(BLE_EVENTS.CONNECTION_ERROR, { 
            id: deviceId, 
            name: deviceName,
            error: error.message 
        });
        return false;
    } finally {
        state.connectionInProgress = false;
    }
}

// Helper to save device to connection history
function saveToConnectionHistory(deviceId, deviceName) {
    try {
        const history = JSON.parse(localStorage.getItem('bleConnectionHistory') || '[]');
        
        // Add to beginning, remove duplicates, limit to 5 devices
        const updatedHistory = [
            { id: deviceId, name: deviceName, lastConnected: new Date().toISOString() },
            ...history.filter(device => device.id !== deviceId)
        ].slice(0, 5);
        
        localStorage.setItem('bleConnectionHistory', JSON.stringify(updatedHistory));
        localStorage.setItem('bleLastConnectedDevice', deviceId);
    } catch (e) {
        console.error('Error saving connection history:', e);
    }
}

// Try to reconnect to the last device
function tryAutoReconnect() {
    const autoReconnect = localStorage.getItem('bleAutoReconnect') === 'true';
    if (!autoReconnect) return;
    
    const lastDeviceId = localStorage.getItem('bleLastConnectedDevice');
    if (!lastDeviceId) return;
    
    try {
        const history = JSON.parse(localStorage.getItem('bleConnectionHistory') || '[]');
        const lastDevice = history.find(device => device.id === lastDeviceId);
        
        if (lastDevice) {
            logMessage(`Attempting to reconnect to last device: ${lastDevice.name || lastDevice.id}`, 'info');
            setTimeout(() => {
                connectToDevice(state, lastDevice.id, lastDevice.name);
            }, 1500);
        }
    } catch (e) {
        console.error('Error during auto-reconnect:', e);
    }
}

// Connect to WebSocket with retry
function connectWebSocketWithRetry(attemptCount = 0) {
    connectWebSocket(state).catch(error => {
        const maxRetries = 5;
        const delay = Math.min(30000, Math.pow(2, attemptCount) * 1000);
        
        if (attemptCount < maxRetries) {
            logMessage(`WebSocket connection failed. Retrying in ${delay/1000}s...`, 'warning');
            setTimeout(() => connectWebSocketWithRetry(attemptCount + 1), delay);
        } else {
            logMessage('Failed to establish WebSocket connection after multiple attempts', 'error');
        }
    });
}

function setupErrorBoundaries() {
    // Error boundaries implementation (existing code)
    // ...
}

// Add this event listener to handle connecting to bonded devices
window.addEventListener('CONNECT_TO_DEVICE', (event) => {
    const { address } = event.detail;
    if (address) {
        connectToDevice(state, address)
            .catch(error => {
                logMessage(`Failed to connect to bonded device: ${error.message}`, 'error');
            });
    }
});

// Export the properly wrapped functions
export {
    state,
    initializeUI,
    updateStatus,
    updateScanStatus,
    logMessage,
    setLoading,
    updateSubscriptionStatus,
    connectToDevice,
    disconnectFromDevice,
    pairWithDevice,
    scanDevices,
    scanDevicesWithErrorHandling,
    getServices,
    getCharacteristics,
    readCharacteristic,
    writeCharacteristic,
    toggleNotification,
    connectWebSocket,
    handleWebSocketMessage,
    initializeDebugPanel,
    initializeDebugShortcuts,
    getBatteryLevel,
    powerEfficientScan,
    getDeviceInformation
};
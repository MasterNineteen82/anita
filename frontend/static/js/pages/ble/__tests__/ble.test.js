import { initializeUI, updateStatus, updateScanStatus, logMessage, setLoading, updateSubscriptionStatus, enableDebugMode } from './ble-ui.js';
import { connectToDevice as connectToDeviceOriginal, disconnectFromDevice, pairWithDevice } from './ble-connection.js';
import { scanDevices, scanDevicesWithErrorHandling } from './ble-scanning.js';
import { getServices, getCharacteristics, readCharacteristic, writeCharacteristic, toggleNotification } from './ble-services.js';
import { connectWebSocket, handleWebSocketMessage } from './ble-websocket.js';
import { initializeDebugPanel, initializeDebugShortcuts } from './ble-debug.js';
import { bleEventEmitter, BLE_EVENTS } from './ble-events.js';
import { getBatteryLevel, powerEfficientScan } from './ble-power.js';
import { getDeviceInformation } from './ble-device-info.js';
import { initializeAdvancedFeatures } from './ble-advanced.js';
import { initializeAdapterInfo, resetAdapter } from './ble-adapter.js';
import { initializeRecovery } from './ble-recovery.js';
import { runDiagnostics } from './ble-debug-helper.js';

// Initialize event system and make globally available
const bleEvents = bleEventEmitter;
window.bleEvents = bleEvents;

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

// Make state globally available for debugging
window.bleState = state;

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

document.addEventListener('DOMContentLoaded', () => {
    try {
        console.log('BLE Manager initializing...');
        
        // Enable debug mode in development
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            enableDebugMode();
        }
        
        // Initialize UI first to ensure DOM elements are accessible
        initializeUI(state);
        
        // Initialize DOM references
        initializeDomReferences();
        
        // Setup error boundaries
        setupErrorBoundaries();
        
        // Connect WebSocket
        connectWebSocketWithRetry();
        
        // Setup event listeners after DOM elements are initialized
        setupEventListeners();
        
        // Initialize recovery subsystem
        initializeRecovery(state);
        
        // Initialize adapter info and controls
        initializeAdapterUI();
        
        // Initialize advanced features
        initializeAdvancedFeatures(state);
        
        // Initialize debug panel
        initializeDebugPanel(state);
        
        // Expose diagnostics function globally
        window.runBleDiagnostics = runDiagnostics;
        
        // Attempt auto-reconnect
        tryAutoReconnect();
        
        logMessage('BLE Manager initialized successfully', 'success');
    } catch (error) {
        console.error('Failed to initialize BLE Manager:', error);
        
        // Run diagnostics automatically when there's an error
        setTimeout(() => {
            try {
                runDiagnostics();
            } catch (diagError) {
                console.error('Failed to run diagnostics:', diagError);
            }
        }, 500);
        
        // Add visible error message to page
        const errorBanner = document.createElement('div');
        errorBanner.className = 'fixed top-0 left-0 right-0 bg-red-600 text-white p-4 text-center z-50';
        errorBanner.innerHTML = `
            <p>Failed to initialize BLE Manager: ${error.message}</p>
            <p class="text-sm mt-2">Check the console for more details.</p>
            <button id="retry-init-btn" class="bg-white text-red-600 px-4 py-1 rounded mt-2">Retry</button>
        `;
        document.body.prepend(errorBanner);
        
        // Add retry button handler
        const retryButton = document.getElementById('retry-init-btn');
        if (retryButton) {
            retryButton.addEventListener('click', () => {
                errorBanner.remove();
                window.location.reload();
            });
        }
    }
});

// Try to reconnect to the last device
function tryAutoReconnect() {
    const autoReconnect = localStorage.getItem('bleAutoReconnect') === 'true';
    
    if (autoReconnect) {
        const lastDeviceId = localStorage.getItem('bleLastConnectedDevice');
        if (lastDeviceId) {
            logMessage('Attempting to reconnect to last device...', 'info');
            setTimeout(() => {
                connectToDevice(state, lastDeviceId)
                    .catch(err => logMessage(`Auto-reconnect failed: ${err.message}`, 'warning'));
            }, 1000);
        }
    }
}

function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Scan button
    if (state.domElements.scanBtn) {
        console.log('Attaching event listener to scan button');
        state.domElements.scanBtn.addEventListener('click', async () => {
            if (state.scanningActive) {
                logMessage('Scan already in progress', 'warning');
                return;
            }
            
            try {
                state.scanningActive = true;
                updateScanStatus(state, 'scanning', 'Scanning for devices...');
                
                // Clear previous results
                const deviceList = state.domElements.deviceList;
                if (deviceList) deviceList.innerHTML = '';
                
                // Execute scan
                const devices = await scanDevicesWithErrorHandling(5, true);
                
                // Display results
                displayDevices(devices);
                
                updateScanStatus(state, 'complete', `Found ${devices.length} devices`);
            } catch (error) {
                console.error('Scanning error:', error);
                logMessage(`Scanning error: ${error.message}`, 'error');
                updateScanStatus(state, 'error', 'Scan failed');
            } finally {
                state.scanningActive = false;
            }
        });
    } else {
        console.warn('Scan button not found in DOM');
    }
    
    // Clear log button
    if (state.domElements.clearLogBtn) {
        state.domElements.clearLogBtn.addEventListener('click', () => {
            if (state.domElements.logContainer) {
                state.domElements.logContainer.innerHTML = '';
                logMessage('Log cleared', 'info');
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
    
    // Disconnect button
    if (state.domElements.disconnectBtn) {
        state.domElements.disconnectBtn.addEventListener('click', () => {
            if (state.connectedDevice) {
                disconnectFromDevice(state)
                    .then(success => {
                        if (success) {
                            logMessage('Device disconnected successfully', 'success');
                        }
                    })
                    .catch(err => logMessage(`Disconnect error: ${err.message}`, 'error'));
            } else {
                logMessage('No device connected', 'warning');
            }
        });
    }
    
    // Debug toggle button
    if (state.domElements.debugToggleBtn && state.domElements.debugPanel) {
        state.domElements.debugToggleBtn.addEventListener('click', () => {
            state.domElements.debugPanel.classList.toggle('hidden');
        });
    }
    
    console.log('Event listeners setup complete');
}

function initializeDomReferences() {
    console.log('Initializing DOM references...');
    
    // Create container for dynamically added elements if needed
    let dynamicContainer = document.getElementById('ble-dynamic-elements');
    if (!dynamicContainer) {
        dynamicContainer = document.createElement('div');
        dynamicContainer.id = 'ble-dynamic-elements';
        document.body.appendChild(dynamicContainer);
    }
    
    // Helper to get or create element
    const getOrCreateElement = (id, type = 'div', parent = dynamicContainer) => {
        let element = document.getElementById(id);
        if (!element) {
            element = document.createElement(type);
            element.id = id;
            parent.appendChild(element);
            console.log(`Created missing element "${id}"`);
        }
        return element;
    };
    
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
        batteryLevel: getOrCreateElement('battery-level'),
        batteryIcon: getOrCreateElement('battery-icon'),
        batteryContainer: getOrCreateElement('battery-container'),
        refreshBatteryBtn: getOrCreateElement('refresh-battery-btn', 'button'),
        // Add device info elements
        deviceInfoContainer: getOrCreateElement('device-info-container')
    };
    
    // Setup created elements
    if (elements.refreshBatteryBtn && elements.refreshBatteryBtn.textContent === '') {
        elements.refreshBatteryBtn.textContent = 'Refresh Battery';
    }
    
    state.domElements = elements;
    console.log('DOM references initialized');
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

// Function to display scanned devices
function displayDevices(devices) {
    const deviceList = state.domElements.deviceList;
    if (!deviceList) return;
    
    // Clear existing list
    deviceList.innerHTML = '';
    
    if (devices.length === 0) {
        deviceList.innerHTML = '<div class="text-center py-4 text-gray-500">No devices found</div>';
        return;
    }
    
    // Sort devices by signal strength (RSSI)
    devices.sort((a, b) => b.rssi - a.rssi);
    
    devices.forEach(device => {
        const deviceCard = document.createElement('div');
        deviceCard.className = 'device-card bg-gray-800 rounded-lg p-3 mb-2 hover:bg-gray-700 transition-colors';
        
        const deviceName = device.name || 'Unknown Device';
        const deviceId = device.address;
        const rssi = device.rssi || 'N/A';
        
        // Determine signal strength indicator
        let signalStrength = 'weak';
        let signalColor = 'text-red-400';
        
        if (rssi >= -60) {
            signalStrength = 'excellent';
            signalColor = 'text-green-400';
        } else if (rssi >= -70) {
            signalStrength = 'good';
            signalColor = 'text-blue-400';
        } else if (rssi >= -80) {
            signalStrength = 'fair';
            signalColor = 'text-yellow-400';
        }
        
        deviceCard.innerHTML = `
            <div class="flex justify-between items-center">
                <div>
                    <div class="font-medium text-white">${deviceName}</div>
                    <div class="text-xs text-gray-400">${deviceId}</div>
                    <div class="text-xs ${signalColor}">Signal: ${signalStrength} (${rssi} dBm)</div>
                </div>
                <button class="connect-btn bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                    Connect
                </button>
            </div>
        `;
        
        deviceList.appendChild(deviceCard);
        
        // Add connect button handler
        deviceCard.querySelector('.connect-btn').addEventListener('click', () => {
            connectToDevice(state, deviceId, deviceName)
                .catch(error => {
                    logMessage(`Connection error: ${error.message}`, 'error');
                });
        });
    });
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

// Connect to WebSocket with retry
async function connectWebSocketWithRetry(attemptCount = 0) {
    try {
        await connectWebSocket(state);
    } catch (err) {
        const maxRetries = 5;
        const delay = Math.min(30000, Math.pow(2, attemptCount) * 1000);
        
        if (attemptCount < maxRetries) {
            logMessage(`WebSocket connection failed: ${err.message}. Retrying in ${delay/1000}s...`, 'warning');
            setTimeout(() => connectWebSocketWithRetry(attemptCount + 1), delay);
        } else {
            logMessage(`Failed to establish WebSocket connection after multiple attempts: ${err.message}`, 'error');
        }
    }
}

function setupErrorBoundaries() {
    // Simple error handling for UI components
    window.addEventListener('error', (event) => {
        console.error('Caught in error boundary:', event.error);
        logMessage(`Error: ${event.error?.message || 'Unknown error occurred'}`, 'error');
        return false;
    });
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

// Initialize adapter info UI and controls
function initializeAdapterUI() {
    console.log('Initializing adapter UI...');
    
    // Initialize adapter info
    initializeAdapterInfo(state);
    
    // Add event listener for adapter reset button
    const resetAdapterBtn = document.getElementById('reset-adapter');
    if (resetAdapterBtn) {
        resetAdapterBtn.addEventListener('click', async () => {
            try {
                resetAdapterBtn.disabled = true;
                resetAdapterBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Resetting...';
                
                const success = await resetAdapter();
                
                if (success) {
                    // Refresh adapter info
                    initializeAdapterInfo(state);
                    logMessage('Adapter reset successful', 'success');
                } else {
                    logMessage('Adapter reset failed', 'error');
                }
            } catch (error) {
                console.error('Error resetting adapter:', error);
                logMessage(`Failed to reset adapter: ${error.message}`, 'error');
            } finally {
                resetAdapterBtn.disabled = false;
                resetAdapterBtn.innerHTML = '<i class="fas fa-power-off mr-1"></i> Reset Adapter';
            }
        });
    } else {
        console.warn('Reset adapter button not found in DOM');
    }
    
    console.log('Adapter UI initialized');
}

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
    getDeviceInformation,
    initializeAdapterInfo,
    resetAdapter
};
/**
 * @fileoverview Central module for the BLE application, orchestrating UI components,
 * connection management, scanning, service/characteristic handling, WebSocket
 * communication, debugging, power management, device information, adapter management,
 * recovery, and advanced features.
 */

// Import UI Components
import * as BleUI from './ble-ui.js';

// Import Connection Management
import * as BleConnection from './ble-connection.js';

// Import Scanning
import * as BleScanning from './ble-scanning.js';

// Import Services and Characteristics
import * as BleServices from './ble-services.js';

// Import WebSocket Communication
import * as BleWebSocket from './ble-websocket.js';

// Import Debugging
import * as BleDebug from './ble-debug.js';

// Import Event System - Updated import
import { BleEvents, BLE_EVENTS } from './ble-events.js';

// Import Battery and Power Management
import * as BlePower from './ble-power.js';

// Import Device Information
import * as BleDeviceInfo from './ble-device-info.js';

// Import Advanced Features
import * as BleAdvanced from './ble-advanced.js';

// Import Adapter Management
import * as BleAdapter from './ble-adapter.js';

// Import Recovery and Diagnostics
import * as BleRecovery from './ble-recovery.js';

// Import Device Listing and Details
import * as BleDeviceList from './ble-device-list.js';
import * as BleDeviceDetails from './ble-device-details.js';

// Make event system globally available
// Updated: Use BleEvents instead of bleEventEmitter
window.bleEvents = BleEvents;

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

// Set up event handlers - Using BleEvents
BleEvents.on(BLE_EVENTS.DEVICE_CONNECTED, (device) => {
    BleUI.updateStatus(state, 'connected', `Connected to ${device.name || 'device'}`);
    
    // Check device battery after connection
    setTimeout(() => {
        BlePower.getBatteryLevel(state)
            .catch(err => BleUI.logMessage(`Unable to check battery: ${err.message}`, 'warning'));
        
        BleDeviceInfo.getDeviceInformation(state)
            .catch(err => BleUI.logMessage(`Unable to get device info: ${err.message}`, 'warning'));
    }, 1000);
});

BleEvents.on(BLE_EVENTS.DEVICE_DISCONNECTED, () => {
    // Handle disconnect events
    BleUI.updateStatus(state, 'disconnected', 'Device disconnected');
    BleConnection.resetUIAfterDisconnect(state);
    
    // Hide battery indicator when disconnected
    if (state.domElements.batteryContainer) {
        state.domElements.batteryContainer.classList.add('hidden');
    }
});

// Add more event handlers for comprehensive event coverage
BleEvents.on(BLE_EVENTS.CONNECTION_FAILED, (data) => {
    BleUI.logMessage(`Connection error: ${data.error}`, 'error');
    BleUI.updateStatus(state, 'error', `Connection failed: ${data.error}`);
});

BleEvents.on(BLE_EVENTS.ERROR_SCAN, (data) => {
    BleUI.logMessage(`Scan error: ${data.error}`, 'error');
    BleUI.updateScanStatus(state, 'error', `Scan failed: ${data.error}`);
});

BleEvents.on(BLE_EVENTS.CHARACTERISTIC_NOTIFICATION, (data) => {
    BleUI.logMessage(`Notification from characteristic: ${data.uuid.substring(0, 8)}...`, 'info');
    // Update UI for notifications
    if (state.domElements.notificationsContainer) {
        const notificationItem = document.createElement('div');
        notificationItem.className = 'notification-item bg-gray-800 p-2 mb-1 rounded';
        notificationItem.textContent = `${new Date().toLocaleTimeString()}: ${data.value}`;
        state.domElements.notificationsContainer.prepend(notificationItem);
        
        // Limit to 10 notifications
        const notifications = state.domElements.notificationsContainer.children;
        if (notifications.length > 10) {
            state.domElements.notificationsContainer.removeChild(notifications[notifications.length - 1]);
        }
    }
});

document.addEventListener('DOMContentLoaded', async () => {
    try {
        console.log('BLE Manager initializing...');
        
        // Enable debug mode in development
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            BleUI.enableDebugMode();
        }
        
        // Initialize UI first to ensure DOM elements are accessible
        await BleUI.initializeUI(state);
        
        // Initialize DOM references
        initializeDomReferences();
        
        // Setup error boundaries
        setupErrorBoundaries();
        
        // Initialize connection manager
        BleConnection.initializeConnectionManager(state);
        
        // Initialize device list and details components
        BleDeviceList.initializeDeviceList(state);
        BleDeviceDetails.initializeDeviceDetails(state);
        
        // Connect WebSocket
        connectWebSocketWithRetry();
        
        // Setup event listeners after DOM elements are initialized
        setupEventListeners();
        
        // Initialize recovery subsystem
        BleRecovery.initializeRecovery(state);
        
        // Initialize adapter info and controls
        initializeAdapterUI();
        
        // Initialize advanced features
        BleAdvanced.initializeAdvancedFeatures(state);
        
        // Initialize debug panel and shortcuts
        BleDebug.initializeDebugPanel(state);
        BleDebug.initializeDebugShortcuts(state);
        
        // Add custom debug endpoints
        BleDebug.addDebugEndpoint(state, '/api/ble/debug/deep-diagnostics', 'Deep BLE Diagnostics');
        BleDebug.addDebugEndpoint(state, '/api/ble/adapter/detailed-info', 'Detailed Adapter Info');
        
        // Expose diagnostics function globally
        window.runBleDiagnostics = BleDebug.runDiagnostics;
        window.logBleState = () => BleDebug.logBleState(state);
        
        // Attempt auto-reconnect
        tryAutoReconnect();
        
        BleUI.logMessage('BLE Manager initialized successfully', 'success');
    } catch (error) {
        console.error('Failed to initialize BLE Manager:', error);
        
        // Run diagnostics automatically when there's an error
        setTimeout(() => {
            try {
                BleDebug.runDiagnostics();
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

function tryAutoReconnect() {
    const autoReconnect = localStorage.getItem('bleAutoReconnect') === 'true';
    
    if (autoReconnect) {
        const lastDeviceId = localStorage.getItem('bleLastConnectedDevice');
        if (lastDeviceId) {
            BleUI.logMessage('Attempting to reconnect to last device...', 'info');
            setTimeout(() => {
                BleConnection.connectToDevice(state, lastDeviceId)
                    .catch(err => BleUI.logMessage(`Auto-reconnect failed: ${err.message}`, 'warning'));
            }, 1000);
        }
    }
}

// Initialize BLE settings
function initializeSettings() {
    // Set default settings if not already set
    if (localStorage.getItem('ble_auto_connect') === null) {
        localStorage.setItem('ble_auto_connect', 'false'); // Disabled by default
    }
    
    if (localStorage.getItem('ble_scan_duration') === null) {
        localStorage.setItem('ble_scan_duration', '5'); // 5 seconds default
    }
    
    if (localStorage.getItem('ble_active_scan') === null) {
        localStorage.setItem('ble_active_scan', 'true'); // Active scanning by default
    }
    
    // Initialize settings UI if it exists
    const settingsForm = document.getElementById('ble-settings-form');
    if (settingsForm) {
        // Load current settings into form
        const autoConnectCheckbox = document.getElementById('setting-auto-connect');
        if (autoConnectCheckbox) {
            autoConnectCheckbox.checked = localStorage.getItem('ble_auto_connect') === 'true';
            autoConnectCheckbox.addEventListener('change', function() {
                localStorage.setItem('ble_auto_connect', this.checked ? 'true' : 'false');
                BleUI.showMessage(`Auto-connect ${this.checked ? 'enabled' : 'disabled'}`);
            });
        }
        
        const scanDurationInput = document.getElementById('setting-scan-duration');
        if (scanDurationInput) {
            scanDurationInput.value = localStorage.getItem('ble_scan_duration') || '5';
            scanDurationInput.addEventListener('change', function() {
                const value = parseInt(this.value) || 5;
                // Limit to reasonable values
                const limitedValue = Math.min(Math.max(value, 1), 30);
                this.value = limitedValue;
                localStorage.setItem('ble_scan_duration', limitedValue.toString());
            });
        }
        
        const activeScanCheckbox = document.getElementById('setting-active-scan');
        if (activeScanCheckbox) {
            activeScanCheckbox.checked = localStorage.getItem('ble_active_scan') === 'true';
            activeScanCheckbox.addEventListener('change', function() {
                localStorage.setItem('ble_active_scan', this.checked ? 'true' : 'false');
            });
        }
    }
}

// Initialize the BLE Manager when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeBleManager();
});

// Initialize BLE Manager
function initializeBleManager() {
    console.log("BLE Manager initializing...");
    
    // Initialize settings first
    initializeSettings();
    
    // Initialize UI components
    BleUI.initializeUI();
    
    // Setup scan button
    const scanButton = document.getElementById('ble-scan-button');
    if (scanButton) {
        scanButton.addEventListener('click', async function() {
            try {
                scanButton.disabled = true;
                
                // Get scan parameters from settings
                const duration = parseInt(localStorage.getItem('ble_scan_duration')) || 5;
                const active = localStorage.getItem('ble_active_scan') !== 'false';
                
                // Show scan is starting
                BleUI.showMessage(`Starting scan (${duration}s)...`);
                
                // Start scan with settings
                await BleScanning.startScanning({
                    duration: duration,
                    active: active
                });
            } catch (error) {
                console.error("Scan error:", error);
                BleUI.showError(`Scan failed: ${error.message || error}`);
            } finally {
                scanButton.disabled = false;
            }
        });
    }
    
    // Initialize adapter info 
    checkAdapterStatus();
    
    // Setup other components with a slight delay
    setTimeout(() => {
        // Initialize connection manager
        BleConnection.initializeConnectionManager();
        
        BleUI.showMessage("BLE Manager initialized");
    }, 500);
}

// Check BLE adapter status and update UI
async function checkAdapterStatus() {
    try {
        const adapterInfo = await fetchAdapterInfo();
        
        // Update adapter status UI
        BleUI.updateAdapterStatus(adapterInfo);
        
        if (!adapterInfo.available) {
            BleUI.showError("Bluetooth adapter is not available");
        }
    } catch (error) {
        console.error("Failed to get adapter info:", error);
        BleUI.updateAdapterStatus({ available: false, error: error.message });
        BleUI.showError(`Bluetooth error: ${error.message || "Could not get adapter info"}`);
    }
}

// Fetch BLE adapter information
async function fetchAdapterInfo() {
    try {
        const response = await fetch('/api/ble/adapter');
        
        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error("Error fetching adapter info:", error);
        return { available: false, error: error.message };
    }
}

function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Scan button
    if (state.domElements.scanBtn) {
        console.log('Attaching event listener to scan button');
        state.domElements.scanBtn.addEventListener('click', async () => {
            if (state.scanningActive) {
                BleUI.logMessage('Scan already in progress', 'warning');
                return;
            }
            
            try {
                state.scanningActive = true;
                BleUI.updateScanStatus(state, 'scanning', 'Scanning for devices...');
                BleUI.setLoading(state, true, 'Scanning for BLE devices...');
                
                // Clear previous results
                const deviceList = state.domElements.deviceList;
                if (deviceList) deviceList.innerHTML = '';
                
                // Define scan options with power-efficient parameters
                const options = {
                    duration: 5,
                    active: true,
                    allowDuplicates: false,
                    namePrefix: '',
                    services: [],
                    rssiThreshold: -100,
                    sortBy: 'rssi',
                    sortOrder: 'desc'
                };
                
                // Use power efficient scan when battery is low
                if (state.batteryLevel && state.batteryLevel < 20) {
                    BleUI.logMessage('Battery low, using power-efficient scanning', 'info');
                    await BlePower.powerEfficientScan(options, state);
                } else {
                    // Start the scan with regular parameters
                    await BleScanning.startScanning(options, state);
                }
                
                // Fetch devices after scanning is complete
                const devices = await BleScanning.scanDevicesWithErrorHandling(5, true);
                
                // Add devices to cache
                if (BleScanning.deviceCache && BleScanning.deviceCache.addDevices) {
                    BleScanning.deviceCache.addDevices(devices);
                }
                
                // Display results using imported function
                BleDeviceList.displayDevices(state, devices);
                
                // Update scan status
                BleUI.updateScanStatus(state, 'complete', `Found ${devices.length} devices`);
                BleDeviceList.updateDeviceList(devices);
            } catch (error) {
                console.error('Scanning error:', error);
                BleUI.logMessage(`Scanning error: ${error.message}`, 'error');
                BleUI.updateScanStatus(state, 'error', 'Scan failed');
                // Updated to use BleEvents
                BleEvents.emit(BLE_EVENTS.ERROR_SCAN, { error: error.message });
            } finally {
                state.scanningActive = false;
                BleUI.setLoading(state, false);
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
                BleUI.logMessage('Log cleared', 'info');
            }
        });
    }
    
    // Add battery refresh button handler
    if (state.domElements.refreshBatteryBtn) {
        state.domElements.refreshBatteryBtn.addEventListener('click', () => {
            BlePower.getBatteryLevel(state)
                .catch(err => BleUI.logMessage(`Unable to refresh battery: ${err.message}`, 'warning'));
        });
    }
    
    // Disconnect button
    if (state.domElements.disconnectBtn) {
        state.domElements.disconnectBtn.addEventListener('click', () => {
            if (state.connectedDevice) {
                BleConnection.disconnectDevice(state)
                    .then(success => {
                        if (success) {
                            BleUI.logMessage('Device disconnected successfully', 'success');
                        }
                    })
                    .catch(err => BleUI.logMessage(`Disconnect error: ${err.message}`, 'error'));
            } else {
                BleUI.logMessage('No device connected', 'warning');
            }
        });
    }
    
    // Debug toggle button
    if (state.domElements.debugToggleBtn && state.domElements.debugPanel) {
        state.domElements.debugToggleBtn.addEventListener('click', () => {
            state.domElements.debugPanel.classList.toggle('hidden');
        });
    }
    
    // Setup device click handlers using imported function
    if (BleDeviceList.setupDeviceClickHandlers) {
        BleDeviceList.setupDeviceClickHandlers();
    }
    
    console.log('Event listeners setup complete');
}

function initializeDomReferences() {
    console.log('Initializing DOM references...');
    
    // Helper to get or create element
    const getOrCreateElement = (id, type = 'div', parent = document.body) => {
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
        deviceList: document.getElementById('devices-list'),
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
        refreshBatteryBtn: document.getElementById('refresh-battery'),
        // Add device info elements
        deviceInfoContainer: document.getElementById('device-info')
    };
    
    // Create missing critical elements instead of just logging warnings
    if (!elements.deviceList) {
        elements.deviceList = getOrCreateElement('devices-list');
    }
    
    if (!elements.logContainer) {
        elements.logContainer = getOrCreateElement('ble-log-container');
    }
    
    if (!elements.statusIndicatorContainer) {
        elements.statusIndicatorContainer = getOrCreateElement('status-indicator-container');
    }
    
    state.domElements = elements;
    console.log('DOM references initialized');
}

// Enhanced connect to device function that uses event system
async function connectToDevice(state, deviceId, deviceName) {
    // Prevent multiple simultaneous connection attempts
    if (state.connectionInProgress) {
        BleUI.logMessage('Connection already in progress, please wait', 'warning');
        return false;
    }
    
    state.connectionInProgress = true;
    state.lastConnectionAttempt = Date.now();
    
    try {
        // Updated to use BleEvents
        BleEvents.emit(BLE_EVENTS.DEVICE_CONNECTING, { id: deviceId, name: deviceName });
        BleUI.setLoading(state, true, `Connecting to ${deviceName || deviceId}...`);
        
        // Call the original connection function
        const result = await BleConnection.connectToDevice(state, deviceId, deviceName);
        
        if (result) {
            // Save to connection history using both imported and local functions
            if (BleConnection.saveDeviceToHistory) {
                BleConnection.saveDeviceToHistory(deviceId, deviceName);
            }
            if (BleConnection.saveToConnectionHistory) {
                BleConnection.saveToConnectionHistory(deviceId, deviceName);
            } else {
                saveToConnectionHistory(deviceId, deviceName);
            }
            
            // Emit connected event with device data - Updated to use BleEvents
            BleEvents.emit(BLE_EVENTS.DEVICE_CONNECTED, { 
                address: deviceId, 
                name: deviceName 
            });
            
            // Emit connection state change event
            state.eventBus.emit('CONNECTION_STATE_CHANGED', true);
            state.eventBus.emit('DEVICE_SELECTED', { address: deviceId, name: deviceName });
            
            // Use imported function to emit device selected event
            if (BleDeviceList.emitDeviceSelected) {
                BleDeviceList.emitDeviceSelected({ address: deviceId, name: deviceName });
            }
            
            // Show device details using imported function
            if (state.domElements.deviceInfoContainer && BleDeviceDetails.showDeviceDetails) {
                BleDeviceDetails.showDeviceDetails(state.domElements.deviceInfoContainer, { address: deviceId, name: deviceName });
            }
        }
        
        return result;
    } catch (error) {
        BleUI.logMessage(`Connection error: ${error.message}`, 'error');
        // Updated to use BleEvents
        BleEvents.emit(BLE_EVENTS.CONNECTION_FAILED, { 
            id: deviceId, 
            name: deviceName,
            error: error.message 
        });
        return false;
    } finally {
        state.connectionInProgress = false;
        BleUI.setLoading(state, false);
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

// Connect to WebSocket with retry
async function connectWebSocketWithRetry(attemptCount = 0) {
    try {
        await BleWebSocket.connectWebSocket(state);
    } catch (err) {
        const maxRetries = 5;
        const delay = Math.min(30000, Math.pow(2, attemptCount) * 1000);
        
        if (attemptCount < maxRetries) {
            BleUI.logMessage(`WebSocket connection failed: ${err.message}. Retrying in ${delay/1000}s...`, 'warning');
            setTimeout(() => connectWebSocketWithRetry(attemptCount + 1), delay);
        } else {
            BleUI.logMessage(`Failed to establish WebSocket connection after multiple attempts: ${err.message}`, 'error');
        }
    }
}

function setupErrorBoundaries() {
    // Simple error handling for UI components
    window.addEventListener('error', (event) => {
        console.error('Caught in error boundary:', event.error);
        BleUI.logMessage(`Error: ${event.error?.message || 'Unknown error occurred'}`, 'error');
        return false;
    });
    
    // Add unhandled promise rejection handler
    window.addEventListener('unhandledrejection', (event) => {
        console.error('Unhandled promise rejection:', event.reason);
        BleUI.logMessage(`Promise error: ${event.reason?.message || 'Unknown promise error'}`, 'error');
        return false;
    });
}

// Add this event listener to handle connecting to bonded devices
window.addEventListener('CONNECT_TO_DEVICE', (event) => {
    const { address, name } = event.detail;
    if (address) {
        connectToDevice(state, address, name)
            .catch(error => {
                BleUI.logMessage(`Failed to connect to bonded device: ${error.message}`, 'error');
            });
    }
});

function initializeAdapterUI() {
    console.log('Initializing adapter UI...');
    
    // Initialize adapter info
    if (BleAdapter.initializeAdapterInfo) {
        BleAdapter.initializeAdapterInfo(state);
    }
    
    // Add event listener for adapter reset button
    const resetAdapterBtn = document.getElementById('reset-adapter');
    if (resetAdapterBtn) {
        resetAdapterBtn.addEventListener('click', async () => {
            try {
                resetAdapterBtn.disabled = true;
                resetAdapterBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Resetting...';
                
                if (BleAdapter.resetAdapter) {
                    const success = await BleAdapter.resetAdapter();
                    
                    if (success) {
                        // Get updated adapter info using imported function
                        if (BleAdapter.getAdapterInfo) {
                            const adapterInfo = await BleAdapter.getAdapterInfo();
                            
                            // Display updated adapter info using imported function
                            if (state.domElements.deviceInfoContainer && BleAdapter.displayAdapterInfo) {
                                BleAdapter.displayAdapterInfo(state.domElements.deviceInfoContainer, adapterInfo);
                            }
                        }
                        
                        // Refresh adapter info
                        if (BleAdapter.initializeAdapterInfo) {
                            BleAdapter.initializeAdapterInfo(state);
                        }
                        BleUI.logMessage('Adapter reset successful', 'success');
                        
                        // Run diagnostics after reset
                        if (state.domElements.deviceInfoContainer && BleAdapter.simulateDiagnostics) {
                            BleAdapter.simulateDiagnostics(state.domElements.deviceInfoContainer);
                        }
                    } else {
                        BleUI.logMessage('Adapter reset failed', 'error');
                    }
                }
            } catch (error) {
                console.error('Error resetting adapter:', error);
                BleUI.logMessage(`Failed to reset adapter: ${error.message}`, 'error');
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

// Core state and event system
// Initialize variables
const bleState = { /* state properties */ };

// Make state globally available
window.bleState = bleState;

// At the end of your file, export everything at once:
export {
    bleState as state,
    BleEvents,
    BLE_EVENTS
};

// UI Functions
export const initializeUI = BleUI.initializeUI;
export const updateStatus = BleUI.updateStatus;
export const updateScanStatus = BleUI.updateScanStatus;
export const logMessage = BleUI.logMessage;
export const setLoading = BleUI.setLoading;
export const updateSubscriptionStatus = BleUI.updateSubscriptionStatus;
export const enableDebugMode = BleUI.enableDebugMode;

// Connection functions
export { connectToDevice };
export const disconnectDevice = BleConnection.disconnectDevice;
export const pairWithDevice = BleConnection.pairWithDevice;
export { saveToConnectionHistory };
export const initializeConnectionManager = BleConnection.initializeConnectionManager;

// Scanning functions
export const startScanning = BleScanning.startScanning;
export const stopScanning = BleScanning.stopScanning;
export const scanDevicesWithErrorHandling = BleScanning.scanDevicesWithErrorHandling;
export const deviceCache = BleScanning.deviceCache;

// Service/characteristic functions
export const getServices = BleServices.getServices;
export const getCharacteristics = BleServices.getCharacteristics;
export const readCharacteristic = BleServices.readCharacteristic;
export const writeCharacteristic = BleServices.writeCharacteristic;
export const toggleNotification = BleServices.toggleNotification;

// WebSocket functions
export const connectWebSocket = BleWebSocket.connectWebSocket;
export const handleWebSocketMessage = BleWebSocket.handleWebSocketMessage;

// Debug functions
export const initializeDebugPanel = BleDebug.initializeDebugPanel;
export const initializeDebugShortcuts = BleDebug.initializeDebugShortcuts;
export const logBleState = BleDebug.logBleState;
export const runDiagnostics = BleDebug.runDiagnostics;

// Power/battery functions
export const getBatteryLevel = BlePower.getBatteryLevel;
export const powerEfficientScan = BlePower.powerEfficientScan;

// Device info functions
export const getDeviceInformation = BleDeviceInfo.getDeviceInformation;
export const showDeviceDetails = BleDeviceDetails.showDeviceDetails;

// Adapter functions
export const initializeAdapterInfo = BleAdapter.initializeAdapterInfo;
export const resetAdapter = BleAdapter.resetAdapter;
export const getAdapterInfo = BleAdapter.getAdapterInfo;

// Advanced features
export const initializeAdvancedFeatures = BleAdvanced.initializeAdvancedFeatures;
export const fetchBondedDevices = BleAdvanced.fetchBondedDevices;

// Device list functions
export const initializeDeviceList = BleDeviceList.initializeDeviceList;
export const initializeDeviceDetails = BleDeviceDetails.initializeDeviceDetails;
export const displayDevices = BleDeviceList.displayDevices;

// Recovery functions
export const initializeRecovery = BleRecovery.initializeRecovery;
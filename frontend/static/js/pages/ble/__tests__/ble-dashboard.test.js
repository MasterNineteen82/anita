import { getBatteryLevel, powerEfficientScan } from './ble-power.js';
import { bleEventEmitter as BLEEventEmitter, BLE_EVENTS } from './ble-events.js';
import { getDeviceInformation } from './ble-device-info.js';
import { connectToDevice, disconnectFromDevice } from './ble-connection.js';
import { getServices, getCharacteristics } from './ble-services.js';
import { connectWebSocket } from './ble-websocket.js';

import { 
    listBondedDevices, 
    bondDevice, 
    unbondDevice, 
    negotiateMTU, 
    setConnectionParameters, 
    getConnectionParameters 
} from './ble-bond.js';
import { scanDevicesWithErrorHandling, deviceCache } from './ble-scanning.js'; // Import the scan function and deviceCache
import { updateScanStatus, logMessage } from './ble-ui.js';

// Initialize state
const state = {
    connectedDevice: null,
    subscribedCharacteristics: new Set(),
    socketConnected: false,
    socket: null,
    scanningActive: false,
    connectionInProgress: false,
    deviceInfo: null,
    batteryLevel: null,
    domElements: {}
};

// Initialize event system and make globally available
const bleEvents = new BLEEventEmitter();
window.bleEvents = bleEvents;

// DOM ready handler
document.addEventListener('DOMContentLoaded', async () => {
    console.log('BLE HTML template loaded - inline script works');

    // Initialize DOM elements
    state.domElements = {
        scanButton: document.getElementById('scanButton'),
        deviceList: document.getElementById('deviceList'),
        clearLogButton: document.getElementById('clearLogButton'),
        logMessages: document.getElementById('logMessages'),
        batteryLevel: document.getElementById('batteryLevel'),
        batteryIcon: document.getElementById('batteryIcon'),
        batteryContainer: document.getElementById('batteryContainer'),
        refreshBatteryBtn: document.getElementById('refreshBatteryBtn'),
        deviceInfoContainer: document.getElementById('deviceInfoContainer'),
        debugPanel: document.getElementById('debugPanel'),
        debugToggleButton: document.getElementById('debugToggleButton'),
        debugEndpointSelect: document.getElementById('debugEndpointSelect'),
        debugSendButton: document.getElementById('debugSendButton'),
        debugResponse: document.getElementById('debugResponse'),
        scanStatus: document.getElementById('scanStatus'),
        clearCacheButton: document.getElementById('clearCacheButton') // Add the clear cache button
    };

    // Check if elements exist before proceeding
    for (const [key, element] of Object.entries(state.domElements)) {
        if (!element) {
            console.warn('\n DOM element "' + key + '" not found');
        }
    }

    // Initialize UI components
    bleUIInit(state);

    // Connect to WebSocket
    state.socket = connectWebSocket(state);
    state.socketConnected = true;

    // Load bonded devices
    loadBondedDevices();

    // Load BLE metrics
    loadBleMetrics();

    // Setup event listeners
    setupEventListeners();

    // Log initialization
    logMessage('BLE Manager initializing...', 'info');
    logMessage('BLE Manager initialization complete', 'info');
});

// UI initialization
function bleUIInit(state) {
    logMessage('BLE UI components initialized', 'info');
}

// Load bonded devices
async function loadBondedDevices() {
    try {
        const bondedDevices = await listBondedDevices();
        console.log('Bonded devices:', bondedDevices);
    } catch (error) {
        console.error('Error loading bonded devices:', error);
        logMessage(`Error loading bonded devices: ${error.message}`, 'error');
    }
}

// Load BLE metrics
async function loadBleMetrics() {
    try {
        const bleMetrics = await getBleMetrics();
        console.log('BLE metrics:', bleMetrics);
    } catch (error) {
        console.error('Error loading BLE metrics:', error);
        logMessage(`Error loading BLE metrics: ${error.message}`, 'error');
    }
}

// Get BLE metrics
async function getBleMetrics() {
    try {
        const response = await fetch('/api/ble/metrics');
        if (!response.ok) {
            throw new Error(`Failed to get BLE metrics: ${response.status} ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error getting BLE metrics:', error);
        return null;
    }
}

function setupEventListeners() {
    // Scan button
    const scanButton = state.domElements.scanButton;
    if (scanButton) {
        console.log('Attaching event listener to scan button');
        scanButton.addEventListener('click', async () => {
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
                
                // Emit scan error event
                if (window.bleEvents) {
                    window.bleEvents.emit(BLE_EVENTS.SCAN_ERROR, {
                        error: error.message
                    });
                }
            } finally {
                state.scanningActive = false;
            }
        });
    }
    
    // Clear log button
    const clearLogButton = state.domElements.clearLogButton;
    if (clearLogButton) {
        clearLogButton.addEventListener('click', () => {
            const logMessages = state.domElements.logMessages;
            if (logMessages) logMessages.innerHTML = '';
            logMessage('Log cleared', 'info');
        });
    }
    
    // Clear cache button
    const clearCacheButton = state.domElements.clearCacheButton;
    if (clearCacheButton) {
        clearCacheButton.addEventListener('click', () => {
            // Clear device cache
            deviceCache.clear();
            logMessage('Device cache cleared', 'info');
            
            // Clear connection history
            localStorage.removeItem('ble-device-history');
            logMessage('Connection history cleared', 'info');
            
            // Refresh list if showing devices
            const deviceList = state.domElements.deviceList;
            if (deviceList && deviceList.children.length > 0) {
                deviceList.innerHTML = '';
                logMessage('Device list cleared', 'info');
            }
        });
    }
    
    // Debug toggle button
    const debugToggleButton = state.domElements.debugToggleButton;
    const debugPanel = state.domElements.debugPanel;
    if (debugToggleButton && debugPanel) {
        debugToggleButton.addEventListener('click', () => {
            if (debugPanel.classList.contains('hidden')) {
                debugPanel.classList.remove('hidden');
            } else {
                debugPanel.classList.add('hidden');
            }
        });
    }
    
    console.log('All event listeners attached successfully');
}

function displayDevices(devices) {
    const deviceList = document.getElementById('deviceList');
    if (!deviceList) {
        console.warn('Device list element not found');
        return;
    }

    deviceList.innerHTML = ''; // Clear existing list

    if (devices.length === 0) {
        deviceList.innerHTML = '<div class="text-gray-500">No devices found.</div>';
        return;
    }

    try {
        devices.forEach(device => {
            const deviceEl = document.createElement('div');
            deviceEl.className = 'bg-gray-800 p-3 rounded mb-2 hover:bg-gray-700 transition-colors';
            const name = device.name || 'Unknown Device';
            deviceEl.innerHTML = `
                <div class="flex items-center justify-between">
                    <div>
                        <div class="font-medium text-white">${name}</div>
                        <div class="text-xs text-gray-400">${device.address}</div>
                        <div class="text-xs text-gray-400 mt-1">RSSI: ${device.rssi || 'N/A'}</div>
                    </div>
                    <button class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">Connect</button>
                </div>
            `;
            deviceList.appendChild(deviceEl);
        });
    } catch (error) {
        console.error('Error displaying devices:', error);
        logMessage(`Error displaying devices: ${error.message}`, 'error');
        deviceList.innerHTML = '<div class="text-red-500">Error displaying devices.</div>';
    }
}
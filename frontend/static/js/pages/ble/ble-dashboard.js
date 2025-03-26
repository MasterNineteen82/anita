import { getBatteryLevel, powerEfficientScan } from './ble-power.js';
import { BLEEventEmitter, BLE_EVENTS } from './ble-events.js';
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
document.addEventListener('DOMContentLoaded', () => {
    console.log("BLE Dashboard initializing...");
    
    // Initialize DOM references
    initializeDomReferences();
    
    // Set up event listeners
    setupEventListeners();
    
    // Setup tabs
    setupTabs();
    
    // Initialize WebSocket connection
    try {
        connectWebSocket(state)
            .then(() => {
                logMessage('WebSocket connected successfully', 'info');
            })
            .catch(error => {
                logMessage(`WebSocket connection failed: ${error.message}`, 'error');
            });
    } catch (error) {
        logMessage(`WebSocket initialization error: ${error.message}`, 'error');
    }
    
    // Try auto-reconnect if enabled
    tryAutoReconnect();
    
    // Initialize bonding UI
    initBondingUI(state);
    
    logMessage('BLE Dashboard initialized', 'info');
});

function initializeDomReferences() {
    // Core UI elements
    state.domElements = {
        scanButton: document.getElementById('scan-button'),
        devicesContainer: document.getElementById('devices-container'),
        deviceName: document.getElementById('device-name'),
        connectionStatus: document.getElementById('connection-status'),
        
        // Tab content containers
        deviceInfoContainer: document.getElementById('device-info-container'),
        servicesContainer: document.getElementById('services-container'),
        characteristicsContainer: document.getElementById('characteristics-container'),
        logContainer: document.getElementById('log-container'),
        logEntries: document.getElementById('log-entries'),
        
        // Battery display
        batteryContainer: document.getElementById('battery-container'),
        batteryIcon: document.getElementById('battery-icon'),
        batteryLevel: document.getElementById('battery-level'),
        
        // Controls
        clearLogButton: document.getElementById('clear-log'),
        clearHistoryLink: document.getElementById('clear-history'),
        toggleAutoReconnectLink: document.getElementById('toggle-auto-reconnect'),
        
        // Tab buttons
        tabButtons: document.querySelectorAll('.tab-button'),
        tabContents: document.querySelectorAll('.tab-content')
    };
    
    // Check if all elements were found
    Object.entries(state.domElements).forEach(([key, element]) => {
        if (!element && !key.endsWith('s')) { // Skip collections (ending with 's')
            console.warn(`DOM element "${key}" not found`);
        }
    });
}

function setupEventListeners() {
    // Scan button
    if (state.domElements.scanButton) {
        state.domElements.scanButton.addEventListener('click', () => {
            if (state.scanningActive) return;
            
            state.scanningActive = true;
            state.domElements.scanButton.disabled = true;
            state.domElements.scanButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
            
            powerEfficientScan(state)
                .then(devices => {
                    displayDevices(devices);
                    logMessage(`Found ${devices.length} devices`, 'info');
                })
                .catch(error => {
                    logMessage(`Scan error: ${error.message}`, 'error');
                })
                .finally(() => {
                    state.scanningActive = false;
                    state.domElements.scanButton.disabled = false;
                    state.domElements.scanButton.innerHTML = '<i class="fas fa-search"></i> Scan';
                });
        });
    }
    
    // Clear log button
    if (state.domElements.clearLogButton) {
        state.domElements.clearLogButton.addEventListener('click', () => {
            if (state.domElements.logEntries) {
                state.domElements.logEntries.innerHTML = '';
            }
        });
    }
    
    // Clear history link
    if (state.domElements.clearHistoryLink) {
        state.domElements.clearHistoryLink.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Clear device history from localStorage
            localStorage.removeItem('bleConnectionHistory');
            localStorage.removeItem('bleLastConnectedDevice');
            localStorage.removeItem('bleDeviceCacheTimestamp');
            
            logMessage('Device history cleared', 'info');
        });
    }
    
    // Toggle auto-reconnect link
    if (state.domElements.toggleAutoReconnectLink) {
        state.domElements.toggleAutoReconnectLink.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Toggle auto-reconnect setting
            const currentSetting = localStorage.getItem('bleAutoReconnect') === 'true';
            const newSetting = !currentSetting;
            
            localStorage.setItem('bleAutoReconnect', newSetting.toString());
            
            // Update UI to show current setting
            state.domElements.toggleAutoReconnectLink.innerHTML = 
                `${newSetting ? 'Disable' : 'Enable'} Auto Reconnect`;
            
            logMessage(`Auto-reconnect ${newSetting ? 'enabled' : 'disabled'}`, 'info');
        });
        
        // Initialize text
        const autoReconnectEnabled = localStorage.getItem('bleAutoReconnect') === 'true';
        state.domElements.toggleAutoReconnectLink.innerHTML = 
            `${autoReconnectEnabled ? 'Disable' : 'Enable'} Auto Reconnect`;
    }
    
    // BLE Events
    bleEvents.on(BLE_EVENTS.DEVICE_CONNECTED, (device) => {
        updateConnectionStatus('connected');
        state.connectedDevice = device;
        
        // Update device name in UI
        if (state.domElements.deviceName) {
            state.domElements.deviceName.textContent = device.name || `Device (${device.address})`;
        }
        
        // Get device information
        getDeviceInformation(state).catch(err => 
            logMessage(`Failed to get device info: ${err.message}`, 'warning'));
        
        // Get battery level
        setTimeout(() => {
            getBatteryLevel(state).catch(err => 
                logMessage(`Failed to get battery level: ${err.message}`, 'warning'));
        }, 1000);
        
        // Get services
        getServices(state).then(services => {
            displayServices(services);
        }).catch(err => 
            logMessage(`Failed to get services: ${err.message}`, 'error'));
    });
    
    bleEvents.on(BLE_EVENTS.DEVICE_DISCONNECTED, () => {
        updateConnectionStatus('disconnected');
        state.connectedDevice = null;
        
        // Reset UI elements
        if (state.domElements.deviceName) {
            state.domElements.deviceName.textContent = 'Device Details';
        }
        
        if (state.domElements.batteryContainer) {
            state.domElements.batteryContainer.classList.add('hidden');
        }
        
        // Reset service and characteristic containers
        if (state.domElements.servicesContainer) {
            state.domElements.servicesContainer.innerHTML = 
                '<div class="text-gray-500">Connect to a device to view services</div>';
        }
        
        if (state.domElements.characteristicsContainer) {
            state.domElements.characteristicsContainer.innerHTML = 
                '<div class="text-gray-500">Select a service to view characteristics</div>';
        }
        
        if (state.domElements.deviceInfoContainer) {
            state.domElements.deviceInfoContainer.innerHTML = 
                '<div class="text-gray-500">Connect to a device to see information</div>';
        }
    });
    
    // Battery updated event
    bleEvents.on('BATTERY_UPDATED', (data) => {
        logMessage(`Battery level updated: ${data.level}%`, 'info');
    });
}

function setupTabs() {
    // Exit if tab elements aren't found
    if (!state.domElements.tabButtons || !state.domElements.tabContents) return;
    
    state.domElements.tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            state.domElements.tabButtons.forEach(btn => btn.classList.remove('active'));
            state.domElements.tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked button
            button.classList.add('active');
            
            // Find and show the corresponding content
            const tabId = button.getAttribute('data-tab');
            const content = document.getElementById(`tab-${tabId}`);
            if (content) {
                content.classList.add('active');
            }
        });
    });
}

function displayDevices(devices) {
    if (!state.domElements.devicesContainer) return;
    
    if (!devices || devices.length === 0) {
        state.domElements.devicesContainer.innerHTML = 
            '<div class="text-gray-500">No devices found</div>';
        return;
    }
    
    // Get connection history to mark previously connected devices
    const history = JSON.parse(localStorage.getItem('bleConnectionHistory') || '[]');
    const historyMap = new Map(history.map(device => [device.id, device]));
    
    // Clear and rebuild device list
    state.domElements.devicesContainer.innerHTML = '';
    
    devices.forEach(device => {
        const deviceElement = document.createElement('div');
        deviceElement.className = 'device-item p-3 rounded bg-gray-800 hover:bg-gray-700 cursor-pointer';
        
        // Add a history badge if this device was previously connected
        const historyDevice = historyMap.get(device.address);
        const historyBadge = historyDevice ? 
            `<span class="badge badge-info ml-2" title="Last connected: ${new Date(historyDevice.lastConnected).toLocaleString()}">History</span>` : '';
        
        deviceElement.innerHTML = `
            <div class="flex justify-between items-center">
                <div>
                    <div class="font-medium">${device.name || 'Unnamed Device'}</div>
                    <div class="text-xs text-gray-400">${device.address}</div>
                </div>
                <div>
                    <span class="text-xs bg-blue-500 text-white px-2 py-1 rounded">${device.rssi} dBm</span>
                    ${historyBadge}
                </div>
            </div>
        `;
        
        // Add click handler to connect
        deviceElement.addEventListener('click', () => {
            connectToDevice(state, device.address, device.name)
                .then(success => {
                    if (!success) {
                        logMessage(`Failed to connect to ${device.name || 'device'}`, 'error');
                    }
                })
                .catch(error => {
                    logMessage(`Connection error: ${error.message}`, 'error');
                });
        });
        
        state.domElements.devicesContainer.appendChild(deviceElement);
    });
}

function displayServices(services) {
    if (!state.domElements.servicesContainer) return;
    
    if (!services || services.length === 0) {
        state.domElements.servicesContainer.innerHTML = 
            '<div class="text-gray-500">No services found</div>';
        return;
    }
    
    // Clear and rebuild services list
    state.domElements.servicesContainer.innerHTML = '';
    
    services.forEach(service => {
        const serviceElement = document.createElement('div');
        serviceElement.className = 'service-item p-3 mb-2 rounded bg-gray-800 hover:bg-gray-700 cursor-pointer';
        
        // Try to get a friendly name for known services
        const serviceName = getServiceName(service.uuid);
        
        serviceElement.innerHTML = `
            <div class="font-medium">${serviceName}</div>
            <div class="text-xs text-gray-400">${service.uuid}</div>
        `;
        
        // Add click handler to get characteristics
        serviceElement.addEventListener('click', () => {
            // Mark this service as selected
            document.querySelectorAll('.service-item').forEach(el => 
                el.classList.remove('bg-blue-800', 'hover:bg-blue-700'));
            serviceElement.classList.add('bg-blue-800', 'hover:bg-blue-700');
            
            getCharacteristics(state, service.uuid)
                .then(characteristics => {
                    displayCharacteristics(characteristics, service.uuid);
                })
                .catch(error => {
                    logMessage(`Error getting characteristics: ${error.message}`, 'error');
                });
        });
        
        state.domElements.servicesContainer.appendChild(serviceElement);
    });
}

function displayCharacteristics(characteristics, serviceUuid) {
    if (!state.domElements.characteristicsContainer) return;
    
    if (!characteristics || characteristics.length === 0) {
        state.domElements.characteristicsContainer.innerHTML = 
            '<div class="text-gray-500">No characteristics found</div>';
        return;
    }
    
    // Clear and rebuild characteristics list
    state.domElements.characteristicsContainer.innerHTML = '';
    
    characteristics.forEach(characteristic => {
        const charElement = document.createElement('div');
        charElement.className = 'characteristic-item p-3 mb-2 rounded bg-gray-800';
        
        // Try to get a friendly name for known characteristics
        const charName = getCharacteristicName(characteristic.uuid);
        
        // Properties badges
        const propBadges = [];
        if (characteristic.properties.includes('read')) 
            propBadges.push('<span class="badge badge-success">Read</span>');
        if (characteristic.properties.includes('write')) 
            propBadges.push('<span class="badge badge-warning">Write</span>');
        if (characteristic.properties.includes('notify') || characteristic.properties.includes('indicate')) 
            propBadges.push('<span class="badge badge-info">Notify</span>');
        
        charElement.innerHTML = `
            <div class="font-medium">${charName}</div>
            <div class="text-xs text-gray-400 mb-2">${characteristic.uuid}</div>
            <div class="flex flex-wrap gap-2 mb-2">
                ${propBadges.join('')}
            </div>
            <div class="flex flex-wrap gap-2 mt-2">
                ${characteristic.properties.includes('read') ? 
                    '<button class="btn btn-sm btn-primary read-btn">Read</button>' : ''}
                ${characteristic.properties.includes('write') ? 
                    '<button class="btn btn-sm btn-warning write-btn">Write</button>' : ''}
                ${(characteristic.properties.includes('notify') || characteristic.properties.includes('indicate')) ? 
                    '<button class="btn btn-sm btn-info notify-btn">Subscribe</button>' : ''}
            </div>
            <div class="char-value mt-2 hidden">
                <div class="text-xs text-gray-400">Value:</div>
                <div class="bg-gray-900 p-2 rounded font-mono text-xs value-display"></div>
            </div>
        `;
        
        // Add event handlers for buttons
        const readBtn = charElement.querySelector('.read-btn');
        if (readBtn) {
            readBtn.addEventListener('click', () => {
                // Implement read logic
                logMessage(`Reading characteristic ${characteristic.uuid}...`, 'info');
            });
        }
        
        state.domElements.characteristicsContainer.appendChild(charElement);
    });
}

function updateConnectionStatus(status) {
    if (!state.domElements.connectionStatus) return;
    
    state.domElements.connectionStatus.className = 'badge';
    
    switch(status) {
        case 'connected':
            state.domElements.connectionStatus.classList.add('badge-success');
            state.domElements.connectionStatus.textContent = 'Connected';
            break;
        case 'connecting':
            state.domElements.connectionStatus.classList.add('badge-warning');
            state.domElements.connectionStatus.textContent = 'Connecting...';
            break;
        case 'disconnected':
        default:
            state.domElements.connectionStatus.classList.add('badge-inactive');
            state.domElements.connectionStatus.textContent = 'Disconnected';
            break;
    }
}

function logMessage(message, level = 'info') {
    if (!state.domElements.logEntries) return;
    
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry py-1';
    
    // Set color based on level
    let levelClass = '';
    switch(level) {
        case 'error':
            levelClass = 'text-red-500';
            break;
        case 'warning':
            levelClass = 'text-yellow-500';
            break;
        case 'success':
            levelClass = 'text-green-500';
            break;
        case 'info':
        default:
            levelClass = 'text-blue-500';
            break;
    }
    
    const timestamp = new Date().toLocaleTimeString();
    logEntry.innerHTML = `<span class="text-gray-500">[${timestamp}]</span> <span class="${levelClass}">${level.toUpperCase()}</span>: ${message}`;
    
    state.domElements.logEntries.appendChild(logEntry);
    
    // Auto-scroll to bottom
    state.domElements.logEntries.scrollTop = state.domElements.logEntries.scrollHeight;
    
    // Also log to console
    console.log(`[BLE ${level.toUpperCase()}] ${message}`);
}

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
            updateConnectionStatus('connecting');
            
            setTimeout(() => {
                connectToDevice(state, lastDevice.id, lastDevice.name)
                    .catch(error => {
                        logMessage(`Auto-reconnect failed: ${error.message}`, 'warning');
                        updateConnectionStatus('disconnected');
                    });
            }, 1500);
        }
    } catch (e) {
        console.error('Error during auto-reconnect:', e);
    }
}

// Helper functions for service and characteristic names
function getServiceName(uuid) {
    const services = {
        '1800': 'Generic Access',
        '1801': 'Generic Attribute',
        '180a': 'Device Information',
        '180f': 'Battery Service',
        '1812': 'HID Service',
        '1813': 'Scan Parameters',
        '1819': 'Location and Navigation',
        // Add more service names as needed
    };
    
    // Extract the short UUID if it's in the standard format
    const shortUuid = uuid.toLowerCase().match(/0000([0-9a-f]{4})-0000-1000-8000-00805f9b34fb/);
    if (shortUuid && services[shortUuid[1]]) {
        return services[shortUuid[1]];
    }
    
    return 'Service'; // Default name
}

function getCharacteristicName(uuid) {
    const characteristics = {
        '2a00': 'Device Name',
        '2a01': 'Appearance',
        '2a19': 'Battery Level',
        '2a29': 'Manufacturer Name',
        '2a24': 'Model Number',
        '2a25': 'Serial Number',
        '2a27': 'Hardware Revision',
        '2a26': 'Firmware Revision',
        // Add more characteristic names as needed
    };
    
    // Extract the short UUID if it's in the standard format
    const shortUuid = uuid.toLowerCase().match(/0000([0-9a-f]{4})-0000-1000-8000-00805f9b34fb/);
    if (shortUuid && characteristics[shortUuid[1]]) {
        return characteristics[shortUuid[1]];
    }
    
    return 'Characteristic'; // Default name
}

function initBondingUI(state) {
    // Get elements
    const bondButton = document.getElementById('bond-button');
    const unbondButton = document.getElementById('unbond-button');
    const bondedDevicesList = document.getElementById('bonded-devices-list');
    const advancedSettingsButton = document.getElementById('advanced-settings-button');
    const mtuInput = document.getElementById('mtu-input');
    const mtuButton = document.getElementById('mtu-button');
    
    // Add event listeners if elements exist
    if (bondButton) {
        bondButton.addEventListener('click', async () => {
            if (state.selectedDevice) {
                try {
                    await bondDevice(state.selectedDevice.address);
                    loadBondedDevices();
                } catch (error) {
                    console.error('Bonding error:', error);
                }
            } else {
                logMessage('No device selected for bonding', 'warning');
            }
        });
    }
    
    if (unbondButton) {
        unbondButton.addEventListener('click', async () => {
            if (state.selectedDevice) {
                try {
                    await unbondDevice(state.selectedDevice.address);
                    loadBondedDevices();
                } catch (error) {
                    console.error('Unbonding error:', error);
                }
            } else {
                logMessage('No device selected for unbonding', 'warning');
            }
        });
    }
    
    if (mtuButton && mtuInput) {
        mtuButton.addEventListener('click', async () => {
            const mtuSize = parseInt(mtuInput.value, 10);
            if (mtuSize >= 23 && mtuSize <= 517) {
                try {
                    const result = await negotiateMTU(mtuSize);
                    logMessage(`MTU negotiated: ${result}`, 'info');
                } catch (error) {
                    console.error('MTU negotiation error:', error);
                }
            } else {
                logMessage('MTU size must be between 23 and 517', 'warning');
            }
        });
    }
    
    // Initial load of bonded devices
    loadBondedDevices();
    
    // Function to load bonded devices
    async function loadBondedDevices() {
        if (!bondedDevicesList) return;
        
        try {
            const devices = await listBondedDevices();
            
            // Clear existing list
            bondedDevicesList.innerHTML = '';
            
            if (devices.length === 0) {
                bondedDevicesList.innerHTML = '<div class="text-gray-500">No bonded devices</div>';
                return;
            }
            
            // Add devices to list
            devices.forEach(device => {
                const deviceElement = document.createElement('div');
                deviceElement.className = 'flex justify-between items-center p-2 border-b';
                deviceElement.innerHTML = `
                    <div>
                        <div class="font-semibold">${device.name || 'Unknown Device'}</div>
                        <div class="text-sm text-gray-500">${device.address}</div>
                    </div>
                    <button class="btn btn-sm btn-secondary connect-bonded" data-address="${device.address}">
                        Connect
                    </button>
                `;
                bondedDevicesList.appendChild(deviceElement);
                
                // Add click handler for connect button
                const connectButton = deviceElement.querySelector('.connect-bonded');
                if (connectButton) {
                    connectButton.addEventListener('click', async () => {
                        try {
                            await connectToDevice(device.address, { autoReconnect: true });
                        } catch (error) {
                            console.error('Connection error:', error);
                        }
                    });
                }
            });
        } catch (error) {
            console.error('Error loading bonded devices:', error);
            bondedDevicesList.innerHTML = '<div class="text-red-500">Error loading bonded devices</div>';
        }
    }
}
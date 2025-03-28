import { BleUI } from './ble-ui.js';
import { BleEvents } from './ble-events.js';

// Constants
export const CONNECTION_STATE = {
    DISCONNECTED: 'disconnected',
    CONNECTING: 'connecting',
    CONNECTED: 'connected',
    DISCONNECTING: 'disconnecting',
    FAILED: 'failed'
};

export const BLE_EVENTS = {
    DEVICE_CONNECTING: 'ble.device.connecting',
    DEVICE_CONNECTED: 'ble.device.connected',
    DEVICE_DISCONNECTING: 'ble.device.disconnecting',
    DEVICE_DISCONNECTED: 'ble.device.disconnected',
    CONNECTION_FAILED: 'ble.connection.failed',
    SERVICES_DISCOVERED: 'ble.services.discovered'
};

/**
 * Update connection status in the application state
 * @param {Object} state - Application state
 * @param {string} status - New connection status
 * @param {string} message - Status message
 */
function updateStatus(state, status, message) {
    if (!state) return;
    
    state.connectionState = status;
    state.statusMessage = message;
    
    // Update UI if available
    if (typeof BleUI !== 'undefined') {
        BleUI.showMessage(message);
        BleUI.updateConnectionStatus(status === CONNECTION_STATE.CONNECTED);
    }
    
    // Log status change
    console.log(`BLE Connection Status: ${status} - ${message}`);
}

/**
 * Save device to connection history
 * @param {string} address - Device address
 * @param {string} name - Device name 
 */
function saveDeviceToHistory(address, name) {
    try {
        const history = getConnectionHistory();
        
        // Check if device is already in history
        const existingIndex = history.findIndex(d => d.address === address);
        if (existingIndex >= 0) {
            // Update existing entry
            history[existingIndex] = {
                address,
                name: name || history[existingIndex].name,
                lastConnected: new Date().toISOString()
            };
        } else {
            // Add new entry
            history.push({
                address,
                name: name || 'Unknown Device',
                lastConnected: new Date().toISOString()
            });
        }
        
        // Keep only the 10 most recent devices
        const recentHistory = history.sort((a, b) => {
            return new Date(b.lastConnected) - new Date(a.lastConnected);
        }).slice(0, 10);
        
        localStorage.setItem('bleConnectedDevices', JSON.stringify(recentHistory));
        return true;
    } catch (error) {
        console.error('Error saving device to history:', error);
        return false;
    }
}

/**
 * Update device information UI
 * @param {Object} deviceInfo - Device information 
 */
function updateDeviceInfoUI(deviceInfo) {
    const deviceInfoElement = document.getElementById('ble-device-info');
    if (!deviceInfoElement) return;
    
    // Generate HTML content
    let content = `
        <div class="device-info-card">
            <div class="device-info-header">
                <h3>${deviceInfo.name || 'Unknown Device'}</h3>
                <div class="device-address">${deviceInfo.address}</div>
            </div>
            <div class="device-info-body">
    `;
    
    // Add services if available
    if (deviceInfo.services && deviceInfo.services.length) {
        content += `<div class="device-services">
            <h4>Services (${deviceInfo.services.length})</h4>
            <ul class="service-list">
        `;
        
        deviceInfo.services.forEach(service => {
            content += `<li data-service-uuid="${service}">${formatUUID(service)}</li>`;
        });
        
        content += `</ul></div>`;
    }
    
    content += `</div></div>`;
    deviceInfoElement.innerHTML = content;
}

/**
 * Format UUID for display
 * @param {string} uuid - UUID to format
 * @returns {string} - Formatted UUID
 */
function formatUUID(uuid) {
    // Remove any dashes or non-hex characters
    const cleanUuid = uuid.replace(/[^0-9a-f]/gi, '');
    
    // Try to match against common services
    const knownServices = {
        '1800': 'Generic Access',
        '1801': 'Generic Attribute',
        '180f': 'Battery Service',
        '180a': 'Device Information',
        '181c': 'User Data',
        '1810': 'Blood Pressure',
        '181d': 'Weight Scale',
        '1809': 'Health Thermometer'
        // Add more as needed
    };
    
    // Check if it's a known service
    for (const [shortUuid, name] of Object.entries(knownServices)) {
        if (uuid.toLowerCase().includes(shortUuid)) {
            return `${name} (${uuid})`;
        }
    }
    
    // Otherwise just return the UUID
    return uuid;
}

/**
 * Reset UI after disconnect
 */
function resetUIAfterDisconnect() {
    // Update connection indicator
    BleUI.updateConnectionStatus(false);
    
    // Clear device info
    const deviceInfoElement = document.getElementById('ble-device-info');
    if (deviceInfoElement) {
        deviceInfoElement.innerHTML = '<div class="no-device">No device connected</div>';
    }
    
    // Disable connection-dependent buttons
    document.querySelectorAll('[data-requires-connection]').forEach(el => {
        el.disabled = true;
    });
    
    // Show/hide elements based on connection state
    document.querySelectorAll('[data-show-when-connected]').forEach(el => {
        el.style.display = 'none';
    });
    
    document.querySelectorAll('[data-show-when-disconnected]').forEach(el => {
        el.style.display = '';
    });
}

/**
 * Core function to establish a BLE connection with a device
 * @param {Object} state - Application state
 * @param {String} deviceId - Device address/ID
 * @param {String} deviceName - Device name
 * @returns {Promise<boolean>} - Connection success
 */
export async function connectToDeviceOriginal(state, deviceId, deviceName) {
    try {
        updateStatus(state, CONNECTION_STATE.CONNECTING, `Connecting to ${deviceName || deviceId}...`);
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const response = await fetch('/api/ble/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address: deviceId }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText);
        }
        
        const result = await response.json();
        
        if (result.connected) {
            // Update state with connected device info
            state.connectedDevice = {
                address: deviceId,
                name: deviceName || result.name || 'Unknown Device',
                connected: true
            };
            
            state.connectionState = CONNECTION_STATE.CONNECTED;
            updateStatus(state, 'connected', `Connected to ${deviceName || deviceId}`);
            
            // Emit connection event using BleEvents instead of bleEventEmitter
            BleEvents.emit(BLE_EVENTS.DEVICE_CONNECTED, { id: deviceId, name: deviceName });
            
            logMessage(`Connected to ${deviceName || deviceId}`, 'success');
            return true;
        } else {
            throw new Error(result.message || 'Connection failed');
        }
    } catch (error) {
        state.connectionState = CONNECTION_STATE.FAILED;
        throw error;
    }
}

/**
 * Log a message
 * @param {string} message - Message to log
 * @param {string} type - Message type (info, success, error)
 */
function logMessage(message, type = 'info') {
    console.log(`BLE [${type}]: ${message}`);
    
    // Use BleUI if available
    if (typeof BleUI !== 'undefined') {
        if (type === 'error') {
            BleUI.showError(message);
        } else {
            BleUI.showMessage(message, type);
        }
    }
}

/**
 * Get services from connected device
 * @param {string} deviceAddress - Device address
 * @returns {Promise<Array>} List of services
 */
export async function getServices(deviceAddress) {
    try {
        const response = await fetch(`/api/ble/services/${deviceAddress}`);
        
        if (!response.ok) {
            throw new Error(`Failed to get services: ${response.status}`);
        }
        
        const data = await response.json();
        return data.services || [];
    } catch (error) {
        console.error('Error getting services:', error);
        return [];
    }
}

/**
 * Connect to a BLE device
 * @param {string} deviceAddress - Device address to connect to
 * @returns {Promise<Object>} Connection result
 */
export async function connectToDevice(deviceAddress) {
    try {
        BleUI.showMessage(`Connecting to ${deviceAddress}...`);
        
        // Emit connecting event
        BleEvents.emit(BLE_EVENTS.DEVICE_CONNECTING, {
            address: deviceAddress
        });
        
        const response = await fetch(`/api/ble/connect/${deviceAddress}`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Connection failed: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.connected) {
            // Update UI
            BleUI.updateConnectionStatus(true, {
                address: deviceAddress,
                name: result.name || 'Connected Device'
            });
            
            // Save to history
            saveDeviceToHistory(deviceAddress, result.name);
            
            // Update device info UI if it exists
            updateDeviceInfoUI({
                address: deviceAddress,
                name: result.name,
                services: result.services || []
            });
            
            // Show success message
            BleUI.showMessage(`Connected to ${result.name || deviceAddress}`);
            
            // Emit connected event
            BleEvents.emit(BLE_EVENTS.DEVICE_CONNECTED, {
                address: deviceAddress,
                name: result.name,
                services: result.services || []
            });
            
            return result;
        } else {
            throw new Error(result.error || 'Connection failed');
        }
    } catch (error) {
        BleUI.showError(`Connection error: ${error.message}`);
        
        // Emit error event
        BleEvents.emit(BLE_EVENTS.CONNECTION_FAILED, {
            address: deviceAddress,
            error: error.message
        });
        
        throw error;
    }
}

/**
 * Disconnect from the currently connected device
 * @returns {Promise<Object>} Disconnection result
 */
export async function disconnectDevice() {
    try {
        BleUI.showMessage('Disconnecting...');
        
        // Emit disconnecting event
        BleEvents.emit(BLE_EVENTS.DEVICE_DISCONNECTING, {});
        
        const response = await fetch('/api/ble/disconnect', {
            method: 'POST'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Disconnection failed: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.disconnected) {
            // Reset UI elements
            resetUIAfterDisconnect();
            
            // Show success message
            BleUI.showMessage('Disconnected from device');
            
            // Emit disconnected event
            BleEvents.emit(BLE_EVENTS.DEVICE_DISCONNECTED, {});
            
            return result;
        } else {
            throw new Error(result.error || 'Disconnection failed');
        }
    } catch (error) {
        BleUI.showError(`Disconnection error: ${error.message}`);
        
        // Emit error event
        BleEvents.emit('ble.error.disconnect', {
            error: error.message
        });
        
        throw error;
    }
}

/**
 * Initialize the connection manager
 */
export function initializeConnectionManager() {
    console.log("Initializing BLE connection manager...");
    
    // Check if auto-connect is enabled (disabled by default)
    const shouldAutoConnect = localStorage.getItem('ble_auto_connect') === 'true';
    
    if (shouldAutoConnect) {
        console.log("Auto-connect is enabled, attempting to connect to last device...");
        setTimeout(() => {
            tryConnectToLastDevice()
                .catch(error => {
                    // Just log the error but don't display to user on page load
                    console.log("Auto-connect failed, but continuing silently:", error);
                });
        }, 1500);  // Wait a bit longer for the app to initialize
    } else {
        console.log("Auto-connect is disabled. User must manually connect.");
    }
    
    // Set up connection-related event listeners
    setupConnectionEventListeners();
}

/**
 * Try to connect to the last used device
 * @returns {Promise<boolean>} Whether connection was successful
 */
async function tryConnectToLastDevice() {
    try {
        // Get the last connected device from localStorage
        const lastDeviceAddress = localStorage.getItem('last_connected_device');
        
        if (!lastDeviceAddress) {
            console.log("No last connected device found");
            return false;
        }
        
        console.log(`Attempting to connect to last device: ${lastDeviceAddress}`);
        
        // Try to connect
        const result = await connectToDevice(lastDeviceAddress);
        return result.connected === true;
    } catch (error) {
        console.error("Failed to connect to last device:", error);
        return false;
    }
}

/**
 * Set up event listeners for connection-related UI elements
 */
function setupConnectionEventListeners() {
    // Connect buttons in the device list
    document.addEventListener('click', function(event) {
        const connectButton = event.target.closest('[data-ble-connect]');
        if (connectButton) {
            const deviceAddress = connectButton.dataset.bleConnect;
            if (deviceAddress) {
                event.preventDefault();
                
                // Update button state
                connectButton.disabled = true;
                connectButton.textContent = 'Connecting...';
                
                // Try to connect
                connectToDevice(deviceAddress)
                    .then(result => {
                        if (result.connected) {
                            BleUI.showMessage(`Connected to ${result.name || deviceAddress}`);
                            // Store as last connected device
                            localStorage.setItem('last_connected_device', deviceAddress);
                        } else {
                            BleUI.showError(`Failed to connect: ${result.error || 'Unknown error'}`);
                        }
                    })
                    .catch(error => {
                        BleUI.showError(`Failed to connect: ${error.message || error}`);
                    })
                    .finally(() => {
                        // Reset button state
                        connectButton.disabled = false;
                        connectButton.textContent = 'Connect';
                    });
            }
        }
    });
    
    // Disconnect button
    const disconnectBtn = document.getElementById('ble-disconnect');
    if (disconnectBtn) {
        disconnectBtn.addEventListener('click', async function() {
            try {
                disconnectBtn.disabled = true;
                disconnectBtn.textContent = 'Disconnecting...';
                
                const result = await disconnectDevice();
                
                if (result.disconnected) {
                    BleUI.showMessage('Device disconnected');
                    BleUI.updateConnectionStatus(false);
                } else {
                    BleUI.showError(`Failed to disconnect: ${result.error || 'Unknown error'}`);
                }
            } catch (error) {
                BleUI.showError(`Disconnect error: ${error.message || error}`);
            } finally {
                disconnectBtn.disabled = false;
                disconnectBtn.textContent = 'Disconnect';
            }
        });
    }
}

/**
 * Check the current connection status of the BLE device
 * @param {Object} state - Application state
 * @returns {String} - Current connection state
 */
export function checkConnectionStatus(state) {
    if (!state) return CONNECTION_STATE.DISCONNECTED;
    return state.connectionState || CONNECTION_STATE.DISCONNECTED;
}

/**
 * Get the connection history from local storage
 * @returns {Array} - Array of previously connected devices
 */
export function getConnectionHistory() {
    try {
        return JSON.parse(localStorage.getItem('bleConnectedDevices') || '[]');
    } catch (error) {
        console.error('Error reading connection history:', error);
        return [];
    }
}

/**
 * Clear the connection history from local storage
 * @returns {boolean} - Success status
 */
export function clearConnectionHistory() {
    try {
        localStorage.removeItem('bleConnectedDevices');
        localStorage.removeItem('last_connected_device');
        return true;
    } catch (error) {
        console.error('Error clearing connection history:', error);
        return false;
    }
}

/**
 * Retry connection to a previously connected device
 * @param {Object} state - Application state
 * @param {String} address - Device address
 * @param {String} name - Device name
 * @returns {Promise<boolean>} - Connection success
 */
export async function retryConnection(state, address, name) {
    try {
        return await connectToDevice(address);
    } catch (error) {
        console.error(`Failed to reconnect to ${name || address}:`, error);
        return false;
    }
}

/**
 * Handle connection timeout scenario
 * @param {Object} state - Application state
 * @param {AbortController} controller - Abort controller for the connection
 * @param {String} address - Device address
 * @param {String} name - Device name
 */
export function handleConnectionTimeout(state, controller, address, name) {
    controller.abort();
    state.connectionState = CONNECTION_STATE.FAILED;
    state.connectionInProgress = false;
    
    logMessage(`Connection to ${name || address} timed out`, 'error');
    
    // Emit timeout event using BleEvents
    BleEvents.emit(BLE_EVENTS.CONNECTION_TIMEOUT || 'ble.connection.timeout', { 
        address, 
        name,
        timestamp: Date.now() 
    });
    
    updateStatus(state, 'failed', 'Connection timed out');
    
    // Use BleUI for loading state
    BleUI.setLoading(false);
}

/**
 * Handle connection state changes
 * @param {Object} state - Application state
 * @param {String} newState - New connection state
 * @param {Object} details - Additional details about the state change
 */
export function onConnectionStateChange(state, newState, details = {}) {
    const prevState = state.connectionState;
    state.connectionState = newState;
    
    logMessage(`Connection state changed: ${prevState} -> ${newState}`, 'info');
    
    // Emit state change event using BleEvents
    BleEvents.emit(BLE_EVENTS.CONNECTION_STATE_CHANGED || 'ble.connection.state_changed', {
        previousState: prevState,
        currentState: newState,
        timestamp: Date.now(),
        ...details
    });
    
    switch (newState) {
        case CONNECTION_STATE.CONNECTED:
            if (state.connectedDevice) {
                saveDeviceToHistory(state.connectedDevice.address, state.connectedDevice.name);
                
                // Fix parameter passing - only pass the device info object, not state
                updateDeviceInfoUI({
                    address: state.connectedDevice.address, 
                    name: state.connectedDevice.name,
                    services: state.connectedDevice.services || []
                });
            }
            break;
        case CONNECTION_STATE.DISCONNECTED:
            // Fix parameter passing - don't pass state to resetUIAfterDisconnect
            resetUIAfterDisconnect();
            break;
        case CONNECTION_STATE.FAILED:
            // Use BleUI for loading state
            BleUI.setLoading(false);
            
            if (details.error) {
                logMessage(`Connection failed: ${details.error}`, 'error');
            }
            break;
        default:
            logMessage(`Unhandled connection state: ${newState}`, 'info');
            break;
    }
    
    updateStatus(state, newState, details.message || '');
}

/**
 * Get connection options from local storage or defaults
 * @returns {Object} - Connection options
 */
export function getConnectionOptions() {
    try {
        const savedOptions = localStorage.getItem('bleConnectionOptions');
        if (savedOptions) {
            return JSON.parse(savedOptions);
        }
    } catch (error) {
        console.error('Error reading connection options:', error);
    }
    
    return {
        timeout: 10,
        autoReconnect: true,
        retryCount: 2,
        pairingEnabled: true
    };
}

/**
 * Save connection options to local storage
 * @param {Object} options - Connection options to save
 * @returns {boolean} - Success status
 */
export function setConnectionOptions(options) {
    try {
        localStorage.setItem('bleConnectionOptions', JSON.stringify(options));
        return true;
    } catch (error) {
        console.error('Error saving connection options:', error);
        return false;
    }
}

/**
 * Cancel an in-progress connection attempt
 * @param {Object} state - Application state
 * @returns {boolean} - Success status
 */
export function cancelConnection(state) {
    if (!state.connectionInProgress) {
        logMessage('No connection in progress to cancel', 'warning');
        return false;
    }
    
    try {
        state.connectionInProgress = false;
        logMessage('Connection attempt cancelled', 'info');
        updateStatus(state, 'disconnected', 'Connection cancelled');
        
        // Use BleUI for loading state
        BleUI.setLoading(false);
        
        // Emit cancelled event using BleEvents
        BleEvents.emit(BLE_EVENTS.CONNECTION_CANCELLED || 'ble.connection.cancelled', {
            timestamp: Date.now()
        });
        
        return true;
    } catch (error) {
        console.error('Error cancelling connection:', error);
        return false;
    }
}
import { logMessage, updateStatus, setLoading } from './ble-ui.js';
import { getServices } from './ble-services.js';
import { BLE_EVENTS } from './ble-events.js';

// Connection states
export const CONNECTION_STATE = {
    DISCONNECTED: 'disconnected',
    CONNECTING: 'connecting',
    CONNECTED: 'connected',
    DISCONNECTING: 'disconnecting',
    FAILED: 'failed'
};

/**
 * Connect to a BLE device with improved error handling
 * @param {Object} state - Application state
 * @param {String} address - Device address
 * @param {String} name - Device name
 * @returns {Promise<boolean>} - Connection success
 */
export async function connectToDevice(state, address, name) {
    const controller = new AbortController();
    let timeoutId;
    
    try {
        // Prevent multiple connection attempts
        if (state.connectionInProgress) {
            logMessage('Connection already in progress, please wait', 'warning');
            return false;
        }
        
        state.connectionInProgress = true;
        
        // Set timeout for the whole operation
        timeoutId = setTimeout(() => {
            controller.abort();
            throw new Error('Connection timed out');
        }, 15000);
        
        // Emit connecting event
        if (window.bleEvents) {
            window.bleEvents.emit(BLE_EVENTS.DEVICE_CONNECTING, {
                address: address,
                name: name
            });
        }

        // Check device availability before connecting
        try {
            await checkDeviceAvailability(address);
        } catch (error) {
            console.warn(`Device availability check failed: ${error.message}`);
            // Continue anyway - device might still be available
        }

        const response = await fetch(`/api/ble/connect/${address}`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache' 
            },
            body: JSON.stringify({
                timeout: 10,            // Connection timeout in seconds
                autoReconnect: true,    // Enable auto-reconnect
                retryCount: 2           // Number of retry attempts
            }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        // Handle failure
        if (!response.ok) {
            let errorMessage = `Connection failed: ${response.status} ${response.statusText}`;
            
            try {
                const errorText = await response.text();
                // Try to parse as JSON
                try {
                    const errorJson = JSON.parse(errorText);
                    errorMessage = errorJson.detail || errorMessage;
                } catch (e) {
                    // If not JSON, use the raw error text
                    errorMessage = errorText || errorMessage;
                }
            } catch (e) {
                // If we can't read the response, just use the status text
                console.error("Error reading error response:", e);
            }

            throw new Error(errorMessage);
        }

        // Parse response
        const connectionData = await response.json();
        
        // Set device connected state and update UI
        state.connectedDevice = {
            address,
            name,
            connectionTime: new Date(),
            services: connectionData.services || {}
        };
        
        logMessage(`Successfully connected to ${name}`, 'success');
        updateStatus(state, 'connected', `Connected to ${name}`);
        
        return true;
    } catch (error) {
        console.error('Connection error:', error);
        logMessage(`Connection failed: ${error.message}`, 'error');
        
        // Emit error event
        if (window.bleEvents) {
            window.bleEvents.emit(BLE_EVENTS.CONNECTION_ERROR, {
                address,
                name,
                error: error.message
            });
        }
        
        return false;
    } finally {
        state.connectionInProgress = false;
        clearTimeout(timeoutId);
    }
}

/**
 * Check device availability before connecting
 * @param {String} address - Device address
 * @returns {Promise<void>}
 */
async function checkDeviceAvailability(address) {
    try {
        // Make a quick scan to verify the device is still available
        const response = await fetch(`/api/ble/device-exists/${address}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            timeout: 3000
        });
        
        if (!response.ok) {
            const data = await response.json();
            if (data.exists === false) {
                throw new Error(`Device ${address} is not currently available. Please scan again.`);
            }
        }
    } catch (error) {
        console.warn(`Device availability check failed: ${error.message}`);
        // We don't throw here - just log the warning and continue with connection attempt
    }
}

/**
 * Update the device info UI with connected device details
 */
function updateDeviceInfoUI(state, address, name) {
    if (state.domElements.deviceInfoContent) {
        state.domElements.deviceInfoContent.innerHTML = `
            <div class="flex flex-col space-y-2">
                <div class="font-semibold text-white">${name}</div>
                <div class="text-sm text-gray-400">Address: ${address}</div>
                <div class="text-sm text-gray-400">Status: <span class="text-green-500">Connected</span></div>
                <div class="flex items-center mt-1 space-x-2">
                    <div class="w-2 h-2 rounded-full bg-green-500"></div>
                    <span class="text-xs text-gray-400">Active connection</span>
                </div>
                <div class="mt-4 flex space-x-2">
                    <button id="pair-btn" class="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm">
                        <i class="fas fa-link mr-1"></i> Pair
                    </button>
                    <button id="refresh-services-btn" class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                        <i class="fas fa-sync mr-1"></i> Refresh
                    </button>
                </div>
            </div>
        `;
        
        // Add button event handlers
        const pairBtn = document.getElementById('pair-btn');
        if (pairBtn) {
            pairBtn.addEventListener('click', () => pairWithDevice(state, address, name));
        }
        
        const refreshBtn = document.getElementById('refresh-services-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => getServices(state));
        }
    }
}

/**
 * Save device to connection history
 */
function saveDeviceToHistory(address, name) {
    try {
        const savedDevices = JSON.parse(localStorage.getItem('bleConnectedDevices') || '[]');
        const deviceToSave = { 
            id: address, 
            name: name || 'Unknown Device',
            lastConnected: new Date().toISOString() 
        };
        
        // Add to front of array, remove duplicates, limit to 5 devices
        savedDevices.unshift(deviceToSave);
        const uniqueDevices = savedDevices.filter((device, index, self) => 
            index === self.findIndex(d => d.id === device.id)
        ).slice(0, 5);
        
        localStorage.setItem('bleConnectedDevices', JSON.stringify(uniqueDevices));
    } catch (error) {
        console.error('Error saving device history:', error);
    }
}

/**
 * Disconnect from the currently connected device
 * @param {Object} state - Application state
 * @returns {Promise<boolean>} - Disconnection success
 */
export async function disconnectFromDevice(state) {
    if (!state.connectedDevice) {
        logMessage('No device connected', 'warning');
        return false;
    }

    try {
        // Update state
        state.connectionState = CONNECTION_STATE.DISCONNECTING;
        
        // Update UI
        logMessage('Disconnecting from device...', 'info');
        setLoading(state, true, 'Disconnecting...');
        updateStatus(state, 'disconnecting', 'Disconnecting from device...');

        // Emit event before actual disconnect
        if (window.bleEvents) {
            window.bleEvents.emit(BLE_EVENTS.DEVICE_DISCONNECTING, {
                address: state.connectedDevice.address,
                name: state.connectedDevice.name
            });
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const response = await fetch('/api/ble/disconnect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Disconnection failed: ${errorText}`);
        }

        await response.json();
        
        // Clear state
        const disconnectedDevice = {...state.connectedDevice};
        state.connectedDevice = null;
        state.subscribedCharacteristics.clear();
        state.connectionState = CONNECTION_STATE.DISCONNECTED;
        
        // Update UI
        logMessage('Disconnected from device', 'success');
        updateStatus(state, 'disconnected', 'Not connected to any device');

        // Hide/reset UI elements
        resetUIAfterDisconnect(state);

        // Emit disconnect event
        if (window.bleEvents) {
            window.bleEvents.emit(BLE_EVENTS.DEVICE_DISCONNECTED, disconnectedDevice);
        }

        return true;
    } catch (error) {
        console.error('Disconnection error:', error);
        logMessage(`Disconnection failed: ${error.message}`, 'error');
        updateStatus(state, 'error', `Disconnection failed: ${error.message}`);
        
        // Force disconnect if backend failed but we want UI to reflect disconnected state
        if (error.message.includes('already disconnected') || error.message.includes('not connected')) {
            state.connectedDevice = null;
            state.subscribedCharacteristics.clear();
            state.connectionState = CONNECTION_STATE.DISCONNECTED;
            resetUIAfterDisconnect(state);
            
            if (window.bleEvents) {
                window.bleEvents.emit(BLE_EVENTS.DEVICE_DISCONNECTED, {forced: true});
            }
            
            return true;
        }
        
        return false;
    } finally {
        setLoading(state, false);
    }
}

/**
 * Reset UI elements after disconnect
 */
function resetUIAfterDisconnect(state) {
    if (state.domElements.disconnectBtn) {
        state.domElements.disconnectBtn.classList.add('hidden');
    }
    if (state.domElements.deviceInfoContent) {
        state.domElements.deviceInfoContent.innerHTML = '<div class="text-gray-500">No device connected</div>';
    }
    if (state.domElements.servicesList) {
        state.domElements.servicesList.innerHTML = '<div class="text-gray-500">Connect to a device to view services</div>';
    }
    if (state.domElements.characteristicsList) {
        state.domElements.characteristicsList.innerHTML = '<div class="text-gray-500">Select a service to view characteristics</div>';
    }
    if (state.domElements.notificationsContainer) {
        state.domElements.notificationsContainer.innerHTML = '<div class="text-gray-500">Subscribe to receive characteristic updates</div>';
    }
    if (state.domElements.batteryContainer) {
        state.domElements.batteryContainer.classList.add('hidden');
    }
}

/**
 * Attempt to pair with a connected device
 * @param {Object} state - Application state
 * @param {String} address - Device address
 * @param {String} name - Device name
 * @returns {Promise<boolean>} - Pairing success
 */
export async function pairWithDevice(state, address, name) {
    try {
        logMessage(`Attempting to pair with ${name}...`, 'info');
        setLoading(state, true, `Pairing with ${name}...`);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const response = await fetch(`/api/ble/pair/${address}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Pairing failed: ${errorText}`);
        }

        const result = await response.json();
        if (result.status === 'paired') {
            logMessage(`Successfully paired with ${name}`, 'success');
            if (state.domElements.deviceInfoContent) {
                const currentContent = state.domElements.deviceInfoContent.innerHTML;
                const updatedContent = currentContent.replace('Status: <span class="text-green-500">Connected</span>', 'Status: <span class="text-blue-500">Paired</span>');
                state.domElements.deviceInfoContent.innerHTML = updatedContent;
                const pairBtn = document.getElementById('pair-btn');
                if (pairBtn) {
                    const pairLabel = document.createElement('div');
                    pairLabel.className = 'bg-blue-700 text-white px-3 py-1 rounded text-sm inline-block';
                    pairLabel.innerHTML = '<i class="fas fa-link mr-1"></i> Paired';
                    pairBtn.parentNode.replaceChild(pairLabel, pairBtn);
                }
            }
            
            // Emit pairing event
            if (window.bleEvents) {
                window.bleEvents.emit(BLE_EVENTS.DEVICE_PAIRED, {
                    address: address,
                    name: name
                });
            }
            
            return true;
        } else {
            logMessage(`Pairing status: ${result.status}`, 'warning');
            return false;
        }
    } catch (error) {
        console.error('Pairing error:', error);
        logMessage(`Pairing failed: ${error.message}`, 'error');
        
        // Emit pairing error event
        if (window.bleEvents) {
            window.bleEvents.emit(BLE_EVENTS.PAIRING_ERROR, {
                address: address,
                name: name,
                error: error.message
            });
        }
        
        return false;
    } finally {
        setLoading(state, false);
    }
}

/**
 * Initialize connection manager and setup reconnection
 * @param {Object} state - Application state
 */
export function initializeConnectionManager(state) {
    // Load previously connected devices from localStorage
    const savedDevices = JSON.parse(localStorage.getItem('bleConnectedDevices') || '[]');
    
    // Check if we should attempt auto-reconnect
    const shouldAutoReconnect = localStorage.getItem('bleAutoReconnect') === 'true';
    
    if (shouldAutoReconnect && savedDevices.length > 0) {
        const lastDevice = savedDevices[0];
        logMessage(`Attempting to reconnect to last device: ${lastDevice.name || lastDevice.id}`, 'info');
        
        // Wait a bit before trying to reconnect
        setTimeout(() => {
            connectToDevice(state, lastDevice.id, lastDevice.name);
        }, 2000);
    }
}
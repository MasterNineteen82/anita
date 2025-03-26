import { logMessage, updateStatus, setLoading } from './ble-ui.js';
import { getServices } from './ble-services.js';

/**
 * Connect to a BLE device
 * @param {Object} state - Application state
 * @param {String} address - Device address
 * @param {String} name - Device name
 * @returns {Promise<boolean>} - Connection success
 */
export async function connectToDevice(state, address, name) {
    try {
        console.log(`Attempting to connect to ${name} (${address})...`);
        logMessage(`Attempting to connect to ${name} (${address})...`, 'info');
        setLoading(state, true, `Connecting to ${name}...`);
        updateStatus(state, 'connecting', `Connecting to ${name}...`);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000);
        const response = await fetch(`/api/ble/connect/${address}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (response.ok) {
            // Existing code...
        } else {
            // Add this error handling
            logMessage(`Failed to read battery level: ${response.status} ${response.statusText}`, 'error');
        }

        await response.json();
        state.connectedDevice = { address, name };
        logMessage(`Successfully connected to ${name}`, 'success');
        updateStatus(state, 'connected', `Connected to ${name}`);

        if (state.domElements.disconnectBtn) {
            state.domElements.disconnectBtn.classList.remove('hidden');
        }

        if (state.domElements.deviceInfoContent) {
            state.domElements.deviceInfoContent.innerHTML = `
                <div class="flex flex-col space-y-2">
                    <div class="font-semibold text-white">${name}</div>
                    <div class="text-sm text-gray-400">Address: ${address}</div>
                    <div class="text-sm text-gray-400">Status: Connected</div>
                    <div class="mt-4">
                        <button id="pair-btn" class="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm">
                            Pair Device
                        </button>
                    </div>
                </div>
            `;
            const pairBtn = document.getElementById('pair-btn');
            if (pairBtn) {
                pairBtn.addEventListener('click', () => pairWithDevice(state, address, name));
            }
        }

        await getServices(state);

        // Save connected device to localStorage
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

        return true;
    } catch (error) {
        console.error('Connection error:', error);
        logMessage(`Connection failed: ${error.message}`, 'error');
        updateStatus(state, 'error', `Connection failed: ${error.message}`);
        return false;
    } finally {
        setLoading(state, false);
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
        logMessage('Disconnecting from device...', 'info');
        setLoading(state, true, 'Disconnecting...');
        updateStatus(state, 'disconnecting', 'Disconnecting from device...');

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
        state.connectedDevice = null;
        state.subscribedCharacteristics.clear();
        logMessage('Disconnected from device', 'success');
        updateStatus(state, 'disconnected', 'Not connected to any device');

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

        return true;
    } catch (error) {
        console.error('Disconnection error:', error);
        logMessage(`Disconnection failed: ${error.message}`, 'error');
        updateStatus(state, 'error', `Disconnection failed: ${error.message}`);
        return false;
    } finally {
        setLoading(state, false);
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
                const updatedContent = currentContent.replace('Status: Connected', 'Status: Paired');
                state.domElements.deviceInfoContent.innerHTML = updatedContent;
                const pairBtn = document.getElementById('pair-btn');
                if (pairBtn) {
                    const pairLabel = document.createElement('div');
                    pairLabel.className = 'bg-green-700 text-white px-3 py-1 rounded text-sm inline-block';
                    pairLabel.innerHTML = '<i class="fas fa-check mr-1"></i> Paired';
                    pairBtn.parentNode.replaceChild(pairLabel, pairBtn);
                }
            }
            return true;
        } else {
            logMessage(`Pairing status: ${result.status}`, 'warning');
            return false;
        }
    } catch (error) {
        console.error('Pairing error:', error);
        logMessage(`Pairing failed: ${error.message}`, 'error');
        return false;
    } finally {
        setLoading(state, false);
    }
}

function initializeConnectionManager(state) {
    // Load previously connected devices from localStorage
    const savedDevices = JSON.parse(localStorage.getItem('bleConnectedDevices') || '[]');
    
    // Check if we should attempt auto-reconnect
    const shouldAutoReconnect = localStorage.getItem('bleAutoReconnect') === 'true';
    
    if (shouldAutoReconnect && savedDevices.length > 0) {
      const lastDevice = savedDevices[0];
      logMessage(`Attempting to reconnect to last device: ${lastDevice.name || lastDevice.id}`, 'info');
      connectToDevice(state, lastDevice.id);
    }
}
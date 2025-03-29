import { BleUI } from './ble-ui.js';
import { BleEvents } from './ble-events.js';

/**
 * BLE Connection module for handling device connections
 */
export class BleConnection {
    constructor(state = {}) {
        this.state = state;
        this.connecting = false;
    }

    /**
     * Initialize the connection module
     */
    async initialize() {
        console.log('Initializing BLE Connection module');
        // Any initialization logic here
    }

    /**
     * Connect to a BLE device
     * @param {string} deviceId - The device address to connect to
     * @returns {Promise<boolean>} - Success status
     */
    async connectToDevice(deviceId) {
        if (this.connecting) {
            BleUI.showToast('Connection already in progress', 'warning');
            return false;
        }

        if (this.state.connectedDevice === deviceId) {
            BleUI.showToast('Already connected to this device', 'info');
            return true;
        }

        try {
            this.connecting = true;
            BleUI.showToast(`Connecting to device ${deviceId}...`, 'info');

            const response = await fetch(`/api/ble/device/${deviceId}/connect`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Connection failed');
            }

            const result = await response.json();

            // Update state
            this.state.connectedDevice = deviceId;

            // Emit connection event
            BleEvents.emit('DEVICE_CONNECTED', {
                deviceId,
                details: result
            });

            BleUI.showToast('Connected successfully', 'success');
            return true;
        } catch (error) {
            console.error('Connection error:', error);
            BleUI.showToast(`Connection failed: ${error.message}`, 'error');
            return false;
        } finally {
            this.connecting = false;
        }
    }

    /**
     * Disconnect from the currently connected device
     * @returns {Promise<boolean>} - Success status
     */
    async disconnectDevice() {
        if (!this.state.connectedDevice) {
            BleUI.showToast('No device connected', 'warning');
            return false;
        }

        try {
            BleUI.showToast('Disconnecting...', 'info');
            const deviceId = this.state.connectedDevice;

            const response = await fetch(`/api/ble/device/${deviceId}/disconnect`, {
                method: 'POST'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Disconnection failed');
            }

            await response.json();

            // Update state
            this.state.connectedDevice = null;

            // Emit disconnection event
            BleEvents.emit('DEVICE_DISCONNECTED', {
                deviceId
            });

            BleUI.showToast('Disconnected successfully', 'success');
            return true;
        } catch (error) {
            console.error('Disconnection error:', error);
            BleUI.showToast(`Disconnection failed: ${error.message}`, 'error');
            return false;
        }
    }
}

// Export stand-alone function for compatibility with existing code
export const connectToDevice = (deviceId) => {
    const connection = new BleConnection();
    return connection.connectToDevice(deviceId);
};
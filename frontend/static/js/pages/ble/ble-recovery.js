import { BleUI } from './ble-ui.js';
import { BleEvents, BLE_EVENTS } from './ble-events.js';
import { connectToDevice } from './ble-connection.js';

/**
 * BLE Recovery Module
 * Handles recovery from common BLE errors and connection issues
 */
export class BleRecovery {
    constructor(state = {}) {
        this.state = state;
    }

    async initialize() {
        console.log('Initializing BLE Recovery module');

        // Subscribe to error events
        BleEvents.on(BLE_EVENTS.ERROR, (error) => this.handleError(error));
    }

    /**
     * Handle BLE errors and attempt recovery
     * @param {Object} error - Error object
     */
    async handleError(error) {
        console.warn('Handling BLE error:', error);

        switch (error.message) {
            case 'Device connection was lost':
                BleUI.showToast('Device connection lost. Attempting to reconnect...', 'warning');
                await this.reconnectDevice();
                break;
            case 'GATT operation failed':
                BleUI.showToast('GATT operation failed. Resetting connection...', 'warning');
                await this.resetConnection();
                break;
            default:
                BleUI.showToast(`Unhandled BLE error: ${error.message}`, 'error');
        }
    }

    /**
     * Attempt to reconnect to the last connected device
     */
    async reconnectDevice() {
        if (!this.state.connectedDevice) {
            BleUI.showToast('No device to reconnect to', 'info');
            return;
        }

        BleUI.showToast(`Attempting to reconnect to ${this.state.connectedDevice}...`, 'info');

        try {
            const success = await connectToDevice(this.state.connectedDevice);
            if (success) {
                BleUI.showToast('Reconnected successfully', 'success');
            } else {
                BleUI.showToast('Reconnection failed', 'error');
            }
        } catch (error) {
            console.error('Reconnection error:', error);
            BleUI.showToast(`Reconnection failed: ${error.message}`, 'error');
        }
    }

    /**
     * Reset the BLE connection
     */
    async resetConnection() {
        BleUI.showToast('Resetting BLE connection...', 'info');

        try {
            // Disconnect if connected
            if (this.state.connectedDevice) {
                await this.disconnectDevice();
            }

            // Reset adapter
            await this.resetAdapter();

            BleUI.showToast('BLE connection reset', 'success');
        } catch (error) {
            console.error('Reset connection error:', error);
            BleUI.showToast(`Reset connection failed: ${error.message}`, 'error');
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

    /**
     * Reset the BLE adapter
     */
    async resetAdapter() {
        BleUI.showToast('Resetting BLE adapter...', 'info');

        try {
            const response = await fetch('/api/ble/adapter/reset', {
                method: 'POST'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Adapter reset failed');
            }

            await response.json();
            BleUI.showToast('BLE adapter reset successfully', 'success');
        } catch (error) {
            console.error('Adapter reset error:', error);
            BleUI.showToast(`Adapter reset failed: ${error.message}`, 'error');
        }
    }
}
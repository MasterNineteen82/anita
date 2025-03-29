import { BleUI, logMessage } from './ble-ui.js';
import { BleEvents, BLE_EVENTS } from './ble-events.js';
import { formatCharacteristicValue } from './ble-services.js';
import { sendWebSocketCommand } from './ble-websocket.js';

/**
 * BLE Notifications Module
 * Handles subscription, unsubscription, and displaying of BLE characteristic notifications
 */
export class BleNotifications {
    constructor(state = {}) {
        this.state = state;
        this.subscribedCharacteristics = new Set();
    }

    async initialize() {
        console.log('Initializing BLE Notifications module');
    }

    /**
     * Subscribe to notifications for a characteristic
     * @param {Object} state - Application state
     * @param {String} serviceUuid - Service UUID
     * @param {String} charUuid - Characteristic UUID
     * @returns {Promise<boolean>} - Success status
     */
    async subscribeToNotifications(serviceUuid, charUuid) {
        try {
            const response = await fetch(`/api/ble/services/${serviceUuid}/characteristics/${charUuid}/notify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notify: true })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to subscribe to characteristic: ${errorText}`);
            }

            await response.json();
            this.subscribedCharacteristics.add(charUuid);
            logMessage(`Subscribed to notifications for ${charUuid}`, 'success');

            // Emit event using BleEvents instead of window.bleEvents
            BleEvents.emit(BLE_EVENTS.NOTIFICATION_SUBSCRIBED, {
                serviceUuid,
                charUuid,
                timestamp: Date.now()
            });

            return true;
        } catch (error) {
            logMessage(`Subscription error: ${error.message}`, 'error');
            return false;
        }
    }

    /**
     * Unsubscribe from notifications for a characteristic
     * @param {Object} state - Application state
     * @param {String} serviceUuid - Service UUID
     * @param {String} charUuid - Characteristic UUID
     * @returns {Promise<boolean>} - Success status
     */
    async unsubscribeFromNotifications(serviceUuid, charUuid) {
        try {
            const response = await fetch(`/api/ble/services/${serviceUuid}/characteristics/${charUuid}/notify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notify: false })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to unsubscribe from characteristic: ${errorText}`);
            }

            await response.json();
            this.subscribedCharacteristics.delete(charUuid);
            logMessage(`Unsubscribed from notifications for ${charUuid}`, 'success');

            // Emit event using BleEvents instead of window.bleEvents
            BleEvents.emit(BLE_EVENTS.NOTIFICATION_UNSUBSCRIBED, {
                serviceUuid,
                charUuid,
                timestamp: Date.now()
            });

            return true;
        } catch (error) {
            logMessage(`Unsubscription error: ${error.message}`, 'error');
            return false;
        }
    }

    /**
     * Handle incoming notification
     * @param {Object} state - Application state
     * @param {String} serviceUuid - Service UUID
     * @param {String} charUuid - Characteristic UUID
     * @param {String} value - Characteristic value
     */
    handleNotification(serviceUuid, charUuid, value) {
        logMessage(`Notification received for ${charUuid}: ${value}`, 'info');

        // Format the characteristic value
        const formattedValue = formatCharacteristicValue(value);

        // Emit event using BleEvents instead of window.bleEvents
        BleEvents.emit(BLE_EVENTS.CHARACTERISTIC_NOTIFICATION, {
            serviceUuid,
            charUuid,
            value: formattedValue,
            timestamp: Date.now()
        });
    }
}


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
    async subscribeToNotifications(characteristic_uuid) {
        try {
            // Updated endpoint for the notification manager
            const response = await fetch('/api/ble/notifications/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    characteristic_uuid: characteristic_uuid,
                    enable: true 
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to subscribe to characteristic');
            }

            await response.json();
            this.subscribedCharacteristics.add(characteristic_uuid);
            
            BleUI.showToast(`Subscribed to ${characteristic_uuid}`, 'success');
            
            // Emit event
            BleEvents.emit(BleEvents.NOTIFICATION_SUBSCRIBED, {
                characteristic: characteristic_uuid
            });
            
            return true;
        } catch (error) {
            console.error('Error subscribing to characteristic:', error);
            BleUI.showToast(`Subscription failed: ${error.message}`, 'error');
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


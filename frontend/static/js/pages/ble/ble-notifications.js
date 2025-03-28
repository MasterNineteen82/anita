import { BleUI, logMessage } from './ble-ui.js';
import { BleEvents, BLE_EVENTS } from './ble-events.js';
import { formatCharacteristicValue } from './ble-services.js';
import { sendWebSocketCommand } from './ble-websocket.js';

/**
 * BLE Notifications Module
 * Handles subscription, unsubscription, and displaying of BLE characteristic notifications
 */

// Keep track of subscribed characteristics
const subscribedCharacteristics = new Set();

/**
 * Subscribe to notifications for a characteristic
 * @param {Object} state - Application state
 * @param {String} serviceUuid - Service UUID
 * @param {String} charUuid - Characteristic UUID
 * @returns {Promise<boolean>} - Success status
 */
export async function subscribeToNotifications(state, serviceUuid, charUuid) {
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
        subscribedCharacteristics.add(charUuid);
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
        console.error('Failed to subscribe to notifications:', error);
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
export async function unsubscribeFromNotifications(state, serviceUuid, charUuid) {
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
        subscribedCharacteristics.delete(charUuid);
        logMessage(`Unsubscribed from notifications for ${charUuid}`, 'success');
        
        // Emit event using BleEvents
        BleEvents.emit(BLE_EVENTS.NOTIFICATION_UNSUBSCRIBED, { 
            serviceUuid, 
            charUuid,
            timestamp: Date.now()
        });
        
        return true;
    } catch (error) {
        logMessage(`Unsubscription error: ${error.message}`, 'error');
        console.error('Failed to unsubscribe from notifications:', error);
        return false;
    }
}

/**
 * Handle an incoming notification
 * @param {Object} state - Application state
 * @param {Object} notification - Notification data
 */
export function handleNotification(state, notification) {
    const { characteristic, value_hex, decoded_value } = notification;
    
    console.log(`Notification received for ${characteristic}: ${value_hex}`);
    
    // Add to notification history UI
    addNotificationToUI(state, characteristic, value_hex);
    
    // Emit event using BleEvents
    BleEvents.emit(BLE_EVENTS.CHARACTERISTIC_NOTIFICATION, {
        uuid: characteristic,
        valueHex: value_hex,
        value: decoded_value || formatCharacteristicValue(value_hex),
        timestamp: Date.now()
    });
}

/**
 * Add a notification to the UI
 * @param {Object} state - Application state
 * @param {String} characteristic - Characteristic UUID
 * @param {String} value_hex - Hex value
 */
export function addNotificationToUI(state, characteristic, value_hex) {
    const { notificationsContainer } = state.domElements;
    if (!notificationsContainer) return;

    const formattedValue = formatCharacteristicValue(value_hex);
    const timestamp = new Date().toLocaleTimeString();
    const notificationEl = document.createElement('div');
    notificationEl.className = 'bg-gray-800 p-3 rounded mb-2 border border-gray-700 notification-item';
    notificationEl.innerHTML = `
        <div class="flex justify-between">
            <div class="text-xs text-gray-400">${timestamp}</div>
            <div class="text-xs text-blue-400">${characteristic.substring(0, 8)}...</div>
        </div>
        <div class="mt-1 font-mono text-sm text-white">${formattedValue}</div>
    `;

    // Add animation class
    notificationEl.classList.add('notification-highlight');
    
    // Remove animation after it completes
    setTimeout(() => {
        notificationEl.classList.remove('notification-highlight');
    }, 1000);

    if (notificationsContainer.firstChild) {
        notificationsContainer.insertBefore(notificationEl, notificationsContainer.firstChild);
    } else {
        notificationsContainer.appendChild(notificationEl);
    }

    // Limit number of notifications
    const MAX_NOTIFICATIONS = 20;
    while (notificationsContainer.children.length > MAX_NOTIFICATIONS) {
        notificationsContainer.removeChild(notificationsContainer.lastChild);
    }
}

/**
 * Clear all notifications from the UI
 * @param {Object} state - Application state
 */
export function clearNotifications(state) {
    const { notificationsContainer } = state.domElements;
    if (!notificationsContainer) return;
    
    while (notificationsContainer.firstChild) {
        notificationsContainer.removeChild(notificationsContainer.firstChild);
    }
    
    logMessage('Notifications cleared', 'info');
}

/**
 * Get a list of currently subscribed characteristics
 * @returns {Set<string>} - Set of characteristic UUIDs
 */
export function getSubscribedCharacteristics() {
    return new Set(subscribedCharacteristics);
}

/**
 * Check if a characteristic is currently subscribed
 * @param {String} charUuid - Characteristic UUID
 * @returns {Boolean} - Whether the characteristic is subscribed
 */
export function isSubscribed(charUuid) {
    return subscribedCharacteristics.has(charUuid);
}

/**
 * Setup WebSocket connection for BLE notifications
 * @param {Object} state - Application state
 * @returns {WebSocket} - The WebSocket connection
 */
export function setupNotificationWebSocket(state) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/ble/notifications/ws`;
    
    const socket = new WebSocket(wsUrl);
    
    socket.onopen = () => {
        logMessage('Notification WebSocket connected', 'success');
    };
    
    socket.onmessage = (event) => {
        try {
            const notification = JSON.parse(event.data);
            handleNotification(state, notification);
        } catch (error) {
            console.error('Error processing notification:', error);
        }
    };
    
    socket.onerror = (error) => {
        logMessage('WebSocket error', 'error');
        console.error('WebSocket error:', error);
    };
    
    socket.onclose = () => {
        logMessage('Notification WebSocket disconnected', 'info');
        // Attempt to reconnect after a delay
        setTimeout(() => {
            if (state.connected) {
                setupNotificationWebSocket(state);
            }
        }, 3000);
    };
    
    return socket;
}


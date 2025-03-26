import { logMessage } from './ble-ui.js';

/**
 * Get services for connected device
 * @param {Object} state - Application state
 */
export async function getServices(state) {
    if (!state.connectedDevice) {
        logMessage('No device connected', 'warning');
        return;
    }

    const { servicesList } = state.domElements;
    if (!servicesList) {
        logMessage('Services list element not found', 'error');
        return;
    }

    try {
        logMessage('Fetching BLE services...', 'info');
        servicesList.innerHTML = '<div class="text-gray-500 animate-pulse">Loading services...</div>';

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const response = await fetch('/api/ble/services', { signal: controller.signal });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to get services: ${errorText}`);
        }

        const services = await response.json();
        servicesList.innerHTML = '';

        if (!services.length) {
            servicesList.innerHTML = '<div class="text-gray-500">No services found</div>';
            logMessage('No services detected on device', 'warning');
            return;
        }

        logMessage(`Found ${services.length} services`, 'success');
        services.forEach(service => {
            const serviceEl = document.createElement('div');
            serviceEl.className = 'bg-gray-700 p-3 rounded mb-2 hover:bg-gray-600 transition-colors';
            serviceEl.innerHTML = `
                <div class="font-medium text-white">${service.description || 'Unknown Service'}</div>
                <div class="text-xs text-gray-400">${service.uuid}</div>
                <button class="get-chars-btn mt-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition-colors"
                        data-uuid="${service.uuid}">
                    Get Characteristics
                </button>
                <div class="chars-container mt-2 hidden" id="chars-${service.uuid.replace(/[^a-z0-9]/gi, '')}"></div>
            `;
            servicesList.appendChild(serviceEl);
        });

        document.querySelectorAll('.get-chars-btn').forEach(button => {
            button.addEventListener('click', async (e) => {
                const serviceUuid = e.target.dataset.uuid;
                const charsContainer = document.getElementById(`chars-${serviceUuid.replace(/[^a-z0-9]/gi, '')}`);
                if (charsContainer) {
                    charsContainer.classList.toggle('hidden');
                    if (!charsContainer.innerHTML) {
                        await getCharacteristics(state, serviceUuid);
                    }
                }
            });
        });
    } catch (error) {
        console.error('Error fetching services:', error);
        servicesList.innerHTML = `<div class="text-red-500">Error: ${error.message}</div>`;
        logMessage(`Failed to get services: ${error.message}`, 'error');
    }
}

/**
 * Get characteristics for a service
 * @param {Object} state - Application state
 * @param {String} serviceUuid - Service UUID
 */
export async function getCharacteristics(state, serviceUuid) {
    if (!state.connectedDevice) {
        logMessage('No device connected', 'warning');
        return;
    }

    const charsContainer = document.getElementById(`chars-${serviceUuid.replace(/[^a-z0-9]/gi, '')}`);
    if (!charsContainer) {
        logMessage(`Characteristics container for ${serviceUuid} not found`, 'warning');
        return;
    }

    try {
        logMessage(`Fetching characteristics for service ${serviceUuid}...`, 'info');
        charsContainer.innerHTML = '<div class="text-gray-500 animate-pulse">Loading characteristics...</div>';

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const response = await fetch(`/api/ble/services/${serviceUuid}/characteristics`, { signal: controller.signal });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to get characteristics: ${errorText}`);
        }

        const characteristics = await response.json();
        charsContainer.innerHTML = '';

        if (!characteristics.length) {
            charsContainer.innerHTML = '<div class="text-gray-500">No characteristics found</div>';
            logMessage('No characteristics detected on service', 'warning');
            return;
        }

        logMessage(`Found ${characteristics.length} characteristics`, 'success');
        characteristics.forEach(char => {
            const charEl = document.createElement('div');
            charEl.className = 'bg-gray-800 p-3 rounded mb-2 hover:bg-gray-700 transition-colors';
            charEl.innerHTML = `
                <div class="font-medium text-white">${char.description || 'Unknown Characteristic'}</div>
                <div class="text-xs text-gray-400">${char.uuid}</div>
                <div class="flex mt-2 space-x-2">
                    <button class="read-char-btn bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-sm transition-colors"
                            data-service-uuid="${serviceUuid}" data-char-uuid="${char.uuid}">
                        <i class="fas fa-book-reader"></i> Read
                    </button>
                    <button class="write-char-btn bg-yellow-600 hover:bg-yellow-700 text-white px-3 py-1 rounded text-sm transition-colors"
                            data-service-uuid="${serviceUuid}" data-char-uuid="${char.uuid}">
                        <i class="fas fa-pen"></i> Write
                    </button>
                    <button class="notify-char-btn bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition-colors"
                            data-service-uuid="${serviceUuid}" data-char-uuid="${char.uuid}"
                            data-subscribed="false" title="Subscribe to notifications">
                        <i class="fas fa-bell"></i>
                    </button>
                </div>
                <div class="notification-value mt-2 text-sm text-gray-300 font-mono"></div>
            `;
            charsContainer.appendChild(charEl);
        });

        document.querySelectorAll('.read-char-btn').forEach(button => {
            button.addEventListener('click', async (e) => {
                await readCharacteristic(state, e.target.dataset.serviceUuid, e.target.dataset.charUuid);
            });
        });

        document.querySelectorAll('.write-char-btn').forEach(button => {
            button.addEventListener('click', async (e) => {
                await writeCharacteristic(state, e.target.dataset.serviceUuid, e.target.dataset.charUuid);
            });
        });

        document.querySelectorAll('.notify-char-btn').forEach(button => {
            button.addEventListener('click', async (e) => {
                await toggleNotification(state, e.target.dataset.serviceUuid, e.target.dataset.charUuid);
            });
        });
    } catch (error) {
        console.error('Error fetching characteristics:', error);
        charsContainer.innerHTML = `<div class="text-red-500">Failed to load characteristics: ${error.message}</div>`;
        logMessage(`Failed to get characteristics: ${error.message}`, 'error');
    }
}

/**
 * Read characteristic value
 * @param {Object} state - Application state
 * @param {String} serviceUuid - Service UUID
 * @param {String} charUuid - Characteristic UUID
 */
export async function readCharacteristic(state, serviceUuid, charUuid) {
    if (!state.connectedDevice) {
        logMessage('No device connected', 'warning');
        return;
    }

    try {
        logMessage(`Reading characteristic ${charUuid}...`, 'info');
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const response = await fetch(`/api/ble/services/${serviceUuid}/characteristics/${charUuid}/read`, { signal: controller.signal });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to read characteristic: ${errorText}`);
        }

        const data = await response.json();
        const formattedValue = formatCharacteristicValue(data.value_hex);
        logMessage(`Value of ${charUuid.substring(0, 8)}...: ${formattedValue}`, 'success');

        const charsContainer = document.getElementById(`chars-${serviceUuid.replace(/[^a-z0-9]/gi, '')}`);
        if (charsContainer) {
            const charElement = charsContainer.querySelector(`[data-char-uuid="${charUuid}"]`);
            if (charElement) {
                const notificationValue = charElement.closest('.bg-gray-800')?.querySelector('.notification-value');
                if (notificationValue) {
                    notificationValue.textContent = formattedValue;
                }
            }
        }
    } catch (error) {
        console.error('Read error:', error);
        logMessage(`Failed to read characteristic: ${error.message}`, 'error');
    }
}

/**
 * Write characteristic value
 * @param {Object} state - Application state
 * @param {String} serviceUuid - Service UUID
 * @param {String} charUuid - Characteristic UUID
 */
export async function writeCharacteristic(state, serviceUuid, charUuid) {
    if (!state.connectedDevice) {
        logMessage('No device connected', 'warning');
        return;
    }

    try {
        logMessage(`Writing to characteristic ${charUuid}...`, 'info');
        const value = prompt(`Enter value to write to ${charUuid}:`, '1');
        if (value === null) {
            logMessage('Write cancelled', 'warning');
            return;
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const response = await fetch(`/api/ble/services/${serviceUuid}/characteristics/${charUuid}/write`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ value }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to write characteristic: ${errorText}`);
        }

        await response.json();
        logMessage(`Successfully wrote to characteristic ${charUuid}`, 'success');
    } catch (error) {
        console.error('Write error:', error);
        logMessage(`Failed to write characteristic: ${error.message}`, 'error');
    }
}

/**
 * Toggle characteristic notifications
 * @param {Object} state - Application state
 * @param {String} serviceUuid - Service UUID
 * @param {String} charUuid - Characteristic UUID
 */
export async function toggleNotification(state, serviceUuid, charUuid) {
    if (!state.connectedDevice) {
        logMessage('No device connected', 'warning');
        return;
    }

    const button = document.querySelector(`[data-char-uuid="${charUuid}"]`);
    if (!button) {
        logMessage(`Button for characteristic ${charUuid} not found`, 'warning');
        return;
    }

    try {
        const isSubscribed = button.dataset.subscribed === 'true';
        const subscribe = !isSubscribed;
        logMessage(`${subscribe ? 'Subscribing to' : 'Unsubscribing from'} notifications for ${charUuid}...`, 'info');

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const response = await fetch(`/api/ble/services/${serviceUuid}/characteristics/${charUuid}/notify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notify: subscribe }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to ${subscribe ? 'subscribe to' : 'unsubscribe from'} characteristic: ${errorText}`);
        }

        await response.json();
        if (subscribe) {
            state.subscribedCharacteristics.add(charUuid);
            logMessage(`Subscribed to notifications for ${charUuid}`, 'success');
        } else {
            state.subscribedCharacteristics.delete(charUuid);
            logMessage(`Unsubscribed from notifications for ${charUuid}`, 'success');
        }

        button.dataset.subscribed = subscribe.toString();
        button.innerHTML = subscribe ? '<i class="fas fa-bell-slash"></i>' : '<i class="fas fa-bell"></i>';
        button.title = subscribe ? 'Unsubscribe from notifications' : 'Subscribe to notifications';
    } catch (error) {
        console.error('Toggle notification error:', error);
        logMessage(`Failed to toggle notification: ${error.message}`, 'error');
    }
}

/**
 * Unsubscribe from a characteristic
 * @param {string} charUuid - Characteristic UUID
 * @param {Object} state - Application state
 */
export async function unsubscribeFromCharacteristic(charUuid, state) {
    try {
        logMessage(`Unsubscribing from characteristic ${charUuid}...`, 'info');
        state.subscribedCharacteristics.delete(charUuid);
        const { updateSubscriptionStatus } = await import('./ble-ui.js');
        updateSubscriptionStatus(charUuid, false);
        logMessage(`Unsubscribed from characteristic ${charUuid}`, 'success');
    } catch (error) {
        console.error('Unsubscribe error:', error);
        logMessage(`Failed to unsubscribe from characteristic: ${error.message}`, 'error');
    }
}

/**
 * Format characteristic values
 * @param {string} hexValue - Hexadecimal value
 * @returns {string} - Formatted value
 */
export function formatCharacteristicValue(hexValue) {
    if (!hexValue) return 'No value';

    try {
        const bytes = hexToBytes(hexValue);
        const ascii = bytesToAscii(bytes);
        if (/^[ -~]+$/.test(ascii)) {
            return `${ascii} (ASCII)`;
        }
        return `[${bytes.join(', ')}] (Decimal)`;
    } catch (e) {
        return hexValue;
    }
}

/**
 * Convert hex string to byte array
 * @param {string} hex - Hex string
 * @returns {number[]} - Byte array
 */
function hexToBytes(hex) {
    const bytes = [];
    for (let i = 0; i < hex.length; i += 2) {
        bytes.push(parseInt(hex.substr(i, 2), 16));
    }
    return bytes;
}

/**
 * Convert byte array to ASCII
 * @param {number[]} bytes - Byte array
 * @returns {string} - ASCII string
 */
function bytesToAscii(bytes) {
    return bytes.map(byte => String.fromCharCode(byte)).join('');
}

/**
 * Read characteristic value with retry
 * @param {Object} state - Application state
 * @param {String} serviceUuid - Service UUID
 * @param {String} charUuid - Characteristic UUID
 * @param {Number} maxRetries - Maximum number of retries
 */
export async function readCharacteristicWithRetry(state, serviceUuid, charUuid, maxRetries = 3) {
    let retryCount = 0;
    let lastError = null;
    
    while (retryCount < maxRetries) {
        try {
            const response = await fetch(`/api/ble/characteristics/${charUuid}/read?service=${serviceUuid}`, {
                // Existing fetch configuration
            });
            
            if (!response.ok) {
                throw new Error(`Failed to read characteristic: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            lastError = error;
            retryCount++;
            
            // Log the retry attempt
            logMessage(`Read attempt ${retryCount} failed: ${error.message}. ${retryCount < maxRetries ? 'Retrying...' : 'Giving up.'}`, 'warning');
            
            if (retryCount < maxRetries) {
                // Exponential backoff
                const delay = Math.min(2000, Math.pow(2, retryCount) * 100);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    
    // If we get here, all retries failed
    throw lastError;
}
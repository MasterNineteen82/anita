import { logMessage } from './ble-ui.js';
import { setupNotificationWebSocket } from './ble-notifications.js';

/**
/**
 * Get services for the connected device
 * @param {Object} state - Application state
 */
export async function getServices(state) {
    if (!state.connectedDevice) {
        logMessage('No device connected. Please connect to a device first.', 'warning');
        return;
    }

    const { servicesList } = state.domElements;
    if (!servicesList) {
        logMessage('Services list element not found in the DOM.', 'error');
        return;
    }

    try {
        logMessage('Fetching BLE services...', 'info');
        servicesList.innerHTML = `
            <div class="text-gray-500 animate-pulse">
                <i class="fas fa-spinner fa-spin mr-2"></i>Loading services...
            </div>
        `;

        // Abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        // Fetch services from the backend
        const response = await fetch(`/api/ble/services/${state.connectedDevice.address}`, {
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to fetch services: ${errorText}`);
        }

        const services = await response.json();
        servicesList.innerHTML = '';

        if (!services.length) {
            servicesList.innerHTML = `
                <div class="text-gray-500 text-center">
                    <i class="fas fa-info-circle mr-2"></i>No services found on this device.
                </div>
            `;
            logMessage('No services detected on the connected device.', 'warning');
            return;
        }

        logMessage(`Found ${services.length} services on the device.`, 'success');

        // Render each service
        services.forEach(service => {
            const serviceEl = document.createElement('div');
            serviceEl.className = 'bg-gray-700 p-3 rounded mb-2 hover:bg-gray-600 transition-colors';
            serviceEl.innerHTML = `
                <div class="font-medium text-white">${service.description || 'Unknown Service'}</div>
                <div class="text-xs text-gray-400">UUID: ${service.uuid}</div>
                <button class="get-chars-btn mt-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition-colors"
                        data-uuid="${service.uuid}">
                    Get Characteristics
                </button>
                <div class="chars-container mt-2 hidden" id="chars-${service.uuid.replace(/[^a-z0-9]/gi, '')}"></div>
            `;
            servicesList.appendChild(serviceEl);
        });

        // Add event listeners for "Get Characteristics" buttons
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
        servicesList.innerHTML = `
            <div class="text-red-500 text-center">
                <i class="fas fa-exclamation-circle mr-2"></i>Error: ${error.message}
            </div>
        `;
        logMessage(`Failed to fetch services: ${error.message}`, 'error');
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
export function hexToBytes(hex) {
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

/**
 * Subscribe to characteristic notifications
 * @param {Object} state - Application state
 * @param {String} serviceUuid - Service UUID
 * @param {String} charUuid - Characteristic UUID
 * @returns {Promise<boolean>} - Success status
 */
export async function subscribeToCharacteristic(state, serviceUuid, charUuid) {
    if (!state.connectedDevice) {
        logMessage('No device connected', 'warning');
        return false;
    }

    try {
        logMessage(`Subscribing to notifications for ${charUuid}...`, 'info');
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const response = await fetch(`/api/ble/services/${serviceUuid}/characteristics/${charUuid}/notify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notify: true }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to subscribe to characteristic: ${errorText}`);
        }

        await response.json();
        state.subscribedCharacteristics.add(charUuid);
        logMessage(`Subscribed to notifications for ${charUuid}`, 'success');
        
        const button = document.querySelector(`[data-char-uuid="${charUuid}"]`);
        if (button) {
            button.dataset.subscribed = 'true';
            button.innerHTML = '<i class="fas fa-bell-slash"></i>';
            button.title = 'Unsubscribe from notifications';
        }
        
        return true;
    } catch (error) {
        console.error('Subscribe error:', error);
        logMessage(`Failed to subscribe to characteristic: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Get detailed information about a service
 * @param {String} serviceUuid - Service UUID
 * @returns {Promise<Object>} - Service information
 */
export async function getServiceInfo(serviceUuid) {
    try {
        const response = await fetch(`/api/ble/services/${serviceUuid}/info`);
        if (!response.ok) {
            throw new Error(`Failed to fetch service info: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching service info:', error);
        throw error;
    }
}

/**
 * Get detailed information about a characteristic
 * @param {String} serviceUuid - Service UUID
 * @param {String} charUuid - Characteristic UUID
 * @returns {Promise<Object>} - Characteristic information
 */
export async function getCharacteristicInfo(serviceUuid, charUuid) {
    try {
        const response = await fetch(`/api/ble/services/${serviceUuid}/characteristics/${charUuid}/info`);
        if (!response.ok) {
            throw new Error(`Failed to fetch characteristic info: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching characteristic info:', error);
        throw error;
    }
}

/**
 * Get supported properties for a characteristic
 * @param {String} serviceUuid - Service UUID
 * @param {String} charUuid - Characteristic UUID
 * @returns {Promise<Object>} - Supported properties
 */
export async function getSupportedProperties(serviceUuid, charUuid) {
    try {
        const response = await fetch(`/api/ble/services/${serviceUuid}/characteristics/${charUuid}/properties`);
        if (!response.ok) {
            throw new Error(`Failed to fetch characteristic properties: ${response.status}`);
        }
        const data = await response.json();
        return {
            read: !!data.read,
            write: !!data.write,
            writeWithoutResponse: !!data.writeWithoutResponse,
            notify: !!data.notify,
            indicate: !!data.indicate,
            broadcast: !!data.broadcast,
            authenticatedSignedWrites: !!data.authenticatedSignedWrites,
            extendedProperties: !!data.extendedProperties
        };
    } catch (error) {
        console.error('Error fetching characteristic properties:', error);
        throw error;
    }
}

/**
 * Set up event listeners for service-related elements
 * @param {Object} state - Application state
 */
export function setupServiceListeners(state) {
    // Event delegation for service discovery, characteristic operations
    document.addEventListener('click', async (event) => {
        // Handle service discovery button clicks
        if (event.target.matches('#discover-services-btn')) {
            await getServices(state);
        }
        
        // Handle service expansion clicks (delegated event handling)
        if (event.target.closest('.service-item-header')) {
            const serviceItem = event.target.closest('.service-item');
            if (serviceItem) {
                const contentEl = serviceItem.querySelector('.service-item-content');
                if (contentEl) {
                    contentEl.classList.toggle('hidden');
                    
                    // If expanded and no characteristics loaded yet, fetch them
                    if (!contentEl.classList.contains('hidden') && contentEl.children.length === 0) {
                        const serviceUuid = serviceItem.dataset.uuid;
                        if (serviceUuid) {
                            await getCharacteristics(state, serviceUuid);
                        }
                    }
                }
            }
        }
    });
    
    // Setup WebSocket for notifications if available
    if (window.WebSocket) {
        setupNotificationWebSocket(state);
    }
}

/**
 * Handle characteristic change notifications
 * @param {Object} state - Application state 
 * @param {Object} data - Notification data
 */
export function handleCharacteristicChange(state, data) {
    const { charUuid, value } = data;
    if (!charUuid || !value) return;
    
    // Update UI with the new value
    const formattedValue = formatCharacteristicValue(value);
    logMessage(`Notification from ${charUuid.substring(0, 8)}...: ${formattedValue}`, 'info');
    
    // Find and update the correct characteristic UI element
    const charElement = document.querySelector(`[data-char-uuid="${charUuid}"]`);
    if (charElement) {
        const notificationValue = charElement.closest('.bg-gray-800')?.querySelector('.notification-value');
        if (notificationValue) {
            notificationValue.textContent = formattedValue;
        }
    }
    
    // Dispatch an event for other components that might be listening
    document.dispatchEvent(new CustomEvent('ble-characteristic-changed', { 
        detail: { charUuid, value, formattedValue } 
    }));
}

/**
 * Get a hierarchical representation of services, characteristics, and descriptors
 * @param {Object} state - Application state
 * @returns {Promise<Object>} - Service tree
 */
export async function getServiceTree(state) {
    if (!state.connectedDevice) {
        logMessage('No device connected', 'warning');
        return null;
    }
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000);
        const response = await fetch(`/api/ble/device/${state.connectedDevice.address}/tree`, {
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch service tree: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error fetching service tree:', error);
        logMessage(`Failed to fetch service tree: ${error.message}`, 'error');
        return null;
    }
}

/**
 * Get descriptors for a characteristic
 * @param {String} serviceUuid - Service UUID
 * @param {String} charUuid - Characteristic UUID
 * @returns {Promise<Array>} - Descriptors
 */
export async function getDescriptors(serviceUuid, charUuid) {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const response = await fetch(`/api/ble/services/${serviceUuid}/characteristics/${charUuid}/descriptors`, {
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch descriptors: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error fetching descriptors:', error);
        throw error;
    }
}

/**
 * Read a descriptor value
 * @param {String} serviceUuid - Service UUID
 * @param {String} charUuid - Characteristic UUID
 * @param {String} descriptorUuid - Descriptor UUID
 * @returns {Promise<Object>} - Descriptor value
 */
export async function readDescriptor(serviceUuid, charUuid, descriptorUuid) {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const response = await fetch(
            `/api/ble/services/${serviceUuid}/characteristics/${charUuid}/descriptors/${descriptorUuid}/read`,
            { signal: controller.signal }
        );
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`Failed to read descriptor: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error reading descriptor:', error);
        throw error;
    }
}

/**
 * Write a value to a descriptor
 * @param {String} serviceUuid - Service UUID
 * @param {String} charUuid - Characteristic UUID
 * @param {String} descriptorUuid - Descriptor UUID
 * @param {String|Object} value - Value to write
 * @returns {Promise<Object>} - Result
 */
export async function writeDescriptor(serviceUuid, charUuid, descriptorUuid, value) {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const response = await fetch(
            `/api/ble/services/${serviceUuid}/characteristics/${charUuid}/descriptors/${descriptorUuid}/write`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value }),
                signal: controller.signal
            }
        );
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`Failed to write descriptor: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error writing descriptor:', error);
        throw error;
    }
}

/**
 * Parse characteristic value into appropriate data type
 * @param {String} value - Raw value (hex)
 * @param {String} dataType - Data type (uint8, uint16, string, etc.)
 * @returns {*} - Parsed value
 */
export function parseCharacteristicValue(value, dataType = 'auto') {
    if (!value) return null;
    
    const bytes = hexToBytes(value);
    
    switch(dataType) {
        case 'uint8':
            return bytes[0];
        case 'int8':
            return new Int8Array([bytes[0]])[0];
        case 'uint16':
            return new Uint16Array(new Uint8Array(bytes.slice(0, 2)).buffer)[0];
        case 'int16':
            return new Int16Array(new Uint8Array(bytes.slice(0, 2)).buffer)[0];
        case 'uint32':
            return new Uint32Array(new Uint8Array(bytes.slice(0, 4)).buffer)[0];
        case 'int32':
            return new Int32Array(new Uint8Array(bytes.slice(0, 4)).buffer)[0];
        case 'float':
            return new Float32Array(new Uint8Array(bytes.slice(0, 4)).buffer)[0];
        case 'string':
            return bytesToAscii(bytes);
        case 'hex':
            return value;
        case 'auto':
        default:
            // Try to determine the most likely data type
            if (/^[0-9A-F]+$/i.test(value) && value.length <= 2) {
                return bytes[0]; // Likely a uint8
            } else if (bytes.every(b => b >= 32 && b <= 126)) {
                return bytesToAscii(bytes); // Likely ASCII
            } else {
                return bytes; // Return as byte array
            }
    }
}

/**
 * Format value for writing to characteristic
 * @param {*} value - Input value
 * @param {String} dataType - Data type (uint8, uint16, string, etc.)
 * @returns {String} - Formatted value (hex)
 */
export function formatValueForWrite(value, dataType = 'auto') {
    if (value === null || value === undefined) return '';
    
    switch(dataType) {
        case 'uint8':
        case 'int8':
            const num = parseInt(value, 10);
            return num.toString(16).padStart(2, '0');
        case 'uint16':
        case 'int16':
            const view16 = new DataView(new ArrayBuffer(2));
            view16.setUint16(0, parseInt(value, 10), true);
            return Array.from(new Uint8Array(view16.buffer))
                .map(b => b.toString(16).padStart(2, '0'))
                .join('');
        case 'uint32':
        case 'int32':
        case 'float':
            const view32 = new DataView(new ArrayBuffer(4));
            if (dataType === 'float') {
                view32.setFloat32(0, parseFloat(value), true);
            } else {
                view32.setUint32(0, parseInt(value, 10), true);
            }
            return Array.from(new Uint8Array(view32.buffer))
                .map(b => b.toString(16).padStart(2, '0'))
                .join('');
        case 'string':
            return Array.from(new TextEncoder().encode(value))
                .map(b => b.toString(16).padStart(2, '0'))
                .join('');
        case 'hex':
            return value.replace(/[^0-9A-F]/gi, '');
        case 'auto':
        default:
            // Try to guess the format
            if (typeof value === 'number') {
                if (value <= 255 && value >= 0) {
                    return value.toString(16).padStart(2, '0');
                } else {
                    const view = new DataView(new ArrayBuffer(4));
                    view.setUint32(0, value, true);
                    return Array.from(new Uint8Array(view.buffer))
                        .map(b => b.toString(16).padStart(2, '0'))
                        .join('');
                }
            } else if (typeof value === 'string') {
                // Check if it's already a hex string
                if (/^[0-9A-F]+$/i.test(value)) {
                    return value;
                } else {
                    return Array.from(new TextEncoder().encode(value))
                        .map(b => b.toString(16).padStart(2, '0'))
                        .join('');
                }
            } else {
                return '';
            }
    }
}

/**
 * Get a list of known BLE service names/descriptions
 * @returns {Promise<Object>} - Map of UUID to service names
 */
export async function getServiceNames() {
    try {
        const response = await fetch('/api/ble/services/known');
        if (!response.ok) {
            throw new Error(`Failed to fetch service names: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching service names:', error);
        return {}; // Return empty object on error
    }
}

/**
 * Continuously monitor a characteristic by periodic reads
 * @param {Object} state - Application state
 * @param {String} serviceUuid - Service UUID
 * @param {String} charUuid - Characteristic UUID
 * @param {Number} interval - Polling interval in ms
 * @returns {Object} - Monitor controller
 */
export function monitorCharacteristic(state, serviceUuid, charUuid, interval = 1000) {
    const monitorId = `${serviceUuid}:${charUuid}`;
    
    // Clear any existing monitor
    if (state.monitorTimers && state.monitorTimers[monitorId]) {
        clearInterval(state.monitorTimers[monitorId]);
    }
    
    if (!state.monitorTimers) {
        state.monitorTimers = {};
    }
    
    logMessage(`Starting monitor for ${charUuid} (every ${interval}ms)`, 'info');
    
    // Start the polling
    state.monitorTimers[monitorId] = setInterval(async () => {
        if (!state.connectedDevice) {
            clearInterval(state.monitorTimers[monitorId]);
            delete state.monitorTimers[monitorId];
            logMessage(`Monitor for ${charUuid} stopped: device disconnected`, 'warning');
            return;
        }
        
        try {
            await readCharacteristic(state, serviceUuid, charUuid);
        } catch (error) {
            console.error(`Monitor read error for ${charUuid}:`, error);
        }
    }, interval);
    
    return {
        stop: () => {
            if (state.monitorTimers[monitorId]) {
                clearInterval(state.monitorTimers[monitorId]);
                delete state.monitorTimers[monitorId];
                logMessage(`Monitor for ${charUuid} stopped`, 'info');
            }
        },
        isActive: () => !!state.monitorTimers[monitorId]
    };
}
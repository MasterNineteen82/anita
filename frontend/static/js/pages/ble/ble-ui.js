/**
 * Initialize the BLE UI components
 * @param {Object} state - Application state
 */
export async function initializeUI(state) {
    const { scanBtn, disconnectBtn } = state.domElements;

    if (scanBtn) {
        scanBtn.addEventListener('click', async () => {
            try {
                const { scanDevicesWithErrorHandling } = await import('./ble-scanning.js');
                scanDevicesWithErrorHandling(state);
            } catch (err) {
                logMessage(`Failed to load scanning module: ${err.message}`, 'error');
            }
        });
    }

    if (disconnectBtn) {
        disconnectBtn.addEventListener('click', async () => {
            try {
                const { disconnectFromDevice } = await import('./ble-connection.js');
                disconnectFromDevice(state);
            } catch (err) {
                logMessage(`Failed to load disconnection module: ${err.message}`, 'error');
            }
        });
    }

    console.log("BLE UI components initialized");
}

/**
 * Update the connection status indicator
 * @param {Object} state - Application state
 * @param {String} status - Status type
 * @param {String} message - Status message to display
 */
export function updateStatus(state, status, message) {
    const { statusIndicatorContainer } = state.domElements;
    if (!statusIndicatorContainer) return;

    const statusStyles = {
        connected: { icon: 'fa-check-circle', color: 'text-green-500', bg: 'bg-green-900' },
        connecting: { icon: 'fa-spinner fa-spin', color: 'text-blue-500', bg: 'bg-blue-900' },
        disconnecting: { icon: 'fa-spinner fa-spin', color: 'text-yellow-500', bg: 'bg-yellow-900' },
        error: { icon: 'fa-exclamation-circle', color: 'text-red-500', bg: 'bg-red-900' },
        disconnected: { icon: 'fa-times-circle', color: 'text-gray-500', bg: 'bg-gray-900' }
    };

    const { icon, color, bg } = statusStyles[status] || statusStyles.disconnected;
    statusIndicatorContainer.innerHTML = `
        <div class="flex items-center p-3 rounded ${bg} border border-gray-700">
            <i class="fas ${icon} ${color} mr-2"></i>
            <span class="text-white">${message}</span>
        </div>
    `;
}

/**
 * Update the scan status indicator
 * @param {Object} state - Application state
 * @param {String} status - Status type
 * @param {String} message - Status message
 */
export function updateScanStatus(state, status, message) {
    const { scanStatus } = state.domElements;
    if (!scanStatus) return;

    const statusStyles = {
        scanning: 'bg-blue-500',
        complete: 'bg-green-500',
        idle: 'bg-gray-500',
        error: 'bg-red-500'
    };

    scanStatus.innerHTML = `
        <span class="w-3 h-3 rounded-full ${statusStyles[status] || statusStyles.idle} mr-2"></span>
        <span class="text-gray-400">${message}</span>
    `;
}

/**
 * Log a message to the BLE operations log
 * @param {String} message - Message to log
 * @param {String} type - Log type
 */
export function logMessage(message, type = 'info') {
    const logContainer = document.getElementById('ble-log-container');
    if (!logContainer) return;

    const timestamp = new Date().toLocaleTimeString();
    const typeStyles = {
        success: { color: 'text-green-400', prefix: '[Success]' },
        warning: { color: 'text-yellow-400', prefix: '[Warning]' },
        error: { color: 'text-red-400', prefix: '[Error]' },
        debug: { color: 'text-purple-400', prefix: '[Debug]' },
        info: { color: 'text-blue-400', prefix: '[Info]' }
    };

    const { color, prefix } = typeStyles[type] || typeStyles.info;
    const logEntry = document.createElement('div');
    logEntry.className = color;
    logEntry.innerHTML = `${timestamp} ${prefix} ${message}`;
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

/**
 * Show/hide the loading indicator
 * @param {Object} state - Application state
 * @param {Boolean} show - Whether to show or hide
 * @param {String} message - Loading message
 */
export function setLoading(state, show, message = 'Loading...') {
    const { loadingIndicator } = state.domElements;
    if (!loadingIndicator) return;

    if (show) {
        loadingIndicator.querySelector('span').textContent = message;
        loadingIndicator.classList.remove('hidden');
    } else {
        loadingIndicator.classList.add('hidden');
    }
}

/**
 * Update subscription status in UI
 * @param {string} charUuid - Characteristic UUID
 * @param {boolean} isSubscribed - Subscription status
 */
export function updateSubscriptionStatus(charUuid, isSubscribed) {
    const button = document.querySelector(`[data-char-uuid="${charUuid}"]`);
    if (button) {
        button.dataset.subscribed = isSubscribed.toString();
        button.innerHTML = isSubscribed ? '<i class="fas fa-bell-slash"></i>' : '<i class="fas fa-bell"></i>';
        button.title = isSubscribed ? 'Unsubscribe from notifications' : 'Subscribe to notifications';
    }
}
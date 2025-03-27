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
 * Update the BLE connection status indicator
 * @param {Object} state - Application state
 * @param {String} status - Status (disconnected, connecting, connected, error)
 * @param {String} message - Optional status message
 */
export function updateStatus(state, status, message = null) {
    const statusContainer = document.getElementById('status-indicator-container');
    if (!statusContainer) return;
    
    // Status configurations
    const statusConfigs = {
        disconnected: {
            icon: 'fa-unlink',
            bg: 'bg-gray-700',
            text: 'text-gray-300',
            dot: 'bg-gray-500',
            defaultMessage: 'Not connected to any device'
        },
        connecting: {
            icon: 'fa-spinner fa-spin',
            bg: 'bg-blue-700',
            text: 'text-white',
            dot: 'bg-blue-400',
            defaultMessage: 'Connecting...'
        },
        connected: {
            icon: 'fa-link',
            bg: 'bg-green-700',
            text: 'text-white',
            dot: 'bg-green-400',
            defaultMessage: 'Connected'
        },
        error: {
            icon: 'fa-exclamation-triangle',
            bg: 'bg-red-700',
            text: 'text-white',
            dot: 'bg-red-400',
            defaultMessage: 'Connection error'
        },
        scanning: {
            icon: 'fa-search fa-pulse',
            bg: 'bg-blue-700',
            text: 'text-white',
            dot: 'bg-blue-400',
            defaultMessage: 'Scanning...'
        }
    };
    
    // Get config for current status
    const config = statusConfigs[status] || statusConfigs.disconnected;
    
    // Update state
    if (state) {
        state.connectionStatus = status;
    }
    
    // Create alert HTML
    statusContainer.innerHTML = `
        <div class="rounded-md ${config.bg} p-3 mb-4">
            <div class="flex items-center">
                <div class="flex-shrink-0">
                    <i class="fas ${config.icon} ${config.text}"></i>
                </div>
                <div class="ml-3">
                    <div class="flex items-center">
                        <p class="text-sm font-medium ${config.text}">
                            <span class="inline-block w-2 h-2 rounded-full ${config.dot} mr-2"></span>
                            ${message || config.defaultMessage}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Update the scan status indicator
 * @param {Object} state - Application state
 * @param {String} status - Status (inactive, scanning, complete, error)
 * @param {String} message - Status message
 */
export function updateScanStatus(state, status, message) {
    const scanStatus = document.getElementById('scan-status');
    if (!scanStatus) return;
    
    // Status configurations
    const statusConfigs = {
        inactive: {
            dot: 'bg-gray-500',
            text: 'text-gray-400',
            defaultMessage: 'Inactive'
        },
        scanning: {
            dot: 'bg-blue-500 animate-pulse',
            text: 'text-blue-400',
            defaultMessage: 'Scanning...'
        },
        complete: {
            dot: 'bg-green-500',
            text: 'text-green-400',
            defaultMessage: 'Scan complete'
        },
        error: {
            dot: 'bg-red-500',
            text: 'text-red-400',
            defaultMessage: 'Scan error'
        }
    };
    
    // Get config for current status
    const config = statusConfigs[status] || statusConfigs.inactive;
    
    // Update the status element
    scanStatus.innerHTML = `
        <span class="w-3 h-3 rounded-full ${config.dot} mr-2"></span>
        <span class="${config.text}">${message || config.defaultMessage}</span>
    `;
    
    // Update state
    if (state) {
        state.scanStatus = status;
    }
}

/**
 * Log a message to the BLE operations log
 * @param {String} message - Message to log
 * @param {String} level - Log level (info, success, warning, error)
 */
export function logMessage(message, level = 'info') {
    const logContainer = document.getElementById('ble-log-container');
    if (!logContainer) return;
    
    // Get timestamp
    const now = new Date();
    const timestamp = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    
    // Create log entry
    const logEntry = document.createElement('div');
    
    // Define colors for different log levels
    const colors = {
        info: 'text-blue-400',
        success: 'text-green-400',
        warning: 'text-yellow-400',
        error: 'text-red-400'
    };
    
    // Set class and icon based on level
    const icons = {
        info: 'fa-info-circle',
        success: 'fa-check-circle',
        warning: 'fa-exclamation-triangle',
        error: 'fa-times-circle'
    };
    
    logEntry.className = `text-sm ${colors[level] || 'text-gray-400'}`;
    logEntry.innerHTML = `
        <span class="text-gray-500">[${timestamp}]</span>
        <i class="fas ${icons[level] || 'fa-info-circle'} mr-1"></i>
        ${message}
    `;
    
    // Add to log container
    logContainer.appendChild(logEntry);
    
    // Scroll to bottom
    logContainer.scrollTop = logContainer.scrollHeight;
    
    // Limit log entries (keep last 100)
    const entries = logContainer.children;
    if (entries.length > 100) {
        logContainer.removeChild(entries[0]);
    }
    
    // Also log to console for debugging
    if (level === 'error') {
        console.error(`BLE: ${message}`);
    } else if (level === 'warning') {
        console.warn(`BLE: ${message}`);
    } else {
        console.log(`BLE: ${message}`);
    }
}

/**
 * Show or hide the loading indicator
 * @param {Object} state - Application state
 * @param {Boolean} loading - Whether to show loading
 * @param {String} message - Optional loading message
 */
export function setLoading(state, loading, message = 'Loading...') {
    const loadingIndicator = document.getElementById('loading-indicator');
    if (!loadingIndicator) return;
    
    if (loading) {
        // Update message
        const messageElement = loadingIndicator.querySelector('span');
        if (messageElement) {
            messageElement.textContent = message;
        }
        
        // Show loading indicator
        loadingIndicator.classList.remove('hidden');
    } else {
        // Hide loading indicator
        loadingIndicator.classList.add('hidden');
    }
    
    // Update state
    if (state) {
        state.isLoading = loading;
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

export function enableDebugMode() {
    window.BLE_DEBUG = true;
    
    // Add debug information to page
    const debugInfo = document.createElement('div');
    debugInfo.className = 'fixed bottom-0 right-0 bg-gray-800 text-white p-2 text-xs z-50';
    debugInfo.id = 'ble-debug-info';
    debugInfo.innerHTML = `
        <div>Debug Mode Enabled</div>
        <div id="ble-debug-status">Status: Initialized</div>
        <div>
            <button id="check-imports-btn" class="bg-blue-600 hover:bg-blue-700 px-2 py-1 rounded text-xs">
                Check Imports
            </button>
            <button id="check-events-btn" class="bg-green-600 hover:bg-green-700 px-2 py-1 rounded text-xs ml-1">
                Check Events
            </button>
        </div>
    `;
    
    document.body.appendChild(debugInfo);
    
    // Add event listeners for debug buttons
    document.getElementById('check-imports-btn').addEventListener('click', () => {
        try {
            // Import BLE_EVENTS dynamically
            import('./ble-events.js').then(module => {
                console.log('BLE_EVENTS:', module.BLE_EVENTS);
                console.log('bleEventEmitter:', window.bleEvents);
                document.getElementById('ble-debug-status').textContent = 'Status: Imports OK';
            }).catch(err => {
                console.error('Import check failed:', err);
                document.getElementById('ble-debug-status').textContent = `Status: Import Error: ${err.message}`;
            });
        } catch (err) {
            console.error('Import check failed:', err);
            document.getElementById('ble-debug-status').textContent = `Status: Import Error: ${err.message}`;
        }
    });
    
    document.getElementById('check-events-btn').addEventListener('click', () => {
        try {
            const testEvent = 'ble.test.event';
            let received = false;
            
            // Register test listener
            window.bleEvents.on(testEvent, () => {
                received = true;
                document.getElementById('ble-debug-status').textContent = 'Status: Event System Working';
            });
            
            // Emit test event
            window.bleEvents.emit(testEvent, {test: true});
            
            if (!received) {
                document.getElementById('ble-debug-status').textContent = 'Status: Event Not Received';
            }
        } catch (err) {
            console.error('Event check failed:', err);
            document.getElementById('ble-debug-status').textContent = `Status: Event Error: ${err.message}`;
        }
    });
    
    console.log('Debug mode enabled');
}
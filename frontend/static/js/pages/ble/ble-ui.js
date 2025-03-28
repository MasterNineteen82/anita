import { BleEvents } from './ble-events.js';

/**
 * BLE UI Module - Handles all UI-related functionality for BLE operations
 */

// Create BleUI as a module with exported functions
export const BleUI = {
    /**
     * Initialize the UI components
     */
    initializeUI() {
        // Initialize message area
        const appContainer = document.getElementById('ble-app');
        if (appContainer && !document.getElementById('ble-messages')) {
            const messagesDiv = document.createElement('div');
            messagesDiv.id = 'ble-messages';
            messagesDiv.className = 'ble-messages';
            appContainer.appendChild(messagesDiv);
        }
        
        // Set initial states
        this.updateScanStatus(false, 'Ready');
        this.updateConnectionStatus(false);
        
        // Log initialization
        this.logMessage("BLE UI initialized", 'info');
    },
    
    /**
     * Update the scan status in the UI
     * @param {boolean} isScanning - Whether scanning is in progress
     * @param {string} message - Status message
     */
    updateScanStatus(isScanning, message) {
        const statusElement = document.getElementById('ble-scan-status');
        if (statusElement) {
            statusElement.textContent = message || (isScanning ? 'Scanning...' : 'Idle');
            statusElement.className = isScanning ? 'status-scanning' : 'status-idle';
        }
        
        // Update scan button states
        const scanButton = document.getElementById('ble-scan-button');
        const stopButton = document.getElementById('ble-stop-scan');
        
        if (scanButton) scanButton.disabled = isScanning;
        if (stopButton) stopButton.disabled = !isScanning;
    },
    
    /**
     * Show a message in the UI
     * @param {string} message - Message text
     * @param {string} type - Message type (info, success, warning, error)
     */
    showMessage(message, type = 'info') {
        console.log(`BLE: ${message}`);
        const messageElement = document.getElementById('ble-messages');
        if (messageElement) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `ble-message message-${type}`;
            msgDiv.textContent = message;
            messageElement.appendChild(msgDiv);
            
            // Auto-remove after delay
            setTimeout(() => {
                if (msgDiv.parentNode === messageElement) {
                    messageElement.removeChild(msgDiv);
                }
            }, 5000);
        }
        
        // Also log to the log container
        this.logMessage(message, type);
    },
    
    /**
     * Show an error message
     * @param {string} message - Error message
     */
    showError(message) {
        this.showMessage(message, 'error');
    },
    
    /**
     * Update the device list in the UI
     * @param {Array} devices - List of BLE devices 
     */
    updateDeviceList(devices) {
        const deviceList = document.getElementById('ble-device-list');
        if (!deviceList) return;
        
        // Clear current list
        deviceList.innerHTML = '';
        
        if (!devices || devices.length === 0) {
            deviceList.innerHTML = '<div class="ble-no-devices">No devices found</div>';
            return;
        }
        
        // Sort devices by RSSI (strongest signal first)
        const sortedDevices = [...devices].sort((a, b) => (b.rssi || -100) - (a.rssi || -100));
        
        // Create device elements
        sortedDevices.forEach(device => {
            const deviceEl = document.createElement('div');
            deviceEl.className = 'ble-device';
            deviceEl.dataset.bleDevice = device.address;
            
            // Calculate signal strength icon
            const rssi = device.rssi || -100;
            let signalStrength = 'low';
            if (rssi > -70) {
                signalStrength = 'high';
            } else if (rssi > -85) {
                signalStrength = 'medium';
            }
            
            // Create device content with more detailed information
            deviceEl.innerHTML = `
                <div class="ble-device-header">
                    <div class="ble-device-name">${device.name || 'Unknown Device'}</div>
                    <div class="ble-device-signal signal-${signalStrength}" title="Signal: ${rssi} dBm">
                        <i class="fas fa-signal"></i>
                    </div>
                </div>
                <div class="ble-device-address">${device.address}</div>
                <div class="ble-device-details">
                    <div class="ble-device-rssi">RSSI: ${rssi} dBm</div>
                    ${device.services && device.services.length ? 
                      `<div class="ble-device-services">Services: ${device.services.length}</div>` : ''}
                </div>
                <div class="ble-device-actions">
                    <button class="ble-device-connect" data-ble-connect="${device.address}">Connect</button>
                    <button class="ble-device-details-btn" data-ble-details="${device.address}">Details</button>
                </div>
            `;
            
            deviceList.appendChild(deviceEl);
        });
    },
    
    /**
     * Update connection status in the UI
     * @param {boolean} isConnected - Whether a device is connected
     * @param {Object} deviceInfo - Connected device info
     */
    updateConnectionStatus(isConnected, deviceInfo = null) {
        const statusEl = document.getElementById('ble-connection-status');
        if (statusEl) {
            statusEl.className = isConnected ? 'status-connected' : 'status-disconnected';
            statusEl.textContent = isConnected ? 
                `Connected to ${deviceInfo?.name || deviceInfo?.address || 'device'}` : 
                'Disconnected';
        }
        
        // Update UI elements that depend on connection state
        document.querySelectorAll('[data-requires-connection]').forEach(el => {
            el.disabled = !isConnected;
        });
        
        // Toggle visibility of connection-dependent elements
        document.querySelectorAll('[data-show-when-connected]').forEach(el => {
            el.style.display = isConnected ? '' : 'none';
        });
        
        document.querySelectorAll('[data-show-when-disconnected]').forEach(el => {
            el.style.display = isConnected ? 'none' : '';
        });
    },
    
    /**
     * Update adapter status in the UI
     * @param {Object} adapterInfo - Adapter information
     */
    updateAdapterStatus(adapterInfo) {
        const statusEl = document.getElementById('ble-adapter-status');
        if (statusEl) {
            statusEl.className = adapterInfo.available ? 'status-available' : 'status-unavailable';
            statusEl.textContent = adapterInfo.available ? 
                `Adapter: ${adapterInfo.name}` : 
                'Bluetooth not available';
        }
        
        // Update adapter information display if it exists
        const infoEl = document.getElementById('ble-adapter-info');
        if (infoEl && adapterInfo.available) {
            infoEl.innerHTML = `
                <div><strong>Name:</strong> ${adapterInfo.name}</div>
                <div><strong>Address:</strong> ${adapterInfo.address}</div>
                <div><strong>Platform:</strong> ${adapterInfo.platform}</div>
                <div><strong>API:</strong> ${adapterInfo.api_version}</div>
            `;
        }
        
        // Also update detailed adapter info if available
        this.updateAdapterInfo(adapterInfo);
    },
    
    /**
     * Log a message to the BLE operations log
     * @param {String} message - Message to log
     * @param {String} level - Log level (info, success, warning, error)
     */
    logMessage(message, level = 'info') {
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
    },
    
    /**
     * Set loading state and show/hide loading indicator
     * @param {Boolean} loading - Whether to show loading
     * @param {String} message - Optional loading message
     */
    setLoading(loading, message = 'Loading...') {
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
    },
    
    /**
     * Update subscription status for a characteristic
     * @param {string} charUuid - Characteristic UUID
     * @param {boolean} isSubscribed - Subscription status
     */
    updateSubscriptionStatus(charUuid, isSubscribed) {
        const button = document.querySelector(`[data-char-uuid="${charUuid}"]`);
        if (button) {
            button.dataset.subscribed = isSubscribed.toString();
            button.innerHTML = isSubscribed ? '<i class="fas fa-bell-slash"></i>' : '<i class="fas fa-bell"></i>';
            button.title = isSubscribed ? 'Unsubscribe from notifications' : 'Subscribe to notifications';
        }
    },
    
    /**
     * Enable debug mode with additional UI controls
     */
    enableDebugMode() {
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
                // Import dynamically
                import('./ble-events.js').then(module => {
                    const debugStatus = document.getElementById('ble-debug-status');
                    debugStatus.textContent = 'Status: Imports OK';
                    console.log('BleEvents imported:', module.BleEvents);
                }).catch(err => {
                    console.error('Import check failed:', err);
                    const debugStatus = document.getElementById('ble-debug-status');
                    debugStatus.textContent = `Status: Import Error: ${err.message}`;
                });
            } catch (err) {
                console.error('Import check failed:', err);
                const debugStatus = document.getElementById('ble-debug-status');
                debugStatus.textContent = `Status: Import Error: ${err.message}`;
            }
        });
        
        document.getElementById('check-events-btn').addEventListener('click', () => {
            try {
                const testEvent = 'ble.test.event';
                let received = false;
                
                // Register test listener using BleEvents
                const unsubscribe = BleEvents.on(testEvent, () => {
                    received = true;
                    const debugStatus = document.getElementById('ble-debug-status');
                    debugStatus.textContent = 'Status: Event System Working';
                });
                
                // Emit test event
                BleEvents.emit(testEvent, {test: true});
                
                if (!received) {
                    const debugStatus = document.getElementById('ble-debug-status');
                    debugStatus.textContent = 'Status: Event Not Received';
                }
                
                // Clean up the test listener
                unsubscribe();
            } catch (err) {
                console.error('Event check failed:', err);
                const debugStatus = document.getElementById('ble-debug-status');
                debugStatus.textContent = `Status: Event Error: ${err.message}`;
            }
        });
        
        console.log('Debug mode enabled');
    },
    
    /**
     * Update adapter information in the UI
     * @param {Object} info - Adapter information object
     */
    updateAdapterInfo(info) {
        const adapterInfoContainer = document.getElementById('adapter-info');
        if (!adapterInfoContainer) {
            return;
        }

        adapterInfoContainer.innerHTML = `
            <div class="mb-2">
                <div class="text-sm font-medium text-gray-400">Adapter Name</div>
                <div class="font-semibold">${info.name || 'Unknown'}</div>
            </div>
            <div class="mb-2">
                <div class="text-sm font-medium text-gray-400">Address</div>
                <div class="font-mono text-sm">${info.address || 'Unknown'}</div>
            </div>
            ${info.vendor ? `
            <div class="mb-2">
                <div class="text-sm font-medium text-gray-400">Vendor</div>
                <div>${info.vendor}</div>
            </div>` : ''}
            ${info.model ? `
            <div class="mb-2">
                <div class="text-sm font-medium text-gray-400">Model</div>
                <div>${info.model}</div>
            </div>` : ''}
        `;
    },
    
    /**
     * Create a UI element with the given properties
     * @param {String} type - Element type (div, button, etc)
     * @param {Object} attributes - Element attributes
     * @param {String} innerHTML - Element inner HTML content
     * @param {Object} eventListeners - Event listeners to attach
     * @returns {HTMLElement} Created element
     */
    createUIElement(type, attributes = {}, innerHTML = '', eventListeners = {}) {
        const element = document.createElement(type);
        
        // Set attributes
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'dataset') {
                Object.entries(value).forEach(([dataKey, dataValue]) => {
                    element.dataset[dataKey] = dataValue;
                });
            } else {
                element.setAttribute(key, value);
            }
        });
        
        // Set inner HTML
        if (innerHTML) {
            element.innerHTML = innerHTML;
        }
        
        // Add event listeners
        Object.entries(eventListeners).forEach(([event, callback]) => {
            element.addEventListener(event, callback);
        });
        
        return element;
    },
    
    /**
     * Show a notification toast
     * @param {String} message - Notification message
     * @param {String} type - Notification type (success, error, warning, info)
     * @param {Number} duration - Duration in ms
     */
    showNotification(message, type = 'info', duration = 3000) {
        const types = {
            success: { bg: 'bg-green-500', icon: 'fa-check-circle' },
            error: { bg: 'bg-red-500', icon: 'fa-exclamation-circle' },
            warning: { bg: 'bg-yellow-500', icon: 'fa-exclamation-triangle' },
            info: { bg: 'bg-blue-500', icon: 'fa-info-circle' }
        };
        
        const config = types[type] || types.info;
        
        // Create notification container if it doesn't exist
        let notifContainer = document.getElementById('notification-container');
        if (!notifContainer) {
            notifContainer = document.createElement('div');
            notifContainer.id = 'notification-container';
            notifContainer.className = 'fixed top-4 right-4 z-50 flex flex-col items-end space-y-2';
            document.body.appendChild(notifContainer);
        }
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `${config.bg} text-white py-2 px-4 rounded-md shadow-lg transform transition-transform duration-300 flex items-center`;
        notification.innerHTML = `
            <i class="fas ${config.icon} mr-2"></i>
            ${message}
        `;
        
        // Add to container
        notifContainer.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 10);
        
        // Remove after duration
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (notification.parentNode === notifContainer) {
                    notifContainer.removeChild(notification);
                }
            }, 300); // Wait for transition to complete
        }, duration);
    },
    
    /**
     * Update the BLE connection status with detailed information
     * @param {Object} state - Application state
     * @param {String} status - Status (disconnected, connecting, connected, error)
     * @param {String} message - Optional status message
     */
    updateStatus(state, status, message = null) {
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
};

// Export individual functions to maintain compatibility with existing code
export const {
    updateScanStatus,
    showMessage,
    showError,
    updateDeviceList,
    updateConnectionStatus,
    updateAdapterStatus,
    logMessage,
    setLoading,
    updateSubscriptionStatus,
    enableDebugMode,
    updateAdapterInfo,
    createUIElement,
    showNotification,
    updateStatus,
    initializeUI
} = BleUI;
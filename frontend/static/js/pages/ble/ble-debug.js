import { logMessage } from './ble-ui.js';

/**
 * Initialize the debug panel and its functionality
 * @param {Object} state - Application state
 */
export function initializeDebugPanel(state) {
    const {
        showDebugBtn,
        debugPanel,
        debugToggleBtn,
        debugSendBtn,
        debugEndpointSelect,
        debugResponseContainer
    } = state.domElements;

    if (!debugPanel) {
        console.warn('Debug panel not found in DOM');
        return;
    }

    if (showDebugBtn) {
        showDebugBtn.addEventListener('click', () => toggleDebugPanel(state));
    } else {
        console.warn('showDebugBtn not found; debug panel toggle unavailable');
    }

    if (debugToggleBtn) {
        debugToggleBtn.addEventListener('click', () => toggleDebugPanel(state));
    }

    if (debugSendBtn) {
        debugSendBtn.addEventListener('click', () => sendDebugRequest(state));
    }

    populateDebugEndpoints(state);
    logMessage('Debug panel initialized', 'debug');
}

/**
 * Toggle the visibility of the debug panel
 * @param {Object} state - Application state
 */
export function toggleDebugPanel(state) {
    const { debugPanel } = state.domElements;

    if (!debugPanel) {
        console.warn('Debug panel element missing');
        return;
    }

    debugPanel.classList.toggle('hidden');
    if (!debugPanel.classList.contains('hidden')) {
        logMessage('Debug panel opened', 'debug');
    }
}

/**
 * Send a request to the selected debug endpoint
 * @param {Object} state - Application state
 */
export async function sendDebugRequest(state) {
    const { debugEndpointSelect, debugResponseContainer } = state.domElements;

    if (!debugEndpointSelect || !debugResponseContainer) {
        logMessage('Debug components not found', 'error');
        return;
    }

    const endpoint = debugEndpointSelect.value;
    if (!endpoint) {
        debugResponseContainer.textContent = 'Please select an endpoint';
        return;
    }

    try {
        logMessage(`Sending debug request to ${endpoint}`, 'debug');
        debugResponseContainer.textContent = 'Loading...';

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

        const response = await fetch(endpoint, { signal: controller.signal });
        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        debugResponseContainer.textContent = JSON.stringify(data, null, 2);
        logMessage('Debug request completed', 'debug');
    } catch (error) {
        console.error('Debug request error:', error);
        debugResponseContainer.textContent = `Error: ${error.message}`;
        logMessage(`Debug request failed: ${error.message}`, 'error');
    }
}

/**
 * Populate the debug endpoint selector with available endpoints
 * @param {Object} state - Application state
 */
export function populateDebugEndpoints(state) {
    const { debugEndpointSelect } = state.domElements;

    if (!debugEndpointSelect) {
        console.warn('Debug endpoint selector not found');
        return;
    }

    const endpoints = [
        { value: '/api/ble/debug/info', label: 'BLE Debug Info' },
        { value: '/api/ble/debug/status', label: 'BLE Connection Status' },
        { value: '/api/system/status', label: 'System Status' },
        { value: '/api/ble/scan?scan_time=1', label: 'Quick BLE Scan (1s)' }
    ];

    debugEndpointSelect.innerHTML = '';
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Select debug endpoint...';
    debugEndpointSelect.appendChild(defaultOption);

    endpoints.forEach(endpoint => {
        const option = document.createElement('option');
        option.value = endpoint.value;
        option.textContent = endpoint.label;
        debugEndpointSelect.appendChild(option);
    });
}

/**
 * Add a custom debug endpoint to the selector
 * @param {Object} state - Application state
 * @param {String} endpoint - Endpoint URL
 * @param {String} label - Display label
 */
export function addDebugEndpoint(state, endpoint, label) {
    const { debugEndpointSelect } = state.domElements;

    if (!debugEndpointSelect) {
        console.warn('Debug endpoint selector not found');
        return;
    }

    const option = document.createElement('option');
    option.value = endpoint;
    option.textContent = label;
    debugEndpointSelect.appendChild(option);
    logMessage(`Added debug endpoint: ${label}`, 'debug');
}

/**
 * Log current BLE state for debugging
 * @param {Object} state - Application state
 */
export function logBleState(state) {
    console.group('BLE State Debug');
    console.log('Connected Device:', state.connectedDevice);
    console.log('Socket Connected:', state.socketConnected);
    console.log('Subscribed Characteristics:', Array.from(state.subscribedCharacteristics));
    console.groupEnd();
    logMessage('BLE state logged to console', 'debug');
}

/**
 * Initialize keyboard shortcuts for debugging
 * @param {Object} state - Application state
 */
export function initializeDebugShortcuts(state) {
    document.addEventListener('keydown', (event) => {
        if (event.ctrlKey && event.shiftKey && event.key === 'D') {
            event.preventDefault();
            toggleDebugPanel(state);
        }
        if (event.ctrlKey && event.shiftKey && event.key === 'L') {
            event.preventDefault();
            logBleState(state);
        }
    }, { passive: true });
}

/**
 * BLE Debug Panel
 * Provides UI for executing direct API calls and debugging
 */

document.addEventListener('DOMContentLoaded', () => {
    const debugEndpointSelect = document.getElementById('debug-endpoint');
    const debugResponsePre = document.getElementById('debug-response');
    const debugSendButton = document.getElementById('debug-send');
    const debugToggleButton = document.getElementById('debug-toggle');
    const showDebugButton = document.getElementById('show-debug');
    const debugPanel = document.getElementById('debug-panel');
    
    // Check if elements exist
    if (!debugEndpointSelect || !debugResponsePre || 
        !debugSendButton || !showDebugButton || !debugPanel) {
        console.error('Missing debug panel elements');
        return;
    }
    
    // Populate debug endpoints
    const endpoints = [
        { value: '/api/ble/scan', label: 'Scan for Devices' },
        { value: '/api/ble/devices', label: 'List Known Devices' },
        { value: '/api/ble/devices/bonded', label: 'List Bonded Devices' },
        { value: '/api/ble/metrics', label: 'Get BLE Metrics' },
        { value: '/api/ble/errors/statistics', label: 'Get Error Statistics' },
        { value: '/api/ble/recovery/diagnostics', label: 'Run BLE Diagnostics' }
    ];
    
    endpoints.forEach(endpoint => {
        const option = document.createElement('option');
        option.value = endpoint.value;
        option.textContent = endpoint.label;
        debugEndpointSelect.appendChild(option);
    });
    
    // Show/hide debug panel
    showDebugButton.addEventListener('click', () => {
        debugPanel.classList.toggle('hidden');
    });
    
    // Toggle visibility
    if (debugToggleButton) {
        debugToggleButton.addEventListener('click', () => {
            debugPanel.classList.toggle('hidden');
        });
    }
    
    // Send debug request
    debugSendButton.addEventListener('click', async () => {
        const endpoint = debugEndpointSelect.value;
        if (!endpoint) {
            debugResponsePre.textContent = 'Please select an endpoint';
            return;
        }
        
        try {
            debugResponsePre.textContent = 'Loading...';
            
            const response = await fetch(endpoint);
            const data = await response.json();
            
            // Pretty-print the response
            debugResponsePre.textContent = JSON.stringify(data, null, 2);
        } catch (error) {
            debugResponsePre.textContent = `Error: ${error.message}`;
        }
    });
});

/**
 * Format debug data for display or logging
 * @param {Object} data - The data to format
 * @param {String} type - The type of data being formatted
 * @returns {String} Formatted data string
 */
export function formatDebugData(data, type = 'json') {
    try {
        if (type === 'json') {
            return JSON.stringify(data, null, 2);
        } else if (type === 'table' && Array.isArray(data)) {
            return data.map(item => JSON.stringify(item)).join('\n');
        } else {
            return String(data);
        }
    } catch (error) {
        console.error('Error formatting debug data:', error);
        return `[Error formatting data: ${error.message}]`;
    }
}

/**
 * Log a debug message with timestamp
 * @param {String} message - The message to log
 * @param {Object} data - Optional data to include
 * @param {String} level - Log level (info, warning, error)
 */
export function debugLog(message, data = null, level = 'info') {
    const timestamp = new Date().toISOString();
    const logEntry = {
        timestamp,
        level,
        message,
        data
    };
    
    console.log(`[BLE-DEBUG][${timestamp}][${level}] ${message}`);
    if (data) {
        console.log(formatDebugData(data));
    }
    
    // Store in debug history
    if (!window.bleDebugHistory) {
        window.bleDebugHistory = [];
    }
    window.bleDebugHistory.push(logEntry);
    
    // Limit history size
    if (window.bleDebugHistory.length > 500) {
        window.bleDebugHistory.shift();
    }
    
    logMessage(message, level);
}

/**
 * Create a snapshot of the current BLE state for debugging
 * @param {Object} state - Application state
 * @returns {Object} Debug snapshot object
 */
export function createDebugSnapshot(state) {
    const snapshot = {
        timestamp: new Date().toISOString(),
        connected: !!state.connectedDevice,
        deviceInfo: state.connectedDevice ? {
            id: state.connectedDevice.id,
            name: state.connectedDevice.name || 'Unknown',
            gatt: state.connectedDevice.gatt ? 'Connected' : 'Disconnected'
        } : null,
        socketConnected: state.socketConnected,
        subscribedCharacteristics: Array.from(state.subscribedCharacteristics || []),
        queuedOperations: state.operationQueue ? state.operationQueue.length : 0,
        lastError: state.lastError,
        browserInfo: {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            bluetooth: navigator.bluetooth ? 'Available' : 'Not Available'
        }
    };
    
    debugLog('Debug snapshot created', snapshot);
    return snapshot;
}

/**
 * Export debug logs to a downloadable file
 * @param {Object} state - Application state
 */
export function exportDebugLogs(state) {
    try {
        const snapshot = createDebugSnapshot(state);
        const exportData = {
            snapshot,
            logs: window.bleDebugHistory || [],
            exportDate: new Date().toISOString()
        };
        
        const blob = new Blob([formatDebugData(exportData)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `ble-debug-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
        document.body.appendChild(a);
        a.click();
        
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 100);
        
        logMessage('Debug logs exported to file', 'info');
    } catch (error) {
        console.error('Error exporting debug logs:', error);
        logMessage(`Failed to export debug logs: ${error.message}`, 'error');
    }
}

/**
 * Set up event listeners for debug events
 * @param {Object} state - Application state
 */
export function setupDebugListeners(state) {
    const { debugExportBtn } = state.domElements;
    
    if (debugExportBtn) {
        debugExportBtn.addEventListener('click', () => exportDebugLogs(state));
    }
    
    // Monitor bluetooth events
    if (navigator.bluetooth) {
        navigator.bluetooth.addEventListener('availabilitychanged', (event) => {
            debugLog('Bluetooth availability changed', { available: event.value }, 'info');
        });
    }
    
    // Listen for uncaught BLE errors
    window.addEventListener('unhandledrejection', (event) => {
        if (event.reason && event.reason.toString().includes('bluetooth')) {
            debugLog('Unhandled BLE promise rejection', { error: event.reason.toString() }, 'error');
        }
    });
    
    debugLog('Debug listeners initialized', null, 'debug');
}

/**
 * Monitor BLE operations and log them
 * @param {Object} state - Application state
 */
export function monitorBleOperations(state) {
    let operationCount = 0;
    
    // Create wrapped versions of common BLE operations for monitoring
    const monitoredOperations = {
        connect: async (device) => {
            const opId = ++operationCount;
            debugLog(`Starting BLE connect operation #${opId}`, { deviceId: device.id });
            try {
                const result = await state.bleOperations.connect(device);
                debugLog(`Completed BLE connect operation #${opId}`, { success: true });
                return result;
            } catch (error) {
                debugLog(`Failed BLE connect operation #${opId}`, { error: error.toString() }, 'error');
                throw error;
            }
        },
        
        disconnect: async () => {
            const opId = ++operationCount;
            debugLog(`Starting BLE disconnect operation #${opId}`);
            try {
                const result = await state.bleOperations.disconnect();
                debugLog(`Completed BLE disconnect operation #${opId}`, { success: true });
                return result;
            } catch (error) {
                debugLog(`Failed BLE disconnect operation #${opId}`, { error: error.toString() }, 'error');
                throw error;
            }
        }
    };
    
    // Assign monitored operations back to state
    state.monitoredBleOperations = monitoredOperations;
    
    debugLog('BLE operation monitoring initialized', null, 'debug');
    return monitoredOperations;
}

/**
 * Toggle visibility of debug elements
 * @param {Object} state - Application state
 * @param {String} elementId - Target element ID (optional)
 */
export function toggleDebugVisibility(state, elementId = null) {
    if (elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.toggle('hidden');
            debugLog(`Toggled visibility of debug element: ${elementId}`, 
                     { visible: !element.classList.contains('hidden') });
        } else {
            console.warn(`Debug element not found: ${elementId}`);
        }
    } else {
        // Toggle all debug elements
        const debugElements = document.querySelectorAll('.debug-element');
        debugElements.forEach(element => {
            element.classList.toggle('hidden');
        });
        
        // Also toggle the main debug panel
        toggleDebugPanel(state);
    }
}
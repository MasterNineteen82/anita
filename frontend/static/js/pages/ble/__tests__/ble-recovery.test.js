import { logMessage } from './ble-ui.js';
import { BLE_EVENTS } from './ble-events.js';
import { connectToDevice } from './ble-connection.js';

/**
 * Initialize the recovery subsystem
 * @param {Object} state - Application state
 */
export function initializeRecovery(state) {
    // Clean up any previous recovery resources
    if (state.recoveryCleanupNeeded) {
        try {
            // Clear any recovery timeouts and intervals
            if (state.recoveryTimeoutId) {
                clearTimeout(state.recoveryTimeoutId);
                state.recoveryTimeoutId = null;
            }
            
            // Reset recovery state
            state.inRecoveryMode = false;
            state.recoveryCleanupNeeded = false;
            
            logMessage('Cleaned up previous recovery session', 'info');
        } catch (error) {
            console.error('Error cleaning up recovery resources:', error);
        }
    }
    
    // Initialize recovery event listeners
    if (window.bleEvents) {
        window.bleEvents.on(BLE_EVENTS.DEVICE_DISCONNECTED, (data) => {
            // Check if this was unexpected and auto-reconnect is enabled
            if (state.connectedDevice && state.connectedDevice.address === data.address) {
                console.log('Device disconnected unexpectedly, attempting recovery...');
                // Handle recovery logic here
            }
        });
    }
    
    logMessage('BLE recovery subsystem initialized', 'info');
}

/**
 * Reset the Bluetooth adapter with better error handling
 * @returns {Promise<Boolean>} Success status
 */
export async function resetAdapter() {
    try {
        logMessage('Attempting to reset Bluetooth adapter...', 'info');
        
        // Create AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 20000); // 20 second timeout
        
        try {
            const response = await fetch('/api/ble/recovery/reset-adapter', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache' 
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            // Check if response is ok
            if (!response.ok) {
                let errorMessage = 'Failed to reset adapter';
                
                try {
                    // Try to parse the error response
                    const errorText = await response.text();
                    
                    try {
                        const errorJson = JSON.parse(errorText);
                        errorMessage = errorJson.detail || errorMessage;
                    } catch (e) {
                        // If parsing fails, use the raw text
                        errorMessage = errorText || errorMessage;
                    }
                } catch (e) {
                    // If we can't read the response text, use a generic message
                    errorMessage = `Failed to reset adapter: ${response.status} ${response.statusText}`;
                }
                
                throw new Error(errorMessage);
            }
            
            const result = await response.json();
            logMessage(`Adapter reset ${result.status === 'success' ? 'successful' : 'failed'}`, 
                      result.status === 'success' ? 'success' : 'error');
            
            return result.status === 'success';
        } catch (fetchError) {
            if (fetchError.name === 'AbortError') {
                throw new Error('Adapter reset operation timed out');
            }
            throw fetchError;
        }
    } catch (error) {
        console.error('Error resetting adapter:', error);
        logMessage(`Adapter reset failed: ${error.message}`, 'error');
        return false;
    }
}
/**
 * Record recovery metrics
 * @param {String} address - Device address
 * @param {Boolean} success - Whether recovery was successful
 * @param {Number} time - Time taken for recovery in ms
 */
function recordRecoveryAttempt(address, success, time) {
    try {
        // Get existing metrics
        const metricsStr = localStorage.getItem('ble-recovery-metrics');
        const metrics = metricsStr ? JSON.parse(metricsStr) : {
            attempts: 0,
            successes: 0,
            failures: 0,
            averageTime: 0,
            devices: {}
        };
        
        // Update metrics
        metrics.attempts++;
        if (success) {
            metrics.successes++;
        } else {
            metrics.failures++;
        }
        
        // Update average time
        metrics.averageTime = ((metrics.averageTime * (metrics.attempts - 1)) + time) / metrics.attempts;
        
        // Update device-specific metrics
        if (!metrics.devices[address]) {
            metrics.devices[address] = {
                attempts: 0,
                successes: 0,
                failures: 0
            };
        }
        
        metrics.devices[address].attempts++;
        if (success) {
            metrics.devices[address].successes++;
        } else {
            metrics.devices[address].failures++;
        }
        
        // Save metrics
        localStorage.setItem('ble-recovery-metrics', JSON.stringify(metrics));
        
        // Send metrics to server if possible
        fetch('/api/ble/metrics/recovery', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                address,
                success,
                time,
                timestamp: Date.now()
            })
        }).catch(err => console.warn('Failed to send recovery metrics to server:', err));
    } catch (error) {
        console.error('Error recording recovery metrics:', error);
    }
}

/**
 * Attempt to reconnect to a device without full recovery
 * @param {Object} state - Application state
 * @param {String} address - Device address
 * @param {String} name - Device name
 * @returns {Promise<Boolean>} Success status
 */
async function attemptReconnection(state, address, name) {
    try {
        logMessage(`Attempting simple reconnection to ${name}...`, 'info');
        
        // Try direct connection without resetting adapter
        const response = await fetch(`/api/ble/connect/${encodeURIComponent(address)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            body: JSON.stringify({
                timeout: 10,
                autoReconnect: true,
                retryCount: 3,
                recovery: false // This is a simple reconnect, not a recovery attempt
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Reconnection failed: ${errorText}`);
        }
        
        const result = await response.json();
        
        if (result.status === 'connected') {
            logMessage(`Successfully reconnected to ${name}`, 'success');
            return true;
        } else {
            logMessage(`Could not reconnect to ${name}: ${result.message}`, 'warning');
            return false;
        }
    } catch (error) {
        console.error('Reconnection error:', error);
        logMessage(`Reconnection error: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Initialize recovery UI components
 * @param {Object} state - Application state
 */
function initializeRecoveryUI(state) {
    // Add recovery mode toggle to advanced settings
    const advancedSettingsContainer = document.querySelector('#ble-advanced-settings');
    if (advancedSettingsContainer) {
        const recoverySection = document.createElement('div');
        recoverySection.className = 'mt-4';
        recoverySection.innerHTML = `
            <h3 class="text-sm font-semibold text-gray-300 uppercase mb-2">Recovery Options</h3>
            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <span class="text-sm text-gray-400">Auto-Reconnect</span>
                    <label class="switch">
                        <input type="checkbox" id="auto-reconnect-toggle" checked>
                        <span class="slider round"></span>
                    </label>
                </div>
                <div class="flex items-center justify-between">
                    <span class="text-sm text-gray-400">Advanced Recovery</span>
                    <label class="switch">
                        <input type="checkbox" id="advanced-recovery-toggle" checked>
                        <span class="slider round"></span>
                    </label>
                </div>
                <div class="flex items-center justify-between mt-2">
                    <button id="diagnose-connection-btn" class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                        <i class="fas fa-stethoscope mr-1"></i> Diagnose Connection
                    </button>
                    <button id="clear-recovery-metrics-btn" class="bg-gray-600 hover:bg-gray-700 text-white px-3 py-1 rounded text-sm">
                        <i class="fas fa-eraser mr-1"></i> Clear Metrics
                    </button>
                </div>
            </div>
        `;
        
        // Append after the last section
        advancedSettingsContainer.querySelector('.space-y-4').appendChild(recoverySection);
        
        // Initialize toggle states from state
        state.autoReconnectEnabled = true; // default true
        state.enableAdvancedRecovery = true; // default true
        
        // Add event listeners
        const autoReconnectToggle = document.getElementById('auto-reconnect-toggle');
        if (autoReconnectToggle) {
            autoReconnectToggle.addEventListener('change', e => {
                state.autoReconnectEnabled = e.target.checked;
                logMessage(`Auto-reconnect ${state.autoReconnectEnabled ? 'enabled' : 'disabled'}`, 'info');
            });
        }
        
        const advancedRecoveryToggle = document.getElementById('advanced-recovery-toggle');
        if (advancedRecoveryToggle) {
            advancedRecoveryToggle.addEventListener('change', e => {
                state.enableAdvancedRecovery = e.target.checked;
                logMessage(`Advanced recovery ${state.enableAdvancedRecovery ? 'enabled' : 'disabled'}`, 'info');
            });
        }
        
        const diagnoseBtn = document.getElementById('diagnose-connection-btn');
        if (diagnoseBtn) {
            diagnoseBtn.addEventListener('click', async () => {
                try {
                    diagnoseBtn.disabled = true;
                    diagnoseBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Diagnosing...';
                    
                    const diagnostics = await diagnoseBleConnection(state);
                    showDiagnosticsResults(diagnostics);
                } catch (error) {
                    logMessage(`Diagnostics error: ${error.message}`, 'error');
                } finally {
                    diagnoseBtn.disabled = false;
                    diagnoseBtn.innerHTML = '<i class="fas fa-stethoscope mr-1"></i> Diagnose Connection';
                }
            });
        }
        
        const clearMetricsBtn = document.getElementById('clear-recovery-metrics-btn');
        if (clearMetricsBtn) {
            clearMetricsBtn.addEventListener('click', () => {
                showConfirmationDialog(
                    'Clear Recovery Metrics',
                    'Are you sure you want to clear all recovery metrics?',
                    () => {
                        localStorage.removeItem('ble-recovery-metrics');
                        logMessage('Recovery metrics cleared', 'info');
                    }
                );
            });
        }
    }
}

/**
 * Show recovery UI when automatic recovery fails
 * @param {Object} state - Application state
 * @param {String} address - Device address
 * @param {String} name - Device name
 */
function showRecoveryUI(state, address, name) {
    // Get the device info container
    const deviceInfoContainer = state.domElements.deviceInfoContent;
    if (!deviceInfoContainer) return;
    
    // Create recovery UI
    deviceInfoContainer.innerHTML = `
        <div class="space-y-4">
            <div class="text-red-500">Connection failed to ${name || address}</div>
            <div class="text-gray-400 text-sm">The connection attempt failed despite automatic recovery attempts. Would you like to try manual recovery?</div>
            
            <div class="flex space-x-2">
                <button id="manual-recovery-btn" class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                    <i class="fas fa-sync mr-1"></i> Try Manual Recovery
                </button>
                <button id="diagnose-btn" class="bg-yellow-600 hover:bg-yellow-700 text-white px-3 py-1 rounded text-sm">
                    <i class="fas fa-stethoscope mr-1"></i> Diagnose
                </button>
            </div>
            
            <div id="recovery-status" class="mt-3 hidden">
                <div class="text-sm text-gray-400">Recovery in progress...</div>
                <div class="h-2 w-full bg-gray-700 rounded-full mt-1">
                    <div id="recovery-progress" class="h-full bg-blue-600 rounded-full transition-all duration-300" style="width: 0%"></div>
                </div>
            </div>
        </div>
    `;
    
    // Add event listeners
    const manualRecoveryBtn = document.getElementById('manual-recovery-btn');
    if (manualRecoveryBtn) {
        manualRecoveryBtn.addEventListener('click', async () => {
            try {
                // Show recovery status
                const recoveryStatus = document.getElementById('recovery-status');
                if (recoveryStatus) recoveryStatus.classList.remove('hidden');
                
                // Update progress indicators
                const progressBar = document.getElementById('recovery-progress');
                
                // Disable buttons during recovery
                manualRecoveryBtn.disabled = true;
                const diagnoseBtn = document.getElementById('diagnose-btn');
                if (diagnoseBtn) diagnoseBtn.disabled = true;
                
                // Show initial progress
                if (progressBar) progressBar.style.width = '10%';
                
                // Step 1: Reset adapter
                logMessage('Step 1/3: Resetting Bluetooth adapter...', 'info');
                const resetSuccess = await resetAdapter();
                if (!resetSuccess) {
                    throw new Error('Adapter reset failed');
                }
                
                // Show progress
                if (progressBar) progressBar.style.width = '40%';
                
                // Step 2: Wait for adapter to stabilize
                logMessage('Step 2/3: Waiting for adapter to stabilize...', 'info');
                await new Promise(resolve => setTimeout(resolve, 3000));
                
                // Show progress
                if (progressBar) progressBar.style.width = '70%';
                
                // Step 3: Attempt connection
                logMessage(`Step 3/3: Attempting to connect to ${name || address}...`, 'info');
                const success = await recoverConnection(address, name || address);
                
                // Show final progress
                if (progressBar) progressBar.style.width = '100%';
                
                if (success) {
                    logMessage(`Manual recovery successful for ${name || address}`, 'success');
                } else {
                    throw new Error('Connection attempt failed after adapter reset');
                }
            } catch (error) {
                console.error('Manual recovery error:', error);
                logMessage(`Manual recovery failed: ${error.message}`, 'error');
                
                // Show error in UI
                const recoveryStatus = document.getElementById('recovery-status');
                if (recoveryStatus) {
                    recoveryStatus.innerHTML = `
                        <div class="text-red-500 text-sm mt-2">Recovery failed: ${error.message}</div>
                        <div class="text-gray-400 text-xs mt-1">Try restarting your device or checking its battery level.</div>
                    `;
                }
            } finally {
                // Re-enable buttons
                manualRecoveryBtn.disabled = false;
                const diagnoseBtn = document.getElementById('diagnose-btn');
                if (diagnoseBtn) diagnoseBtn.disabled = false;
            }
        });
    }
    
    const diagnoseBtn = document.getElementById('diagnose-btn');
    if (diagnoseBtn) {
        diagnoseBtn.addEventListener('click', async () => {
            try {
                diagnoseBtn.disabled = true;
                diagnoseBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Diagnosing...';
                
                const diagnostics = await diagnoseBleConnection(state, address);
                showDiagnosticsResults(diagnostics);
            } catch (error) {
                logMessage(`Diagnostics error: ${error.message}`, 'error');
            } finally {
                diagnoseBtn.disabled = false;
                diagnoseBtn.innerHTML = '<i class="fas fa-stethoscope mr-1"></i> Diagnose';
            }
        });
    }
}

/**
 * Diagnose BLE connection issues
 * @param {Object} state - Application state
 * @param {String} address - Optional device address to diagnose
 * @returns {Promise<Object>} Diagnostic results
 */
async function diagnoseBleConnection(state, address = null) {
    try {
        logMessage('Starting BLE connection diagnostics...', 'info');
        
        // 1. Check if we can reach the backend API
        const apiCheck = await fetch('/api/health', { cache: 'no-store' })
            .then(res => res.ok)
            .catch(() => false);
        
        // 2. Check adapter status
        let adapterStatus = { available: false, error: null };
        try {
            const adapterResponse = await fetch('/api/ble/adapter-info', { cache: 'no-store' });
            if (adapterResponse.ok) {
                adapterStatus = await adapterResponse.json();
            } else {
                adapterStatus.error = await adapterResponse.text();
            }
        } catch (error) {
            adapterStatus.error = error.message;
        }
        
        // 3. Get error statistics
        let errorStats = {};
        try {
            const statsResponse = await fetch('/api/ble/metrics', { cache: 'no-store' });
            if (statsResponse.ok) {
                const data = await statsResponse.json();
                errorStats = data.error_statistics || {};
            }
        } catch (error) {
            console.error('Failed to get error statistics:', error);
        }
        
        // 4. Run device-specific diagnostics if an address was provided
        let deviceDiagnostics = null;
        if (address) {
            try {
                // Check if device is visible
                const deviceCheckResponse = await fetch(`/api/ble/device-exists/${encodeURIComponent(address)}`);
                if (deviceCheckResponse.ok) {
                    const result = await deviceCheckResponse.json();
                    deviceDiagnostics = {
                        visible: result.exists,
                        address: address
                    };
                }
            } catch (error) {
                console.error('Failed to run device diagnostics:', error);
            }
        }
        
        // 5. Check browser compatibility
        const navigatorInfo = {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            vendor: navigator.vendor,
            bluetooth: 'bluetooth' in navigator
        };
        
        // Compile diagnostic results
        const diagnostics = {
            timestamp: new Date().toISOString(),
            apiConnectivity: apiCheck,
            adapter: adapterStatus,
            errorStatistics: errorStats,
            device: deviceDiagnostics,
            browser: navigatorInfo,
            connectionState: state.connectionState || 'unknown'
        };
        
        logMessage('Diagnostics complete', 'info');
        console.log('BLE Diagnostics:', diagnostics);
        
        return diagnostics;
    } catch (error) {
        console.error('Diagnostics error:', error);
        throw error;
    }
}

/**
 * Show diagnostics results in UI
 * @param {Object} diagnostics - Diagnostic results
 */
function showDiagnosticsResults(diagnostics) {
    // Create diagnostics modal
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-70';
    modal.id = 'diagnostics-modal';
    
    // Generate recommendations based on diagnostics
    const recommendations = generateRecommendations(diagnostics);
    
    modal.innerHTML = `
        <div class="bg-gray-800 rounded-lg max-w-2xl w-full mx-4 overflow-hidden shadow-xl">
            <div class="flex justify-between items-center p-4 border-b border-gray-700">
                <h3 class="text-white text-lg font-semibold">BLE Connection Diagnostics</h3>
                <button id="close-diagnostics" class="text-gray-400 hover:text-white">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="p-4 max-h-[70vh] overflow-y-auto">
                <div class="space-y-4">
                    <!-- Summary -->
                    <div class="flex items-center p-3 rounded-lg ${diagnostics.apiConnectivity ? 'bg-green-900 bg-opacity-20' : 'bg-red-900 bg-opacity-20'}">
                        <i class="fas ${diagnostics.apiConnectivity ? 'fa-check-circle text-green-500' : 'fa-exclamation-circle text-red-500'} mr-3 text-xl"></i>
                        <div>
                            <div class="font-medium text-white">Backend API Connectivity</div>
                            <div class="text-sm text-gray-300">${diagnostics.apiConnectivity ? 'Connected' : 'Not Connected'}</div>
                        </div>
                    </div>
                    
                    <!-- Adapter Status -->
                    <div class="flex items-center p-3 rounded-lg ${diagnostics.adapter.available ? 'bg-green-900 bg-opacity-20' : 'bg-red-900 bg-opacity-20'}">
                        <i class="fas ${diagnostics.adapter.available ? 'fa-check-circle text-green-500' : 'fa-exclamation-circle text-red-500'} mr-3 text-xl"></i>
                        <div>
                            <div class="font-medium text-white">Bluetooth Adapter Status</div>
                            <div class="text-sm text-gray-300">${diagnostics.adapter.available ? 'Available' : 'Not Available'}</div>
                            ${diagnostics.adapter.error ? `<div class="text-sm text-red-400 mt-1">Error: ${diagnostics.adapter.error}</div>` : ''}
                        </div>
                    </div>
                    
                    <!-- Device Status (if applicable) -->
                    ${diagnostics.device ? `
                    <div class="flex items-center p-3 rounded-lg ${diagnostics.device.visible ? 'bg-green-900 bg-opacity-20' : 'bg-yellow-900 bg-opacity-20'}">
                        <i class="fas ${diagnostics.device.visible ? 'fa-check-circle text-green-500' : 'fa-exclamation-triangle text-yellow-500'} mr-3 text-xl"></i>
                        <div>
                            <div class="font-medium text-white">Device Visibility</div>
                            <div class="text-sm text-gray-300">${diagnostics.device.visible ? 'Device is visible' : 'Device not visible'}</div>
                            <div class="text-xs text-gray-400">${diagnostics.device.address}</div>
                        </div>
                    </div>
                    ` : ''}
                    
                    <!-- Browser Compatibility -->
                    <div class="flex items-center p-3 rounded-lg ${diagnostics.browser.bluetooth ? 'bg-green-900 bg-opacity-20' : 'bg-red-900 bg-opacity-20'}">
                        <i class="fas ${diagnostics.browser.bluetooth ? 'fa-check-circle text-green-500' : 'fa-exclamation-circle text-red-500'} mr-3 text-xl"></i>
                        <div>
                            <div class="font-medium text-white">Browser Compatibility</div>
                            <div class="text-sm text-gray-300">${diagnostics.browser.bluetooth ? 'Web Bluetooth API Available' : 'Web Bluetooth API Not Available'}</div>
                            <div class="text-xs text-gray-400">${diagnostics.browser.userAgent}</div>
                        </div>
                    </div>
                    
                    <!-- Recommendations -->
                    <div class="mt-4">
                        <h4 class="text-white font-medium mb-2">Recommendations</h4>
                        <ul class="list-disc list-inside space-y-1 text-gray-300">
                            ${recommendations.map(rec => `<li>${rec}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            </div>
            <div class="p-4 border-t border-gray-700 flex justify-end">
                <button id="download-diagnostics" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm mr-2">
                    <i class="fas fa-download mr-1"></i> Export
                </button>
                <button id="close-diagnostics-btn" class="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded text-sm">
                    Close
                </button>
            </div>
        </div>
    `;
    
    // Add to body
    document.body.appendChild(modal);
    
    // Add event listeners
    document.getElementById('close-diagnostics').addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    document.getElementById('close-diagnostics-btn').addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    document.getElementById('download-diagnostics').addEventListener('click', () => {
        // Create downloadable file with diagnostics
        const blob = new Blob([JSON.stringify(diagnostics, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ble-diagnostics-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
}

/**
 * Generate recommendations based on diagnostics
 * @param {Object} diagnostics - Diagnostic results
 * @returns {Array<String>} Recommendations
 */
function generateRecommendations(diagnostics) {
    const recommendations = [];
    
    // API connectivity issues
    if (!diagnostics.apiConnectivity) {
        recommendations.push('Check your network connection or refresh the page.');
        recommendations.push('Verify the backend service is running and accessible.');
    }
    
    // Adapter issues
    if (!diagnostics.adapter.available) {
        recommendations.push('Ensure your device has Bluetooth enabled.');
        recommendations.push('Try resetting the Bluetooth adapter via system settings.');
        if (diagnostics.adapter.error) {
            recommendations.push('Adapter error detected. Try restarting the application.');
        }
    }
    
    // Device-specific issues
    if (diagnostics.device && !diagnostics.device.visible) {
        recommendations.push('Ensure the device is powered on and in range.');
        recommendations.push('Check the device battery level if applicable.');
        recommendations.push('Try scanning again to discover nearby devices.');
    }
    
    // Browser compatibility
    if (!diagnostics.browser.bluetooth) {
        recommendations.push('Your browser does not support the Web Bluetooth API. Try using Chrome, Edge, or Opera.');
    }
    
    // Add general recommendations if list is empty
    if (recommendations.length === 0) {
        recommendations.push('Try resetting the Bluetooth adapter.');
        recommendations.push('Restart the device you are trying to connect to.');
        recommendations.push('Restart this application and try again.');
    }
    
    return recommendations;
}

/**
 * Set up diagnostic collection for BLE issues
 */
function setupDiagnosticCollection() {
    // Listen for certain types of errors
    window.addEventListener('unhandledrejection', event => {
        // Only capture BLE-related errors
        if (event.reason && event.reason.message && 
            (event.reason.message.includes('BLE') || 
             event.reason.message.includes('Bluetooth') || 
             event.reason.message.includes('connect'))) {
            
            recordErrorForDiagnostics('unhandledRejection', event.reason.message);
        }
    });
    
    // Extend the console.error method to capture BLE errors
    const originalError = console.error;
    console.error = function() {
        // Call original method
        originalError.apply(console, arguments);
        
        // Check if this is a BLE error
        const errorText = Array.from(arguments).join(' ');
        if (errorText.includes('BLE') || 
            errorText.includes('Bluetooth') || 
            errorText.includes('connect')) {
            
            recordErrorForDiagnostics('consoleError', errorText);
        }
    };
}

/**
 * Record error for diagnostics
 * @param {String} type - Error type
 * @param {String} message - Error message
 */
function recordErrorForDiagnostics(type, message) {
    try {
        // Get existing diagnostics
        const diagnosticsStr = localStorage.getItem('ble-error-diagnostics');
        const diagnostics = diagnosticsStr ? JSON.parse(diagnosticsStr) : {
            errors: []
        };
        
        // Add error
        diagnostics.errors.push({
            type,
            message,
            timestamp: new Date().toISOString()
        });
        
        // Limit the number of errors
        if (diagnostics.errors.length > 50) {
            diagnostics.errors = diagnostics.errors.slice(-50);
        }
        
        // Save diagnostics
        localStorage.setItem('ble-error-diagnostics', JSON.stringify(diagnostics));
    } catch (error) {
        // Don't need to do anything - this is just diagnostic collection
    }
}


/**
 * Recover connection to a device
 * @param {String} address - Device address
 * @param {String} name - Device name
 * @returns {Promise<Boolean>} Success status
 */
async function recoverConnection(address, name) {
    try {
        logMessage(`Attempting connection recovery for ${name}...`, 'info');
        
        // Step 1: Check if device is still in range
        const deviceCheckResponse = await fetch(`/api/ble/device-exists/${encodeURIComponent(address)}`, {
            headers: { 'Cache-Control': 'no-cache' },
            // Add a timeout to prevent hanging
            signal: AbortSignal.timeout(5000)
        });
        
        if (!deviceCheckResponse.ok) {
            throw new Error('Failed to check device availability');
        }
        
        const deviceCheck = await deviceCheckResponse.json();
        
        if (!deviceCheck.exists) {
            logMessage(`Device ${name} is not currently visible. It may be out of range or powered off.`, 'warning');
            return false;
        }
        
        // Step 2: Try resetting adapter if needed
        logMessage('Resetting Bluetooth adapter...', 'info');
        const resetSuccess = await resetAdapter();
        
        if (!resetSuccess) {
            logMessage('Adapter reset failed, but continuing with connection attempt', 'warning');
        } else {
            // Wait for adapter to stabilize
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        
        // Step 3: Attempt connection with recovery flag
        logMessage(`Connecting to ${name} with recovery mode...`, 'info');
        
        const response = await fetch(`/api/ble/connect/${encodeURIComponent(address)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            body: JSON.stringify({
                timeout: 15,            // Extended timeout for recovery
                autoReconnect: true,
                retryCount: 3,          // More retries for recovery
                recovery: true          // Indicate this is a recovery attempt
            }),
            // Add a timeout to prevent hanging
            signal: AbortSignal.timeout(20000) // 20 second timeout
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Recovery connection failed: ${errorText}`);
        }
        
        const connectionResult = await response.json();
        
        if (connectionResult.status.includes('connected')) {
            logMessage(`Successfully recovered connection to ${name}`, 'success');
            
            // Emit recovered event
            if (window.bleEvents) {
                window.bleEvents.emit(BLE_EVENTS.DEVICE_RECOVERED, {
                    address: address,
                    name: name
                });
            }
            
            return true;
        } else {
            logMessage(`Recovery failed: ${connectionResult.message || 'Unknown error'}`, 'error');
            return false;
        }
    } catch (error) {
        console.error('Connection recovery error:', error);
        logMessage(`Recovery failed: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Shows a custom confirmation dialog
 * @param {String} title - Dialog title
 * @param {String} message - Confirmation message
 * @param {Function} onConfirm - Function to call when user confirms
 */
function showConfirmationDialog(title, message, onConfirm) {
    // Create modal dialog
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-70';
    modal.innerHTML = `
        <div class="bg-gray-800 rounded-lg max-w-md w-full mx-4 overflow-hidden shadow-xl">
            <div class="flex justify-between items-center p-4 border-b border-gray-700">
                <h3 class="text-white text-lg font-semibold">${title}</h3>
                <button class="confirm-dialog-cancel text-gray-400 hover:text-white">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="p-4">
                <p class="text-gray-300">${message}</p>
            </div>
            <div class="p-4 border-t border-gray-700 flex justify-end">
                <button class="confirm-dialog-cancel bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded text-sm mr-2">
                    Cancel
                </button>
                <button class="confirm-dialog-confirm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm">
                    Confirm
                </button>
            </div>
        </div>
    `;
    
    // Add to body
    document.body.appendChild(modal);
    
    // Handle cancel
    const cancelButtons = modal.querySelectorAll('.confirm-dialog-cancel');
    cancelButtons.forEach(button => {
        button.addEventListener('click', () => {
            document.body.removeChild(modal);
        });
    });
    
    // Handle confirm
    const confirmButton = modal.querySelector('.confirm-dialog-confirm');
    confirmButton.addEventListener('click', () => {
        onConfirm();
        document.body.removeChild(modal);
    });
}

// Export additional functions
export { recoverConnection, diagnoseBleConnection, showDiagnosticsResults };

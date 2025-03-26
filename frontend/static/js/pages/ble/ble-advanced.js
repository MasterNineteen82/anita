/**
 * BLE Advanced Features Module
 * Handles MTU negotiation, connection parameters, bonding, and metrics
 */

import { logMessage } from './ble-ui.js';

/**
 * Initialize advanced BLE features
 * @param {Object} state - Shared BLE state object
 */
export function initializeAdvancedFeatures(state) {
    // Initialize controls
    initializeMtuControls(state);
    initializeConnectionParamControls(state);
    initializeBondingControls(state);
    initializeMetricsDisplay(state);
    initializeAdapterControls(state);
    
    // Update metrics on page load
    refreshMetrics();
    
    // Setup periodic metrics refresh
    setInterval(refreshMetrics, 30000); // Refresh every 30 seconds
    
    logMessage('Advanced BLE features initialized', 'info');
}

/**
 * Initialize MTU negotiation controls
 * @param {Object} state - Shared BLE state object
 */
function initializeMtuControls(state) {
    const mtuInput = document.getElementById('mtu-input');
    const mtuButton = document.getElementById('mtu-button');
    
    if (!mtuInput || !mtuButton) return;
    
    // Enable/disable MTU button based on connection state
    state.eventBus.on('CONNECTION_STATE_CHANGED', (connected) => {
        mtuButton.disabled = !connected;
    });
    
    // Handle MTU negotiation
    mtuButton.addEventListener('click', async () => {
        if (!state.connected) {
            logMessage('Cannot negotiate MTU: Not connected to a device', 'warning');
            return;
        }
        
        const mtuSize = parseInt(mtuInput.value, 10);
        if (isNaN(mtuSize) || mtuSize < 23 || mtuSize > 517) {
            logMessage('Invalid MTU size. Must be between 23 and 517', 'error');
            return;
        }
        
        try {
            // Show loading state
            mtuButton.disabled = true;
            mtuButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Negotiating...';
            
            const response = await fetch('/api/ble/mtu', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ size: mtuSize })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to negotiate MTU');
            }
            
            const result = await response.json();
            logMessage(`MTU negotiated successfully: ${result.mtu} bytes`, 'success');
        } catch (error) {
            logMessage(`MTU negotiation failed: ${error.message}`, 'error');
        } finally {
            // Restore button state
            mtuButton.disabled = false;
            mtuButton.innerHTML = '<i class="fas fa-exchange-alt mr-1"></i> Negotiate MTU';
        }
    });
}

/**
 * Initialize connection parameter controls
 * @param {Object} state - Shared BLE state object
 */
// Add a fallback when buttons aren't found

function initializeConnectionParamControls(state) {
    const minIntervalInput = document.getElementById('min-interval');
    const maxIntervalInput = document.getElementById('max-interval');
    const latencyInput = document.getElementById('latency');
    const timeoutInput = document.getElementById('timeout');
    
    // Create buttons if they don't exist yet
    let setParamsButton = document.getElementById('set-params-button');
    let getParamsButton = document.getElementById('get-params-button');
    
    if (!setParamsButton && timeoutInput) {
        // Create and append the buttons if they don't exist
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'flex space-x-2 mt-2';
        buttonContainer.innerHTML = `
            <button id="set-params-button" class="btn btn-sm btn-primary disabled:opacity-50" disabled>
                <i class="fas fa-save mr-1"></i> Set Parameters
            </button>
            <button id="get-params-button" class="btn btn-sm btn-secondary disabled:opacity-50" disabled>
                <i class="fas fa-sync mr-1"></i> Get Current
            </button>
        `;
        
        // Find a good place to insert the buttons
        const parent = timeoutInput.closest('div')?.parentElement;
        if (parent) {
            parent.appendChild(buttonContainer);
            
            // Update references to the newly created buttons
            setParamsButton = document.getElementById('set-params-button');
            getParamsButton = document.getElementById('get-params-button');
        }
    }
    
if (!setParamsButton || !getParamsButton) {
    console.warn('Connection parameter buttons not found in DOM');
    return;
}

// Rest of the function remains the same...

// Handle get parameters
getParamsButton.addEventListener('click', async () => {
        if (!state.connected) {
            logMessage('Cannot get connection parameters: Not connected to a device', 'warning');
            return;
        }
        
        try {
            // Show loading state
            getParamsButton.disabled = true;
            getParamsButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Loading...';
            
            const response = await fetch('/api/ble/connection-parameters');
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to get connection parameters');
            }
            
            const result = await response.json();
            
            // Update input fields
            if (result.min_interval) minIntervalInput.value = result.min_interval;
            if (result.max_interval) maxIntervalInput.value = result.max_interval;
            if (result.latency !== undefined) latencyInput.value = result.latency;
            if (result.timeout) timeoutInput.value = result.timeout;
            
            logMessage('Connection parameters retrieved', 'info');
            
        } catch (error) {
            logMessage(`Failed to get connection parameters: ${error.message}`, 'error');
        } finally {
            // Restore button state
            getParamsButton.disabled = false;
            getParamsButton.innerHTML = '<i class="fas fa-sync mr-1"></i> Get Current';
        }
    });
}

/**
 * Initialize device bonding controls
 * @param {Object} state - Shared BLE state object
 */
function initializeBondingControls(state) {
    const bondButton = document.getElementById('bond-button');
    const unbondButton = document.getElementById('unbond-button');
    const bondedDevicesList = document.getElementById('bonded-devices-list');
    
    if (!bondButton || !unbondButton || !bondedDevicesList) return;
    
    // Update button state based on device selection
    state.eventBus.on('DEVICE_SELECTED', (device) => {
        const deviceSelected = !!device;
        bondButton.disabled = !deviceSelected;
        unbondButton.disabled = !deviceSelected;
    });
    
    // Bond button event handler
    bondButton.addEventListener('click', async () => {
        if (!state.selectedDevice) {
            logMessage('No device selected for bonding', 'warning');
            return;
        }
        
        try {
            // Show loading state
            bondButton.disabled = true;
            bondButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Bonding...';
            
            const response = await fetch(`/api/ble/devices/${state.selectedDevice.address}/bond`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Bonding failed');
            }
            
            const result = await response.json();
            logMessage(result.message || 'Device bonded successfully', 'success');
            
            // Refresh bonded devices list
            await loadBondedDevices(bondedDevicesList);
            
        } catch (error) {
            logMessage(`Bonding failed: ${error.message}`, 'error');
        } finally {
            // Restore button state
            bondButton.disabled = false;
            bondButton.innerHTML = '<i class="fas fa-link mr-1"></i> Bond Device';
        }
    });
    
    // Unbond button event handler
    unbondButton.addEventListener('click', async () => {
        if (!state.selectedDevice) {
            logMessage('No device selected for unbonding', 'warning');
            return;
        }
        
        try {
            // Show loading state
            unbondButton.disabled = true;
            unbondButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Removing...';
            
            const response = await fetch(`/api/ble/devices/${state.selectedDevice.address}/bond`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Unbonding failed');
            }
            
            const result = await response.json();
            logMessage(result.message || 'Device unbonded successfully', 'success');
            
            // Refresh bonded devices list
            await loadBondedDevices(bondedDevicesList);
            
        } catch (error) {
            logMessage(`Unbonding failed: ${error.message}`, 'error');
        } finally {
            // Restore button state
            unbondButton.disabled = false;
            unbondButton.innerHTML = '<i class="fas fa-unlink mr-1"></i> Remove Bond';
        }
    });
    
    // Load bonded devices initially
    loadBondedDevices(bondedDevicesList);
}

/**
 * Load and display bonded devices
 * @param {HTMLElement} container - Container element for bonded devices list
 */
async function loadBondedDevices(container) {
    if (!container) return;
    
    try {
        // Show loading
        container.innerHTML = '<div class="text-gray-500 text-center py-2"><i class="fas fa-spinner fa-spin mr-2"></i>Loading...</div>';
        
        const response = await fetch('/api/ble/devices/bonded');
        
        if (!response.ok) {
            throw new Error('Failed to load bonded devices');
        }
        
        const devices = await response.json();
        
        // Display devices
        if (devices.length === 0) {
            container.innerHTML = '<div class="text-gray-500 text-sm">No bonded devices</div>';
            return;
        }
        
        // Create list items
        container.innerHTML = '';
        devices.forEach(device => {
            const deviceEl = document.createElement('div');
            deviceEl.className = 'flex justify-between items-center p-1 border-b border-gray-700 last:border-0';
            deviceEl.innerHTML = `
                <div class="text-sm truncate" title="${device.address}">
                    ${device.name || 'Unknown Device'}
                </div>
                <button class="connect-bonded-btn text-xs text-blue-400 hover:text-blue-300 ml-2" 
                        data-address="${device.address}">
                    <i class="fas fa-plug mr-1"></i>Connect
                </button>
            `;
            container.appendChild(deviceEl);
            
            // Add connection event handler
            const connectBtn = deviceEl.querySelector('.connect-bonded-btn');
            if (connectBtn) {
                connectBtn.addEventListener('click', () => {
                    // This should trigger connection in main BLE module
                    window.dispatchEvent(new CustomEvent('CONNECT_TO_DEVICE', { 
                        detail: { address: device.address } 
                    }));
                });
            }
        });
        
    } catch (error) {
        console.error('Error loading bonded devices:', error);
        container.innerHTML = `<div class="text-red-400 text-sm">Error: ${error.message}</div>`;
    }
}

/**
 * Initialize metrics display
 */
function initializeMetricsDisplay() {
    const refreshMetricsBtn = document.getElementById('refresh-metrics');
    
    if (!refreshMetricsBtn) return;
    
    // Refresh button handler
    refreshMetricsBtn.addEventListener('click', () => refreshMetrics());
}

// Fix the refreshMetrics function to use the correct API endpoints that actually exist

/**
 * Show a confirmation dialog to the user
 * @param {string} message - The message to display in the dialog
 * @returns {Promise<boolean>} A promise that resolves to true if confirmed, false otherwise
 */
function showConfirmationDialog(message) {
    return new Promise((resolve) => {
        const confirmed = window.confirm(message);
        resolve(confirmed);
    });
}

async function refreshMetrics() {
    const successRateEl = document.getElementById('connection-success-rate');
    const avgConnTimeEl = document.getElementById('avg-connection-time');
    const deviceCountEl = document.getElementById('device-count');
    const recoveryRateEl = document.getElementById('recovery-success-rate');
    const topErrorsEl = document.getElementById('top-errors');
    
    if (!successRateEl || !avgConnTimeEl || !deviceCountEl || !recoveryRateEl || !topErrorsEl) {
        return;
    }
    
    try {
        // Use the correct API endpoint
        const response = await fetch('/api/ble/metrics');
        if (!response.ok) throw new Error('Failed to fetch metrics and error statistics');
        const data = await response.json();
        
        const metrics = data.metrics || {};
        const errorStats = data.error_statistics || {};
        
        // Update connection success rate
        successRateEl.textContent = metrics.connection_attempts > 0
            ? `${metrics.connection_success_rate?.toFixed(1) || '0.0'}%`
            : 'N/A';
            
        // Update average connection time
        avgConnTimeEl.textContent = metrics.avg_connection_time
            ? `${metrics.avg_connection_time.toFixed(2)}ms`
            : 'N/A';
            
        // Update device count
        deviceCountEl.textContent = metrics.device_count || '0';
        
        // Update recovery success rate
        recoveryRateEl.textContent = errorStats.recovery_attempts > 0
            ? `${errorStats.recovery_success_rate?.toFixed(1) || '0.0'}%`
            : 'N/A';
            
        // Update top errors
        if (errorStats.error_counts && Object.keys(errorStats.error_counts).length > 0) {
            const topErrors = Object.entries(errorStats.error_counts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([type, count]) => ({ type, count }));
                
            topErrorsEl.innerHTML = topErrors.map(error => 
                `<div class="text-sm flex justify-between">
                    <span class="text-gray-300">${error.type}</span>
                    <span class="text-gray-400">${error.count}</span>
                </div>`
            ).join('');
        } else {
            topErrorsEl.innerHTML = '<div class="text-gray-500 text-sm">No errors recorded</div>';
        }
        
    } catch (error) {
        console.error('Error refreshing metrics:', error);
        // Provide a more user-friendly message in the UI
        if (topErrorsEl) {
            topErrorsEl.innerHTML = '<div class="text-red-400 text-sm">Failed to load metrics data</div>';
        }
    }
}

/**
 * Initialize adapter control buttons
 */
function initializeAdapterControls() {
    const resetAdapterBtn = document.getElementById('reset-adapter');
    
    if (!resetAdapterBtn) return;
    
    resetAdapterBtn.addEventListener('click', async () => {
        try {
            const confirmReset = await showConfirmationDialog('Are you sure you want to reset the Bluetooth adapter? This will disconnect all devices.');
            if (!confirmReset) {
                return;
            }
            
            // Show loading state
            resetAdapterBtn.disabled = true;
            resetAdapterBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Resetting...';
            
            const response = await fetch('/api/ble/recovery/reset-adapter', {
                method: 'POST'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to reset adapter');
            }
            
            const result = await response.json();
            logMessage(result.message || 'Bluetooth adapter reset successfully', 'success');
            
        } catch (error) {
            logMessage(`Failed to reset adapter: ${error.message}`, 'error');
        } finally {
            // Restore button state
            resetAdapterBtn.disabled = false;
            resetAdapterBtn.innerHTML = '<i class="fas fa-power-off mr-1"></i> Reset Adapter';
        }
    });
}
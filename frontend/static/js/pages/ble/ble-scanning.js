import { updateScanStatus, setLoading } from './ble-ui.js';
import { deviceCache } from './ble-device-list.js';
import { logMessage,  } from './ble-ui.js';
import { BleUI } from './ble-ui.js';
import { BleEvents } from './ble-events.js';


// Re-export deviceCache for modules that import from this file
export { deviceCache };


// Enhanced default scan options with validation
const DEFAULT_SCAN_OPTIONS = Object.freeze({
    duration: 10,          // Scan duration in seconds (5-60)
    active: true,          // Active scanning (vs passive)
    allowDuplicates: false, // Filter duplicates
    namePrefix: '',        // Optional name prefix filter
    services: [],          // Optional service UUIDs to filter
    rssiThreshold: -80,    // Minimum RSSI value (-100 to -40)
    sortBy: 'rssi',        // Sort criteria: 'rssi', 'name', 'address'
    sortOrder: 'desc'      // Sort order: 'asc' or 'desc'
});

// Store discovered devices with address as key
const discoveredDevices = new Map();

/**
 * Initialize scanner UI with enhanced error handling
 * @param {Object} state - Global BLE state
 */
export function initializeScanner(state) {
    try {
        const container = document.getElementById('scanner-content');
        if (!container) {
            throw new Error('Scanner container element not found');
        }

        container.innerHTML = generateScannerHTML();
        setupScannerEventListeners(state);

        // Verify that the devices-list container exists
        const deviceListContainer = document.getElementById('devices-list');
        if (!deviceListContainer) {
            throw new Error('Device list container not found after initialization');
        }
    } catch (error) {
        logMessage(`Scanner initialization failed: ${error.message}`, 'error');
        throw error;
    }
}

/**
 * Generate scanner UI HTML template
 */
export function generateScannerHTML() {
    return `
        <div class="space-y-4">
            <!-- Scan controls -->
            <div class="flex items-center space-x-2">
                <button id="start-scan-btn" class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded flex items-center">
                    <i class="fas fa-search mr-1"></i> Scan for Devices
                </button>
                <button id="stop-scan-btn" class="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded flex items-center" disabled>
                    <i class="fas fa-stop mr-1"></i> Stop
                </button>
                <div class="ml-auto">
                    <button id="scan-options-btn" class="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-white text-xs rounded flex items-center">
                        <i class="fas fa-cog mr-1"></i> Options
                    </button>
                </div>
            </div>
            
            <!-- Scan status -->
            <div id="scan-status" class="hidden text-sm text-gray-400 flex items-center">
                <i class="fas fa-circle-notch fa-spin mr-2"></i>
                <span id="scan-status-text">Scanning...</span>
                <span id="scan-progress" class="ml-2 text-gray-500"></span>
            </div>
            
            <!-- Devices list -->
            <div class="relative">
                <div class="text-xs text-gray-400 flex justify-between mb-1">
                    <span id="devices-count">0 devices found</span>
                    <button id="clear-devices-btn" class="text-gray-500 hover:text-gray-300">
                        <i class="fas fa-times mr-1"></i> Clear
                    </button>
                </div>
                <div id="devices-list" class="bg-gray-800 border border-gray-700 rounded p-2 max-h-80 overflow-y-auto space-y-2">
                    <div class="text-center text-gray-500 py-6">
                        <i class="fas fa-bluetooth-b text-2xl mb-2"></i>
                        <p>No devices found</p>
                        <p class="text-xs mt-1">Start scanning to discover BLE devices</p>
                    </div>
                </div>
            </div>
            
            <!-- Advanced options panel -->
            <div id="scan-options-panel" class="hidden bg-gray-800 border border-gray-700 rounded p-3 space-y-3">
                ${generateOptionsPanelHTML()}
            </div>
        </div>
    `;
}

/**
 * Generate options panel HTML template
 */
export function generateOptionsPanelHTML() {
    return `
        <h4 class="text-sm font-semibold">Scan Options</h4>
        <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1">
                <label for="scan-duration" class="text-xs text-gray-400">Duration (seconds):</label>
                <div class="flex items-center">
                    <input type="range" id="scan-duration" min="5" max="60" step="5" value="${DEFAULT_SCAN_OPTIONS.duration}" 
                        class="mr-2 bg-gray-700 rounded w-full">
                    <span id="scan-duration-value" class="text-xs w-8 text-right">${DEFAULT_SCAN_OPTIONS.duration}s</span>
                </div>
            </div>
            <div class="space-y-1">
                <label for="rssi-threshold" class="text-xs text-gray-400">RSSI threshold:</label>
                <div class="flex items-center">
                    <input type="range" id="rssi-threshold" min="-100" max="-40" step="5" value="${DEFAULT_SCAN_OPTIONS.rssiThreshold}" 
                        class="mr-2 bg-gray-700 rounded w-full">
                    <span id="rssi-threshold-value" class="text-xs w-10 text-right">${DEFAULT_SCAN_OPTIONS.rssiThreshold} dBm</span>
                </div>
            </div>
        </div>
        
        <div class="grid grid-cols-2 gap-3">
            <div class="flex items-center">
                <input type="checkbox" id="active-scan" class="mr-2" ${DEFAULT_SCAN_OPTIONS.active ? 'checked' : ''}>
                <label for="active-scan" class="text-sm">Active scanning</label>
                <i class="fas fa-question-circle text-gray-500 ml-1 cursor-help" 
                   title="Active scanning requests scan response data from devices"></i>
            </div>
            <div class="flex items-center">
                <input type="checkbox" id="allow-duplicates" class="mr-2" ${DEFAULT_SCAN_OPTIONS.allowDuplicates ? 'checked' : ''}>
                <label for="allow-duplicates" class="text-sm">Allow duplicates</label>
                <i class="fas fa-question-circle text-gray-500 ml-1 cursor-help" 
                   title="Show multiple advertisements from the same device"></i>
            </div>
        </div>
        
        <div class="space-y-1">
            <label for="name-prefix" class="text-xs text-gray-400">Device name filter:</label>
            <input type="text" id="name-prefix" placeholder="Filter by name prefix (optional)" 
                value="${DEFAULT_SCAN_OPTIONS.namePrefix}"
                class="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm">
        </div>
        
        <div class="space-y-1">
            <label class="text-xs text-gray-400">Sort results by:</label>
            <div class="flex space-x-3">
                <label class="flex items-center">
                    <input type="radio" name="sort-by" value="rssi" ${DEFAULT_SCAN_OPTIONS.sortBy === 'rssi' ? 'checked' : ''} class="mr-1">
                    <span class="text-sm">Signal strength</span>
                </label>
                <label class="flex items-center">
                    <input type="radio" name="sort-by" value="name" ${DEFAULT_SCAN_OPTIONS.sortBy === 'name' ? 'checked' : ''} class="mr-1">
                    <span class="text-sm">Name</span>
                </label>
                <label class="flex items-center">
                    <input type="radio" name="sort-by" value="address" ${DEFAULT_SCAN_OPTIONS.sortBy === 'address' ? 'checked' : ''} class="mr-1">
                    <span class="text-sm">Address</span>
                </label>
            </div>
        </div>
        
        <div class="flex justify-end">
            <button id="reset-options-btn" class="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded mr-2">
                Reset to Default
            </button>
            <button id="apply-options-btn" class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded">
                Apply Options
            </button>
        </div>
    `;
}

/**
 * Setup event listeners for scanner UI with better memory management
 */
export function setupScannerEventListeners(state) {
    const startScanBtn = document.getElementById('start-scan-btn');
    const stopScanBtn = document.getElementById('stop-scan-btn');
    const clearDevicesBtn = document.getElementById('clear-devices-btn');
    const optionsBtn = document.getElementById('scan-options-btn');
    const optionsPanel = document.getElementById('scan-options-panel');
    const resetOptionsBtn = document.getElementById('reset-options-btn');
    const applyOptionsBtn = document.getElementById('apply-options-btn');

    // Clean up any existing listeners
    const cleanUpListeners = () => {
        if (startScanBtn) startScanBtn.removeEventListener('click', startScanHandler);
        if (stopScanBtn) stopScanBtn.removeEventListener('click', stopScanHandler);
        if (clearDevicesBtn) clearDevicesBtn.removeEventListener('click', clearDevicesList);
        if (optionsBtn) optionsBtn.removeEventListener('click', toggleOptionsPanel);
        if (resetOptionsBtn) resetOptionsBtn.removeEventListener('click', resetOptions);
        if (applyOptionsBtn) applyOptionsBtn.removeEventListener('click', applyOptions);
    };

    // Define handlers
    const startScanHandler = async () => {
        try {
            const options = getScanOptions();
            startScanBtn.disabled = true;
            stopScanBtn.disabled = false;
            document.getElementById('scan-status').classList.remove('hidden');
            
            if (!options.allowDuplicates) {
                clearDevicesList();
            }
            
            await startScanning(options, state);
        } catch (error) {
            logMessage(`Scan failed: ${error.message}`, 'error');
            resetScannerState();
        }
    };

    const stopScanHandler = async () => {
        try {
            await stopScanning(state);
            resetScannerState();
        } catch (error) {
            logMessage(`Failed to stop scan: ${error.message}`, 'error');
        }
    };

    const toggleOptionsPanel = () => {
        optionsPanel.classList.toggle('hidden');
    };

    const resetOptions = () => {
        document.getElementById('scan-duration').value = DEFAULT_SCAN_OPTIONS.duration;
        document.getElementById('scan-duration-value').textContent = `${DEFAULT_SCAN_OPTIONS.duration}s`;
        document.getElementById('rssi-threshold').value = DEFAULT_SCAN_OPTIONS.rssiThreshold;
        document.getElementById('rssi-threshold-value').textContent = `${DEFAULT_SCAN_OPTIONS.rssiThreshold} dBm`;
        document.getElementById('active-scan').checked = DEFAULT_SCAN_OPTIONS.active;
        document.getElementById('allow-duplicates').checked = DEFAULT_SCAN_OPTIONS.allowDuplicates;
        document.getElementById('name-prefix').value = DEFAULT_SCAN_OPTIONS.namePrefix;
        
        document.querySelectorAll('input[name="sort-by"]').forEach(radio => {
            radio.checked = (radio.value === DEFAULT_SCAN_OPTIONS.sortBy);
        });
    };

    const applyOptions = async () => {
        optionsPanel.classList.add('hidden');
        if (stopScanBtn && !stopScanBtn.disabled) {
            await stopScanning(state).then(() => {
                startScanBtn.click();
            }).catch(error => {
                logMessage(`Failed to update scan options: ${error.message}`, 'error');
            });
        }
    };

    // Clean up first
    cleanUpListeners();

    // Add new listeners
    if (startScanBtn) startScanBtn.addEventListener('click', startScanHandler);
    if (stopScanBtn) stopScanBtn.addEventListener('click', stopScanHandler);
    if (clearDevicesBtn) clearDevicesBtn.addEventListener('click', clearDevicesList);
    if (optionsBtn) optionsBtn.addEventListener('click', toggleOptionsPanel);
    if (resetOptionsBtn) resetOptionsBtn.addEventListener('click', resetOptions);
    if (applyOptionsBtn) applyOptionsBtn.addEventListener('click', applyOptions);

    // Input listeners
    const scanDurationInput = document.getElementById('scan-duration');
    if (scanDurationInput) {
        scanDurationInput.addEventListener('input', (e) => {
            document.getElementById('scan-duration-value').textContent = `${e.target.value}s`;
        });
    }

    const rssiThresholdInput = document.getElementById('rssi-threshold');
    if (rssiThresholdInput) {
        rssiThresholdInput.addEventListener('input', (e) => {
            document.getElementById('rssi-threshold-value').textContent = `${e.target.value} dBm`;
        });
    }
}

/**
 * Get current scan options from UI with validation
 */
export function getScanOptions() {
    const options = {...DEFAULT_SCAN_OPTIONS};
    
    try {
        const durationInput = document.getElementById('scan-duration');
        if (durationInput) {
            const duration = parseInt(durationInput.value, 10);
            options.duration = Math.min(60, Math.max(5, duration)); // Clamp to 5-60
        }

        const rssiInput = document.getElementById('rssi-threshold');
        if (rssiInput) {
            const rssi = parseInt(rssiInput.value, 10);
            options.rssiThreshold = Math.min(-40, Math.max(-100, rssi)); // Clamp to -100 to -40
        }

        const activeCheckbox = document.getElementById('active-scan');
        if (activeCheckbox) {
            options.active = activeCheckbox.checked;
        }

        const duplicatesCheckbox = document.getElementById('allow-duplicates');
        if (duplicatesCheckbox) {
            options.allowDuplicates = duplicatesCheckbox.checked;
        }

        const namePrefixInput = document.getElementById('name-prefix');
        if (namePrefixInput) {
            options.namePrefix = namePrefixInput.value.trim();
        }

        const selectedSort = document.querySelector('input[name="sort-by"]:checked');
        if (selectedSort) {
            options.sortBy = selectedSort.value;
        }

        return options;
    } catch (error) {
        logMessage(`Error getting scan options: ${error.message}`, 'error');
        return DEFAULT_SCAN_OPTIONS;
    }
}

export function processScanResults(devices, options, state) {
    const { deviceList } = state.domElements;
    if (!deviceList) {
        console.warn('Device list element not found');
        return;
    }

    let newDeviceCount = 0;
    const fragment = document.createDocumentFragment();
    const discoveredDevices = new Map(); // Use a Map to track discovered devices

    // Filter and process devices
    devices.forEach(device => {
        if (!options.allowDuplicates && discoveredDevices.has(device.address)) {
            return;
        }

        // Add device to discoveredDevices map
        discoveredDevices.set(device.address, device);

        // Create device element
        const deviceEl = createDeviceElement(device);
        fragment.appendChild(deviceEl);
        newDeviceCount++;
    });

    // Append new devices to the container
    deviceList.innerHTML = ''; // Clear the existing list
    fragment.childNodes.forEach(node => deviceList.appendChild(node));
    updateDeviceCount(discoveredDevices.size);
    logMessage(`Added ${newDeviceCount} new devices. Total: ${discoveredDevices.size}`, 'success');
}

/**
 * Create device element with connection handler
 */
export function createDeviceElement(device) {
    const deviceEl = document.createElement('div');
    deviceEl.className = 'device-card bg-gray-800 rounded-lg p-3 mb-2 hover:bg-gray-700 transition-colors';
    deviceEl.innerHTML = `
        <div class="flex justify-between items-center">
            <div>
                <div class="font-medium text-white">${device.name || 'Unknown Device'}</div>
                <div class="text-xs text-gray-400">${device.address}</div>
                <div class="text-xs text-gray-400">RSSI: ${device.rssi} dBm</div>
            </div>
            <button class="connect-btn bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                Connect
            </button>
        </div>
    `;

    const connectBtn = deviceEl.querySelector('.connect-btn');
    if (connectBtn) {
        connectBtn.addEventListener('click', () => {
            window.dispatchEvent(new CustomEvent('CONNECT_TO_DEVICE', {
                detail: { address: device.address }
            }));
        });
    }

    return deviceEl;
}

/**
 * Update device count display
 */
export function updateDeviceCount(count) {
    const countElement = document.getElementById('devices-count');
    if (countElement) {
        countElement.textContent = `${count} device${count !== 1 ? 's' : ''} found`;
    }
}

/**
 * Start scanning for BLE devices
 * @param {Object} options - Scan options
 * @param {number} options.duration - Scan duration in seconds (default: 5)
 * @param {boolean} options.active - Whether to use active scanning (default: true)
 * @param {string} options.name_prefix - Optional name prefix filter
 * @param {Array} options.services - Optional service UUIDs filter
 * @returns {Promise<Array>} List of discovered devices
 */
async function startScanning(options = {}) {
    try {
        // Set default options and remove unsupported parameters
        const scanOptions = {
            duration: options.duration || 5,
            active: options.active !== undefined ? options.active : true
            // DO NOT include allow_duplicates as it's not supported by the backend
        };

        // Add optional filters if provided
        if (options.name_prefix) {
            scanOptions.name_prefix = options.name_prefix;
        }
        if (options.services && options.services.length > 0) {
            scanOptions.services = options.services;
        }
        
        // Update UI to show scanning is in progress
        BleUI.updateScanStatus(true, "Scanning...");
        BleUI.showMessage(`Starting BLE scan for ${scanOptions.duration}s...`);
        
        // Send scan request to the backend
        const response = await fetch('/api/ble/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                options: scanOptions  // Use the structured options format
            })
        });
        
        if (!response.ok) {
            // Handle HTTP errors
            let errorDetail;
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || "Unknown error";
            } catch (e) {
                errorDetail = await response.text() || `HTTP error: ${response.status}`;
            }
            
            console.error("Scanning error:", errorDetail);
            BleUI.updateScanStatus(false, "Scan failed");
            BleUI.showError(`Scanning error: ${errorDetail}`);
            BleEvents.emit('ble.error.scan', { error: errorDetail });
            return [];
        }
        
        // Process the scan results
        const result = await response.json();
        const devices = result.devices || [];
        const scanTime = result.scan_time || 0;
        
        // Update UI with scan results
        BleUI.updateDeviceList(devices);
        BleUI.updateScanStatus(false, "Scan complete");
        BleUI.showMessage(`Found ${devices.length} devices in ${scanTime.toFixed(1)}s`);
        
        // Emit an event with the scan results
        BleEvents.emit('ble.scan.complete', { 
            devices,
            scanTime,
            count: devices.length
        });
        
        return devices;
    } catch (error) {
        // Handle JavaScript errors
        console.error("Scanning error:", error);
        BleUI.updateScanStatus(false, "Scan failed");
        BleUI.showError(`Scanning error: ${error.message || String(error)}`);
        BleEvents.emit('ble.error.scan', { error: error.message || String(error) });
        return [];
    }
}

/**
 * Sort devices based on options
 */
export function sortDevices(devices, options) {
    return [...devices].sort((a, b) => {
        if (options.sortBy === 'rssi') {
            return options.sortOrder === 'asc' ? a.rssi - b.rssi : b.rssi - a.rssi;
        } else if (options.sortBy === 'name') {
            const nameA = a.name || '';
            const nameB = b.name || '';
            return options.sortOrder === 'asc' ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
        } else if (options.sortBy === 'address') {
            return options.sortOrder === 'asc' ? a.address.localeCompare(b.address) : b.address.localeCompare(a.address);
        }
        return 0;
    });
}

export async function stopScanning() {
    try {
        const response = await fetch('/api/ble/stop-scan', {
            method: 'POST',
            headers: { 'Accept': 'application/json' }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to stop scan');
        }
        
        logMessage('Scan stopped successfully', 'info');
    } catch (error) {
        logMessage(`Error stopping scan: ${error.message}`, 'error');
        throw error;
    }
}

/**
 * Reset scanner UI state
 */
export function resetScannerState() {
    const startScanBtn = document.getElementById('start-scan-btn');
    const stopScanBtn = document.getElementById('stop-scan-btn');
    const scanStatus = document.getElementById('scan-status');

    if (startScanBtn) startScanBtn.disabled = false;
    if (stopScanBtn) stopScanBtn.disabled = true;
    if (scanStatus) scanStatus.classList.add('hidden');
}

/**
 * Clear devices list
 */
export function clearDevicesList() {
    discoveredDevices.clear();
    const devicesList = document.getElementById('devices-list');
    if (devicesList) {
        devicesList.innerHTML = `
            <div class="text-center text-gray-500 py-6">
                <i class="fas fa-bluetooth-b text-2xl mb-2"></i>
                <p>No devices found</p>
            </div>
        `;
    }
    updateDeviceCount(0);
}

/**
 * Enhanced scan wrapper with cleanup
 */
export async function scanDevicesWithErrorHandling(scanDuration = 5, active = true, useCache = false) {
    if (!useCache) {
        clearDevicesList();
    }

    try {
        const options = {
            ...DEFAULT_SCAN_OPTIONS,
            duration: Math.max(5, Math.min(60, scanDuration)),
            active,
            allowDuplicates: false
        };

        return new Promise((resolve, reject) => {
            const eventListener = (devices) => {
                window.bleState.eventBus.removeListener('DEVICE_LIST_UPDATED', eventListener);
                resolve(devices);
            };

            window.bleState.eventBus.on('DEVICE_LIST_UPDATED', eventListener);
            
            startScanning(options, window.bleState)
                .catch(error => {
                    window.bleState.eventBus.removeListener('DEVICE_LIST_UPDATED', eventListener);
                    reject(error);
                });
        });
    } catch (error) {
        logMessage(`Scan error: ${error.message}`, 'error');
        return [];
    }
}

// deviceCache is already imported at the top of the file

export { startScanning };
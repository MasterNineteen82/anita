import { logMessage, updateScanStatus, setLoading } from './ble-ui.js';
import { connectToDevice } from './ble-connection.js';

// Device cache
export const deviceCache = {
    devices: [],
    lastScanTime: null,
    
    addDevices(devices) {
        this.devices = devices;
        this.lastScanTime = new Date();
    },
    
    getDevices() {
        // Return devices only if the cache is less than 1 minute old
        if (this.lastScanTime && (new Date() - this.lastScanTime) < 60000) {
            return this.devices;
        }
        return [];
    },
    
    clear() {
        this.devices = [];
        this.lastScanTime = null;
    }
};

/**
 * Scan for nearby BLE devices
 * @param {Object} state - Application state
 * @param {Boolean} active - Whether to use active scanning
 * @param {Boolean} useCache - Whether to use cached devices
 * @returns {Promise<Array>} - Found devices
 */
export async function scanDevices(state, active = true, useCache = true) {
    const { deviceList } = state.domElements;
    if (!deviceList) {
        throw new Error("Device list element not found");
    }

    // Check if we have a valid cache first
    if (useCache) {
        const cachedDevices = deviceCache.getDevices();
        if (cachedDevices && cachedDevices.length > 0) {
            logMessage('Using cached device list', 'info');
            displayDevices(state, cachedDevices);
            return cachedDevices;
        }
    }

    try {
        logMessage(`Starting BLE scan (${active ? 'active' : 'passive'} mode)...`, 'info');
        updateScanStatus(state, 'scanning', `Scanning (${active ? 'active' : 'passive'})...`);
        setLoading(state, true, 'Scanning for devices...');
        deviceList.innerHTML = '<div class="text-gray-500 animate-pulse">Scanning for devices...</div>';

        const scanTime = 5;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000); // Increased timeout for scanning
        
        // Add timestamp to prevent caching
        const timestamp = new Date().getTime();
        const response = await fetch(`/api/ble/scan?scan_time=${scanTime}&active=${active}&_=${timestamp}`, { 
            signal: controller.signal,
            headers: { 
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Scan failed: ${response.status} - ${errorText}`);
        }

        // Get response as text first for debugging
        const responseText = await response.text();
        
        // Log raw response for debugging
        console.log("Raw scan response:", responseText);
        
        // Parse JSON after logging
        let devices;
        try {
            devices = JSON.parse(responseText);
        } catch (jsonError) {
            console.error("JSON parse error:", jsonError);
            logMessage(`Error parsing scan results: ${jsonError.message}`, 'error');
            throw new Error(`Failed to parse scan results: ${jsonError.message}`);
        }

        // Debug log the parsed devices
        console.log("Parsed devices:", devices);

        if (!devices || !Array.isArray(devices) || devices.length === 0) {
            deviceList.innerHTML = '<div class="text-gray-500">No devices found.</div>';
            logMessage('No devices found during scan', 'warning');
            updateScanStatus(state, 'complete', 'No devices found');
            return [];
        }

        logMessage(`Found ${devices.length} devices`, 'success');
        updateScanStatus(state, 'complete', `${devices.length} devices found`);

        // Display devices in UI
        displayDevices(state, devices);

        // Cache the devices we found
        deviceCache.addDevices(devices);
        return devices;
    } catch (error) {
        console.error('Scan error:', error);
        logMessage(`Scan failed: ${error.message}`, 'error');
        updateScanStatus(state, 'error', 'Scan failed');
        
        // Show more detailed error in the device list
        deviceList.innerHTML = `
            <div class="text-red-500">Scan failed: ${error.message}</div>
            <button id="retry-scan" class="mt-2 bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm">
                Retry Scan
            </button>
        `;
        
        const retryButton = document.getElementById('retry-scan');
        if (retryButton) {
            retryButton.addEventListener('click', () => {
                logMessage('Retrying scan...', 'info');
                scanDevicesWithErrorHandling(state, active, false); // Don't use cache on retry
            });
        }
        
        return [];
    } finally {
        setLoading(state, false);
    }
}

/**
 * Display devices in the UI
 * @param {Object} state - Application state
 * @param {Array} devices - List of devices to display
 */
function displayDevices(state, devices) {
    const { deviceList } = state.domElements;
    if (!deviceList) return;

    deviceList.innerHTML = '';

    if (devices.length === 0) {
        deviceList.innerHTML = '<div class="text-gray-500">No devices found.</div>';
        return;
    }

    devices.forEach(device => {
        if (!device || !device.address) {
            console.warn("Invalid device data:", device);
            return; // Skip invalid devices
        }
        
        const deviceEl = document.createElement('div');
        deviceEl.className = 'bg-gray-800 p-3 rounded mb-2 hover:bg-gray-700 transition-colors';
        
        // Handle potentially missing name safely
        const name = device.name || 'Unknown Device';
        
        // Generate signal strength icon based on RSSI
        const rssi = typeof device.rssi === 'number' ? device.rssi : -100;
        const signalIcon = getSignalStrengthIcon(rssi);
        
        deviceEl.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex-grow">
                    <div class="font-medium text-white">${name}</div>
                    <div class="text-xs text-gray-400">${device.address}</div>
                    <div class="flex items-center mt-2">
                        ${signalIcon}
                        <span class="text-xs text-gray-400 ml-2">RSSI: ${rssi} dBm</span>
                    </div>
                </div>
                <div class="flex flex-col space-y-2">
                    ${device.bonded ? '<span class="text-center bg-blue-600 text-xs px-2 py-1 rounded">Paired</span>' : ''}
                    <button class="connect-btn bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                        Connect
                    </button>
                </div>
            </div>
        `;
        deviceList.appendChild(deviceEl);
        
        // Add connect button event listener
        const connectBtn = deviceEl.querySelector('.connect-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => {
                connectToDevice(state, device.address, name)
                    .catch(error => {
                        logMessage(`Connection error: ${error.message}`, 'error');
                    });
            });
        }
    });
}

/**
 * Get signal strength icon based on RSSI value
 * @param {Number} rssi - RSSI value in dBm
 * @returns {String} - HTML for signal strength icon
 */
function getSignalStrengthIcon(rssi) {
    // Determine icon and color based on signal strength
    let iconClass, colorClass;
    
    if (rssi >= -60) {
        iconClass = 'fa-signal';
        colorClass = 'text-green-500';
    } else if (rssi >= -75) {
        iconClass = 'fa-signal';
        colorClass = 'text-yellow-500';
    } else if (rssi >= -85) {
        iconClass = 'fa-signal';
        colorClass = 'text-orange-500';
    } else {
        iconClass = 'fa-signal';
        colorClass = 'text-red-500';
    }
    
    return `
    <div class="flex flex-col items-center">
        <i class="fas ${iconClass} ${colorClass} text-lg" aria-hidden="true"></i>
        <span class="text-xs ${colorClass} mt-1">
            ${rssi >= -60 ? 'Strong' : rssi >= -75 ? 'Good' : rssi >= -85 ? 'Fair' : 'Weak'}
        </span>
    </div>`;
}

/**
 * Wrapper for scanDevices with error handling
 * @param {Object} state - Application state
 * @param {Boolean} active - Whether to use active scanning
 * @param {Boolean} useCache - Whether to use cached devices
 * @returns {Promise<Array>} - Found devices
 */
export async function scanDevicesWithErrorHandling(state, active = true, useCache = true) {
    try {
        if (state.scanningActive) {
            logMessage('Scan already in progress', 'warning');
            return [];
        }
        
        state.scanningActive = true;
        const scanBtn = state.domElements.scanBtn;
        if (scanBtn) {
            scanBtn.disabled = true;
            scanBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
        }
        
        const devices = await scanDevices(state, active, useCache);
        return devices;
    } catch (error) {
        logMessage(`Scan error: ${error.message}`, 'error');
        return [];
    } finally {
        state.scanningActive = false;
        const scanBtn = state.domElements.scanBtn;
        if (scanBtn) {
            scanBtn.disabled = false;
            scanBtn.innerHTML = '<i class="fas fa-search"></i> Scan for Devices';
        }
    }
}

/**
 * Perform power-efficient scan (passive scan)
 * @param {Object} state - Application state
 * @returns {Promise<Array>} - Found devices
 */
export async function powerEfficientScan(state) {
    return scanDevicesWithErrorHandling(state, false, false);
}
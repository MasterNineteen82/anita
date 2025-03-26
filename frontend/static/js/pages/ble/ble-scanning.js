import { logMessage, updateScanStatus, setLoading } from './ble-ui.js';
import { connectToDevice } from './ble-connection.js';

// Add a device cache with time-based expiration
const deviceCache = {
    devices: {},
    timestamp: null,
    cacheDuration: 30000, // 30 seconds
    
    addDevices(devices) {
        this.devices = devices.reduce((cache, device) => {
            cache[device.address] = device;
            return cache;
        }, {});
        this.timestamp = Date.now();
    },
    
    getDevices() {
        if (this.timestamp && (Date.now() - this.timestamp < this.cacheDuration)) {
            return Object.values(this.devices);
        }
        return null; // Cache expired or empty
    },
    
    clear() {
        this.devices = {};
        this.timestamp = null;
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
        if (cachedDevices) {
            logMessage('Using cached device list', 'info');
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
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const response = await fetch(`/api/ble/scan?scan_time=${scanTime}&active=${active}`, { signal: controller.signal });
        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Scan failed: ${errorText}`);
        }

        const devices = await response.json();
        if (devices.length === 0) {
            deviceList.innerHTML = '<div class="text-gray-500">No devices found.</div>';
            logMessage('No devices found during scan', 'warning');
            updateScanStatus(state, 'complete', 'No devices found');
            return [];
        }

        logMessage(`Found ${devices.length} devices`, 'success');
        updateScanStatus(state, 'complete', `${devices.length} devices found`);
        deviceList.innerHTML = '';

        devices.forEach(device => {
            const deviceEl = document.createElement('div');
            deviceEl.className = 'bg-gray-800 p-3 rounded mb-2 hover:bg-gray-700 transition-colors';
            const name = device.name || 'Unknown Device';
            deviceEl.innerHTML = `
                <div class="flex items-center justify-between">
                    <div>
                        <div class="font-medium text-white">${name}</div>
                        <div class="text-xs text-gray-400">${device.address}</div>
                        <div class="text-xs text-gray-400 mt-1">RSSI: ${device.rssi || 'N/A'}</div>
                    </div>
                    <button class="connect-btn bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
                            data-address="${device.address}" data-name="${name}">
                        Connect
                    </button>
                </div>
            `;
            deviceList.appendChild(deviceEl);
        });

        document.querySelectorAll('.connect-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const address = e.target.dataset.address;
                const name = e.target.dataset.name;
                connectToDevice(state, address, name);
            });
        });

        // Add successful results to cache
        deviceCache.addDevices(devices);
        return devices;
    } catch (error) {
        console.error('Scan error:', error);
        logMessage(`Scan failed: ${error.message}`, 'error');
        updateScanStatus(state, 'error', 'Scan failed');
        deviceList.innerHTML = `
            <div class="text-red-500">Scan failed: ${error.message}</div>
            <button id="retry-scan" class="mt-2 bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm">
                Retry Scan
            </button>
        `;
        const retryButton = document.getElementById('retry-scan');
        if (retryButton) {
            retryButton.addEventListener('click', () => scanDevicesWithErrorHandling(state, active));
        }
    } finally {
        setLoading(state, false);
    }
}

/**
 * Scan for devices with error handling
 * @param {Object} state - Application state
 * @param {Boolean} active - Whether to use active scanning
 */
export async function scanDevicesWithErrorHandling(state, active = true) {
    try {
        await scanDevices(state, active);
    } catch (error) {
        console.error("Scan handled error:", error);
    }
}
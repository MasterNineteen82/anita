import { logMessage } from './ble-ui.js';

/**
 * Setup click handlers for device selection.
 */
export function setupDeviceClickHandlers() {
    document.addEventListener('click', function(event) {
        // Check if the clicked element is a connect button
        if (event.target.classList.contains('connect-btn')) {
            const deviceCard = event.target.closest('.device-card');
            if (deviceCard) {
                // Get all text-xs elements (should include address)
                const textElements = deviceCard.querySelectorAll('.text-xs.text-gray-400');
                
                // The address is in the first text-xs element
                if (textElements.length > 0) {
                    const address = textElements[0].textContent.trim();
                    
                    // Find the device in the cache
                    const device = deviceCache.getDevice(address);
                    if (device) {
                        emitDeviceSelected(device);
                    }
                }
            }
        }
    });
}

/**
 * Initialize the device list component.
 */
export function initializeDeviceList(state) {
    const deviceListContainer = document.getElementById('devices-list');
    if (!deviceListContainer) {
        console.warn('Device list container not found');
        return;
    }

    // Initial display message
    deviceListContainer.innerHTML = '<div class="text-center py-4 text-gray-500">No devices found.</div>';

    // Setup device selection handlers
    setupDeviceClickHandlers();

    logMessage('Device list initialized', 'info');
}

/**
 * Emit a device selected event.
 * @param {Object} device - The selected device.
 */
export function emitDeviceSelected(device) {
    const event = new CustomEvent('ble-device-selected', { detail: { device } });
    document.dispatchEvent(event);
}

/**
 * Display the list of scanned devices.
 * @param {Object} state - The global BLE state object.
 * @param {Array} devices - The array of scanned devices.
 */
export function displayDevices(state, devices) {
    const deviceListContainer = document.getElementById('devices-list');
    if (!deviceListContainer) {
        console.warn('Device list container not found in DOM');
        return;
    }

    // Clear existing list
    deviceListContainer.innerHTML = '';

    if (devices.length === 0) {
        deviceListContainer.innerHTML = '<div class="text-center py-4 text-gray-500">No devices found.</div>';
        return;
    }

    devices.forEach(device => {
        // Create device element
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

        deviceListContainer.appendChild(deviceEl);
    });
}

/**
 * Update the device list with devices received from the server
 * @param {Array} devices - Array of device objects
 */
export function updateDeviceList(devices) {
    const deviceListContainer = document.getElementById('devices-list');
    if (!deviceListContainer) {
        console.error('Device list container not found in DOM');
        return;
    }

    // Clear current list
    deviceListContainer.innerHTML = '';
    
    // Add devices to cache
    deviceCache.addDevices(devices);
    
    if (devices.length === 0) {
        deviceListContainer.innerHTML = '<div class="text-gray-500">No devices found.</div>';
        return;
    }

    // Create device elements
    devices.forEach(device => {
        // Create device element
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

        // Add click event handler to connect button
        const connectBtn = deviceEl.querySelector('.connect-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => {
                window.dispatchEvent(new CustomEvent('CONNECT_TO_DEVICE', {
                    detail: { 
                        address: device.address,
                        name: device.name || 'Unknown Device'
                    }
                }));
            });
        }

        deviceListContainer.appendChild(deviceEl);
    });
}

export const deviceCache = {
    devices: new Map(),

    addDevice(device) {
        this.devices.set(device.address, device);
    },

    addDevices(devices) {
        devices.forEach(device => this.addDevice(device));
    },

    getDevice(address) {
        return this.devices.get(address);
    },

    getAllDevices() {
        return Array.from(this.devices.values());
    },

    clear() {
        this.devices.clear();
    }
};

/**
 * Filter devices based on specified criteria.
 * @param {Array} devices - List of devices to filter
 * @param {Object} filters - Filter criteria
 * @returns {Array} - Filtered devices
 */
export function filterDeviceList(devices, filters = {}) {
    if (!filters || Object.keys(filters).length === 0) {
        return devices;
    }

    return devices.filter(device => {
        let matches = true;
        
        // Filter by name
        if (filters.name && device.name) {
            matches = matches && device.name.toLowerCase().includes(filters.name.toLowerCase());
        }
        
        // Filter by signal strength (RSSI)
        if (filters.minRssi !== undefined) {
            matches = matches && device.rssi >= filters.minRssi;
        }
        
        // Filter by favorite status
        if (filters.favoritesOnly && filters.favorites) {
            matches = matches && filters.favorites.includes(device.address);
        }
        
        return matches;
    });
}

/**
 * Sort devices based on criteria.
 * @param {Array} devices - Devices to sort
 * @param {string} sortBy - Sorting criteria ('name', 'rssi', etc.)
 * @param {boolean} ascending - Sort direction
 * @returns {Array} - Sorted devices
 */
export function sortDeviceList(devices, sortBy = 'rssi', ascending = false) {
    return [...devices].sort((a, b) => {
        let comparison = 0;
        
        switch (sortBy) {
            case 'name':
                const nameA = (a.name || 'Unknown Device').toLowerCase();
                const nameB = (b.name || 'Unknown Device').toLowerCase();
                comparison = nameA.localeCompare(nameB);
                break;
            case 'rssi':
                comparison = b.rssi - a.rssi;
                break;
            case 'favorite':
                const favorites = loadDeviceFilters().favorites || [];
                const aIsFavorite = favorites.includes(a.address);
                const bIsFavorite = favorites.includes(b.address);
                comparison = bIsFavorite - aIsFavorite;
                break;
            default:
                comparison = 0;
        }
        
        return ascending ? -comparison : comparison;
    });
}

/**
 * Refresh the device list with current devices from cache.
 */
export function refreshDeviceList(filters = null, sortBy = 'rssi', ascending = false) {
    const allDevices = deviceCache.getAllDevices();
    const filteredDevices = filters ? filterDeviceList(allDevices, filters) : allDevices;
    const sortedDevices = sortDeviceList(filteredDevices, sortBy, ascending);
    updateDeviceList(sortedDevices);
}

/**
 * Save device filters to localStorage.
 * @param {Object} filters - Filter settings to save
 */
export function saveDeviceFilters(filters) {
    localStorage.setItem('bleDeviceFilters', JSON.stringify(filters));
}

/**
 * Load device filters from localStorage.
 * @returns {Object} - Saved filter settings
 */
export function loadDeviceFilters() {
    const filtersJson = localStorage.getItem('bleDeviceFilters');
    return filtersJson ? JSON.parse(filtersJson) : {
        name: '',
        minRssi: -100,
        favoritesOnly: false,
        favorites: [],
        sortBy: 'rssi',
        ascending: false
    };
}

/**
 * Get filtered devices based on current filters.
 * @returns {Array} - Filtered and sorted device list
 */
export function getFilteredDevices() {
    const allDevices = deviceCache.getAllDevices();
    const filters = loadDeviceFilters();
    const filteredDevices = filterDeviceList(allDevices, filters);
    return sortDeviceList(filteredDevices, filters.sortBy, filters.ascending);
}

/**
 * Mark or unmark a device as favorite.
 * @param {string} address - Device address
 * @param {boolean} isFavorite - Whether the device should be marked as favorite
 */
export function markFavoriteDevice(address, isFavorite = true) {
    const filters = loadDeviceFilters();
    const favorites = filters.favorites || [];
    
    if (isFavorite && !favorites.includes(address)) {
        favorites.push(address);
    } else if (!isFavorite && favorites.includes(address)) {
        const index = favorites.indexOf(address);
        favorites.splice(index, 1);
    }
    
    filters.favorites = favorites;
    saveDeviceFilters(filters);
    refreshDeviceList(filters, filters.sortBy, filters.ascending);
}

/**
 * Clear the device list display and optionally the cache.
 * @param {boolean} clearCache - Whether to also clear the device cache
 */
export function clearDeviceList(clearCache = true) {
    const deviceListContainer = document.getElementById('devices-list');
    if (deviceListContainer) {
        deviceListContainer.innerHTML = '<div class="text-center py-4 text-gray-500">No devices found.</div>';
    }
    
    if (clearCache) {
        deviceCache.clear();
    }
    
    logMessage('Device list cleared', 'info');
}

/**
 * Get a device by its address.
 * @param {string} address - The device address
 * @returns {Object|null} - The found device or null
 */
export function getDeviceById(address) {
    return deviceCache.getDevice(address);
}
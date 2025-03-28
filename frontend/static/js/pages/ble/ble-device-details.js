import { logMessage } from './ble-ui.js';

// Store the currently selected device
let currentDevice = null;
// Track connection state
let isConnected = false;
// Store discovered services and characteristics
let deviceServices = [];

/**
 * Initialize device details component
 * @param {Object} state - Global BLE state
 */
export function initializeDeviceDetails(state) {
    const container = document.getElementById('device-details-container');
    if (!container) return;
    
    // Show default state
    showEmptyState(container);
    
    // Listen for device selection events
    document.addEventListener('ble-device-selected', (event) => {
        currentDevice = event.detail.device;
        showDeviceDetails(container, currentDevice);
    });
}

/**
 * Show empty state when no device is selected
 * @param {HTMLElement} container - Container element
 */
export function showEmptyState(container) {
    container.innerHTML = `
        <div class="text-center text-gray-500 py-12">
            <i class="fas fa-bluetooth text-4xl mb-3"></i>
            <p>No device selected</p>
            <p class="text-xs mt-1">Scan for and select a device to view details</p>
        </div>
    `;
}

/**
 * Show details for the selected device
 * @param {HTMLElement} container - Container element
 * @param {Object} device - Selected device
 */
export function showDeviceDetails(container, device) {
    if (!device) {
        showEmptyState(container);
        return;
    }
    
    // Format device name
    const name = device.name || 'Unknown Device';
    
    // Calculate signal strength class
    let signalClass = 'text-red-500';
    if (device.rssi > -70) signalClass = 'text-green-500';
    else if (device.rssi > -85) signalClass = 'text-yellow-500';
    
    // Format signal strength icon
    let signalIcon = 'fa-signal-slash';
    if (device.rssi > -90) signalIcon = 'fa-signal-weak';
    if (device.rssi > -80) signalIcon = 'fa-signal-fair';
    if (device.rssi > -70) signalIcon = 'fa-signal-good';
    if (device.rssi > -60) signalIcon = 'fa-signal-strong';
    
    // Get advertising data if available
    const advData = device.advertising_data || {};
    
    container.innerHTML = `
        <div class="space-y-4">
            <!-- Header with device info and connection controls -->
            <div class="bg-gray-800 p-3 rounded-md border border-gray-700">
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="text-lg font-semibold">${name}</h3>
                        <div class="text-sm font-mono text-gray-400">${device.address}</div>
                    </div>
                    <div class="text-right">
                        <div class="${signalClass} flex items-center justify-end">
                            <i class="fas ${signalIcon} mr-1"></i>
                            ${device.rssi} dBm
                        </div>
                        <div class="text-xs text-gray-500 mt-1">
                            Last seen: ${new Date(device.lastSeen).toLocaleTimeString()}
                        </div>
                    </div>
                </div>
                
                <!-- Connection buttons -->
                <div class="flex mt-3 space-x-2">
                    <button id="connect-btn" class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded flex-1 flex items-center justify-center">
                        <i class="fas fa-plug mr-1"></i> Connect
                    </button>
                    <button id="disconnect-btn" class="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded flex-1 flex items-center justify-center" disabled>
                        <i class="fas fa-times mr-1"></i> Disconnect
                    </button>
                </div>
            </div>
            
            <!-- Device info tabs -->
            <div class="border-b border-gray-700">
                <nav class="flex -mb-px">
                    <button class="tab-button tab-active px-3 py-2 text-sm font-medium" data-tab="info">
                        <i class="fas fa-info-circle mr-1"></i> Basic Info
                    </button>
                    <button class="tab-button px-3 py-2 text-sm font-medium" data-tab="services">
                        <i class="fas fa-server mr-1"></i> Services
                    </button>
                    <button class="tab-button px-3 py-2 text-sm font-medium" data-tab="characteristics">
                        <i class="fas fa-list mr-1"></i> Characteristics
                    </button>
                    <button class="tab-button px-3 py-2 text-sm font-medium" data-tab="console">
                        <i class="fas fa-terminal mr-1"></i> Console
                    </button>
                </nav>
            </div>
            
            <!-- Tab content -->
            <div class="tab-content" id="tab-info">
                <div class="bg-gray-800 p-3 rounded-md border border-gray-700">
                    <h4 class="text-sm font-semibold mb-2">Device Information</h4>
                    <div class="grid grid-cols-2 gap-1 text-sm">
                        <div class="text-gray-400">Name:</div>
                        <div>${name}</div>
                        
                        <div class="text-gray-400">Address:</div>
                        <div class="font-mono">${device.address}</div>
                        
                        <div class="text-gray-400">Signal Strength:</div>
                        <div class="${signalClass}">${device.rssi} dBm</div>
                        
                        <div class="text-gray-400">Address Type:</div>
                        <div>${device.address_type || 'Unknown'}</div>
                        
                        <div class="text-gray-400">Connectable:</div>
                        <div>${device.connectable === true ? 
                            '<span class="text-green-400">Yes</span>' : 
                            (device.connectable === false ? 
                                '<span class="text-red-400">No</span>' : 
                                '<span class="text-gray-500">Unknown</span>')}</div>
                    </div>
                    
                    ${generateAdvertisingDataHTML(advData)}
                </div>
            </div>
            
            <div class="tab-content hidden" id="tab-services">
                <div id="services-container" class="bg-gray-800 p-3 rounded-md border border-gray-700">
                    <div class="flex items-center justify-between mb-2">
                        <h4 class="text-sm font-semibold">GATT Services</h4>
                        <button id="discover-services-btn" class="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded flex items-center" disabled>
                            <i class="fas fa-sync mr-1"></i> Discover
                        </button>
                    </div>
                    <div class="text-center text-gray-500 py-6">
                        <p>Not connected to device</p>
                        <p class="text-xs mt-1">Connect to discover services</p>
                    </div>
                </div>
            </div>
            
            <div class="tab-content hidden" id="tab-characteristics">
                <div id="characteristics-container" class="bg-gray-800 p-3 rounded-md border border-gray-700">
                    <div class="flex items-center justify-between mb-2">
                        <h4 class="text-sm font-semibold">Characteristics</h4>
                    </div>
                    <div class="text-center text-gray-500 py-6">
                        <p>No service selected</p>
                        <p class="text-xs mt-1">Select a service to view characteristics</p>
                    </div>
                </div>
            </div>
            
            <div class="tab-content hidden" id="tab-console">
                <div class="bg-gray-800 p-3 rounded-md border border-gray-700">
                    <div class="flex items-center justify-between mb-2">
                        <h4 class="text-sm font-semibold">Console</h4>
                        <button id="clear-console-btn" class="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-white text-xs rounded flex items-center">
                            <i class="fas fa-trash mr-1"></i> Clear
                        </button>
                    </div>
                    <div id="device-console" class="bg-gray-900 p-2 rounded font-mono text-xs h-48 overflow-y-auto">
                        <div class="text-gray-500">// Device console initialized</div>
                        <div class="text-gray-500">// Connect to device to interact with characteristics</div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Update page title with device name
    const deviceNameElement = document.getElementById('device-name');
    if (deviceNameElement) {
        deviceNameElement.textContent = name;
    }
    
    // Add event listeners
    setupDeviceDetailsEventListeners(container, device);
}

/**
 * Generate HTML for advertising data
 * @param {Object} advData - Advertising data
 * @returns {string} - HTML string
 */
export function generateAdvertisingDataHTML(advData) {
    if (!advData || Object.keys(advData).length === 0) {
        return '';
    }
    
    let html = `
        <div class="mt-3 pt-3 border-t border-gray-700">
            <h4 class="text-sm font-semibold mb-2">Advertising Data</h4>
            <div class="grid grid-cols-2 gap-1 text-sm">
    `;
    
    // Manufacturer data
    if (advData.manufacturer_data) {
        const manufacturerData = advData.manufacturer_data;
        html += `
            <div class="text-gray-400">Manufacturer:</div>
            <div>${getManufacturerName(manufacturerData.company_id)} (0x${manufacturerData.company_id.toString(16).padStart(4, '0')})</div>
            
            <div class="text-gray-400">Data:</div>
            <div class="font-mono text-xs overflow-x-auto">${formatHexData(manufacturerData.data)}</div>
        `;
    }
    
    // Service UUIDs
    if (advData.service_uuids && advData.service_uuids.length) {
        html += `
            <div class="text-gray-400">Service UUIDs:</div>
            <div>
                ${advData.service_uuids.map(uuid => 
                    `<div class="font-mono text-xs">${uuid} <span class="text-gray-500">(${getServiceNameByUuid(uuid)})</span></div>`
                ).join('')}
            </div>
        `;
    }
    
    // Service data
    if (advData.service_data && Object.keys(advData.service_data).length) {
        html += `
            <div class="text-gray-400">Service Data:</div>
            <div>
                ${Object.entries(advData.service_data).map(([uuid, data]) => 
                    `<div class="font-mono text-xs">${uuid}: ${formatHexData(data)}</div>`
                ).join('')}
            </div>
        `;
    }
    
    // Flags and other fields
    if (advData.flags && advData.flags.length) {
        html += `
            <div class="text-gray-400">Flags:</div>
            <div>${advData.flags.map(flag => `<span class="text-xs bg-gray-700 px-1 py-0.5 rounded mr-1">${flag}</span>`).join('')}</div>
        `;
    }
    
    // TX Power
    if (advData.tx_power !== undefined) {
        html += `
            <div class="text-gray-400">TX Power:</div>
            <div>${advData.tx_power} dBm</div>
        `;
    }
    
    html += `
            </div>
        </div>
    `;
    
    return html;
}

/**
 * Format hex data for display
 * @param {Uint8Array|Array} data - Binary data
 * @returns {string} - Formatted hex string
 */
export function formatHexData(data) {
    if (!data) return 'No data';
    
    // Convert to array if it's a Uint8Array
    const arr = Array.from(data);
    
    // Format as hex
    const hexStr = arr.map(b => b.toString(16).padStart(2, '0').toUpperCase()).join(' ');
    
    // Also show as ASCII if printable
    const asciiStr = arr.map(b => {
        if (b >= 32 && b <= 126) {
            return String.fromCharCode(b);
        }
        return '.';
    }).join('');
    
    return `${hexStr} <span class="text-gray-500">${asciiStr}</span>`;
}

/**
 * Look up manufacturer name from company ID
 * @param {number} id - Company ID
 * @returns {string} - Manufacturer name
 */
export function getManufacturerName(id) {
    // Common Bluetooth manufacturer IDs
    const manufacturers = {
        0x0000: 'Ericsson',
        0x0001: 'Nokia',
        0x0002: 'Intel',
        0x0003: 'IBM',
        0x0004: 'Toshiba',
        0x0005: '3Com',
        0x0006: 'Microsoft',
        0x0007: 'Lucent',
        0x000A: 'Motorola',
        0x000C: 'Cambridge Silicon Radio',
        0x000F: 'Broadcom',
        0x0010: 'Mitel',
        0x0075: 'Samsung',
        0x004C: 'Apple',
        0x008A: 'Google',
        0x0199: 'Nordic Semiconductor',
        0x01FF: 'Silicon Labs',
        0x02F0: 'Xiaomi',
        0x03C0: 'Fitbit',
        0x038F: 'Amazfit',
        0x0499: 'Ruuvi Innovations'
    };
    
    return manufacturers[id] || 'Unknown';
}

/**
 * Get service name by UUID
 * @param {string} uuid - Service UUID
 * @returns {string} - Service name
 */
export function getServiceNameByUuid(uuid) {
    // Common BLE service UUIDs
    const services = {
        '1800': 'Generic Access',
        '1801': 'Generic Attribute',
        '1802': 'Immediate Alert',
        '1803': 'Link Loss',
        '1804': 'Tx Power',
        '1805': 'Current Time',
        '1806': 'Reference Time Update',
        '1807': 'Next DST Change',
        '1808': 'Glucose',
        '1809': 'Health Thermometer',
        '180A': 'Device Information',
        '180D': 'Heart Rate',
        '180E': 'Phone Alert Status',
        '180F': 'Battery',
        '1810': 'Blood Pressure',
        '1811': 'Alert Notification',
        '1812': 'Human Interface Device',
        '1813': 'Scan Parameters',
        '1814': 'Running Speed and Cadence',
        '1815': 'Automation IO',
        '1816': 'Cycling Speed and Cadence',
        '1818': 'Cycling Power',
        '1819': 'Location and Navigation',
        '181A': 'Environmental Sensing',
        '181B': 'Body Composition',
        '181C': 'User Data',
        '181D': 'Weight Scale',
        '181E': 'Bond Management',
        '181F': 'Continuous Glucose Monitoring',
        '1820': 'Internet Protocol Support',
        '1821': 'Indoor Positioning',
        '1822': 'Pulse Oximeter',
        '1823': 'HTTP Proxy',
        '1824': 'Transport Discovery',
        '1825': 'Object Transfer',
        '1826': 'Fitness Machine',
        '1827': 'Mesh Provisioning',
        '1828': 'Mesh Proxy',
        '1829': 'Reconnection Configuration'
    };
    
    // Strip out any dashes and get the 16-bit UUID portion
    const shortUuid = uuid.replace(/-/g, '').slice(-4).toUpperCase();
    
    return services[shortUuid] || 'Unknown Service';
}

/**
 * Set up event listeners for device details UI
 * @param {HTMLElement} container - Container element
 * @param {Object} device - Device object
 */
export function setupDeviceDetailsEventListeners(container, device) {
    // Tab navigation
    const tabButtons = container.querySelectorAll('.tab-button');
    const tabContents = container.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons
            tabButtons.forEach(btn => btn.classList.remove('tab-active'));
            // Add active class to clicked button
            button.classList.add('tab-active');
            
            // Hide all tab contents
            tabContents.forEach(content => content.classList.add('hidden'));
            // Show selected tab content
            const tabId = `tab-${button.dataset.tab}`;
            document.getElementById(tabId).classList.remove('hidden');
        });
    });
    
    // Connect button
    const connectBtn = container.querySelector('#connect-btn');
    const disconnectBtn = container.querySelector('#disconnect-btn');
    const discoverServicesBtn = container.querySelector('#discover-services-btn');
    
    if (connectBtn) {
        connectBtn.addEventListener('click', async () => {
            if (isConnected) return;
            
            try {
                connectBtn.disabled = true;
                connectBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Connecting...';
                
                // Log connection attempt
                logToDeviceConsole(`Connecting to ${device.name || 'device'} (${device.address})...`);
                
                // Call API to connect
                const response = await fetch(`/api/ble/connect/${device.address}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        timeout: 15,
                        auto_reconnect: true
                    })
                });
                
                if (!response.ok) {
                    const error = await response.text();
                    throw new Error(`Connection failed: ${error}`);
                }
                
                const result = await response.json();
                
                // Update UI for connected state
                isConnected = true;
                connectBtn.disabled = true;
                disconnectBtn.disabled = false;
                discoverServicesBtn.disabled = false;
                
                // Log success
                logToDeviceConsole(`Connected successfully to ${device.name || 'device'}`);
                
                // Automatically discover services
                await discoverServices(device);
                
            } catch (error) {
                logToDeviceConsole(`Error: ${error.message}`, 'error');
                console.error('Connection error:', error);
                
                connectBtn.disabled = false;
                connectBtn.innerHTML = '<i class="fas fa-plug mr-1"></i> Connect';
            }
        });
    }
    
    // Disconnect button
    if (disconnectBtn) {
        disconnectBtn.addEventListener('click', async () => {
            if (!isConnected) return;
            
            try {
                disconnectBtn.disabled = true;
                disconnectBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Disconnecting...';
                
                // Log disconnection attempt
                logToDeviceConsole(`Disconnecting from ${device.name || 'device'}...`);
                
                // Call API to disconnect
                const response = await fetch(`/api/ble/disconnect/${device.address}`, {
                    method: 'POST'
                });
                
                if (!response.ok) {
                    const error = await response.text();
                    throw new Error(`Disconnection failed: ${error}`);
                }
                
                // Update UI for disconnected state
                handleDisconnect();
                
                // Log success
                logToDeviceConsole(`Disconnected from ${device.name || 'device'}`);
                
            } catch (error) {
                logToDeviceConsole(`Error: ${error.message}`, 'error');
                console.error('Disconnection error:', error);
                
                disconnectBtn.disabled = false;
                disconnectBtn.innerHTML = '<i class="fas fa-times mr-1"></i> Disconnect';
            }
        });
    }
    
    // Discover services button
    if (discoverServicesBtn) {
        discoverServicesBtn.addEventListener('click', async () => {
            if (!isConnected) {
                logToDeviceConsole('Not connected to device', 'warning');
                return;
            }
            
            await discoverServices(device);
        });
    }
    
    // Clear console button
    const clearConsoleBtn = container.querySelector('#clear-console-btn');
    if (clearConsoleBtn) {
        clearConsoleBtn.addEventListener('click', () => {
            const consoleElement = document.getElementById('device-console');
            if (consoleElement) {
                consoleElement.innerHTML = '<div class="text-gray-500">// Console cleared</div>';
            }
        });
    }
}

/**
 * Handle device disconnection (both manual and automatic)
 */
export function handleDisconnect() {
    isConnected = false;
    
    // Update UI elements
    const connectBtn = document.getElementById('connect-btn');
    const disconnectBtn = document.getElementById('disconnect-btn');
    const discoverServicesBtn = document.getElementById('discover-services-btn');
    
    if (connectBtn) {
        connectBtn.disabled = false;
        connectBtn.innerHTML = '<i class="fas fa-plug mr-1"></i> Connect';
    }
    
    if (disconnectBtn) {
        disconnectBtn.disabled = true;
        disconnectBtn.innerHTML = '<i class="fas fa-times mr-1"></i> Disconnect';
    }
    
    if (discoverServicesBtn) {
        discoverServicesBtn.disabled = true;
    }
    
    // Reset services and characteristics
    deviceServices = [];
    
    // Update services container
    const servicesContainer = document.getElementById('services-container');
    if (servicesContainer) {
        servicesContainer.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <h4 class="text-sm font-semibold">GATT Services</h4>
                <button id="discover-services-btn" class="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded flex items-center" disabled>
                    <i class="fas fa-sync mr-1"></i> Discover
                </button>
            </div>
            <div class="text-center text-gray-500 py-6">
                <p>Not connected to device</p>
                <p class="text-xs mt-1">Connect to discover services</p>
            </div>
        `;
    }
    
    // Update characteristics container
    const characteristicsContainer = document.getElementById('characteristics-container');
    if (characteristicsContainer) {
        characteristicsContainer.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <h4 class="text-sm font-semibold">Characteristics</h4>
            </div>
            <div class="text-center text-gray-500 py-6">
                <p>No service selected</p>
                <p class="text-xs mt-1">Select a service to view characteristics</p>
            </div>
        `;
    }
}

/**
 * Discover services for the connected device
 * @param {Object} device - Device object
 */
export async function discoverServices(device) {
    if (!isConnected) {
        logToDeviceConsole('Cannot discover services: Not connected to device', 'warning');
        return;
    }
    
    const servicesContainer = document.getElementById('services-container');
    if (!servicesContainer) return;
    
    try {
        // Update UI to show loading
        servicesContainer.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <h4 class="text-sm font-semibold">GATT Services</h4>
                <button id="discover-services-btn" class="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded flex items-center" disabled>
                    <i class="fas fa-spinner fa-spin mr-1"></i> Discovering...
                </button>
            </div>
            <div class="text-center py-6">
                <div class="inline-block animate-pulse">
                    <i class="fas fa-circle-notch fa-spin text-blue-500 text-2xl"></i>
                </div>
                <p class="mt-2 text-sm">Discovering services...</p>
            </div>
        `;
        
        // Log discovery attempt
        logToDeviceConsole(`Discovering services for ${device.name || 'device'}...`);
        
        // Call API to discover services
        const response = await fetch(`/api/ble/services/${device.address}`, {
            method: 'GET'
        });
        
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Service discovery failed: ${error}`);
        }
        
        const services = await response.json();
        deviceServices = services;
        
        // Log discovery result
        logToDeviceConsole(`Discovered ${services.length} services`);
        
        // Render services UI
        renderServices(servicesContainer, services);
        
    } catch (error) {
        logToDeviceConsole(`Error: ${error.message}`, 'error');
        console.error('Service discovery error:', error);
        
        // Show error in UI
        servicesContainer.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <h4 class="text-sm font-semibold">GATT Services</h4>
                <button id="discover-services-btn" class="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded flex items-center">
                    <i class="fas fa-sync mr-1"></i> Retry
                </button>
            </div>
            <div class="bg-red-900 bg-opacity-30 text-red-400 p-3 rounded text-sm">
                <i class="fas fa-exclamation-triangle mr-1"></i>
                Failed to discover services: ${error.message}
            </div>
        `;
        
        // Re-add discover button listener
        const discoverServicesBtn = servicesContainer.querySelector('#discover-services-btn');
        if (discoverServicesBtn) {
            discoverServicesBtn.addEventListener('click', () => discoverServices(device));
        }
    }
}

/**
 * Render services list
 * @param {HTMLElement} container - Container element
 * @param {Array} services - Services array
 */
export function renderServices(container, services) {
    if (!services || services.length === 0) {
        container.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <h4 class="text-sm font-semibold">GATT Services</h4>
                <button id="discover-services-btn" class="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded flex items-center">
                    <i class="fas fa-sync mr-1"></i> Discover
                </button>
            </div>
            <div class="text-center text-gray-500 py-6">
                <p>No services found</p>
                <p class="text-xs mt-1">Device did not report any GATT services</p>
            </div>
        `;
        return;
    }
    
    // Start building HTML
    let html = `
        <div class="flex items-center justify-between mb-2">
            <h4 class="text-sm font-semibold">GATT Services (${services.length})</h4>
            <button id="discover-services-btn" class="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded flex items-center">
                <i class="fas fa-sync mr-1"></i> Refresh
            </button>
        </div>
        <div class="space-y-2">
    `;
    
    // Add each service
    services.forEach(service => {
        const serviceName = getServiceNameByUuid(service.uuid);
        const isPrimary = service.is_primary ? 'Primary' : 'Secondary';
        
        html += `
            <div class="service-item bg-gray-900 p-2 rounded border border-gray-800 hover:border-gray-700 cursor-pointer">
                <div class="flex justify-between items-start">
                    <div>
                        <div class="font-medium">${serviceName}</div>
                        <div class="font-mono text-xs text-gray-400">${service.uuid}</div>
                    </div>
                    <div class="text-xs bg-gray-800 px-1.5 py-0.5 rounded">
                        ${isPrimary}
                    </div>
                </div>
                <div class="text-xs text-gray-500 mt-1">
                    ${service.characteristics ? `${service.characteristics.length} characteristics` : 'Unknown characteristics'}
                </div>
                <div class="service-uuid hidden">${service.uuid}</div>
            </div>
        `;
    });
    
    html += `
        </div>
    `;
    
    // Update container
    container.innerHTML = html;
    
    // Add event listeners for service selection
    const serviceItems = container.querySelectorAll('.service-item');
    serviceItems.forEach(item => {
        item.addEventListener('click', () => {
            const uuid = item.querySelector('.service-uuid').textContent;
            const service = deviceServices.find(s => s.uuid === uuid);
            
            if (service) {
                // Select this service
                serviceItems.forEach(i => i.classList.remove('ring-2', 'ring-blue-500'));
                item.classList.add('ring-2', 'ring-blue-500');
                
                // Show characteristics for this service
                showServiceCharacteristics(service);
            }
        });
    });
    
    // Re-add discover button listener
    const discoverServicesBtn = container.querySelector('#discover-services-btn');
    if (discoverServicesBtn) {
        discoverServicesBtn.addEventListener('click', () => {
            if (currentDevice) {
                discoverServices(currentDevice);
            }
        });
    }
}

/**
 * Show characteristics for a selected service
 * @param {Object} service - Service object
 */
export function showServiceCharacteristics(service) {
    const container = document.getElementById('characteristics-container');
    if (!container) return;
    
    // Check if service has characteristics
    if (!service.characteristics || service.characteristics.length === 0) {
        container.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <h4 class="text-sm font-semibold">Characteristics</h4>
            </div>
            <div class="text-center text-gray-500 py-6">
                <p>No characteristics found</p>
                <p class="text-xs mt-1">Service does not have any characteristics</p>
            </div>
        `;
        return;
    }
    
    // Start building HTML
    let html = `
        <div class="flex items-center justify-between mb-2">
            <h4 class="text-sm font-semibold">Characteristics (${service.characteristics.length})</h4>
            <div class="text-xs text-gray-500">
                Service: ${getServiceNameByUuid(service.uuid)}
            </div>
        </div>
        <div class="space-y-3">
    `;
    
    // Add each characteristic
    service.characteristics.forEach(characteristic => {
        const uuid = characteristic.uuid;
        const properties = characteristic.properties || [];
        
        // Determine what operations are supported
        const canRead = properties.includes('read');
        const canWrite = properties.includes('write') || properties.includes('write-without-response');
        const canNotify = properties.includes('notify') || properties.includes('indicate');
        
        html += `
            <div class="bg-gray-900 p-2 rounded border border-gray-800">
                <div class="flex justify-between items-start">
                    <div>
                        <div class="font-medium">${getCharacteristicName(uuid)}</div>
                        <div class="font-mono text-xs text-gray-400">${uuid}</div>
                    </div>
                    <div>
                        ${canRead ? '<span class="text-xs bg-green-900 text-green-300 px-1.5 py-0.5 rounded mr-1">Read</span>' : ''}
                        ${canWrite ? '<span class="text-xs bg-blue-900 text-blue-300 px-1.5 py-0.5 rounded mr-1">Write</span>' : ''}
                        ${canNotify ? '<span class="text-xs bg-purple-900 text-purple-300 px-1.5 py-0.5 rounded">Notify</span>' : ''}
                    </div>
                </div>
                
                <!-- Properties badges -->
                <div class="flex flex-wrap gap-1 mt-1">
                    ${properties.map(prop => 
                        `<span class="text-xs bg-gray-800 px-1 py-0.5 rounded">${prop}</span>`
                    ).join('')}
                </div>
                
                <!-- Characteristic value and controls -->
                <div class="mt-2 pt-2 border-t border-gray-800">
                    <div class="flex items-center justify-between">
                        <div class="text-xs text-gray-400">Value:</div>
                        <div class="flex space-x-1">
                            ${canRead ? `<button class="read-btn text-xs bg-gray-800 hover:bg-gray-700 px-1.5 py-0.5 rounded" data-uuid="${uuid}">
                                <i class="fas fa-eye mr-0.5"></i> Read
                            </button>` : ''}
                            
                            ${canNotify ? `<button class="notify-btn text-xs bg-gray-800 hover:bg-gray-700 px-1.5 py-0.5 rounded" data-uuid="${uuid}">
                                <i class="fas fa-bell mr-0.5"></i> Subscribe
                            </button>` : ''}
                        </div>
                    </div>
                    
                    <div class="characteristic-value font-mono text-xs bg-gray-950 p-1 mt-1 rounded min-h-5">
                        <span class="text-gray-500">No data read yet</span>
                    </div>
                    
                    ${canWrite ? `
                    <div class="mt-2">
                        <div class="flex items-center justify-between">
                            <div class="text-xs text-gray-400">Write:</div>
                            <select class="write-type-select text-xs bg-gray-800 border border-gray-700 rounded px-1 py-0.5" data-uuid="${uuid}">
                                <option value="hex">Hex</option>
                                <option value="text">Text</option>
                                <option value="number">Number</option>
                            </select>
                        </div>
                        <div class="flex mt-1 space-x-1">
                            <input type="text" class="write-input text-xs bg-gray-950 border border-gray-800 rounded px-1 py-0.5 flex-1" placeholder="Enter value..." data-uuid="${uuid}">
                            <button class="write-btn text-xs bg-blue-800 hover:bg-blue-700 px-1.5 py-0.5 rounded" data-uuid="${uuid}">
                                <i class="fas fa-paper-plane mr-0.5"></i> Write
                            </button>
                        </div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    });
    
    html += `
        </div>
    `;
    
    // Update container
    container.innerHTML = html;
    
    // Add event listeners for characteristic operations
    setupCharacteristicEventListeners(container);
}

/**
 * Set up event listeners for characteristic operations
 * @param {HTMLElement} container - Container element
 */
export function setupCharacteristicEventListeners(container) {
    // Read buttons
    const readButtons = container.querySelectorAll('.read-btn');
    readButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const uuid = button.dataset.uuid;
            await readCharacteristic(uuid, button);
        });
    });
    
    // Write buttons
    const writeButtons = container.querySelectorAll('.write-btn');
    writeButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const uuid = button.dataset.uuid;
            const input = container.querySelector(`.write-input[data-uuid="${uuid}"]`);
            const typeSelect = container.querySelector(`.write-type-select[data-uuid="${uuid}"]`);
            
            if (input && typeSelect) {
                const value = input.value;
                const type = typeSelect.value;
                
                await writeCharacteristic(uuid, value, type, button);
            }
        });
    });
    
    // Notify buttons
    const notifyButtons = container.querySelectorAll('.notify-btn');
    notifyButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const uuid = button.dataset.uuid;
            
            // Toggle subscribe/unsubscribe
            if (button.classList.contains('subscribed')) {
                await unsubscribeNotifications(uuid, button);
            } else {
                await subscribeNotifications(uuid, button);
            }
        });
    });
}

/**
 * Read a characteristic value
 * @param {string} uuid - Characteristic UUID
 * @param {HTMLElement} button - Read button
 */
export async function readCharacteristic(uuid, button) {
    if (!currentDevice || !isConnected) {
        logToDeviceConsole('Cannot read characteristic: Not connected to device', 'warning');
        return;
    }
    
    try {
        // Update button state
        const originalButtonText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin mr-0.5"></i> Reading...';
        button.disabled = true;
        
        // Find the value display element
        const valueElement = button.closest('.bg-gray-900').querySelector('.characteristic-value');
        
        // Call API to read characteristic
        const response = await fetch(`/api/ble/read/${currentDevice.address}/${uuid}`, {
            method: 'GET'
        });
        
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Read failed: ${error}`);
        }
        
        const result = await response.json();
        
        // Display the value
        if (result.value && result.value.length > 0) {
            valueElement.innerHTML = formatCharacteristicValue(result.value);
            
            // Log to console
            logToDeviceConsole(`Read from ${uuid}: ${formatCharacteristicValue(result.value)}`);
        } else {
            valueElement.innerHTML = '<span class="text-gray-500">Empty value</span>';
            
            // Log to console
            logToDeviceConsole(`Read from ${uuid}: Empty value`);
        }
        
    } catch (error) {
        logToDeviceConsole(`Error reading characteristic ${uuid}: ${error.message}`, 'error');
        console.error('Read error:', error);
        
        // Show error in the value element
        const valueElement = button.closest('.bg-gray-900').querySelector('.characteristic-value');
        valueElement.innerHTML = `<span class="text-red-400">Error: ${error.message}</span>`;
        
    } finally {
        // Restore button state
        button.innerHTML = '<i class="fas fa-eye mr-0.5"></i> Read';
        button.disabled = false;
    }
}

/**
 * Write a value to a characteristic
 * @param {string} uuid - Characteristic UUID
 * @param {string} value - Value to write
 * @param {string} type - Value type (hex, text, number)
 * @param {HTMLElement} button - Write button
 */
export async function writeCharacteristic(uuid, value, type, button) {
    if (!currentDevice || !isConnected) {
        logToDeviceConsole('Cannot write characteristic: Not connected to device', 'warning');
        return;
    }
    
    if (!value) {
        logToDeviceConsole('Cannot write empty value', 'warning');
        return;
    }
    
    try {
        // Update button state
        const originalButtonText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin mr-0.5"></i> Writing...';
        button.disabled = true;
        
        // Convert value based on type
        let convertedValue;
        let display = value;
        
        if (type === 'hex') {
            // Convert hex string to byte array
            convertedValue = [];
            const hexString = value.replace(/\s/g, '');
            
            for (let i = 0; i < hexString.length; i += 2) {
                convertedValue.push(parseInt(hexString.substr(i, 2), 16));
            }
            
            display = `hex: ${value}`;
        } else if (type === 'text') {
            // Convert text to UTF-8 bytes
            convertedValue = Array.from(new TextEncoder().encode(value));
            display = `text: "${value}"`;
        } else if (type === 'number') {
            // Convert number to 32-bit integer bytes
            const num = parseInt(value, 10);
            convertedValue = [
                (num >> 24) & 0xFF,
                (num >> 16) & 0xFF,
                (num >> 8) & 0xFF,
                num & 0xFF
            ];
            display = `number: ${value}`;
        }
        
        // Call API to write characteristic
        const response = await fetch(`/api/ble/write/${currentDevice.address}/${uuid}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                value: convertedValue,
                response: true  // Request response from device if available
            })
        });
        
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Write failed: ${error}`);
        }
        
        // Log to console
        logToDeviceConsole(`Written to ${uuid}: ${display}`);
        
    } catch (error) {
        logToDeviceConsole(`Error writing to characteristic ${uuid}: ${error.message}`, 'error');
        console.error('Write error:', error);
        
    } finally {
        // Restore button state
        button.innerHTML = '<i class="fas fa-paper-plane mr-0.5"></i> Write';
        button.disabled = false;
    }
}

/**
 * Format characteristic value for display
 * @param {Array} value - Byte array
 * @returns {string} - Formatted HTML
 */
export function formatCharacteristicValue(value) {
    if (!value || value.length === 0) {
        return '<span class="text-gray-500">Empty</span>';
    }
    
    // Convert to array if needed
    const byteArray = Array.isArray(value) ? value : Array.from(value);
    
    // Format as hex
    const hexStr = byteArray.map(b => b.toString(16).padStart(2, '0').toUpperCase()).join(' ');
    
    // Try to decode as text if possible
    let textStr = '';
    let isPrintable = true;
    
    for (const byte of byteArray) {
        if (byte >= 32 && byte <= 126) {
            textStr += String.fromCharCode(byte);
        } else if (byte === 10 || byte === 13) {
            textStr += ' ';
        } else {
            isPrintable = false;
            break;
        }
    }
    
    // Try to interpret as number for small values
    let numStr = '';
    if (byteArray.length <= 4) {
        let val = 0;
        for (let i = 0; i < byteArray.length; i++) {
            val = (val << 8) | byteArray[i];
        }
        numStr = `<span class="ml-2 text-gray-500">Int: ${val}</span>`;
    }
    
    // Combine formats
    let result = `<span class="text-blue-400">0x</span>${hexStr}`;
    
    if (isPrintable && textStr.trim().length > 0) {
        result += ` <span class="text-gray-500">Text: "${textStr}"</span>`;
    }
    
    if (numStr) {
        result += numStr;
    }
    
    return result;
}

/**
 * Get characteristic name by UUID
 * @param {string} uuid - Characteristic UUID
 * @returns {string} - Characteristic name
 */
export function getCharacteristicName(uuid) {
    // Common BLE characteristic UUIDs
    const characteristics = {
        '2A00': 'Device Name',
        '2A01': 'Appearance',
        '2A04': 'Peripheral Preferred Connection Parameters',
        '2A05': 'Service Changed',
        '2A06': 'Alert Level',
        '2A07': 'Tx Power Level',
        '2A08': 'Date Time',
        '2A09': 'Day of Week',
        '2A0A': 'Day Date Time',
        '2A19': 'Battery Level',
        '2A1C': 'Temperature Measurement',
        '2A1D': 'Temperature Type',
        '2A24': 'Model Number String',
        '2A25': 'Serial Number String',
        '2A26': 'Firmware Revision String',
        '2A27': 'Hardware Revision String',
        '2A28': 'Software Revision String',
        '2A29': 'Manufacturer Name String',
        '2A2A': 'IEEE 11073-20601 Regulatory Certification Data List',
        '2A37': 'Heart Rate Measurement',
        '2A38': 'Body Sensor Location',
        '2A39': 'Heart Rate Control Point',
        '2A5C': 'Descriptor Value Changed',
        '2A63': 'Glucose Measurement',
        '2A64': 'Glucose Context',
        '2A6E': 'Temperature',
        '2A6F': 'Temperature Flags',
        '2A70': 'Temperature Measurement Interval',
        '2A71': 'Temperature Calibration',
        '2A72': 'Temperature Minimum',
        '2A73': 'Temperature Maximum',
        '2A82': 'PLX Spot-Check Measurement',
        '2A83': 'PLX Continuous Measurement',
        '2A84': 'PLX Features',
        '2AA6': 'Central Address Resolution',
        '2AA7': 'Resolvable Private Address Only',
        '2A9D': 'Pressure Measurement',
        '2A9E': 'Pressure Scale',
        '2A9F': 'Pressure Minimum',
        '2AA0': 'Pressure Maximum'
    };
    
    // Strip out any dashes and get the 16-bit UUID portion
    const shortUuid = uuid.replace(/-/g, '').slice(-4).toUpperCase();
    
    return characteristics[shortUuid] || 'Unknown Characteristic';
}

/**
 * Log a message to the device console
 * @param {string} message - Message to log
 * @param {string} type - Message type (info, warning, error)
 */
export function logToDeviceConsole(message, type = 'info') {
    const consoleElement = document.getElementById('device-console');
    if (!consoleElement) return;
    
    const messageElement = document.createElement('div');
    messageElement.classList.add('text-xs', 'mb-0.5');
    
    if (type === 'warning') {
        messageElement.classList.add('text-yellow-400');
    } else if (type === 'error') {
        messageElement.classList.add('text-red-400');
    } else {
        messageElement.classList.add('text-gray-400');
    }
    
    messageElement.innerHTML = `// ${message}`;
    consoleElement.appendChild(messageElement);
    
    // Scroll to bottom
    consoleElement.scrollTop = consoleElement.scrollHeight;
}

/**
 * Subscribe to characteristic notifications
 * @param {string} uuid - Characteristic UUID
 * @param {HTMLElement} button - Notify button
 */
export async function subscribeNotifications(uuid, button) {
    if (!currentDevice || !isConnected) {
        logToDeviceConsole('Cannot subscribe to notifications: Not connected to device', 'warning');
        return;
    }
    
    try {
        // Update button state
        const originalButtonText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin mr-0.5"></i> Subscribing...';
        button.disabled = true;
        
        // Call API to subscribe
        const response = await fetch(`/api/ble/subscribe/${currentDevice.address}/${uuid}`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Subscription failed: ${error}`);
        }
        
        // Update button state
        button.classList.add('subscribed');
        button.innerHTML = '<i class="fas fa-pause mr-0.5"></i> Unsubscribe';
        
        // Log to console
        logToDeviceConsole(`Subscribed to notifications from ${uuid}`);
        
    } catch (error) {
        logToDeviceConsole(`Error subscribing to notifications from ${uuid}: ${error.message}`, 'error');
        console.error('Subscription error:', error);
        
    } finally {
        // Restore button state
        button.innerHTML = '<i class="fas fa-bell mr-0.5"></i> Subscribe';
        button.disabled = false;
    }
}

/**
 * Unsubscribe from characteristic notifications
 * @param {string} uuid - Characteristic UUID
 * @param {HTMLElement} button - Notify button
 */
export async function unsubscribeNotifications(uuid, button) {
    if (!currentDevice || !isConnected) {
        logToDeviceConsole('Cannot unsubscribe from notifications: Not connected to device', 'warning');
        return;
    }
    
    try {
        // Update button state
        const originalButtonText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin mr-0.5"></i> Unsubscribing...';
        button.disabled = true;
        
        // Call API to unsubscribe
        const response = await fetch(`/api/ble/unsubscribe/${currentDevice.address}/${uuid}`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Unsubscription failed: ${error}`);
        }
        
        // Update button state
        button.classList.remove('subscribed');
        button.innerHTML = '<i class="fas fa-bell mr-0.5"></i> Subscribe';
        
        // Log to console
        logToDeviceConsole(`Unsubscribed from notifications from ${uuid}`);
        
    } catch (error) {
        logToDeviceConsole(`Error unsubscribing from notifications from ${uuid}: ${error.message}`, 'error');
        console.error('Unsubscription error:', error);
        
    } finally {
        // Restore button state
        button.innerHTML = '<i class="fas fa-bell mr-0.5"></i> Subscribe';
        button.disabled = false;
    }
}

/**
 * Update device metrics display
 * @param {HTMLElement} container - Container element
 * @param {Object} device - Device object
 */
export function updateDeviceMetrics(container, device) {
    if (!container || !device) return;
    
    const rssiElement = container.querySelector('.device-rssi');
    if (rssiElement) {
        rssiElement.textContent = `${device.rssi} dBm`;
        updateRssiIndicator(rssiElement, device.rssi);
    }
    
    const lastSeenElement = container.querySelector('.device-last-seen');
    if (lastSeenElement) {
        lastSeenElement.textContent = `Last seen: ${new Date(device.lastSeen).toLocaleTimeString()}`;
    }
}

/**
 * Display signal strength with appropriate styling
 * @param {number} rssi - RSSI value in dBm
 * @returns {Object} - Object with class and icon
 */
export function displaySignalStrength(rssi) {
    // Calculate signal strength class
    let signalClass = 'text-red-500';
    if (rssi > -70) signalClass = 'text-green-500';
    else if (rssi > -85) signalClass = 'text-yellow-500';
    
    // Format signal strength icon
    let signalIcon = 'fa-signal-slash';
    if (rssi > -90) signalIcon = 'fa-signal-weak';
    if (rssi > -80) signalIcon = 'fa-signal-fair';
    if (rssi > -70) signalIcon = 'fa-signal-good';
    if (rssi > -60) signalIcon = 'fa-signal-strong';
    
    return { signalClass, signalIcon };
}

/**
 * Format device address for display
 * @param {string} address - Device address
 * @param {boolean} addColons - Whether to add colons
 * @returns {string} - Formatted address
 */
export function formatDeviceAddress(address, addColons = false) {
    if (!address) return 'Unknown';
    
    if (addColons && !address.includes(':')) {
        // Add colons every 2 characters
        return address.match(/.{1,2}/g).join(':').toUpperCase();
    }
    
    return address.toUpperCase();
}

/**
 * Create device details UI elements
 * @param {Object} device - Device object
 * @returns {string} - HTML for device details
 */
export function createDeviceDetailsUI(device) {
    if (!device) return '';
    
    // Format device name
    const name = device.name || 'Unknown Device';
    
    // Get signal strength display info
    const { signalClass, signalIcon } = displaySignalStrength(device.rssi);
    
    // Format address
    const formattedAddress = formatDeviceAddress(device.address);
    
    return `
        <div class="bg-gray-800 p-3 rounded-md border border-gray-700">
            <div class="flex justify-between items-start">
                <div>
                    <h3 class="text-lg font-semibold">${name}</h3>
                    <div class="text-sm font-mono text-gray-400">${formattedAddress}</div>
                </div>
                <div class="text-right">
                    <div class="${signalClass} flex items-center justify-end device-rssi-indicator">
                        <i class="fas ${signalIcon} mr-1"></i>
                        <span class="device-rssi">${device.rssi} dBm</span>
                    </div>
                    <div class="text-xs text-gray-500 mt-1 device-last-seen">
                        Last seen: ${new Date(device.lastSeen).toLocaleTimeString()}
                    </div>
                </div>
            </div>
            ${showConnectivityOptions(device)}
        </div>
    `;
}

/**
 * Parse manufacturer data from advertising data
 * @param {Object} manufacturerData - Manufacturer data object
 * @returns {Object} - Parsed manufacturer data
 */
export function parseManufacturerData(manufacturerData) {
    if (!manufacturerData) return null;
    
    // Create a result object
    const result = {
        companyId: manufacturerData.company_id,
        companyName: getManufacturerName(manufacturerData.company_id),
        data: manufacturerData.data,
        formattedData: formatHexData(manufacturerData.data)
    };
    
    // Try to parse data based on known manufacturer formats
    if (manufacturerData.company_id === 0x004C) {
        // Apple manufacturer data
        result.type = 'Apple';
    } else if (manufacturerData.company_id === 0x0499) {
        // Ruuvi manufacturer data
        result.type = 'Ruuvi';
    }
    
    return result;
}

/**
 * Show device service information
 * @param {Array} services - Array of services
 * @returns {string} - HTML for services information
 */
export function showDeviceServiceInfo(services) {
    if (!services || services.length === 0) {
        return `
            <div class="text-center text-gray-500 py-4">
                <p>No service information available</p>
            </div>
        `;
    }
    
    let html = `
        <div class="space-y-2">
            <h4 class="text-sm font-semibold">Available Services (${services.length})</h4>
    `;
    
    // Add service list
    html += `<ul class="text-sm">`;
    services.forEach(service => {
        const serviceName = getServiceNameByUuid(service.uuid);
        html += `
            <li class="py-1 border-b border-gray-800">
                <div class="font-medium">${serviceName}</div>
                <div class="text-xs text-gray-400 font-mono">${service.uuid}</div>
            </li>
        `;
    });
    html += `</ul>`;
    
    html += `</div>`;
    return html;
}

/**
 * Create device stats display
 * @param {Object} device - Device object
 * @returns {string} - HTML for device stats
 */
export function createDeviceStats(device) {
    if (!device) return '';
    
    return `
        <div class="grid grid-cols-2 gap-2 mt-3">
            <div class="bg-gray-800 p-2 rounded-md border border-gray-700">
                <div class="text-xs text-gray-400">Signal Strength</div>
                <div class="text-lg font-medium ${displaySignalStrength(device.rssi).signalClass}">${device.rssi} dBm</div>
            </div>
            
            <div class="bg-gray-800 p-2 rounded-md border border-gray-700">
                <div class="text-xs text-gray-400">Address Type</div>
                <div class="text-lg font-medium">${device.address_type || 'Unknown'}</div>
            </div>
            
            <div class="bg-gray-800 p-2 rounded-md border border-gray-700">
                <div class="text-xs text-gray-400">Connectable</div>
                <div class="text-lg font-medium">
                    ${device.connectable === true ? 
                        '<span class="text-green-400">Yes</span>' : 
                        (device.connectable === false ? 
                            '<span class="text-red-400">No</span>' : 
                            '<span class="text-gray-500">Unknown</span>')}
                </div>
            </div>
            
            <div class="bg-gray-800 p-2 rounded-md border border-gray-700">
                <div class="text-xs text-gray-400">First Seen</div>
                <div class="text-lg font-medium">${device.firstSeen ? new Date(device.firstSeen).toLocaleTimeString() : 'Unknown'}</div>
            </div>
        </div>
    `;
}

/**
 * Update RSSI indicator
 * @param {HTMLElement} element - RSSI element
 * @param {number} rssi - RSSI value
 */
export function updateRssiIndicator(element, rssi) {
    if (!element) return;
    
    const { signalClass, signalIcon } = displaySignalStrength(rssi);
    
    // Get the parent element with the indicator class
    const indicator = element.closest('.device-rssi-indicator');
    if (!indicator) return;
    
    // Remove existing color classes
    indicator.classList.remove('text-red-500', 'text-yellow-500', 'text-green-500');
    // Add the new color class
    indicator.classList.add(signalClass);
    
    // Update the icon
    const iconElement = indicator.querySelector('i');
    if (iconElement) {
        iconElement.className = `fas ${signalIcon} mr-1`;
    }
}

/**
 * Show connectivity options for a device
 * @param {Object} device - Device object
 * @returns {string} - HTML for connectivity options
 */
export function showConnectivityOptions(device) {
    if (!device) return '';
    
    const isConnectable = device.connectable !== false; // Default to true if unknown
    
    return `
        <div class="flex mt-3 space-x-2">
            <button id="connect-btn" class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded flex-1 flex items-center justify-center" ${!isConnectable ? 'disabled' : ''}>
                <i class="fas fa-plug mr-1"></i> Connect
            </button>
            <button id="disconnect-btn" class="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded flex-1 flex items-center justify-center" disabled>
                <i class="fas fa-times mr-1"></i> Disconnect
            </button>
        </div>
    `;
}
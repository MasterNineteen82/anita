import { logMessage } from './ble-ui.js';

// frontend/static/js/pages/ble/ble-device-info.js
/**
 * Get detailed device information for the connected device
 * @param {Object} state - Application state
 * @param {String} deviceId - Device ID
 * @returns {Promise<Object|null>} - Device information or null if unavailable
 */
export async function getDeviceInformation(state, deviceId) {
    if (!state.connectedDevice) {
        logMessage('No device connected. Please connect to a device first.', 'warning');
        return null;
    }

    // Device Information Service UUID and characteristic UUIDs
    const deviceInfoServiceUuid = '0000180a-0000-1000-8000-00805f9b34fb';
    const characteristicUuids = {
        manufacturerName: '00002a29-0000-1000-8000-00805f9b34fb',
        modelNumber: '00002a24-0000-1000-8000-00805f9b34fb',
        serialNumber: '00002a25-0000-1000-8000-00805f9b34fb',
        hardwareRevision: '00002a27-0000-1000-8000-00805f9b34fb',
        firmwareRevision: '00002a26-0000-1000-8000-00805f9b34fb',
        softwareRevision: '00002a28-0000-1000-8000-00805f9b34fb'
    };

    const deviceInfo = {};

    // Fetch each characteristic value
    for (const [key, uuid] of Object.entries(characteristicUuids)) {
        try {
            const response = await fetch(`/api/ble/characteristics/${uuid}/read?service=${deviceInfoServiceUuid}`);
            if (response.ok) {
                const data = await response.json();
                if (data && data.value) {
                    // Convert hex to ASCII for readable text
                    const hexValue = data.value.replace(/\s/g, '');
                    const textValue = hexToAscii(hexValue);
                    deviceInfo[key] = textValue;
                }
            } else {
                console.warn(`Failed to fetch ${key}: ${response.statusText}`);
            }
        } catch (error) {
            console.error(`Error reading ${key}: ${error.message}`);
        }
    }

    // If device information is available, update the state and UI
    if (Object.keys(deviceInfo).length > 0) {
        state.deviceInfo = deviceInfo;

        // Update the UI
        displayDeviceInfo(state, deviceInfo);

        // Save to device history
        const deviceHistory = JSON.parse(localStorage.getItem('bleDeviceHistory') || '{}');
        deviceHistory[deviceId] = {
            ...deviceHistory[deviceId],
            info: deviceInfo,
            lastSeen: new Date().toISOString()
        };
        localStorage.setItem('bleDeviceHistory', JSON.stringify(deviceHistory));

        logMessage('Device information retrieved successfully.', 'success');
    } else {
        logMessage('No device information available.', 'warning');
    }

    return deviceInfo;
}

/**
 * Convert hexadecimal string to ASCII
 * @param {String} hex - Hexadecimal string
 * @returns {String} - ASCII string
 */
export function hexToAscii(hex) {
    let ascii = '';
    for (let i = 0; i < hex.length; i += 2) {
        const charCode = parseInt(hex.substr(i, 2), 16);
        if (charCode >= 32 && charCode <= 126) { // Printable ASCII range
            ascii += String.fromCharCode(charCode);
        }
    }
    return ascii;
}

/**
 * Display device information in the UI
 * @param {Object} state - Application state
 * @param {Object} deviceInfo - Device information
 */
export function displayDeviceInfo(state, deviceInfo) {
    const container = state.domElements.deviceInfoContainer;
    if (!container) {
        console.warn('Device info container not found in the DOM.');
        return;
    }

    container.innerHTML = '';

    // Create a table for device information
    const table = document.createElement('table');
    table.className = 'w-full text-sm';

    for (const [key, value] of Object.entries(deviceInfo)) {
        if (!value) continue;

        const row = table.insertRow();
        const keyCell = row.insertCell(0);
        const valueCell = row.insertCell(1);

        keyCell.className = 'text-gray-400 pr-2';
        valueCell.className = 'text-white';

        // Format key from camelCase to Title Case
        const formattedKey = key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());

        keyCell.textContent = formattedKey;
        valueCell.textContent = value;
    }

    container.appendChild(table);
}

/**
 * Parse raw device information data
 * @param {Object} rawData - Raw device data
 * @returns {Object} - Parsed device information
 */
export function parseDeviceInfo(rawData) {
    const parsedInfo = {};
    
    if (!rawData) return parsedInfo;
    
    // Process common device information fields
    if (rawData.name) parsedInfo.name = rawData.name;
    if (rawData.id) parsedInfo.id = rawData.id;
    if (rawData.rssi) parsedInfo.signalStrength = rawData.rssi;
    
    // Parse manufacturer data if available
    if (rawData.manufacturerData) {
        parsedInfo.manufacturer = formatManufacturerData(rawData.manufacturerData);
    }
    
    return parsedInfo;
}

/**
 * Format manufacturer-specific data
 * @param {String|Object} manufacturerData - Raw manufacturer data
 * @returns {Object} - Formatted manufacturer information
 */
export function formatManufacturerData(manufacturerData) {
    if (!manufacturerData) return {};
    
    try {
        // If string (hex), convert to buffer for processing
        const dataBuffer = typeof manufacturerData === 'string' 
            ? Buffer.from(manufacturerData.replace(/\s/g, ''), 'hex')
            : manufacturerData;
        
        // First 2 bytes typically represent the company identifier
        const companyId = typeof dataBuffer.readUInt16LE === 'function' 
            ? dataBuffer.readUInt16LE(0)
            : parseInt(dataBuffer.slice(0, 2).toString('hex'), 16);
            
        // Look up company name from the company ID
        const companyName = getCompanyName(companyId);
        
        return {
            companyId,
            companyName,
            data: typeof manufacturerData === 'string' ? manufacturerData : manufacturerData.toString('hex')
        };
    } catch (error) {
        console.error('Error formatting manufacturer data:', error);
        return { raw: typeof manufacturerData === 'string' ? manufacturerData : '(binary data)' };
    }
}

/**
 * Get company name from company identifier
 * @param {Number} companyId - Bluetooth SIG assigned company identifier
 * @returns {String} - Company name or 'Unknown Manufacturer'
 */
function getCompanyName(companyId) {
    // Sample mapping - in a real app, this would be more comprehensive
    const manufacturers = {
        0x004C: 'Apple, Inc.',
        0x0006: 'Microsoft',
        0x0075: 'Samsung Electronics Co. Ltd.',
        0x00E0: 'Google Inc.',
        // Add more as needed
    };
    
    return manufacturers[companyId] || 'Unknown Manufacturer';
}

/**
 * Get device capabilities based on available services and characteristics
 * @param {Object} state - Application state
 * @returns {Promise<Object>} - Device capabilities
 */
export async function getDeviceCapabilities(state) {
    if (!state.connectedDevice) {
        logMessage('No device connected. Please connect to a device first.', 'warning');
        return {};
    }
    
    try {
        const response = await fetch(`/api/ble/services`);
        if (!response.ok) {
            throw new Error(`Failed to fetch services: ${response.statusText}`);
        }
        
        const services = await response.json();
        
        const capabilities = {
            hasDeviceInfo: services.some(s => s.uuid.toLowerCase() === '0000180a-0000-1000-8000-00805f9b34fb'),
            hasBattery: services.some(s => s.uuid.toLowerCase() === '0000180f-0000-1000-8000-00805f9b34fb'),
            hasHeartRate: services.some(s => s.uuid.toLowerCase() === '0000180d-0000-1000-8000-00805f9b34fb'),
            hasHealthThermometer: services.some(s => s.uuid.toLowerCase() === '00001809-0000-1000-8000-00805f9b34fb'),
            // Add more service checks as needed
        };
        
        return capabilities;
    } catch (error) {
        console.error('Error determining device capabilities:', error);
        return {};
    }
}

/**
 * Check if device is compatible with the application
 * @param {Object} deviceInfo - Device information
 * @param {Object} capabilities - Device capabilities
 * @returns {Boolean} - True if compatible
 */
export function isDeviceCompatible(deviceInfo, capabilities) {
    // Define minimum requirements for compatibility
    const requiredCapabilities = ['hasDeviceInfo'];
    const recommendedCapabilities = ['hasBattery'];
    
    // Check if device has all required capabilities
    const hasRequiredCapabilities = requiredCapabilities.every(cap => capabilities[cap]);
    
    // Check manufacturer compatibility if needed
    const supportedManufacturers = ['Apple, Inc.', 'Samsung Electronics Co. Ltd.', 'Google Inc.'];
    const manufacturerSupported = !deviceInfo.manufacturer?.companyName || 
        supportedManufacturers.includes(deviceInfo.manufacturer.companyName);
    
    return hasRequiredCapabilities && manufacturerSupported;
}

/**
 * Get firmware information from the device
 * @param {Object} state - Application state
 * @returns {Promise<Object>} - Firmware information
 */
export async function getDeviceFirmwareInfo(state) {
    if (!state.deviceInfo) {
        await getDeviceInformation(state, state.connectedDevice?.id);
    }
    
    const firmwareInfo = {
        version: state.deviceInfo?.firmwareRevision || 'Unknown',
        hardwareVersion: state.deviceInfo?.hardwareRevision || 'Unknown',
        softwareVersion: state.deviceInfo?.softwareRevision || 'Unknown'
    };
    
    return firmwareInfo;
}

/**
 * Check if firmware version is up to date
 * @param {String} currentVersion - Current firmware version
 * @param {String} manufacturer - Device manufacturer
 * @returns {Promise<Object>} - Version check result
 */
export async function checkFirmwareVersion(currentVersion, manufacturer) {
    if (!currentVersion || currentVersion === 'Unknown') {
        return { isLatest: false, latestVersion: 'Unknown', updateAvailable: false };
    }
    
    try {
        // In a real implementation, this would call an API to check the latest version
        // This is a mockup for demonstration purposes
        const mockApiCall = new Promise(resolve => {
            setTimeout(() => {
                // Simulated response based on manufacturer
                const latestVersions = {
                    'Apple, Inc.': '2.5.0',
                    'Samsung Electronics Co. Ltd.': '3.1.2',
                    'Google Inc.': '1.8.3',
                    'default': '1.0.0'
                };
                
                const latestVersion = latestVersions[manufacturer] || latestVersions.default;
                resolve({ latestVersion });
            }, 300);
        });
        
        const { latestVersion } = await mockApiCall;
        
        // Simple version comparison (would need a more robust implementation for semantic versioning)
        const isLatest = currentVersion >= latestVersion;
        
        return {
            isLatest,
            latestVersion,
            updateAvailable: !isLatest,
            currentVersion
        };
    } catch (error) {
        console.error('Error checking firmware version:', error);
        return { 
            isLatest: false, 
            latestVersion: 'Error', 
            updateAvailable: false,
            error: error.message
        };
    }
}
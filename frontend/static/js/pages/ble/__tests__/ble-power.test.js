import { logMessage, updateScanStatus } from './ble-ui.js';

export async function getBatteryLevel(state, deviceId) {
    if (!state.connectedDevice) {
        logMessage('No device connected', 'warning');
        return null;
    }
    
    // Ensure deviceId matches current connection if provided
    if (deviceId && state.connectedDevice.address !== deviceId) {
        logMessage('Device ID mismatch for battery check', 'warning');
        return null;
    }
    
    try {
        // Try to find the standard battery service
        const batteryServiceUuid = '0000180f-0000-1000-8000-00805f9b34fb';
        const batteryCharUuid = '00002a19-0000-1000-8000-00805f9b34fb';
        
        logMessage('Checking device battery level...', 'info');
        const response = await fetch(`/api/ble/characteristics/${batteryCharUuid}/read?service=${batteryServiceUuid}`);
        
        if (response.ok) {
            const data = await response.json();
            if (data && data.value) {
                // Battery level is typically a single byte percentage
                let batteryLevel = parseInt(data.value, 16);
                
                // Validate battery level is in valid range
                if (isNaN(batteryLevel) || batteryLevel < 0) {
                    batteryLevel = 0;
                } else if (batteryLevel > 100) {
                    batteryLevel = 100;
                }
                
                logMessage(`Battery level: ${batteryLevel}%`, 'info');
                
                // Update UI with battery level
                updateBatteryUI(state, batteryLevel);
                
                // Emit event for other components
                if (window.bleEvents) {
                    window.bleEvents.emit('BATTERY_UPDATED', { 
                        level: batteryLevel, 
                        deviceId: state.connectedDevice.address 
                    });
                }
                
                return batteryLevel;
            } else {
                logMessage('Battery data not available in response', 'warning');
            }
        } else {
            logMessage(`Failed to read battery level: ${response.status} ${response.statusText}`, 'warning');
            
            // Try device-specific approach based on device type
            return await tryDeviceSpecificBatteryCheck(state);
        }
        
        return null;
    } catch (error) {
        logMessage(`Error reading battery level: ${error.message}`, 'error');
        return null;
    }
}

// Helper function to update battery UI
function updateBatteryUI(state, batteryLevel) {
    if (state.domElements.batteryLevel) {
        state.domElements.batteryLevel.textContent = `${batteryLevel}%`;
        
        // Show battery container if it was hidden
        if (state.domElements.batteryContainer) {
            state.domElements.batteryContainer.classList.remove('hidden');
        }
        
        // Add battery icon class based on level
        const iconElement = state.domElements.batteryIcon;
        if (iconElement) {
            // Remove existing battery classes
            iconElement.className = iconElement.className.replace(/fa-battery-\w+/g, '');
            
            // Add appropriate battery icon
            if (batteryLevel <= 10) {
                iconElement.classList.add('fa-battery-empty', 'text-red-500');
            } else if (batteryLevel <= 30) {
                iconElement.classList.add('fa-battery-quarter', 'text-orange-500');
            } else if (batteryLevel <= 60) {
                iconElement.classList.add('fa-battery-half', 'text-yellow-500');
            } else if (batteryLevel <= 90) {
                iconElement.classList.add('fa-battery-three-quarters', 'text-light-green-500');
            } else {
                iconElement.classList.add('fa-battery-full', 'text-green-500');
            }
        }
    }
}

// Try device-specific approaches to get battery level
async function tryDeviceSpecificBatteryCheck(state) {
    // Example implementation for specific device types
    const deviceInfo = state.deviceInfo || {};
    const deviceAddress = state.connectedDevice.address;
    
    // Check device manufacturer/model and try appropriate approach
    if (deviceInfo.manufacturerName && deviceInfo.manufacturerName.includes('Acme')) {
        // Example: Acme devices use a custom service for battery
        return await getAcmeDeviceBattery(deviceAddress);
    }

    async function getAcmeDeviceBattery(deviceAddress) {
        console.warn("getAcmeDeviceBattery function is a placeholder.");
        return null;
    }
    
    // Add more device-specific implementations as needed
    
    return null;
}

// Power-efficient scanning with adaptive behavior
export async function powerEfficientScan(state, duration = 5) {
    try {
        // Update UI to show scanning is in progress
        if (state.domElements.scanStatus) {
            updateScanStatus(state, 'scanning', 'Low-power scanning...');
        }
        
        // Use shorter durations if we've seen devices recently
        const cachedDevices = getDeviceCacheTimestamp();
        const adaptiveDuration = cachedDevices && (Date.now() - cachedDevices < 60000) 
            ? Math.max(2, Math.min(duration, 3)) // Short scan if recent activity
            : duration; // Full duration otherwise
        
        const scanOptions = {
            duration: adaptiveDuration,
            activeMode: false, // Use passive scanning to save power
            filterDuplicates: true
        };
        
        logMessage(`Starting ${adaptiveDuration}s power-efficient scan`, 'info');
        
        // Make sure this uses the regular /scan endpoint with POST
        const response = await fetch('/api/ble/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(scanOptions)
        });
        
        if (!response.ok) {
            throw new Error(`Scan failed: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        
        // Check if result is empty or contains error-like structure
        if (!result || result.length === 0) {
            logMessage('No devices found or scan returned empty result', 'warning');
            // You could also check for a specific error message in result
        }
        
        setDeviceCacheTimestamp(Date.now());
        
        return result;
    } catch (error) {
        logMessage(`Power-efficient scan error: ${error.message}`, 'error');
        throw error;
    } finally {
        // Reset scan status
        if (state.domElements.scanStatus) {
            updateScanStatus(state, 'idle', 'Scan complete');
        }
    }
}

// Helper to get/set device cache timestamp in localStorage
function getDeviceCacheTimestamp() {
    return parseInt(localStorage.getItem('bleDeviceCacheTimestamp') || '0');
}

function setDeviceCacheTimestamp(timestamp) {
    localStorage.setItem('bleDeviceCacheTimestamp', timestamp.toString());
}
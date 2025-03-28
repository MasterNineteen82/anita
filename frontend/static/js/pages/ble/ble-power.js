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
export function updateBatteryUI(state, batteryLevel) {
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
export async function tryDeviceSpecificBatteryCheck(state) {
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
export function getDeviceCacheTimestamp() {
    return parseInt(localStorage.getItem('bleDeviceCacheTimestamp') || '0');
}

export function setDeviceCacheTimestamp(timestamp) {
    localStorage.setItem('bleDeviceCacheTimestamp', timestamp.toString());
}

// Set up periodic battery monitoring for connected device
export function setupBatteryMonitoring(state, intervalMinutes = 5) {
    if (!state || !state.connectedDevice) {
        logMessage('No device connected for battery monitoring', 'warning');
        return false;
    }
    
    // Clear any existing monitoring
    if (state.batteryMonitorInterval) {
        clearInterval(state.batteryMonitorInterval);
    }
    
    // Convert minutes to milliseconds
    const interval = intervalMinutes * 60 * 1000;
    
    // Initial battery check
    getBatteryLevel(state);
    
    // Set up periodic checks
    state.batteryMonitorInterval = setInterval(() => {
        getBatteryLevel(state);
    }, interval);
    
    logMessage(`Battery monitoring started (every ${intervalMinutes} minutes)`, 'info');
    return true;
}

// Optimize BLE settings for power efficiency
export function optimizePowerSettings(state, settings = {}) {
    const defaultSettings = {
        connectionInterval: 30, // ms
        latency: 2,
        timeout: 500, // ms
        scanDutyCycle: 0.25, // 25% duty cycle
        txPower: 'low'
    };
    
    const finalSettings = { ...defaultSettings, ...settings };
    
    // Apply settings through API
    fetch('/api/ble/power-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(finalSettings)
    })
    .then(response => {
        if (response.ok) {
            logMessage('Power settings optimized', 'success');
            return response.json();
        }
        throw new Error('Failed to set power settings');
    })
    .catch(error => {
        logMessage(`Power optimization error: ${error.message}`, 'error');
    });
    
    return finalSettings;
}

// Get estimated battery usage for current configuration
export function getEstimatedBatteryUsage(state) {
    if (!state || !state.connectedDevice) {
        return { estimatedHours: 0, confidence: 'none' };
    }
    
    // Calculate based on device profile and connection parameters
    let baseHours = 0;
    let confidence = 'low';
    
    if (state.deviceInfo && state.deviceInfo.batteryCapacity) {
        // More precise estimation with device battery capacity information
        const connParams = state.connectionParameters || {};
        const interval = connParams.interval || 30;
        const latency = connParams.latency || 0;
        
        // Simple formula - can be enhanced with more detailed calculations
        baseHours = state.deviceInfo.batteryCapacity * 0.8 / (24 / interval * (1 + latency));
        confidence = 'medium';
    } else {
        // Generic estimate based on device type
        baseHours = state.lowPowerMode ? 36 : 20;
    }
    
    return {
        estimatedHours: Math.round(baseHours * 10) / 10,
        confidence: confidence,
        deviceType: state.deviceInfo?.type || 'unknown'
    };
}

// Enable or disable low power mode
export function setLowPowerMode(state, enable = true) {
    state.lowPowerMode = enable;
    
    const settings = enable ? {
        connectionInterval: 100, // Longer interval
        latency: 4,       // Higher latency
        scanDutyCycle: 0.1, // 10% duty cycle
        txPower: 'lowest',
        notifyReduceFactor: 2  // Reduce notification frequency
    } : {
        connectionInterval: 30,
        latency: 0,
        scanDutyCycle: 0.5,
        txPower: 'medium',
        notifyReduceFactor: 1
    };
    
    // Apply the new settings
    optimizePowerSettings(state, settings);
    
    logMessage(`Low power mode ${enable ? 'enabled' : 'disabled'}`, 'info');
    return state.lowPowerMode;
}

// Get current battery threshold settings
export function getBatteryThresholds(state) {
    // Get from state or use defaults
    const thresholds = state.batteryThresholds || {
        critical: 10,
        low: 20,
        normal: 30,
        high: 80
    };
    
    return { ...thresholds };
}

// Set battery thresholds for notifications
export function setBatteryThresholds(state, thresholds) {
    const currentThresholds = getBatteryThresholds(state);
    state.batteryThresholds = {
        ...currentThresholds,
        ...thresholds
    };
    
    // Validate thresholds are in order
    if (state.batteryThresholds.critical > state.batteryThresholds.low ||
        state.batteryThresholds.low > state.batteryThresholds.normal ||
        state.batteryThresholds.normal > state.batteryThresholds.high) {
        logMessage('Invalid battery thresholds (must be in ascending order)', 'error');
        state.batteryThresholds = currentThresholds;
        return false;
    }
    
    logMessage('Battery thresholds updated', 'info');
    return true;
}

// Check current power state for device and connection
export function checkPowerState(state) {
    if (!state || !state.connectedDevice) {
        return { connected: false };
    }
    
    return {
        connected: true,
        deviceId: state.connectedDevice.address,
        lowPowerMode: state.lowPowerMode || false,
        batteryLevel: state.batteryLevel || null,
        connectionParameters: state.connectionParameters || {},
        lastChecked: new Date().toISOString(),
        estimatedUsage: getEstimatedBatteryUsage(state)
    };
}
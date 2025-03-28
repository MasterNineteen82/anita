import { BLEEventEmitter, bleEvents } from './ble-events.js';

// Enhanced diagnostics function

export function runDiagnostics() {
    console.group('BLE System Diagnostics');
    
    // Check event system
    console.log('Checking event system...');
    if (window.bleEvents) {
        console.log('✅ Event system exists', window.bleEvents);
        
        // Test event emission
        try {
            const testEvent = 'test.diagnostic.event';
            let eventReceived = false;
            
            window.bleEvents.on(testEvent, () => { 
                eventReceived = true;
                console.log('✅ Event listener fired successfully');
            });
            
            window.bleEvents.emit(testEvent, {diagnostics: true});
            
            console.log(eventReceived ? 
                '✅ Event system working properly' : 
                '❌ Event emission failed - listeners not called');
                
            // Test specific events to verify proper implementation
            try {
                window.bleEvents.emit(bleEvents.DEVICE_CONNECTING, {id: 'test', name: 'Test Device'});
                console.log('✅ Specific event emission works');
            } catch (err) {
                console.error('❌ Specific event emission failed:', err);
            }
        } catch (e) {
            console.error('❌ Event system test failed', e);
        }
    } else {
        console.error('❌ Event system not initialized (window.bleEvents is undefined)');
    }
    
    // Check DOM references
    console.log('Checking DOM references...');
    const criticalElements = [
        'scanButton', 'deviceList', 'statusIndicatorContainer', 
        'logMessages', 'debugPanel', 'clearLogButton'
    ];
    
    if (window.state && window.state.domElements) {
        const missingElements = criticalElements.filter(id => !window.state.domElements[id]);
        if (missingElements.length === 0) {
            console.log('✅ All critical DOM elements found');
        } else {
            console.warn(`❌ Missing critical DOM elements: ${missingElements.join(', ')}`);
        }
    } else {
        console.error('❌ State or domElements not properly initialized');
    }
    
    // Test WebSocket connection
    console.log('Testing WebSocket connection...');
    if (window.state && window.state.socket) {
        console.log(`✅ WebSocket exists, state: ${window.state.socket.readyState === 1 ? 'OPEN' : 'CLOSED/CONNECTING'}`);
    } else {
        console.error('❌ WebSocket not initialized');
    }
    
    // Check imports
    console.log('Checking module imports...');
    try {
        const requiredModules = [
            'BLE_EVENTS', 'bleEvents', 'connectToDevice', 'disconnectFromDevice',
            'startScanning', 'stopScanning', 'getServices', 'getCharacteristics'
        ];
        
        for (const moduleName of requiredModules) {
            if (typeof window[moduleName] !== 'undefined' || 
                (window.BLE && typeof window.BLE[moduleName] !== 'undefined')) {
                console.log(`✅ Module ${moduleName} is available`);
            } else {
                console.warn(`❌ Module ${moduleName} is missing`);
            }
        }
    } catch (e) {
        console.error('❌ Module check failed:', e);
    }
    
    console.groupEnd();
    
    // Display diagnostic results on page
    const diagnosticsDiv = document.createElement('div');
    diagnosticsDiv.id = 'ble-diagnostics';
    diagnosticsDiv.style.position = 'fixed';
    diagnosticsDiv.style.top = '10px';
    diagnosticsDiv.style.right = '10px';
    diagnosticsDiv.style.backgroundColor = '#1E293B';
    diagnosticsDiv.style.color = 'white';
    diagnosticsDiv.style.padding = '15px';
    diagnosticsDiv.style.borderRadius = '5px';
    diagnosticsDiv.style.zIndex = '10000';
    diagnosticsDiv.style.maxWidth = '400px';
    diagnosticsDiv.style.maxHeight = '80vh';
    diagnosticsDiv.style.overflow = 'auto';
    diagnosticsDiv.innerHTML = `
        <h3 style="margin-top:0;font-size:16px;font-weight:bold;">BLE Diagnostics</h3>
        <div id="diagnostic-results" style="font-size:12px;"></div>
        <button id="close-diagnostics" style="margin-top:10px;padding:5px 10px;background:#4F46E5;border:none;color:white;border-radius:3px;cursor:pointer;">Close</button>
    `;
    
    document.body.appendChild(diagnosticsDiv);
    
    // Log diagnostics to UI
    const diagnosticResults = document.getElementById('diagnostic-results');
    if (diagnosticResults) {
        diagnosticResults.innerHTML = `
            <p>✅ Diagnostics run at: ${new Date().toLocaleTimeString()}</p>
            <p>Event System: ${window.bleEvents ? '✅ Available' : '❌ Missing'}</p>
            <p>WebSocket: ${window.state && window.state.socket ? '✅ Connected' : '❌ Disconnected'}</p>
            <p>DOM Elements: ${window.state && window.state.domElements ? '✅ Initialized' : '❌ Missing'}</p>
        `;
    }
    
    // Close button functionality
    const closeDiagnosticsButton = document.getElementById('close-diagnostics');
    if (closeDiagnosticsButton) {
        closeDiagnosticsButton.addEventListener('click', () => {
            document.getElementById('ble-diagnostics').remove();
        });
    }
    
    return true;
}

/**
 * Checks if the browser supports Web Bluetooth API
 * @returns {Object} Support status and details
 */
export function checkBleSupport() {
    const report = {
        supported: false,
        details: {}
    };
    
    report.details.bluetoothObject = !!navigator.bluetooth;
    report.details.requestDevice = !!(navigator.bluetooth && typeof navigator.bluetooth.requestDevice === 'function');
    report.supported = report.details.bluetoothObject && report.details.requestDevice;
    report.details.secureContext = window.isSecureContext;
    
    return report;
}

/**
 * Validates the current state of BLE connections and system
 * @returns {Object} Current BLE state information
 */
export function validateBleState() {
    const state = {
        eventSystemInitialized: !!window.bleEvents,
        connectedDevices: [],
        domElementsStatus: {}
    };
    
    if (window.state && window.state.connectedDevices) {
        state.connectedDevices = Array.from(window.state.connectedDevices || []).map(device => ({
            name: device.name || 'Unknown Device',
            id: device.id,
            connected: device.gatt ? device.gatt.connected : false
        }));
    }
    
    if (window.state && window.state.domElements) {
        const criticalElements = [
            'scanButton', 'deviceList', 'statusIndicatorContainer', 
            'logMessages', 'debugPanel', 'clearLogButton'
        ];
        
        criticalElements.forEach(elementId => {
            state.domElementsStatus[elementId] = !!window.state.domElements[elementId];
        });
    }
    
    return state;
}

/**
 * Analyzes performance metrics of BLE operations
 * @returns {Object} Performance analysis
 */
export function analyzeBlePerformance() {
    const performance = {
        scanTimes: [],
        connectTimes: [],
        readTimes: [],
        writeTimes: [],
        averages: {}
    };
    
    if (window.state && window.state.metrics) {
        performance.scanTimes = window.state.metrics.scanTimes || [];
        performance.connectTimes = window.state.metrics.connectTimes || [];
        performance.readTimes = window.state.metrics.readTimes || [];
        performance.writeTimes = window.state.metrics.writeTimes || [];
    }
    
    const calculateAverage = array => array.length ? 
        array.reduce((a, b) => a + b, 0) / array.length : 0;
    
    performance.averages = {
        scanTime: calculateAverage(performance.scanTimes),
        connectTime: calculateAverage(performance.connectTimes),
        readTime: calculateAverage(performance.readTimes),
        writeTime: calculateAverage(performance.writeTimes)
    };
    
    return performance;
}

/**
 * Tests the speed of BLE connections
 * @returns {Promise<Object>} Connection speed test results
 */
export async function testConnectionSpeed() {
    const results = {
        success: false,
        connectionTime: null,
        readTime: null,
        writeTime: null,
        disconnectTime: null,
        errors: []
    };
    
    if (!window.state || !window.state.connectedDevices || window.state.connectedDevices.size === 0) {
        results.errors.push('No connected devices to test with');
        return results;
    }
    
    try {
        const device = Array.from(window.state.connectedDevices)[0];
        
        const startConnect = performance.now();
        const server = await device.gatt.connect();
        results.connectionTime = performance.now() - startConnect;
        
        const services = await server.getPrimaryServices();
        if (services.length > 0) {
            const characteristics = await services[0].getCharacteristics();
            
            if (characteristics.length > 0) {
                if (characteristics[0].properties.read) {
                    const startRead = performance.now();
                    await characteristics[0].readValue();
                    results.readTime = performance.now() - startRead;
                }
                
                if (characteristics[0].properties.write) {
                    const startWrite = performance.now();
                    await characteristics[0].writeValue(new Uint8Array([0x00]));
                    results.writeTime = performance.now() - startWrite;
                }
            }
        }
        
        const startDisconnect = performance.now();
        device.gatt.disconnect();
        results.disconnectTime = performance.now() - startDisconnect;
        
        results.success = true;
    } catch (error) {
        results.errors.push(error.message);
    }
    
    return results;
}

/**
 * Checks if the required permissions are granted
 * @returns {Promise<Object>} Permission status
 */
export async function checkPermissions() {
    const permissions = {
        bluetooth: {
            state: 'unknown',
            detail: null
        }
    };
    
    if (navigator.permissions && navigator.permissions.query) {
        try {
            const bluetoothResult = await navigator.permissions.query({ name: 'bluetooth' });
            permissions.bluetooth.state = bluetoothResult.state;
            permissions.bluetooth.detail = {
                name: bluetoothResult.name,
                state: bluetoothResult.state
            };
        } catch (e) {
            permissions.bluetooth.state = 'error';
            permissions.bluetooth.detail = e.message;
        }
    } else {
        permissions.bluetooth.state = 'unsupported';
        permissions.bluetooth.detail = 'Permissions API not supported';
    }
    
    return permissions;
}

/**
 * Validates Web Bluetooth API feature support
 * @returns {Object} Support status for various Web Bluetooth features
 */
export function validateWebBluetoothSupport() {
    const support = {
        core: false,
        scanning: false,
        secureContext: window.isSecureContext,
        availableGATTOperations: {}
    };
    
    support.core = !!navigator.bluetooth;
    
    if (support.core) {
        support.scanning = typeof navigator.bluetooth.requestDevice === 'function';
        
        support.availableGATTOperations = {
            requestDevice: typeof navigator.bluetooth.requestDevice === 'function',
            getDevices: typeof navigator.bluetooth.getDevices === 'function',
            requestLEScan: typeof navigator.bluetooth.requestLEScan === 'function',
            BluetoothRemoteGATTServer: typeof BluetoothRemoteGATTServer !== 'undefined'
        };
    }
    
    return support;
}

/**
 * Gets debug diagnostics information
 * @returns {Object} Debug diagnostic data
 */
export function getDebugDiagnostics() {
    return {
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        bleSupport: checkBleSupport(),
        webBluetoothSupport: validateWebBluetoothSupport(),
        bleState: validateBleState(),
        browserInfo: {
            vendor: navigator.vendor,
            language: navigator.language,
            onLine: navigator.onLine,
            cookieEnabled: navigator.cookieEnabled,
            doNotTrack: navigator.doNotTrack,
        }
    };
}

/**
 * Generates a comprehensive diagnostic report
 * @returns {Promise<Object>} Complete diagnostic report
 */
export async function generateDiagnosticReport() {
    try {
        const supportInfo = checkBleSupport();
        const stateInfo = validateBleState();
        const permissionInfo = await checkPermissions();
        const featureSupport = validateWebBluetoothSupport();
        const performanceMetrics = analyzeBlePerformance();
        const debugInfo = getDebugDiagnostics();
        
        let speedTest = { skipped: true, reason: 'No connected device' };
        if (window.state?.connectedDevices?.size > 0) {
            try {
                speedTest = await testConnectionSpeed();
            } catch (e) {
                speedTest = { error: e.message };
            }
        }
        
        return {
            generatedAt: new Date().toISOString(),
            bleSupport: supportInfo,
            webBluetoothFeatures: featureSupport,
            currentState: stateInfo,
            permissions: permissionInfo,
            performance: performanceMetrics,
            connectionSpeedTest: speedTest,
            debug: debugInfo
        };
    } catch (error) {
        return {
            error: true,
            message: error.message,
            stack: error.stack
        };
    }
}

/**
 * Exports diagnostic data to a file
 * @param {Object} [data=null] Optional diagnostic data to export
 * @returns {Promise<boolean>} True if export was successful
 */
export async function exportDiagnosticsToFile(data = null) {
    try {
        const diagnosticData = data || await generateDiagnosticReport();
        const fileContent = JSON.stringify(diagnosticData, null, 2);
        const fileName = `ble-diagnostics-${new Date().toISOString().replace(/:/g, '-')}.json`;
        
        const blob = new Blob([fileContent], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        return true;
    } catch (error) {
        console.error('Failed to export diagnostics:', error);
        return false;
    }
}

// Export BLEEventEmitter as backup
export { BLEEventEmitter };
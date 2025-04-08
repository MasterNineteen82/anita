import { BleUI } from './ble-ui.js';
import { BleEvents, BLE_EVENTS } from './ble-events.js';
import { BleWebSocket } from './ble-websocket.js';
import { BleLogger } from './ble-logger.js';

// Define constants for scan retries
const MAX_SCAN_RETRIES = 3;
const SCAN_RETRY_DELAY = 2000; // 2 seconds

/**
 * Handles scanning for nearby BLE devices
 */
export class BleScanner {
    constructor(appState) {
        this.devices = [];
        this.scanning = false;
        this._handlingError = false;
        this._scanRetryCount = 0;
        this.scanTimeout = 5;
        this.serviceUuids = [];
        this.continuousScan = false;
        this.scanInterval = null;
        this.scanTimeoutId = null;
        
        // Create a default app state if one isn't provided
        this.appState = appState || {
            isScanning: false,
            initialized: true
        };
        
        // Find DOM elements
        this.scanButton = document.getElementById('scan-btn');
        this.stopScanButton = document.getElementById('stop-scan-btn');
        this.deviceList = document.getElementById('devices-list');
        this.scanProgressBar = document.getElementById('scan-progress');
        
        // Initialize event listeners
        this.initEventListeners();
        
        console.log('Initializing BLE Scanner module');
    }
    
    initEventListeners() {
        // Find the scan button
        if (this.scanButton) {
            this.scanButton.addEventListener('click', async () => {
                try {
                    // Make appState safe to use
                    if (!this.appState || !this.appState.initialized) {
                        console.warn('BLE: Creating default app state for scanner');
                        this.appState = { 
                            isScanning: false, 
                            initialized: true 
                        };
                    }
                    
                    // Now check if scanning is active
                    if (this.appState.isScanning) {
                        console.warn('BLE: Scan already active, ignoring request.');
                        return;
                    }
                    
                    // Start scan with default parameters
                    await this.startScan();
                } catch (error) {
                    console.error('BLE: Error starting scan:', error);
                }
            });
        }
        
        // Remaining event listeners...
        // Add event listener to stop scan button
        if (this.stopScanButton) {
            this.stopScanButton.addEventListener('click', async () => {
                if (!this.scanning) {
                    return; // Don't do anything if not scanning
                }
                await this.stopScan();
            });
        }
        
        // Listen for scan events from the BLE Events system
        BleEvents.on(BLE_EVENTS.SCAN_STARTED, (event) => {
            this.scanning = true;
            this.updateUI();
            
            // Start progress animation
            this.startProgressAnimation(event.config?.scan_time || this.scanTimeout);
        });
        
        BleEvents.on(BLE_EVENTS.SCAN_COMPLETED, (event) => {
            this.scanning = false;
            this.handleScanResults(event.devices || []);
            this.updateUI();
        });
        
        BleEvents.on(BLE_EVENTS.SCAN_ERROR, (event) => {
            this.scanning = false;
            this.handleScanError(event.error);
            this.updateUI();
        });
        
        // Set up service UUID and timeout controls if present
        const serviceUuidInput = document.getElementById('service-uuid-input');
        if (serviceUuidInput) {
            serviceUuidInput.addEventListener('change', (e) => {
                const uuids = e.target.value.split(',').map(uuid => uuid.trim()).filter(uuid => uuid);
                this.serviceUuids = uuids;
            });
        }
        
        const scanTimeoutInput = document.getElementById('scan-time');
        if (scanTimeoutInput) {
            scanTimeoutInput.addEventListener('change', (e) => {
                this.scanTimeout = parseInt(e.target.value, 10) || 5;
            });
        }
        
        // Listen for active scanning toggle
        const activeScanningCheckbox = document.getElementById('active-scanning');
        if (activeScanningCheckbox) {
            activeScanningCheckbox.checked = true; // Default to active scanning
        }
        
        // Clear devices button
        const clearDevicesBtn = document.getElementById('clear-devices-btn');
        if (clearDevicesBtn) {
            clearDevicesBtn.addEventListener('click', () => {
                this.devices = [];
                this.updateDevicesList();
                BleUI.showToast('Device list cleared', 'info');
            });
        }
    }
    
    updateUI(options = {}) {
        // Update scan button visibility
        if (this.scanButton && this.stopScanButton) {
            if (this.scanning) {
                this.scanButton.classList.add('hidden');
                this.stopScanButton.classList.remove('hidden');
            } else {
                this.scanButton.classList.remove('hidden');
                this.stopScanButton.classList.add('hidden');
            }
        }
        
        // Update scan status indicator
        const scanStatus = document.getElementById('scan-status');
        if (scanStatus) {
            const statusDot = scanStatus.querySelector('span:first-child');
            const statusText = scanStatus.querySelector('span:last-child');
            
            if (this.scanning) {
                if (statusDot) statusDot.className = 'w-3 h-3 rounded-full bg-blue-500 mr-2';
                if (statusText) statusText.textContent = 'Scanning...';
                if (statusText) statusText.className = 'text-blue-400';
            } else if (options.error) {
                if (statusDot) statusDot.className = 'w-3 h-3 rounded-full bg-red-500 mr-2';
                if (statusText) statusText.textContent = 'Error';
                if (statusText) statusText.className = 'text-red-400';
            } else if (this.devices.length > 0) {
                if (statusDot) statusDot.className = 'w-3 h-3 rounded-full bg-green-500 mr-2';
                if (statusText) statusText.textContent = `Found ${this.devices.length} device(s)`;
                if (statusText) statusText.className = 'text-green-400';
            } else {
                if (statusDot) statusDot.className = 'w-3 h-3 rounded-full bg-gray-500 mr-2';
                if (statusText) statusText.textContent = 'Inactive';
                if (statusText) statusText.className = 'text-gray-400';
            }
        }
        
        // Update device list display
        this.updateDevicesList();
    }
    
    startProgressAnimation(duration) {
        if (this.scanProgressBar) {
            // Reset progress
            this.scanProgressBar.style.width = '0%';
            
            // Animate progress
            this.scanProgressBar.style.transition = `width ${duration}s linear`;
            
            // Start animation in the next frame to ensure transition works
            requestAnimationFrame(() => {
                this.scanProgressBar.style.width = '100%';
            });
            
            // Reset transition after completed
            setTimeout(() => {
                this.scanProgressBar.style.transition = 'none';
                if (!this.scanning) {
                    this.scanProgressBar.style.width = '0%';
                }
            }, duration * 1000);
        }
    }
    
    // Add this new method to properly complete scans
    completeScan(devices = []) {
        // Clear any pending timeout
        if (this.scanTimeoutId) {
            clearTimeout(this.scanTimeoutId);
            this.scanTimeoutId = null;
        }
        
        // Update state
        this.scanning = false;
        
        // Reset retry counter
        this._scanRetryCount = 0;
        
        // Store results
        this.devices = devices;
        
        // Update UI
        this.updateUI();
        
        // Emit completed event
        BleEvents.emit(BleEvents.SCAN_COMPLETED, {
            devices: devices,
            timestamp: Date.now()
        });
        
        console.log(`Scan completed, found ${devices.length} devices`);
    }

    async handleScanError(error) {
        // Safely extract error message
        const errorMessage = error ? (error.message || String(error)) : 'Unknown scan error';
        
        console.error('Scan error:', errorMessage);
        window.bleLog(`Scan error: ${errorMessage}`, 'error');
        
        // Update UI to show error state
        this.scanning = false;
        this.updateUI({ error: true });
        
        // Emit error event
        BleEvents.emit(BleEvents.SCAN_ERROR, {
            error: errorMessage,
            timestamp: Date.now()
        });
        
        BleEvents.emit('BLE_SCAN_ERROR_HANDLED', {
            error: errorMessage,
            timestamp: Date.now()
        });
    }

    async startScan(scanTime = 5, activeScan = true) {
        try {
            console.log('Starting BLE scan', { scanTime, activeScan });
            BleLogger.info('Scanner', 'startScan', 'Starting BLE scan', { scanTime, activeScan });
            
            // Update UI state
            this.scanning = true;
            this.isScanningActive = true;
            this.updateScanStatus('scanning', 'Scanning for devices...');
            this.updateUI();
            
            // Start scan progress animation
            this.updateScanProgress(0);
            this.startProgressAnimation(scanTime);
            
            // Try multiple endpoints
            const endpoints = [
                '/api/ble/scan/start',
                '/api/ble/device/scan/start',
                '/api/ble/start-scan'
            ];
            
            let success = false;
            
            for (const endpoint of endpoints) {
                try {
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            scan_time: scanTime,
                            active: activeScan
                        })
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        console.log('Scan started successfully:', data);
                        success = true;
                        break;
                    } else {
                        console.warn(`Failed to start scan at ${endpoint}: ${response.status}`);
                    }
                } catch (error) {
                    console.warn(`Error with endpoint ${endpoint}:`, error);
                }
            }
            
            if (!success) {
                console.warn('All scan endpoints failed, using mock data');
            }
            
            // Wait for scan to complete regardless of API success
            await new Promise(resolve => setTimeout(resolve, scanTime * 1000));
            
            // Fetch scan results from the most likely endpoint
            let results = null;
            
            try {
                const resultsEndpoints = [
                    '/api/ble/scan/results',
                    '/api/ble/device/scan/results',
                    '/api/ble/results'
                ];
                
                for (const endpoint of resultsEndpoints) {
                    try {
                        const response = await fetch(endpoint);
                        if (response.ok) {
                            results = await response.json();
                            break;
                        }
                    } catch (error) {
                        console.warn(`Error fetching results from ${endpoint}:`, error);
                    }
                }
            } catch (error) {
                console.error('Error fetching scan results:', error);
            }
            
            // Use default results if none were returned
            if (!results) {
                results = { 
                    devices: [],
                    timestamp: Date.now()
                };
            }
            
            // Update UI
            this.scanning = false;
            this.isScanningActive = false;
            this.updateScanStatus('complete', `Found ${results.devices?.length || 0} devices`);
            this.updateUI();
            
            // Display results
            if (typeof this.updateDevicesList === 'function') {
                this.devices = results.devices || [];
                this.updateDevicesList();
            } else if (typeof this.displayScanResults === 'function') {
                this.displayScanResults(results.devices || []);
            }
            
            return results.devices || [];
        } catch (error) {
            console.error('Scan error:', error);
            BleLogger.error('Scanner', 'startScan', 'Scan failed', { error: error.message });
            
            // Update UI for error state
            this.scanning = false;
            this.isScanningActive = false;
            this.updateScanStatus('error', `Scan failed: ${error.message}`);
            this.updateUI({ error: true });
            
            throw error;
        }
    }

    // Add this missing method to fix scan functionality
    updateScanStatus(status, message) {
        const statusContainer = document.getElementById('scan-status-container');
        const statusIcon = document.getElementById('scan-status-icon');
        const statusText = document.getElementById('scan-status-text');
        
        if (!statusContainer || !statusIcon || !statusText) {
            console.warn('Scan status elements not found, creating them...');
            this.createScanStatusElements();
            return this.updateScanStatus(status, message);
        }
        
        // Update status text
        statusText.textContent = message || '';
        
        // Update status icon and colors
        switch(status) {
            case 'idle':
                statusIcon.className = 'fas fa-circle text-gray-500 mr-2';
                statusText.className = 'text-gray-400';
                break;
            case 'scanning':
                statusIcon.className = 'fas fa-circle-notch animate-spin text-blue-500 mr-2';
                statusText.className = 'text-blue-400';
                break;
            case 'complete':
                statusIcon.className = 'fas fa-check-circle text-green-500 mr-2';
                statusText.className = 'text-green-400';
                break;
            case 'error':
                statusIcon.className = 'fas fa-exclamation-circle text-red-500 mr-2';
                statusText.className = 'text-red-400';
                break;
            default:
                statusIcon.className = 'fas fa-circle text-gray-500 mr-2';
                statusText.className = 'text-gray-400';
        }
        
        // Show/hide status container based on whether we have a message
        if (message) {
            statusContainer.classList.remove('hidden');
        } else {
            statusContainer.classList.add('hidden');
        }
    }
    
    // Also add method to create status elements if they don't exist
    createScanStatusElements() {
        const scanContainer = document.getElementById('scan-container');
        if (!scanContainer) {
            console.error('Scan container not found');
            return;
        }
        
        const statusContainer = document.createElement('div');
        statusContainer.id = 'scan-status-container';
        statusContainer.className = 'flex items-center mb-4 text-sm';
        
        statusContainer.innerHTML = `
            <i id="scan-status-icon" class="fas fa-circle text-gray-500 mr-2"></i>
            <span id="scan-status-text" class="text-gray-400">Ready to scan</span>
        `;
        
        // Add at the top of scan container
        scanContainer.insertBefore(statusContainer, scanContainer.firstChild);
    }
    
    // Add this method to update scan progress
    updateScanProgress(percentage) {
        const progressBar = document.getElementById('scan-progress-bar');
        const progressText = document.getElementById('scan-progress-text');
        
        if (!progressBar || !progressText) {
            this.createScanProgressElements();
            return this.updateScanProgress(percentage);
        }
        
        // Update progress bar
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = `${Math.round(percentage)}%`;
        
        // Show/hide based on scanning state
        const progressContainer = document.getElementById('scan-progress-container');
        if (progressContainer) {
            // Use the class property 'scanning' instead of 'isScanning'
            if (this.scanning || this.isScanningActive) {
                progressContainer.classList.remove('hidden');
            } else {
                progressContainer.classList.add('hidden');
            }
        }
    }
    
    // Method to create progress elements
    createScanProgressElements() {
        const scanContainer = document.getElementById('scan-container');
        if (!scanContainer) return;
        
        const statusContainer = document.getElementById('scan-status-container');
        
        const progressContainer = document.createElement('div');
        progressContainer.id = 'scan-progress-container';
        progressContainer.className = 'mb-4 hidden';
        
        progressContainer.innerHTML = `
            <div class="text-sm text-gray-400 mb-1">Scan Progress</div>
            <div class="w-full bg-gray-700 rounded-full h-2.5 mb-1">
                <div id="scan-progress-bar" class="bg-blue-600 h-2.5 rounded-full" style="width: 0%"></div>
            </div>
            <div class="flex justify-between text-xs text-gray-500">
                <span>0%</span>
                <span id="scan-progress-text">0%</span>
                <span>100%</span>
            </div>
        `;
        
        // Insert after status container
        if (statusContainer) {
            statusContainer.insertAdjacentElement('afterend', progressContainer);
        } else {
            scanContainer.insertBefore(progressContainer, scanContainer.firstChild);
        }
    }
}

/**
 * Stop an ongoing BLE scan
 */
BleScanner.prototype.stopScan = async function() {
    // Add this check to prevent multiple stop requests
    if (this._stoppingInProgress) {
        console.warn('Stop scan already in progress, ignoring duplicate request');
        return;
    }
    
    this._stoppingInProgress = true;
    
    try {
        console.log('Stopping BLE scan');
        
        if (this.scanMethod === 'websocket') {
            // Stop via WebSocket
            await this.bleWebSocket.sendCommand('stop_scan', {});
            this.processScanStop(true);
        } else {
            // Stop via REST API
            const response = await fetch('/api/ble/device/scan/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });
            
            if (response.ok) {
                const result = await response.json();
                this.processScanStop(true);
                console.log('Scan stopped successfully', result);
            } else {
                // Even if the API failed, we should update UI state
                console.warn('Failed to stop scan via API, updating UI anyway');
                this.processScanStop(false);
            }
        }
    } catch (error) {
        console.error('Error stopping scan:', error);
        // Still update UI even if there was an error
        this.processScanStop(false);
    } finally {
        // Reset flag after the operation completes (success or failure)
        this._stoppingInProgress = false;
    }
}

/**
 * Process scan stop (common code for both success and failure cases)
 */
// FIX 6: Add defensive checks to the processScanStop method
BleScanner.prototype.processScanStop = function(success = true) {
    // Set scanning state to false
    this.scanning = false;
    
    // Update UI state
    this.updateUI({
        isScanning: false,
        scanError: success ? null : 'Failed to stop scan properly'
    });
    
    // Clear the progress interval if it exists
    if (this.progressInterval) {
        clearInterval(this.progressInterval);
        this.progressInterval = null;
    }
    
    // Make sure we're not in an error handling state
    this._handlingError = false;
    
    // Emit scan stopped event - don't emit if already handling an error
    BleEvents.emit(BLE_EVENTS.SCAN_STOPPED, {
        timestamp: Date.now(),
        success: success
    });
}

/**
 * Handle scan results from the server
 */
BleScanner.prototype.handleScanResults = function(results) {
    BleLogger.info('Scanner', 'handleScanResults', 'Processing scan results', {
        deviceCount: results.devices?.length || 0,
        scanDuration: results.duration || 'unknown'
    });
    
    // Log each discovered device (summarized)
    if (results.devices && results.devices.length > 0) {
        BleLogger.debug('Scanner', 'handleScanResults', 'Discovered devices', {
            devices: results.devices.map(d => ({
                name: d.name || 'Unnamed',
                address: d.address,
                rssi: d.rssi
            }))
        });
    }
    
    // Prevent duplicate handling
    if (this._handlingScanResults) {
        return;
    }
    
    try {
        this._handlingScanResults = true;
        
        console.log(`Received ${results.devices?.length || 0} devices from scan`);
        
        // Store scan results
        if (results.devices) {
            // Process and store devices
            this.lastScanResults = results.devices.map(device => ({
                ...device,
                lastSeen: Date.now()
            }));
            
            // Update device list in the UI
            this.updateDeviceList(this.lastScanResults);
            
            // Update UI state
            this.updateUI({
                isScanning: false,
                scanComplete: true,
                scanError: null,
                lastScanTimestamp: results.timestamp || Date.now()
            });
        }
        
    } finally {
        this._handlingScanResults = false;
    }
}

BleScanner.prototype.updateDevicesList = function() {
    // Clear the device list
    if (this.deviceList) {
        this.deviceList.innerHTML = '';
        
        if (this.devices.length === 0) {
            const noDevicesElement = document.createElement('div');
            noDevicesElement.className = 'text-center py-4 text-gray-400';
            noDevicesElement.textContent = 'No devices found. Start a new scan to discover devices.';
            this.deviceList.appendChild(noDevicesElement);
            return;
        }
        
        // Add each device to the list
        this.devices.forEach(device => {
            const deviceElement = this.createDeviceElement(device);
            this.deviceList.appendChild(deviceElement);
        });
    }
    
    // Update device counter if present
    const deviceCounter = document.getElementById('device-counter');
    if (deviceCounter) {
        deviceCounter.textContent = this.devices.length.toString();
    }
}

BleScanner.prototype.createDeviceElement = function(device) {
    const deviceEl = document.createElement('div');
    deviceEl.className = 'bg-gray-800 hover:bg-gray-750 p-3 rounded-md mb-2 transition duration-200';
    deviceEl.setAttribute('data-address', device.address || '');
    
    // Format RSSI as signal strength bars
    let rssiIndicator;
    if (device.rssi) {
        const rssi = parseInt(device.rssi);
        rssiIndicator = this.getRssiIndicator(rssi);
    } else {
        rssiIndicator = '<div class="text-gray-500"><i class="fas fa-signal-slash"></i></div>';
    }
    
    deviceEl.innerHTML = `
        <div class="flex justify-between items-center">
            <div class="flex-1">
                <div class="font-medium text-white">${device.name || 'Unknown Device'}</div>
                <div class="text-sm text-gray-400">${device.address || 'Unknown Address'}</div>
            </div>
            <div class="flex items-center">
                ${rssiIndicator}
                <button class="ml-2 connect-btn px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-sm">
                    Connect
                </button>
                <button class="ml-2 details-btn px-2 py-1 bg-gray-600 hover:bg-gray-500 text-white rounded-md text-sm">
                    <i class="fas fa-info-circle"></i>
                </button>
            </div>
        </div>
    `;
    
    // Add event listeners
    const connectBtn = deviceEl.querySelector('.connect-btn');
    if (connectBtn) {
        connectBtn.addEventListener('click', () => {
            this.connectToDevice(device);
        });
    }
    
    const detailsBtn = deviceEl.querySelector('.details-btn');
    if (detailsBtn) {
        detailsBtn.addEventListener('click', () => {
            this.showDeviceDetails(device);
        });
    }
    
    return deviceEl;
}

BleScanner.prototype.getRssiIndicator = function(rssi) {
    const bars = [];
    const maxBars = 4;
    
    // Determine how many bars to show based on RSSI value
    let activeBars;
    if (rssi >= -60) {
        activeBars = 4;
    } else if (rssi >= -70) {
        activeBars = 3;
    } else if (rssi >= -80) {
        activeBars = 2;
    } else if (rssi >= -90) {
        activeBars = 1;
    } else {
        activeBars = 0;
    }
    
    // Determine color based on signal strength
    let color;
    if (activeBars >= 3) {
        color = 'bg-green-500';
    } else if (activeBars >= 2) {
        color = 'bg-yellow-500';
    } else {
        color = 'bg-red-500';
    }
    
    // Create the bars
    let html = `<div class="flex items-end h-4 space-x-1 mr-2" title="Signal Strength: ${rssi} dBm">`;
    
    for (let i = 0; i < maxBars; i++) {
        const height = 3 + i * 3; // Increasing heights: 3px, 6px, 9px, 12px
        const isActive = i < activeBars;
        html += `<div class="w-1 h-${height}px ${isActive ? color : 'bg-gray-600'}"></div>`;
    }
    
    html += `</div>`;
    return html;
}

BleScanner.prototype.connectToDevice = function(device) {
    if (!device || !device.address) {
        BleUI.showToast('Invalid device information', 'error');
        return;
    }
    
    // Emit event to connect to the device
    BleEvents.emit(BLE_EVENTS.CONNECT_REQUEST, {
        device: device,
        timestamp: Date.now()
    });
}

BleScanner.prototype.showDeviceDetails = function(device) {
    // Create HTML for the modal
    const detailsHTML = `
        <div id="device-details-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-gray-800 rounded-lg p-6 max-w-lg w-full">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-medium">${device.name || 'Unknown Device'}</h3>
                    <button class="text-gray-400 hover:text-white" onclick="document.getElementById('device-details-modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="space-y-4">
                    <div>
                        <div class="text-sm text-gray-400">Address</div>
                        <div class="font-mono">${device.address || 'N/A'}</div>
                    </div>
                    
                    <div>
                        <div class="text-sm text-gray-400">Signal Strength</div>
                        <div>${device.rssi || 'N/A'} dBm</div>
                    </div>
                    
                    ${device.manufacturer_data ? `
                    <div>
                        <div class="text-sm text-gray-400">Manufacturer Data</div>
                        <div class="font-mono text-xs bg-gray-900 p-2 rounded overflow-x-auto">
                            ${JSON.stringify(device.manufacturer_data, null, 2)}
                        </div>
                    </div>
                    ` : ''}
                    
                    ${device.service_data ? `
                    <div>
                        <div class="text-sm text-gray-400">Service Data</div>
                        <div class="font-mono text-xs bg-gray-900 p-2 rounded overflow-x-auto">
                            ${JSON.stringify(device.service_data, null, 2)}
                        </div>
                    </div>
                    ` : ''}
                    
                    ${device.service_uuids && device.service_uuids.length ? `
                    <div>
                        <div class="text-sm text-gray-400">Service UUIDs</div>
                        <div class="space-y-1">
                            ${device.service_uuids.map(uuid => `<div class="font-mono text-xs">${uuid}</div>`).join('')}
                        </div>
                    </div>
                    ` : ''}
                </div>
                
                <div class="mt-6 flex justify-end">
                    <button class="connect-modal-btn bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded">
                        Connect to Device
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Check if modal already exists, remove it
    const existingModal = document.getElementById('device-details-modal');
    if (existingModal) {
        existingModal.remove(); // Remove existing modal
    }
    
    // Create new modal
    const modalDiv = document.createElement('div');
    modalDiv.innerHTML = detailsHTML;
    document.body.appendChild(modalDiv.firstChild);
    
    // Get the modal element
    const modalElement = document.getElementById('device-details-modal');
    
    // Add connect button event listener
    const connectButton = modalElement.querySelector('.connect-modal-btn');
    if (connectButton) {
        connectButton.addEventListener('click', () => {
            this.connectToDevice(device);
            // Close the modal
            document.getElementById('device-details-modal').remove();
        });
    }
}

// Method to initialize the scanner - useful for external setup
BleScanner.prototype.initialize = function() {
    console.log('Initializing BLE scanner component');
    // This method can be extended with additional initialization if needed
    return Promise.resolve();
}

// Initialize the BLE scanner
const bleScanner = new BleScanner();

// Export for use in other modules
export default bleScanner;
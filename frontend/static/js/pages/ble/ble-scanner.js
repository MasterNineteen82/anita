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
    /**
     * Create a BLE Scanner
     * @param {Object} options - Scanner options
     */
    constructor(options = {}) {
        // Initialize members
        this.devices = [];
        this.scanning = false;
        this.isScanningActive = false;
        this.scanResults = [];
        this.allowMockDevices = options.allowMockDevices || false;
        this.mockDevices = this.getMockScanResults();
        this.scanTime = options.scanTime || 5;
        this.updateDevicesList = options.updateDevicesList;
        this.displayScanResults = options.displayScanResults;
        
        // Initialize BleEvents - either use the provided instance or create a new one
        this.bleEvents = options.bleEvents || (window.bleEventsInstance || null);
        
        if (!this.bleEvents) {
            console.warn('BLE Events not provided, event functions will be unavailable');
        }
        
        // Initialize API client
        if (options.apiClient) {
            this.apiClient = options.apiClient;
        } else {
            // Import BleApiClient asynchronously if needed
            import('./ble-api-client.js').then(module => {
                const BleApiClient = module.BleApiClient;
                this.apiClient = new BleApiClient({
                    baseUrl: options.baseUrl || '',
                    mockFallback: this.allowMockDevices,
                    debug: options.debug || false
                });
                console.log('Created new API client in BleScanner');
            }).catch(error => {
                console.error('Failed to import BleApiClient:', error);
            });
        }
        
        // Create default app state
        console.warn('BLE: Creating default app state for scanner');
        window.bleLog?.('BLE: Creating default app state for scanner');
        
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
        
        // Get the BleEvents instance from the window
        this.bleEvents = window.bleEvents || BleEvents.getInstance();
        
        // Listen for scan events from the BLE Events system
        this.bleEvents.on(BLE_EVENTS.SCAN_STARTED, (event) => {
            this.scanning = true;
            this.updateUI();
            
            // Start progress animation
            this.startProgressAnimation(event.config?.scan_time || this.scanTimeout);
        });
        
        // Listen for scan completed events
        this.bleEvents.on(BLE_EVENTS.SCAN_COMPLETED, (event) => {
            this.completeScan(event.devices || []);
        });
        
        // Listen for scan error events
        this.bleEvents.on(BLE_EVENTS.SCAN_ERROR, (error) => {
            this.handleScanError(error);
        });
        
        // Listen for scan progress events
        this.bleEvents.on(BLE_EVENTS.SCAN_PROGRESS, (progress) => {
            this.updateScanProgress(progress.percentage || 0);
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
        this.bleEvents.emit(BleEvents.SCAN_COMPLETED, {
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
        this.bleEvents.emit(BLE_EVENTS.SCAN_ERROR, {
            error: errorMessage,
            timestamp: Date.now()
        });
        
        this.bleEvents.emit('BLE_SCAN_ERROR_HANDLED', {
            error: errorMessage,
            timestamp: Date.now()
        });
    }

    /**
     * Start scanning for BLE devices
     * @param {number} scanTime - Time in seconds to scan for
     * @param {boolean} activeScan - Whether to do an active scan
     * @param {boolean} mockScan - Whether to use mock data
     * @returns {Promise<Object>} - The scan results
     */
    async startScan(scanTime = 5, activeScan = true, mockScan = false) {
        if (this.scanning) {
            console.warn('Scan already in progress');
            return false;
        }

        this.scanning = true;
        this.isScanningActive = true;
        console.log('Starting BLE scan...');

        try {
            const scanParams = {
                scan_time: this.scanTime,
                active: true,
                name_prefix: this.namePrefix || null,
                service_uuids: this.serviceUuids.length > 0 ? this.serviceUuids : null
            };

            const response = await fetch('/api/ble/device/scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(scanParams)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Scan started:', data);

            // Fetch scan results after scan time
            setTimeout(() => this.fetchScanResults(), this.scanTime * 1000);
            return true;
        } catch (error) {
            console.error('Error starting scan:', error);
            this.scanning = false;
            this.isScanningActive = false;
            BleUI.showToast(`Scan failed to start: ${error.message}`, 'error');

            if (this.allowMockDevices) {
                console.log('Using mock devices due to scan failure');
                this.scanResults = this.mockDevices;
                this.displayScanResults(this.scanResults);
                return true;
            }
            return false;
        }
    }

    async fetchScanResults() {
        try {
            const response = await fetch('/api/ble/device/discovered');
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Scan results:', data);
            this.scanResults = data.devices || [];

            if (this.scanResults.length === 0 && this.allowMockDevices) {
                console.log('No devices found, using mock devices');
                this.scanResults = this.mockDevices;
            }

            this.displayScanResults(this.scanResults);
        } catch (error) {
            console.error('Error fetching scan results:', error);
            BleUI.showToast(`Failed to fetch scan results: ${error.message}`, 'error');

            if (this.allowMockDevices) {
                console.log('Using mock devices due to fetch failure');
                this.scanResults = this.mockDevices;
                this.displayScanResults(this.scanResults);
            }
        } finally {
            this.scanning = false;
            this.isScanningActive = false;
        }
    }

    getMockScanResults() {
        return [
            {
                address: '00:11:22:33:44:55',
                name: 'Mock Device 1',
                rssi: -75,
                services: []
            },
            {
                address: 'AA:BB:CC:DD:EE:FF',
                name: 'Mock Device 2',
                rssi: -65,
                services: []
            }
        ];
    }

    /**
     * Get discovered devices from the backend using the /api/ble/device/discovered endpoint
     * @returns {Promise<Object>} - The discovered devices
     */
    async getDiscoveredDevices() {
        try {
            console.log('Retrieving discovered devices from /api/ble/device/discovered');
            const response = await this.apiClient.request('/api/ble/device/discovered', {
                method: 'GET'
            });
            
            if (response && response.status === 'success') {
                const devices = response.devices || [];
                console.log(`Retrieved ${devices.length} devices from /api/ble/device/discovered`);
                return { status: 'success', devices };
            } else {
                console.warn('Failed to get discovered devices:', response);
                return { status: 'error', devices: [], message: response ? response.message : 'Unknown error' };
            }
        } catch (error) {
            console.error('Error getting discovered devices:', error);
            throw error;
        }
    }
    
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

    /**
     * Process and normalize device data from various sources
     * @param {Object} device - The device data to process
     * @returns {Object} - The processed device data
     */
    processDeviceData(device) {
        // Ensure we have a valid device object
        if (!device) {
            console.warn('Attempted to process empty device data');
            return {
                address: 'unknown',
                name: 'Unknown Device',
                rssi: 0,
                timestamp: Date.now()
            };
        }
        
        // Create a normalized device object
        const processedDevice = {
            // Essential properties with fallbacks
            address: device.address || device.mac_address || device.id || 'unknown',
            name: device.name || device.local_name || 'Unknown Device',
            rssi: device.rssi || 0,
            
            // Additional properties
            services: device.services || device.service_uuids || [],
            manufacturerData: device.manufacturer_data || device.manufacturerData || null,
            
            // Add timestamp for tracking when we received this data
            timestamp: Date.now()
        };
        
        console.debug('Processed device data:', processedDevice);
        return processedDevice;
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
    this.bleEvents.emit(BLE_EVENTS.SCAN_STOPPED, {
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

BleScanner.prototype.connectToDevice = async function(device) {
    if (!device || !device.address) {
        BleUI.showToast('Invalid device information', 'error');
        return;
    }
    
    try {
        // Show connecting status
        BleUI.showToast(`Connecting to ${device.name || device.address}...`, 'info');
        
        // Get the API client
        const apiClient = window.bleApiClient;
        if (!apiClient) {
            throw new Error('BLE API client not available');
        }
        
        // Attempt to connect to the device
        const response = await apiClient.connectToDevice(device.address, {
            timeout: 15,  // 15 second timeout
            retry: true,
            autoReconnect: true
        });
        
        if (response && response.status === 'success') {
            // Update the connected devices UI
            this.updateConnectedDevicesList(device);
            
            // Show success message
            BleUI.showToast(`Connected to ${device.name || device.address}`, 'success');
            
            // Emit events
            this.bleEvents.emit(BLE_EVENTS.DEVICE_CONNECTED, {
                device: device,
                timestamp: Date.now()
            });
            
            return true;
        } else {
            throw new Error(response?.message || 'Unknown connection error');
        }
    } catch (error) {
        console.error('Scan error:', error.message || 'Unknown scan error');
        BleUI.showToast(`Connection failed: ${error.message || 'Unknown error'}`, 'error');
        this.bleEvents.emit(BLE_EVENTS.SCAN_ERROR, { error: error.message });
        return false;
    }
};

/**
 * Update the connected devices list with a new connected device
 * @param {Object} device The connected device
 */
BleScanner.prototype.updateConnectedDevicesList = function(device) {
    // Get the connected devices element
    const connectedDevicesEl = document.getElementById('connected-devices-list');
    if (!connectedDevicesEl) {
        console.error('Connected devices container not found');
        return;
    }
    
    // Check if we need to create the list
    if (connectedDevicesEl.innerHTML.includes('No connected devices')) {
        connectedDevicesEl.innerHTML = '';
    }
    
    // Check if device is already in the list
    const existingDevice = document.getElementById(`connected-device-${device.address}`);
    if (existingDevice) {
        // Device already in list, update it
        existingDevice.querySelector('.device-name').textContent = device.name || 'Unknown Device';
        return;
    }
    
    // Create a new connected device element
    const deviceEl = document.createElement('div');
    deviceEl.id = `connected-device-${device.address}`;
    deviceEl.className = 'flex items-center justify-between p-3 mb-2 bg-gray-800 rounded-lg';
    
    // Add device icon based on device type
    let deviceIcon = 'bluetooth';
    if (device.device_type) {
        if (device.device_type.toLowerCase().includes('wearable')) deviceIcon = 'watch';
        else if (device.device_type.toLowerCase().includes('phone')) deviceIcon = 'mobile';
        else if (device.device_type.toLowerCase().includes('computer')) deviceIcon = 'laptop';
        else if (device.device_type.toLowerCase().includes('sensor')) deviceIcon = 'sensor';
    }
    
    deviceEl.innerHTML = `
        <div class="flex items-center">
            <div class="mr-3 p-2 bg-blue-900 rounded-full">
                <svg class="w-5 h-5 text-blue-300" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M11 0C9.35 0 8 1.35 8 3V17C8 18.65 9.35 20 11 20H13C14.65 20 16 18.65 16 17V3C16 1.35 14.65 0 13 0H11ZM11 2H13C13.55 2 14 2.45 14 3V17C14 17.55 13.55 18 13 18H11C10.45 18 10 17.55 10 17V3C10 2.45 10.45 2 11 2Z" />
                </svg>
            </div>
            <div>
                <div class="font-medium device-name">${device.name || 'Unknown Device'}</div>
                <div class="text-xs text-gray-400">${device.address}</div>
            </div>
        </div>
        <div class="flex space-x-2">
            <button class="px-2 py-1 text-xs bg-red-600 text-white rounded disconnect-btn">
                Disconnect
            </button>
        </div>
    `;
    
    // Add the device to the list
    connectedDevicesEl.appendChild(deviceEl);
    
    // Add event listener to disconnect button
    const disconnectBtn = deviceEl.querySelector('.disconnect-btn');
    if (disconnectBtn) {
        disconnectBtn.addEventListener('click', async () => {
            await this.disconnectDevice(device);
        });
    }
    
    // Switch to the connected devices tab
    this.switchToConnectedDevicesTab();
};

/**
 * Disconnect from a connected device
 * @param {Object} device The device to disconnect from
 */
BleScanner.prototype.disconnectDevice = async function(device) {
    if (!device || !device.address) {
        BleUI.showToast('Invalid device information', 'error');
        return;
    }
    
    try {
        // Show disconnecting status
        BleUI.showToast(`Disconnecting from ${device.name || device.address}...`, 'info');
        
        // Get the API client
        const apiClient = window.bleApiClient;
        if (!apiClient) {
            throw new Error('BLE API client not available');
        }
        
        // Attempt to disconnect
        const response = await apiClient.disconnectDevice(device.address);
        
        if (response && response.status === 'success') {
            // Remove the device from the connected devices list
            const deviceEl = document.getElementById(`connected-device-${device.address}`);
            if (deviceEl) {
                deviceEl.remove();
            }
            
            // Check if we need to show the no devices message
            const connectedDevicesEl = document.getElementById('connected-devices-list');
            if (connectedDevicesEl && connectedDevicesEl.children.length === 0) {
                connectedDevicesEl.innerHTML = `
                    <div class="text-center py-4 text-gray-400">No connected devices</div>
                `;
            }
            
            // Show success message
            BleUI.showToast(`Disconnected from ${device.name || device.address}`, 'success');
            
            // Emit events
            this.bleEvents.emit(BLE_EVENTS.DEVICE_DISCONNECTED, {
                device: device,
                timestamp: Date.now()
            });
            
            return true;
        } else {
            throw new Error(response?.message || 'Unknown disconnection error');
        }
    } catch (error) {
        console.error('Disconnection error:', error.message || 'Unknown error');
        BleUI.showToast(`Disconnection failed: ${error.message || 'Unknown error'}`, 'error');
        return false;
    }
};

/**
 * Switch to the connected devices tab
 */
BleScanner.prototype.switchToConnectedDevicesTab = function() {
    const connectedTab = document.querySelector('[data-tab="connected-devices"]');
    if (connectedTab) {
        // Find current active tab and deactivate it
        const activeTab = document.querySelector('.tab-btn.active');
        if (activeTab) {
            activeTab.classList.remove('active', 'bg-blue-600');
            activeTab.classList.add('bg-gray-700');
            
            // Hide the active tab content
            const activeContent = document.getElementById(activeTab.dataset.tab);
            if (activeContent) {
                activeContent.classList.add('hidden');
            }
        }
        
        // Activate the connected devices tab
        connectedTab.classList.add('active', 'bg-blue-600');
        connectedTab.classList.remove('bg-gray-700');
        
        // Show the connected devices content
        const connectedContent = document.getElementById('connected-devices');
        if (connectedContent) {
            connectedContent.classList.remove('hidden');
        }
    }
};

BleScanner.prototype.renderScannedDevices = function(devices) {
    const containerEl = document.getElementById('scanned-devices-list');
    if (!containerEl) {
        console.error('Scanned devices container not found');
        return;
    }
    
    // Clear existing devices
    containerEl.innerHTML = '';
    
    if (!devices || devices.length === 0) {
        containerEl.innerHTML = '<div class="text-center py-4 text-gray-400">No devices found</div>';
        return;
    }
    
    // Sort devices by RSSI (strongest signal first)
    devices.sort((a, b) => (b.rssi || -100) - (a.rssi || -100));
    
    // Create list items for each device
    devices.forEach(device => {
        const displayName = device.display_name || device.name || 'Unknown Device';
        const deviceType = device.device_type || 'Unknown Type';
        const manufacturer = device.manufacturer || 'Unknown Manufacturer';
        
        // Create the device list item
        const deviceEl = document.createElement('div');
        deviceEl.className = 'device-item bg-gray-800 rounded-lg p-3 mb-2 hover:bg-gray-700 cursor-pointer';
        deviceEl.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex-1">
                    <div class="font-medium">${displayName}</div>
                    <div class="text-xs text-gray-400">${deviceType} | ${manufacturer}</div>
                    <div class="text-xs font-mono text-gray-500">${device.address || 'No Address'}</div>
                </div>
                <div class="flex flex-col items-end">
                    <div class="text-sm ${this._getRssiColorClass(device.rssi)}">${device.rssi || 'N/A'} dBm</div>
                    <button class="connect-device-btn mt-2 text-xs bg-blue-600 hover:bg-blue-500 text-white px-2 py-1 rounded">
                        Connect
                    </button>
                </div>
            </div>
        `;
        
        // Add the device to the DOM
        containerEl.appendChild(deviceEl);
        
        // Add event listener to the whole device row for device details
        deviceEl.addEventListener('click', (e) => {
            // Ignore if the click was on the connect button
            if (e.target.classList.contains('connect-device-btn') || 
                e.target.closest('.connect-device-btn')) {
                e.stopPropagation();
                return;
            }
            
            this.showDeviceDetails(device);
        });
        
        // Add event listener to connect button
        const connectBtn = deviceEl.querySelector('.connect-device-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent triggering the device details
                this.connectToDevice(device);
            });
        }
    });
};

BleScanner.prototype.showDeviceDetails = function(device) {
    if (!device) {
        console.error('No device data provided');
        return;
    }
    
    // Log that we're showing device details
    console.log(`Showing details for device: ${device.name || device.address || 'Unknown Device'}`);
    
    // Check if modal already exists, remove it
    const existingModal = document.getElementById('device-details-modal');
    if (existingModal) {
        existingModal.remove(); // Remove existing modal
    }
    
    // Create the modal container element directly
    const modalElement = document.createElement('div');
    modalElement.id = 'device-details-modal';
    modalElement.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    
    // Create the modal content
    modalElement.innerHTML = `
        <div class="bg-gray-800 rounded-lg p-6 max-w-lg w-full">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-medium">${device.display_name || device.name || 'Unknown Device'}</h3>
                <button class="text-gray-400 hover:text-white px-2 py-1 rounded" id="close-device-modal">
                    X Close
                </button>
            </div>
            
            <div class="space-y-4">
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <div class="text-sm text-gray-400">Device Type</div>
                        <div>${device.device_type || 'Unknown'}</div>
                    </div>
                    
                    <div>
                        <div class="text-sm text-gray-400">Manufacturer</div>
                        <div>${device.manufacturer || 'Unknown'}</div>
                    </div>
                </div>
                
                <div>
                    <div class="text-sm text-gray-400">Address</div>
                    <div class="font-mono">${device.address || 'N/A'}</div>
                </div>
                
                <div>
                    <div class="text-sm text-gray-400">Signal Strength</div>
                    <div>${device.rssi || 'N/A'} dBm</div>
                </div>
                
                ${device.service_info && device.service_info.length ? `
                <div>
                    <div class="text-sm text-gray-400">Services</div>
                    <div class="bg-gray-900 p-2 rounded overflow-auto max-h-32">
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="text-gray-400 text-left">
                                    <th class="pb-1">Service</th>
                                    <th class="pb-1">Category</th>
                                    <th class="pb-1">UUID</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${device.service_info.map(service => `
                                    <tr>
                                        <td class="pr-2">${service.name}</td>
                                        <td class="pr-2">${service.category}</td>
                                        <td class="font-mono text-xs">${service.uuid}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
                ` : ''}
                
                ${device.manufacturer_info ? `
                <div>
                    <div class="text-sm text-gray-400">Manufacturer Details</div>
                    <div class="bg-gray-900 p-2 rounded overflow-auto max-h-32">
                        ${Object.entries(device.manufacturer_info).map(([id, info]) => `
                            <div class="mb-1">
                                <span class="text-blue-400">${info.company_name}</span> 
                                <span class="text-xs text-gray-400">(${id})</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
                
                ${device.metadata && device.metadata.manufacturer_data ? `
                <div>
                    <div class="text-sm text-gray-400">Raw Manufacturer Data</div>
                    <div class="font-mono text-xs bg-gray-900 p-2 rounded overflow-x-auto">
                        ${JSON.stringify(device.metadata.manufacturer_data, null, 2)}
                    </div>
                </div>
                ` : ''}
                
                ${device.metadata && device.metadata.service_data ? `
                <div>
                    <div class="text-sm text-gray-400">Service Data</div>
                    <div class="font-mono text-xs bg-gray-900 p-2 rounded overflow-x-auto">
                        ${JSON.stringify(device.metadata.service_data, null, 2)}
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
    `;
    
    // Add the modal to the document body
    document.body.appendChild(modalElement);
    
    // Add event listeners
    const closeButton = modalElement.querySelector('#close-device-modal');
    if (closeButton) {
        closeButton.addEventListener('click', () => {
            modalElement.remove();
        });
    }
    
    // Add connect button event listener
    const connectButton = modalElement.querySelector('.connect-modal-btn');
    if (connectButton) {
        connectButton.addEventListener('click', () => {
            this.connectToDevice(device);
            modalElement.remove();
        });
    }
    
    // Add click outside modal to close
    modalElement.addEventListener('click', (e) => {
        if (e.target === modalElement) {
            modalElement.remove();
        }
    });
}

/**
 * Method to initialize the scanner - useful for external setup
 */
BleScanner.prototype.initialize = function() {
    console.log('Initializing BLE scanner component');
    // This method can be extended with additional initialization if needed
    return Promise.resolve();
}

// Initialize the BLE scanner
const bleScanner = new BleScanner();

// Export for use in other modules
export default bleScanner;
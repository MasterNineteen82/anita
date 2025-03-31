import { BleUI } from './ble-ui.js';
import { BleEvents, BLE_EVENTS } from './ble-events.js';
import { BleWebSocket } from './ble-websocket.js';

/**
 * Handles scanning for nearby BLE devices
 */
export class BleScanner {
    constructor() {
        this.scanning = false;
        this.scanResults = [];
        this.uiElements = {
            scanBtn: null,
            stopScanBtn: null,
            scanProgress: null,
            deviceList: null
        };
    }
    
    /**
     * Initialize the scanner module
     */
    async initialize() {
        console.log('Initializing BLE Scanner module');
        
        // Get UI elements
        this.uiElements.scanBtn = document.getElementById('scan-btn');
        this.uiElements.stopScanBtn = document.getElementById('stop-scan-btn');
        this.uiElements.scanProgress = document.getElementById('scan-progress');
        this.uiElements.deviceList = document.getElementById('devices-list');
        
        // Register event listeners
        if (this.uiElements.scanBtn) {
            this.uiElements.scanBtn.addEventListener('click', () => this.startScan());
        }
        
        if (this.uiElements.stopScanBtn) {
            this.uiElements.stopScanBtn.addEventListener('click', () => this.stopScan());
        }
        
        // Register for events
        BleEvents.on(BLE_EVENTS.SCAN_RESULT, (result) => this.handleScanResult(result));
        BleEvents.on(BLE_EVENTS.SCAN_COMPLETED, () => this.handleScanCompleted());

        // Register for scan-related events
        BleEvents.on(BleEvents.SCAN_RESULT, (data) => {
            console.log('Real-time scan result received:', data);
            if (data.device && !data.device.isMock) {
                this.addDevice(data.device);
                this.updateDeviceList();
            }
        });
        
        console.log('BLE Scanner module initialized');
    }
    
    /**
     * Start scanning for BLE devices
     */
    async startScan() {
        console.log('Starting BLE scan');
        
        if (this.scanning) {
            BleUI.showToast('Scan already in progress', 'warning');
            return;
        }
        
        this.scanning = true;
        this.scanResults = [];
        this.updateScanUI(true);
        BleUI.showToast('Scanning for devices...', 'info');
        
        try {
            // Updated parameter names to match new ScanParams model
            const response = await fetch('/api/ble/device/scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    scan_time: parseFloat(document.getElementById('scan-time')?.value || 5),
                    active: document.getElementById('active-scanning')?.checked || true,
                    filter_duplicates: true,
                    service_uuids: [] // Optional service UUID filtering
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Scan failed');
            }
            
            const result = await response.json();
            this.scanResults = result.devices || [];
            
            // Process and display results
            this.updateDeviceList();
            BleUI.showToast(`Found ${this.scanResults.length} devices`, 'success');
        } catch (error) {
            console.error('Scan error:', error);
            BleUI.showToast(`Scan failed: ${error.message}`, 'error');
        } finally {
            this.scanning = false;
            this.updateScanUI(false);
        }
    }
    
    /**
     * Stop scanning for BLE devices
     */
    stopScan() {
        if (!this.scanning) {
            return;
        }
        
        this.scanning = false;
        this.updateScanUI(false);
        BleUI.showToast('Scanning stopped', 'info');
        
        // If WebSocket is connected, send stop command
        if (BleWebSocket.isConnected) {
            BleWebSocket.sendCommand('ble.scan.stop');
        }
    }
    
    /**
     * Update scan UI elements
     */
    updateScanUI(scanning) {
        if (this.uiElements.scanBtn) {
            this.uiElements.scanBtn.classList.toggle('hidden', scanning);
        }
        
        if (this.uiElements.stopScanBtn) {
            this.uiElements.stopScanBtn.classList.toggle('hidden', !scanning);
        }
        
        if (this.uiElements.scanProgress) {
            if (scanning) {
                this.uiElements.scanProgress.style.width = '0%';
                this.startProgressAnimation();
            } else {
                this.uiElements.scanProgress.style.width = '100%';
                setTimeout(() => {
                    if (this.uiElements.scanProgress) {
                        this.uiElements.scanProgress.style.width = '0%';
                    }
                }, 1000);
            }
        }
    }
    
    /**
     * Start progress bar animation
     */
    startProgressAnimation() {
        let progress = 0;
        const interval = setInterval(() => {
            if (!this.scanning) {
                clearInterval(interval);
                return;
            }
            
            progress += 2;
            if (progress > 100) {
                clearInterval(interval);
                return;
            }
            
            if (this.uiElements.scanProgress) {
                this.uiElements.scanProgress.style.width = `${progress}%`;
            }
        }, 100);
    }
    
    /**
     * Add a device to scan results
     */
    addDevice(device) {
        // Check if device already exists
        const index = this.scanResults.findIndex(d => d.address === device.address);
        if (index >= 0) {
            // Update existing device
            this.scanResults[index] = device;
        } else {
            // Add new device
            this.scanResults.push(device);
        }
    }
    
    /**
     * Handle scan result event
     */
    handleScanResult(result) {
        if (result && result.device) {
            this.addDevice(result.device);
            this.updateDeviceList();
        }
    }
    
    /**
     * Handle scan completed event
     */
    handleScanCompleted() {
        this.scanning = false;
        this.updateScanUI(false);
        BleUI.showToast(`Scan completed. Found ${this.scanResults.length} devices.`, 'success');
    }
    
    /**
     * Update device list in UI
     */
    updateDeviceList() {
        if (!this.uiElements.deviceList) {
            return;
        }
        
        // Clear existing list
        this.uiElements.deviceList.innerHTML = '';
        
        // Sort devices by signal strength (strongest first)
        const sortedDevices = [...this.scanResults].sort((a, b) => (b.rssi || -100) - (a.rssi || -100));
        
        if (sortedDevices.length === 0) {
            this.uiElements.deviceList.innerHTML = '<div class="text-gray-500">No devices found</div>';
            return;
        }
        
        // Add devices to list
        sortedDevices.forEach(device => {
            const deviceEl = document.createElement('div');
            deviceEl.className = 'bg-gray-700 rounded p-3 mb-2 flex justify-between items-center';
            deviceEl.innerHTML = `
                <div class="flex-1">
                    <div class="font-medium">${device.name || 'Unknown Device'}</div>
                    <div class="text-gray-400 text-sm">${device.address || 'Unknown Address'}</div>
                </div>
                <div class="text-right">
                    <div class="text-sm font-medium">${device.rssi || 'N/A'} dBm</div>
                    <div class="w-16 bg-gray-600 rounded-full h-1.5 mt-1">
                        <div class="bg-blue-500 h-1.5 rounded-full" style="width: ${Math.min(100, Math.max(0, ((device.rssi || -100) + 100) / 0.7))}%"></div>
                    </div>
                </div>
            `;
            
            this.uiElements.deviceList.appendChild(deviceEl);
        });
    }
}
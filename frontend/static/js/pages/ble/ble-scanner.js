import { BleUI } from './ble-ui.js';
import { BleEvents, BLE_EVENTS } from './ble-events.js';
import { sendWebSocketCommand, BleWebSocket } from './ble-websocket.js';

/**
 * BLE Scanner Module
 * Handles scanning for nearby BLE devices
 */
export class BleScanner {
    constructor(state = {}) {
        this.state = state;
        this.scanning = false;
        this.scanResults = new Map();
        this.uiElements = {
            scanBtn: null,
            stopScanBtn: null,
            deviceList: null,
            scanIndicator: null
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
        this.uiElements.deviceList = document.getElementById('device-list');
        this.uiElements.scanIndicator = document.getElementById('scan-indicator');

        // Check if UI elements are available, and create them if they are missing
        if (!this.uiElements.scanBtn) {
            this.uiElements.scanBtn = this.createButton('scan-btn', 'Scan', 'ble-btn ble-btn-primary', '<i class="fas fa-play"></i> Scan');
        }
        if (!this.uiElements.stopScanBtn) {
            this.uiElements.stopScanBtn = this.createButton('stop-scan-btn', 'Stop', 'ble-btn ble-btn-secondary', '<i class="fas fa-stop"></i> Stop');
        }
        if (!this.uiElements.scanIndicator) {
            this.uiElements.scanIndicator = this.createScanIndicator('scan-indicator', 'Scanning...');
        }
        if (!this.uiElements.deviceList) {
            this.uiElements.deviceList = this.createDeviceList('device-list');
        }

        // Add event listeners
        this.uiElements.scanBtn.addEventListener('click', () => this.startScan());
        this.uiElements.stopScanBtn.addEventListener('click', () => this.stopScan());

        // Register event handlers
        BleEvents.on(BLE_EVENTS.SCAN_RESULT, (result) => this.handleScanResult(result));
        BleEvents.on(BLE_EVENTS.SCAN_COMPLETED, (result) => this.handleScanCompleted(result));

        console.log('BLE Scanner module created');
    }

    /**
     * Create a button element
     * @param {string} id - The ID of the button
     * @param {string} text - The text of the button
     * @param {string} className - The class name of the button
     * @param {string} innerHTML - The inner HTML of the button
     * @returns {HTMLElement} - The button element
     */
    createButton(id, text, className, innerHTML) {
        const button = document.createElement('button');
        button.id = id;
        button.className = className;
        button.innerHTML = innerHTML;
        return button;
    }

    /**
     * Create a scan indicator element
     * @param {string} id - The ID of the scan indicator
     * @param {string} text - The text of the scan indicator
     * @returns {HTMLElement} - The scan indicator element
     */
    createScanIndicator(id, text) {
        const span = document.createElement('span');
        span.id = id;
        span.className = 'hidden text-green-500';
        span.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${text}`;
        return span;
    }

    /**
     * Create a device list element
     * @param {string} id - The ID of the device list
     * @returns {HTMLElement} - The device list element
     */
    createDeviceList(id) {
        const ul = document.createElement('ul');
        ul.id = id;
        ul.className = 'divide-y divide-gray-700';
        return ul;
    }

    /**
     * Start scanning for BLE devices
     */
    async startScan() {
        if (this.scanning) {
            BleUI.showToast('Scan already in progress', 'warning');
            return;
        }

        if (!BleWebSocket.isConnected) {
            BleUI.showToast('WebSocket not connected. Please wait...', 'warning');
            return;
        }

        this.scanning = true;
        this.scanResults.clear();
        this.updateScanIndicator(true);
        BleUI.showToast('Scanning for devices...', 'info');

        // Send command to start scan
        sendWebSocketCommand('ble.scan.start', { duration: 10 });
    }

    /**
     * Stop scanning for BLE devices
     */
    async stopScan() {
        if (!this.scanning) {
            BleUI.showToast('No scan in progress', 'warning');
            return;
        }

        this.scanning = false;
        this.updateScanIndicator(false);
        BleUI.showToast('Stopping scan...', 'info');

        // Send command to stop scan
        sendWebSocketCommand('ble.scan.stop');
    }

    /**
     * Handle a scan result
     * @param {object} result - Scan result data
     */
    handleScanResult(result) {
        const { device, timestamp } = result;

        if (!device || !device.address) {
            console.warn('Invalid scan result:', result);
            return;
        }

        // Format address
        device.formattedAddress = BleUI.formatAddress(device.address);

        // Format signal strength
        device.signalStrengthFormatted = BleUI.formatSignalStrength(device.rssi);

        // Add or update device in scan results
        this.scanResults.set(device.address, device);

        // Update device list
        this.updateDeviceList();
    }

    /**
     * Handle scan completion
     * @param {object} result - Scan completion data
     */
    handleScanCompleted(result) {
        this.scanning = false;
        this.updateScanIndicator(false);
        BleUI.showToast(`Scan completed. Found ${this.scanResults.size} devices`, 'success');
    }

    /**
     * Update the scan indicator
     * @param {boolean} scanning - Whether scanning is in progress
     */
    updateScanIndicator(scanning) {
        if (scanning) {
            this.uiElements.scanIndicator.classList.remove('hidden');
        } else {
            this.uiElements.scanIndicator.classList.add('hidden');
        }
    }

    /**
     * Update the device list in the UI
     */
    updateDeviceList() {
        // Clear existing list
        this.uiElements.deviceList.innerHTML = '';

        // Sort devices by signal strength (strongest first)
        const sortedDevices = Array.from(this.scanResults.values()).sort((a, b) => b.rssi - a.rssi);

        // Add devices to the list
        sortedDevices.forEach(device => {
            const listItem = document.createElement('li');
            listItem.className = 'ble-device-item';
            listItem.innerHTML = `
                <div class="ble-device-info">
                    <div class="ble-device-name">${device.name || 'Unknown Device'}</div>
                    <div class="ble-device-address">${device.formattedAddress}</div>
                </div>
                <div class="ble-device-signal">${device.signalStrengthFormatted}</div>
            `;
            this.uiElements.deviceList.appendChild(listItem);
        });
    }
}
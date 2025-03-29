/**
 * BLE Device Module
 * Handles device connection and management
 */

import { BLE } from './ble.js';

export class BleDevice {
    constructor(state = {}) {
        this.state = state;
        this.deviceInfoElement = null;
        this.noDeviceMessage = null;
        this.deviceNameElement = null;
        this.deviceAddressElement = null;
        this.batteryContainer = null;
        this.batteryLevelBar = null;
        this.batteryLevelText = null;
        this.disconnectButton = null;
        this.isConnected = false;
        this.deviceAddress = null;
        this.deviceName = null;
        this.services = [];
        
        console.log('BLE Device module created');
    }
    
    async initialize() {
        console.log('Initializing BLE Device component');
        
        // Get DOM elements
        this.deviceInfoElement = document.getElementById('device-info');
        this.noDeviceMessage = document.getElementById('no-device-message');
        this.deviceNameElement = document.getElementById('device-name');
        this.deviceAddressElement = document.getElementById('device-address');
        this.batteryContainer = document.getElementById('battery-container');
        this.batteryLevelBar = document.getElementById('battery-level-bar');
        this.batteryLevelText = document.getElementById('battery-level-text');
        this.disconnectButton = document.getElementById('disconnect-btn');
        this.refreshBatteryBtn = document.getElementById('refresh-battery-btn');
        
        // Add event listeners
        if (this.disconnectButton) {
            this.disconnectButton.addEventListener('click', () => this.disconnectDevice());
        }
        
        if (this.refreshBatteryBtn) {
            this.refreshBatteryBtn.addEventListener('click', () => this.refreshBatteryLevel());
        }
        
        // Subscribe to connection events
        if (window.bleEvents) {
            window.bleEvents.on('device_connected', device => this.handleDeviceConnected(device));
            window.bleEvents.on('device_disconnected', () => this.handleDeviceDisconnected());
        }
        
        // Set up BLE event handlers
        BLE.on('ble.connection', this.handleConnection.bind(this));
        BLE.on('ble.disconnect', this.handleDisconnection.bind(this));
        
        console.log('BLE Device component initialized');
    }
    
    handleConnection(data) {
        if (data && data.device) {
            this.isConnected = true;
            this.deviceAddress = data.device;
            
            // Update UI
            this.updateConnectionStatus(true);
            
            // Load device services
            this.loadServices();
        }
    }
    
    handleDisconnection(data) {
        this.isConnected = false;
        
        // Update UI
        this.updateConnectionStatus(false);
        
        // Clear services
        this.services = [];
        this.updateServicesUI();
    }
    
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        const statusTextElement = document.getElementById('connection-status-text');
        
        if (statusElement && statusTextElement) {
            statusElement.classList.toggle('connected', connected);
            statusElement.classList.toggle('disconnected', !connected);
            
            statusTextElement.textContent = connected ? 
                `Connected to ${this.deviceAddress}` : 
                'Not connected';
        }
    }
    
    async loadServices() {
        if (!this.isConnected || !this.deviceAddress) {
            console.warn('Cannot load services: Not connected to a device');
            return;
        }
        
        try {
            const response = await BLE.request('GET', `/services/${this.deviceAddress}`);
            
            if (response.services) {
                this.services = response.services;
                this.updateServicesUI();
            }
        } catch (error) {
            console.error('Error loading services:', error);
        }
    }
    
    updateServicesUI() {
        const servicesContainer = document.getElementById('services-container');
        if (!servicesContainer) {
            return;
        }
        
        if (!this.isConnected || this.services.length === 0) {
            servicesContainer.innerHTML = `
                <div class="p-4 text-center text-gray-500">
                    No services available. Connect to a device first.
                </div>
            `;
            return;
        }
        
        // Create HTML for services and characteristics
        const servicesHTML = this.services.map(service => {
            const characteristicsHTML = service.characteristics.map(characteristic => {
                return `
                    <div class="ml-4 mb-2 p-2 bg-gray-50 rounded border border-gray-200">
                        <div class="flex items-center justify-between">
                            <div>
                                <span class="text-sm font-semibold">${characteristic.uuid}</span>
                                <div class="text-xs text-gray-500">
                                    ${this.getCharacteristicProperties(characteristic)}
                                </div>
                            </div>
                            <div class="space-x-2">
                                ${this.getCharacteristicActions(characteristic)}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            
            return `
                <div class="mb-4 p-3 bg-white rounded shadow-sm">
                    <div class="font-medium">
                        <span class="text-blue-600">
                            <i class="fas fa-layer-group mr-1"></i>
                            Service: ${service.uuid}
                        </span>
                    </div>
                    <div class="mt-2">
                        ${characteristicsHTML}
                    </div>
                </div>
            `;
        }).join('');
        
        servicesContainer.innerHTML = servicesHTML;
        
        // Add event listeners to buttons
        this.addCharacteristicEventListeners();
    }
    
    getCharacteristicProperties(characteristic) {
        const properties = [];
        
        if (characteristic.properties.read) properties.push('Read');
        if (characteristic.properties.write) properties.push('Write');
        if (characteristic.properties.notify) properties.push('Notify');
        if (characteristic.properties.indicate) properties.push('Indicate');
        
        return properties.join(', ');
    }
    
    getCharacteristicActions(characteristic) {
        const actions = [];
        
        if (characteristic.properties.read) {
            actions.push(`
                <button class="btn btn-xs btn-info read-btn" data-uuid="${characteristic.uuid}">
                    <i class="fas fa-eye"></i>
                </button>
            `);
        }
        
        if (characteristic.properties.write) {
            actions.push(`
                <button class="btn btn-xs btn-primary write-btn" data-uuid="${characteristic.uuid}">
                    <i class="fas fa-edit"></i>
                </button>
            `);
        }
        
        if (characteristic.properties.notify || characteristic.properties.indicate) {
            actions.push(`
                <button class="btn btn-xs btn-success notify-btn" data-uuid="${characteristic.uuid}">
                    <i class="fas fa-bell"></i>
                </button>
            `);
        }
        
        return actions.join('');
    }
    
    addCharacteristicEventListeners() {
        // Read buttons
        document.querySelectorAll('.read-btn').forEach(button => {
            button.addEventListener('click', () => {
                const uuid = button.getAttribute('data-uuid');
                this.readCharacteristic(uuid);
            });
        });
        
        // Write buttons
        document.querySelectorAll('.write-btn').forEach(button => {
            button.addEventListener('click', () => {
                const uuid = button.getAttribute('data-uuid');
                this.writeCharacteristic(uuid);
            });
        });
        
        // Notify buttons
        document.querySelectorAll('.notify-btn').forEach(button => {
            button.addEventListener('click', () => {
                const uuid = button.getAttribute('data-uuid');
                
                // Toggle the notification state
                if (button.classList.contains('active')) {
                    button.classList.remove('active');
                    this.unsubscribeFromCharacteristic(uuid);
                } else {
                    button.classList.add('active');
                    this.subscribeToCharacteristic(uuid);
                }
            });
        });
    }
    
    async readCharacteristic(uuid) {
        if (!this.isConnected || !this.deviceAddress) {
            console.warn('Cannot read characteristic: Not connected to a device');
            return;
        }
        
        try {
            const response = await BLE.request('GET', `/characteristics/${this.deviceAddress}/${uuid}`);
            
            if (response.value) {
                // Display the value in a toast or dialog
                alert(`Characteristic ${uuid}: ${response.value}`);
            }
        } catch (error) {
            console.error(`Error reading characteristic ${uuid}:`, error);
            alert(`Failed to read: ${error.message}`);
        }
    }
    
    async writeCharacteristic(uuid) {
        if (!this.isConnected || !this.deviceAddress) {
            console.warn('Cannot write characteristic: Not connected to a device');
            return;
        }
        
        // Prompt for the value to write
        const value = prompt(`Enter value for ${uuid}:`);
        if (value === null) return; // User cancelled
        
        try {
            await BLE.request('POST', `/characteristics/${this.deviceAddress}/${uuid}`, { value });
            
            // Show success message
            alert(`Value written to ${uuid}`);
        } catch (error) {
            console.error(`Error writing to characteristic ${uuid}:`, error);
            alert(`Failed to write: ${error.message}`);
        }
    }
    
    subscribeToCharacteristic(uuid) {
        if (!this.isConnected) {
            console.warn('Cannot subscribe: Not connected to a device');
            return;
        }
        
        BLE.subscribeToCharacteristic(uuid);
    }
    
    unsubscribeFromCharacteristic(uuid) {
        BLE.unsubscribeFromCharacteristic(uuid);
    }
    
    async disconnect() {
        if (!this.isConnected || !this.deviceAddress) {
            console.warn('Not connected to a device');
            return;
        }
        
        try {
            await BLE.request('POST', `/disconnect/${this.deviceAddress}`);
            
            // The disconnection will be handled via WebSocket events
        } catch (error) {
            console.error('Error disconnecting:', error);
            alert(`Failed to disconnect: ${error.message}`);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.bleDevice = new BleDevice();
});
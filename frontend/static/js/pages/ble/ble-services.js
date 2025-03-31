import { BleEvents } from './ble-events.js';
import { BleUI } from './ble-ui.js';

/**
 * Handles BLE service discovery and interaction
 */
export class BleServices {
    /**
     * Initialize the BLE Services module
     * @param {Object} state - Global application state
     */
    constructor(state = {}) {
        this.state = state;
        this.services = [];
        this.characteristics = {};
        this.selectedService = null;
    }
    
    /**
     * Initialize the services module
     */
    initialize() {
        console.log('Initializing BLE Services module');
        
        // Get container elements
        this.servicesList = document.getElementById('services-list');
        this.characteristicsList = document.getElementById('characteristics-list');
        
        // Set up event handlers
        this.setupEventHandlers();
        
        // Set up event subscriptions
        BleEvents.on(BleEvents.DEVICE_CONNECTED, (data) => this.onDeviceConnected(data));
        BleEvents.on(BleEvents.DEVICE_DISCONNECTED, () => this.onDeviceDisconnected());
        
        console.log('BLE Services module initialized');
    }
    
    /**
     * Set up event handlers for UI interactions
     */
    setupEventHandlers() {
        // Add characteristic read/write/notify handlers when characteristics are rendered
        this.addCharacteristicEventListeners();
    }
    
    /**
     * Handle device connected event
     * @param {Object} data - Connection data
     */
    async onDeviceConnected(data) {
        if (!data || !data.device) return;
        
        try {
            // Show loading state
            this.showServicesLoading();
            
            // Get services for the connected device
            await this.discoverServices(data.device);
        } catch (error) {
            console.error('Error discovering services:', error);
            this.showServicesError(error);
        }
    }
    
    /**
     * Handle device disconnected event
     */
    onDeviceDisconnected() {
        // Clear services and characteristics
        this.services = [];
        this.characteristics = {};
        this.selectedService = null;
        
        // Update UI
        this.clearServicesUI();
    }
    
    /**
     * Show loading state for services
     */
    showServicesLoading() {
        if (this.servicesList) {
            this.servicesList.innerHTML = `
                <div class="text-center p-4">
                    <div class="inline-block animate-spin mb-2">
                        <i class="fas fa-spinner"></i>
                    </div>
                    <div>Discovering services...</div>
                </div>
            `;
        }
        
        if (this.characteristicsList) {
            this.characteristicsList.innerHTML = '';
        }
    }
    
    /**
     * Show error state for services
     * @param {Error} error - The error that occurred
     */
    showServicesError(error) {
        if (this.servicesList) {
            this.servicesList.innerHTML = `
                <div class="text-center p-4 text-red-500">
                    <div class="mb-2">
                        <i class="fas fa-exclamation-circle"></i>
                    </div>
                    <div>Error discovering services</div>
                    <div class="text-sm">${error.message}</div>
                </div>
            `;
        }
    }
    
    /**
     * Clear services UI
     */
    clearServicesUI() {
        if (this.servicesList) {
            this.servicesList.innerHTML = `
                <div class="text-center p-4 text-gray-500">
                    <div class="mb-2">
                        <i class="fas fa-info-circle"></i>
                    </div>
                    <div>Connect to a device to discover services</div>
                </div>
            `;
        }
        
        if (this.characteristicsList) {
            this.characteristicsList.innerHTML = '';
        }
    }
    
    /**
     * Discover services for a device
     * @param {string} deviceId - Device ID
     */
    async discoverServices(deviceId) {
        try {
            BleUI.showToast('Discovering services...', 'info');
            
            // Updated endpoint for the new service manager
            const response = await fetch('/api/ble/services');
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to discover services');
            }
            
            const result = await response.json();
            
            // Handle the new ServicesResult format
            this.services = result.services || [];
            
            // Update UI
            this.updateServicesUI();
            
            BleUI.showToast(`Discovered ${this.services.length} services`, 'success');
            
            // Emit event for other components
            BleEvents.emit(BleEvents.DEVICE_SERVICES_DISCOVERED, {
                device: deviceId,
                services: this.services,
                count: this.services.length
            });
            
            return this.services;
        } catch (error) {
            console.error('Error discovering services:', error);
            BleUI.showToast(`Service discovery failed: ${error.message}`, 'error');
            throw error;
        }
    }
    
    /**
     * Render services list
     */
    renderServices() {
        if (!this.servicesList) return;
        
        if (!this.services || this.services.length === 0) {
            this.servicesList.innerHTML = `
                <div class="text-center p-4 text-gray-500">
                    <div class="mb-2">
                        <i class="fas fa-info-circle"></i>
                    </div>
                    <div>No services found for this device</div>
                </div>
            `;
            return;
        }
        
        this.servicesList.innerHTML = this.services.map((service, index) => `
            <div class="service-item p-2 cursor-pointer ${index % 2 === 0 ? 'bg-gray-700' : 'bg-gray-800'}" 
                data-uuid="${service.uuid}">
                <div class="font-medium">${service.name || 'Unknown Service'}</div>
                <div class="text-xs text-gray-400">${service.uuid}</div>
            </div>
        `).join('');
        
        // Add click handlers
        const serviceItems = this.servicesList.querySelectorAll('.service-item');
        serviceItems.forEach(item => {
            item.addEventListener('click', async () => {
                // Clear selected state from all items
                serviceItems.forEach(i => i.classList.remove('bg-blue-900', 'border-l-4', 'border-blue-500'));
                
                // Add selected state to clicked item
                item.classList.add('bg-blue-900', 'border-l-4', 'border-blue-500');
                
                // Get service UUID
                const uuid = item.getAttribute('data-uuid');
                
                // Load characteristics
                await this.loadCharacteristics(uuid);
            });
        });
    }
    
    /**
     * Load characteristics for a service
     * @param {string} serviceUuid - Service UUID
     */
    async loadCharacteristics(serviceUuid) {
        if (!this.characteristicsList) return;
        
        try {
            // Show loading state
            this.characteristicsList.innerHTML = `
                <div class="text-center p-4">
                    <div class="inline-block animate-spin mb-2">
                        <i class="fas fa-spinner"></i>
                    </div>
                    <div>Loading characteristics...</div>
                </div>
            `;
            
            // Store selected service
            this.selectedService = serviceUuid;
            
            // Get device address from state
            const deviceAddress = this.state.connectedDevice;
            if (!deviceAddress) {
                throw new Error('No device connected');
            }
            
            // Load characteristics if not already loaded
            if (!this.characteristics[serviceUuid]) {
                const response = await fetch(`/api/ble/device/${deviceAddress}/service/${serviceUuid}/characteristics`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to load characteristics');
                }
                
                const data = await response.json();
                this.characteristics[serviceUuid] = data.characteristics || [];
            }
            
            // Render characteristics
            this.renderCharacteristics(serviceUuid);
        } catch (error) {
            console.error('Error loading characteristics:', error);
            this.characteristicsList.innerHTML = `
                <div class="text-center p-4 text-red-500">
                    <div class="mb-2">
                        <i class="fas fa-exclamation-circle"></i>
                    </div>
                    <div>Error loading characteristics</div>
                    <div class="text-sm">${error.message}</div>
                </div>
            `;
        }
    }
    
    /**
     * Render characteristics for a service
     * @param {string} serviceUuid - Service UUID
     */
    renderCharacteristics(serviceUuid) {
        if (!this.characteristicsList) return;
        
        const characteristics = this.characteristics[serviceUuid] || [];
        
        if (characteristics.length === 0) {
            this.characteristicsList.innerHTML = `
                <div class="text-center p-4 text-gray-500">
                    <div class="mb-2">
                        <i class="fas fa-info-circle"></i>
                    </div>
                    <div>No characteristics found for this service</div>
                </div>
            `;
            return;
        }
        
        this.characteristicsList.innerHTML = characteristics.map((characteristic, index) => {
            // Determine properties
            const canRead = characteristic.properties.includes('read');
            const canWrite = characteristic.properties.includes('write') || characteristic.properties.includes('write-without-response');
            const canNotify = characteristic.properties.includes('notify') || characteristic.properties.includes('indicate');
            
            return `
                <div class="characteristic-item p-3 ${index % 2 === 0 ? 'bg-gray-700' : 'bg-gray-800'}" 
                    data-uuid="${characteristic.uuid}">
                    <div class="font-medium">${characteristic.name || 'Unknown Characteristic'}</div>
                    <div class="text-xs text-gray-400 mb-2">${characteristic.uuid}</div>
                    
                    <div class="flex flex-wrap gap-1 mb-2">
                        ${characteristic.properties.map(prop => 
                            `<span class="px-2 py-0.5 text-xs rounded bg-gray-600">${prop}</span>`
                        ).join('')}
                    </div>
                    
                    <div class="flex space-x-2 mt-3">
                        ${canRead ? `
                            <button class="read-characteristic px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm"
                                data-uuid="${characteristic.uuid}">
                                <i class="fas fa-eye mr-1"></i> Read
                            </button>
                        ` : ''}
                        
                        ${canWrite ? `
                            <button class="write-characteristic px-2 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-sm"
                                data-uuid="${characteristic.uuid}">
                                <i class="fas fa-edit mr-1"></i> Write
                            </button>
                        ` : ''}
                        
                        ${canNotify ? `
                            <button class="notify-characteristic px-2 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm"
                                data-uuid="${characteristic.uuid}" data-state="off">
                                <i class="fas fa-bell mr-1"></i> Notify
                            </button>
                        ` : ''}
                    </div>
                    
                    <div class="characteristic-value mt-2 p-2 bg-gray-900 rounded hidden"></div>
                </div>
            `;
        }).join('');
        
        // Add event listeners for buttons
        this.addCharacteristicEventListeners();
    }
    
    /**
     * Add event listeners to characteristic buttons
     */
    addCharacteristicEventListeners() {
        // Read characteristic buttons
        document.querySelectorAll('.read-characteristic').forEach(btn => {
            btn.addEventListener('click', event => {
                const uuid = event.currentTarget.getAttribute('data-uuid');
                this.readCharacteristic(uuid);
            });
        });
        
        // Write characteristic buttons
        document.querySelectorAll('.write-characteristic').forEach(btn => {
            btn.addEventListener('click', event => {
                const uuid = event.currentTarget.getAttribute('data-uuid');
                this.writeCharacteristic(uuid);
            });
        });
        
        // Notify characteristic buttons
        document.querySelectorAll('.notify-characteristic').forEach(btn => {
            btn.addEventListener('click', event => {
                const uuid = event.currentTarget.getAttribute('data-uuid');
                const currentState = event.currentTarget.getAttribute('data-state');
                
                if (currentState === 'off') {
                    this.startNotifications(uuid, event.currentTarget);
                } else {
                    this.stopNotifications(uuid, event.currentTarget);
                }
            });
        });
    }
    
    /**
     * Read a characteristic
     * @param {string} uuid - Characteristic UUID
     */
    async readCharacteristic(uuid) {
        try {
            // Get device address from state
            const deviceAddress = this.state.connectedDevice;
            if (!deviceAddress) {
                throw new Error('No device connected');
            }
            
            // Find the characteristic element
            const charElement = document.querySelector(`.characteristic-item[data-uuid="${uuid}"]`);
            if (!charElement) return;
            
            // Get the value element
            const valueElement = charElement.querySelector('.characteristic-value');
            if (!valueElement) return;
            
            // Show loading state
            valueElement.innerHTML = '<div class="animate-pulse">Reading...</div>';
            valueElement.classList.remove('hidden');
            
            // Send read request
            const response = await fetch(`/api/ble/device/${deviceAddress}/characteristic/${uuid}/read`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to read characteristic');
            }
            
            const data = await response.json();
            
            // Format value based on type
            let formattedValue = '';
            
            if (data.encoding === 'hex') {
                formattedValue = `<span class="font-mono text-blue-300">${data.value}</span>`;
            } else if (data.encoding === 'utf-8' || data.encoding === 'utf8') {
                formattedValue = `<span class="text-green-300">"${data.value}"</span>`;
            } else if (data.encoding === 'base64') {
                formattedValue = `<span class="font-mono text-purple-300">${data.value}</span>`;
            } else {
                formattedValue = `<span class="font-mono">${data.value}</span>`;
            }
            
            // Update value element
            valueElement.innerHTML = `
                <div>
                    <div class="text-xs text-gray-400 mb-1">Value (${data.encoding}):</div>
                    <div>${formattedValue}</div>
                </div>
            `;
        } catch (error) {
            console.error(`Error reading characteristic ${uuid}:`, error);
            
            // Show error in value element
            const charElement = document.querySelector(`.characteristic-item[data-uuid="${uuid}"]`);
            if (charElement) {
                const valueElement = charElement.querySelector('.characteristic-value');
                if (valueElement) {
                    valueElement.innerHTML = `
                        <div class="text-red-400">
                            <i class="fas fa-exclamation-circle mr-1"></i>
                            Error: ${error.message}
                        </div>
                    `;
                    valueElement.classList.remove('hidden');
                }
            }
            
            // Show toast notification
            BleUI.showToast(`Failed to read characteristic: ${error.message}`, 'error');
        }
    }
    
    /**
     * Write to a characteristic
     * @param {string} uuid - Characteristic UUID
     */
    async writeCharacteristic(uuid) {
        try {
            // Create dialog for write value input
            const dialogContent = document.createElement('div');
            dialogContent.innerHTML = `
                <div class="p-3">
                    <h3 class="text-lg font-semibold mb-3">Write to Characteristic</h3>
                    <div class="text-sm text-gray-400 mb-3">${uuid}</div>
                    
                    <div class="mb-3">
                        <label for="write-value-type" class="block text-sm font-medium text-gray-300 mb-1">Value Type</label>
                        <select id="write-value-type" class="w-full bg-gray-700 text-white border border-gray-600 rounded px-3 py-2">
                            <option value="text">Text (UTF-8)</option>
                            <option value="hex">Hex</option>
                            <option value="bytes">Bytes (comma-separated)</option>
                        </select>
                    </div>
                    
                    <div class="mb-4">
                        <label for="write-value" class="block text-sm font-medium text-gray-300 mb-1">Value</label>
                        <textarea id="write-value" class="w-full bg-gray-700 text-white border border-gray-600 rounded px-3 py-2 h-20"></textarea>
                    </div>
                    
                    <div class="flex justify-end space-x-2">
                        <button id="cancel-write" class="px-3 py-1 bg-gray-600 hover:bg-gray-500 text-white rounded">
                            Cancel
                        </button>
                        <button id="confirm-write" class="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded">
                            Write
                        </button>
                    </div>
                </div>
            `;
            
            // Show the dialog
            const dialog = BleUI.showDialog(dialogContent);
            
            // Handle dialog buttons
            const cancelButton = document.getElementById('cancel-write');
            const confirmButton = document.getElementById('confirm-write');
            
            // Set up type change handler
            const valueTypeSelect = document.getElementById('write-value-type');
            const valueInput = document.getElementById('write-value');
            
            valueTypeSelect.addEventListener('change', () => {
                const type = valueTypeSelect.value;
                
                if (type === 'hex') {
                    valueInput.placeholder = 'Enter hex value (e.g. 01A2B3)';
                } else if (type === 'bytes') {
                    valueInput.placeholder = 'Enter bytes as comma-separated values (e.g. 1,42,255)';
                } else {
                    valueInput.placeholder = 'Enter text value';
                }
            });
            
            // Trigger initial type change
            valueTypeSelect.dispatchEvent(new Event('change'));
            
            // Cancel button
            cancelButton.addEventListener('click', () => {
                BleUI.closeDialog(dialog);
            });
            
            // Confirm button
            confirmButton.addEventListener('click', async () => {
                const valueType = valueTypeSelect.value;
                const value = valueInput.value.trim();
                
                if (!value) {
                    BleUI.showToast('Please enter a value', 'warning');
                    return;
                }
                
                // Close dialog and show loading state
                BleUI.closeDialog(dialog);
                BleUI.showLoading('Writing value...');
                
                try {
                    // Get device address from state
                    const deviceAddress = this.state.connectedDevice;
                    if (!deviceAddress) {
                        throw new Error('No device connected');
                    }
                    
                    // Process value based on type
                    let processedValue;
                    let encoding;
                    
                    if (valueType === 'hex') {
                        // Validate hex format
                        if (!/^[0-9A-Fa-f]+$/.test(value)) {
                            throw new Error('Invalid hex format. Use only 0-9, A-F characters');
                        }
                        processedValue = value;
                        encoding = 'hex';
                    } else if (valueType === 'bytes') {
                        // Parse comma-separated bytes
                        const bytes = value.split(',').map(b => parseInt(b.trim(), 10));
                        if (bytes.some(isNaN)) {
                            throw new Error('Invalid byte format. Use comma-separated numbers (0-255)');
                        }
                        if (bytes.some(b => b < 0 || b > 255)) {
                            throw new Error('Byte values must be between 0 and 255');
                        }
                        processedValue = bytes;
                        encoding = 'bytes';
                    } else {
                        // Text/UTF-8
                        processedValue = value;
                        encoding = 'utf-8';
                    }
                    
                    // Send write request
                    const response = await fetch(`/api/ble/device/${deviceAddress}/characteristic/${uuid}/write`, {
                        method: 'POST',
                        headers: {
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            value: processedValue,
                            encoding: encoding
                        })
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to write characteristic');
                    }
                    
                    const data = await response.json();
                    
                    // Hide loading and show success
                    BleUI.hideLoading();
                    BleUI.showToast('Value written successfully', 'success');
                    
                    // Update UI to show the written value
                    const charElement = document.querySelector(`.characteristic-item[data-uuid="${uuid}"]`);
                    if (charElement) {
                        const valueElement = charElement.querySelector('.characteristic-value');
                        if (valueElement) {
                            let displayValue;
                            
                            if (encoding === 'hex') {
                                displayValue = `<span class="font-mono text-blue-300">${processedValue}</span>`;
                            } else if (encoding === 'utf-8') {
                                displayValue = `<span class="text-green-300">"${processedValue}"</span>`;
                            } else {
                                displayValue = `<span class="font-mono">[${processedValue.join(', ')}]</span>`;
                            }
                            
                            valueElement.innerHTML = `
                                <div>
                                    <div class="text-xs text-gray-400 mb-1">Value written (${encoding}):</div>
                                    <div>${displayValue}</div>
                                </div>
                            `;
                            valueElement.classList.remove('hidden');
                        }
                    }
                } catch (error) {
                    console.error(`Error writing to characteristic ${uuid}:`, error);
                    BleUI.hideLoading();
                    BleUI.showToast(`Failed to write value: ${error.message}`, 'error');
                }
            });
        } catch (error) {
            console.error('Error showing write dialog:', error);
            BleUI.showToast(`Error: ${error.message}`, 'error');
        }
    }
    
    /**
     * Start notifications for a characteristic
     * @param {string} uuid - Characteristic UUID
     * @param {HTMLElement} button - The notify button element
     */
    async startNotifications(uuid, button) {
        try {
            // Get device address from state
            const deviceAddress = this.state.connectedDevice;
            if (!deviceAddress) {
                throw new Error('No device connected');
            }
            
            // Show loading state
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Starting...';
            
            // Send start notifications request
            const response = await fetch(`/api/ble/device/${deviceAddress}/characteristic/${uuid}/notify`, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ enable: true })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to start notifications');
            }
            
            // Update button state
            button.disabled = false;
            button.setAttribute('data-state', 'on');
            button.innerHTML = '<i class="fas fa-bell-slash mr-1"></i> Stop Notify';
            button.classList.remove('bg-purple-600', 'hover:bg-purple-700');
            button.classList.add('bg-red-600', 'hover:bg-red-700');
            
    // Show toast notification
    BleUI.showToast(`Started notifications for ${uuid.substr(-8)}`, 'success');
            
            // Subscribe to notifications from this characteristic
            this.subscribeToNotifications(uuid);
        } catch (error) {
            console.error(`Error starting notifications for ${uuid}:`, error);
            
            // Reset button state
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-bell mr-1"></i> Notify';
            
            // Show toast notification
            BleUI.showToast(`Failed to start notifications: ${error.message}`, 'error');
        }
    }
    
    /**
     * Stop notifications for a characteristic
     * @param {string} uuid - Characteristic UUID
     * @param {HTMLElement} button - The notify button element
     */
    async stopNotifications(uuid, button) {
        try {
            // Get device address from state
            const deviceAddress = this.state.connectedDevice;
            if (!deviceAddress) {
                throw new Error('No device connected');
            }
            
            // Show loading state
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Stopping...';
            
            // Send stop notifications request
            const response = await fetch(`/api/ble/device/${deviceAddress}/characteristic/${uuid}/notify`, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ enable: false })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to stop notifications');
            }
            
            // Update button state
            button.disabled = false;
            button.setAttribute('data-state', 'off');
            button.innerHTML = '<i class="fas fa-bell mr-1"></i> Notify';
            button.classList.remove('bg-red-600', 'hover:bg-red-700');
            button.classList.add('bg-purple-600', 'hover:bg-purple-700');
            
            // Show toast notification
            BleUI.showToast(`Stopped notifications for ${uuid.substr(-8)}`, 'success');
            
            // Unsubscribe from notifications
            this.unsubscribeFromNotifications(uuid);
        } catch (error) {
            console.error(`Error stopping notifications for ${uuid}:`, error);
            
            // Reset button state
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-bell-slash mr-1"></i> Stop Notify';
            
            // Show toast notification
            BleUI.showToast(`Failed to stop notifications: ${error.message}`, 'error');
        }
    }
    
    /**
     * Subscribe to notifications from a characteristic
     * @param {string} uuid - Characteristic UUID
     */
    subscribeToNotifications(uuid) {
        // We're using WebSocket for notifications, so register this UUID
        // for notification handling
        BleEvents.addCharacteristicHandler(uuid, (value, encoding) => {
            this.handleNotification(uuid, value, encoding);
        });
    }
    
    /**
     * Unsubscribe from notifications
     * @param {string} uuid - Characteristic UUID
     */
    unsubscribeFromNotifications(uuid) {
        // Remove the notification handler
        BleEvents.removeCharacteristicHandler(uuid);
    }
    
    /**
     * Handle a notification from a characteristic
     * @param {string} uuid - Characteristic UUID
     * @param {string} value - Notification value
     * @param {string} encoding - Value encoding
     */
    handleNotification(uuid, value, encoding) {
        // Find the characteristic element
        const charElement = document.querySelector(`.characteristic-item[data-uuid="${uuid}"]`);
        if (!charElement) return;
        
        // Get the value element
        let valueElement = charElement.querySelector('.characteristic-value');
        if (!valueElement) {
            // Create the value element if it doesn't exist
            valueElement = document.createElement('div');
            valueElement.className = 'characteristic-value mt-2 p-2 bg-gray-900 rounded';
            charElement.appendChild(valueElement);
        }
        
        // Format value based on encoding
        let formattedValue = '';
        
        if (encoding === 'hex') {
            formattedValue = `<span class="font-mono text-blue-300">${value}</span>`;
        } else if (encoding === 'utf-8' || encoding === 'utf8') {
            formattedValue = `<span class="text-green-300">"${value}"</span>`;
        } else if (encoding === 'base64') {
            formattedValue = `<span class="font-mono text-purple-300">${value}</span>`;
        } else {
            formattedValue = `<span class="font-mono">${value}</span>`;
        }
        
        // Add timestamp
        const timestamp = new Date().toLocaleTimeString();
        
        // Update value element
        valueElement.innerHTML = `
            <div>
                <div class="text-xs text-gray-400 mb-1">
                    Notification (${encoding}) <span class="ml-2">${timestamp}</span>
                </div>
                <div>${formattedValue}</div>
            </div>
        `;
        valueElement.classList.remove('hidden');
        
        // Add notification to the notification log if available
        const notificationLog = document.getElementById('notification-log');
        if (notificationLog) {
            const row = document.createElement('tr');
            const serviceName = this.getServiceName(this.selectedService);
            const charName = this.getCharacteristicName(uuid);
            
            row.innerHTML = `
                <td class="px-3 py-2 text-sm">${timestamp}</td>
                <td class="px-3 py-2 text-sm">${charName}</td>
                <td class="px-3 py-2 text-sm font-mono">${uuid}</td>
                <td class="px-3 py-2 text-sm font-mono">${value}</td>
            `;
            
            // Insert at the beginning
            if (notificationLog.firstChild) {
                notificationLog.insertBefore(row, notificationLog.firstChild);
            } else {
                notificationLog.appendChild(row);
            }
            
            // Limit the number of entries
            const maxEntries = 50;
            while (notificationLog.children.length > maxEntries) {
                notificationLog.removeChild(notificationLog.lastChild);
            }
        }
    }
    
    /**
     * Get a friendly name for a service
     * @param {string} uuid - Service UUID
     * @returns {string} Service name
     */
    getServiceName(uuid) {
        if (!uuid) return 'Unknown Service';
        
        const service = this.services.find(s => s.uuid === uuid);
        return service ? (service.name || 'Unknown Service') : 'Unknown Service';
    }
    
    /**
     * Get a friendly name for a characteristic
     * @param {string} uuid - Characteristic UUID
     * @returns {string} Characteristic name
     */
    getCharacteristicName(uuid) {
        if (!uuid || !this.selectedService) return 'Unknown Characteristic';
        
        const characteristics = this.characteristics[this.selectedService] || [];
        const characteristic = characteristics.find(c => c.uuid === uuid);
        return characteristic ? (characteristic.name || 'Unknown Characteristic') : 'Unknown Characteristic';
    }
}

// Helper functions outside the class
/**
 * Format characteristic values for display
 * @param {string} hexValue - Hexadecimal value
 * @returns {string} - Formatted value
 */
export function formatCharacteristicValue(hexValue) {
    if (!hexValue) return 'No value';

    try {
        const bytes = hexToBytes(hexValue);
        const ascii = bytesToAscii(bytes);
        if (/^[ -~]+$/.test(ascii)) {
            return `${ascii} (ASCII)`;
        }
        return `[${bytes.join(', ')}] (Decimal)`;
    } catch (e) {
        return hexValue;
    }
}

/**
 * Convert hex string to byte array
 * @param {string} hex - Hex string
 * @returns {number[]} - Byte array
 */
function hexToBytes(hex) {
    const bytes = [];
    for (let i = 0; i < hex.length; i += 2) {
        bytes.push(parseInt(hex.substr(i, 2), 16));
    }
    return bytes;
}

/**
 * Convert byte array to ASCII
 * @param {number[]} bytes - Byte array
 * @returns {string} - ASCII string
 */
function bytesToAscii(bytes) {
    return bytes.map(byte => String.fromCharCode(byte)).join('');
}
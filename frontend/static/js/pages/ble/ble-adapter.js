import { BleUI } from './ble-ui.js';

export class BleAdapter {
    constructor() {
        this.adapterInfo = null;
        this.adapterStatus = 'unknown';
        this.adapters = [];
    }

    async initialize() {
        console.log('Initializing BLE Adapter module');
        await this.loadAdapterInfo();
        this.registerEventListeners();
        console.log('BLE Adapter module initialized');
    }

    // Update loadAdapterInfo method
    async loadAdapterInfo() {
        try {
            // New endpoint for adapter information
            const response = await fetch('/api/ble/adapter/info');
            if (!response.ok) {
                throw new Error('Failed to fetch adapter information');
            }
            
            let data = await response.json();
            
            // Handle the new response format from BleAdapterManager
            if (data.primary_adapter) {
                this.adapterInfo = data.primary_adapter;
            } else if (data.adapters && data.adapters.length > 0) {
                this.adapterInfo = data.adapters[0];
            } else {
                throw new Error('No adapter information available');
            }
            
            this.adapterStatus = this.adapterInfo.status === 'powered' ? 'available' : 'unavailable';
            this.updateUI();
        } catch (error) {
            console.error('Failed to get adapters:', error);
            BleUI.showToast('Failed to get adapters: ' + error.message, 'error');
            this.adapterInfo = null;
            this.adapterStatus = 'error';
            this.updateUI();
        }
    }

    updateUI() {
        // Hide loading message
        const loadingMsg = document.querySelector('#adapter-info-content .text-gray-500');
        if (loadingMsg) {
            loadingMsg.style.display = 'none';
        }
        
        const adapterNameElement = document.getElementById('adapter-name');
        const adapterAddressElement = document.getElementById('adapter-address');
        const adapterTypeElement = document.getElementById('adapter-type');
        const adapterStatusTextElement = document.getElementById('adapter-status-text');
        const adapterManufacturerElement = document.getElementById('adapter-manufacturer');
        const adapterPlatformElement = document.getElementById('adapter-platform');

        if (this.adapterInfo) {
            adapterNameElement.textContent = this.adapterInfo.name || 'N/A';
            adapterAddressElement.textContent = this.adapterInfo.address || 'N/A';
            adapterTypeElement.textContent = this.adapterInfo.hardware?.model || this.adapterInfo.name || 'N/A';
            adapterStatusTextElement.textContent = this.adapterInfo.status || 'N/A';
            adapterManufacturerElement.textContent = this.adapterInfo.manufacturer || 'N/A';
            adapterPlatformElement.textContent = this.adapterInfo.platform || 'N/A';
        } else {
            adapterNameElement.textContent = 'No adapter available';
            adapterAddressElement.textContent = 'N/A';
            adapterTypeElement.textContent = 'N/A';
            adapterStatusTextElement.textContent = 'N/A';
            adapterManufacturerElement.textContent = 'N/A';
            adapterPlatformElement.textContent = 'N/A';
        }
    }

    registerEventListeners() {
        const refreshButton = document.getElementById('refresh-adapter-btn');
        if (refreshButton) {
            refreshButton.addEventListener('click', () => this.loadAdapterInfo());
        }
    }

    /**
     * Reset the Bluetooth adapter
     * @returns {Promise<boolean>} Success status
     */
    async resetAdapter() {
        BleUI.showToast('Resetting BLE adapter...', 'info');

        try {
            // Updated endpoint for adapter reset
            const response = await fetch('/api/ble/adapter/reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    restart_service: true,
                    disconnect_devices: true,
                    rescan_after_reset: true
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Adapter reset failed');
            }

            const result = await response.json();
            BleUI.showToast('BLE adapter reset successfully', 'success');
            
            // Refresh adapter info
            this.loadAdapterInfo();
            
            return true;
        } catch (error) {
            console.error('Adapter reset error:', error);
            BleUI.showToast(`Adapter reset failed: ${error.message}`, 'error');
            return false;
        }
    }
}
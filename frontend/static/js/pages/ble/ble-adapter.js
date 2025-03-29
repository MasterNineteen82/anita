import { BLE } from './ble.js';
import { BleUI } from './ble-ui.js';

/**
 * BLE Adapter Module
 * Handles Bluetooth adapter related operations
 */
export class BleAdapter {
    constructor() {
        this.adapterInfo = null;
        this.adapterStatus = 'unknown';
    }

    /**
     * Initialize the adapter module
     */
    async initialize() {
        console.log('Initializing BLE Adapter module');
        await this.loadAdapterInfo();
        console.log('BLE Adapter module initialized');
    }

    /**
     * Load adapter information
     */
    async loadAdapterInfo() {
        try {
            this.adapterInfo = await BLE.request('/adapters');
            this.adapterStatus = this.adapterInfo.powered ? 'powered' : 'unpowered';
            this.updateUI();
        } catch (error) {
            console.error('Failed to get adapters:', error);
            BleUI.logMessage('Failed to get adapters: ' + error.message, 'error');
            this.adapterStatus = 'error';
            this.updateUI();
        }
    }

    /**
     * Update the UI with adapter information
     */
    updateUI() {
        const adapterNameElement = document.getElementById('adapter-name');
        const adapterAddressElement = document.getElementById('adapter-address');
        const adapterTypeElement = document.getElementById('adapter-type');
        const adapterStatusElement = document.getElementById('adapter-status');
        const adapterStatusIndicatorElement = document.getElementById('adapter-status-indicator');
        const adapterStatusTextElement = document.getElementById('adapter-status-text');

        if (adapterNameElement) {
            adapterNameElement.textContent = this.adapterInfo?.name || 'N/A';
        }
        if (adapterAddressElement) {
            adapterAddressElement.textContent = this.adapterInfo?.address || 'N/A';
        }
         if (adapterTypeElement) {
            adapterTypeElement.textContent = this.adapterInfo?.adapterType || 'N/A';
        }

        if (adapterStatusElement) {
            if (this.adapterStatus === 'powered') {
                adapterStatusIndicatorElement.classList.remove('bg-gray-400', 'bg-red-500');
                adapterStatusIndicatorElement.classList.add('bg-green-500');
                adapterStatusTextElement.textContent = 'Powered On';
            } else if (this.adapterStatus === 'unpowered') {
                adapterStatusIndicatorElement.classList.remove('bg-gray-400', 'bg-green-500');
                adapterStatusIndicatorElement.classList.add('bg-red-500');
                adapterStatusTextElement.textContent = 'Powered Off';
            } else {
                adapterStatusIndicatorElement.classList.remove('bg-green-500', 'bg-red-500');
                adapterStatusIndicatorElement.classList.add('bg-gray-400');
                adapterStatusTextElement.textContent = 'Checking adapter...';
            }
        }
    }
}
import { BleUI } from './ble-ui.js';
import { BleEvents, BLE_EVENTS } from './ble-events.js';
import { BleLogger } from './ble-logger.js';
import { BleApiHelper } from './ble-api-helper.js';
import { bleApiClient } from './ble-api-client.js';

/**
 * BLE Adapter module
 * Handles adapter selection and information display
 */
export class BleAdapter {
    constructor(options = {}) {
        this.apiClient = options.apiClient || bleApiClient;
        this.logger = options.logger || console;
        this.adapters = [];
        this.selectedAdapterId = null;
        this.refreshInProgress = false;
        this.events = options.events || window.BleEvents || { emit: () => {} };
        this.currentAdapter = null;
    }

    /**
     * Initialize the BLE adapter functionality
     */
    async initialize() {
        try {
            // Try to get adapter from localStorage first
            const storedAdapter = localStorage.getItem('currentBluetoothAdapter');
            
            if (storedAdapter) {
                const adapterInfo = JSON.parse(storedAdapter);
                this.logger.info(`Loaded adapter from storage: ${adapterInfo.name || adapterInfo.id}`);
                this.currentAdapter = adapterInfo;
                this.updateAdapterInfoUI(adapterInfo);
            }
            
            // Then get the current adapter from the API regardless, to ensure we have the latest status
            const adapterInfo = await this.getAdapterInfo();
            
            // If we got adapter info from the API and it's different from stored, update
            if (adapterInfo && (!this.currentAdapter || adapterInfo.id !== this.currentAdapter.id)) {
                this.currentAdapter = adapterInfo;
                this.updateAdapterInfoUI(adapterInfo);
            }
            
            // Get list of available adapters
            const adapters = await this.getAdapters();
            this.updateAdapterSelectionUI(adapters);
            
            return true;
        } catch (error) {
            this.logger.error(`Error initializing BleAdapter: ${error.message || error}`);
            return false;
        }
    }

    /**
     * Set up event listeners for adapter-related UI elements
     */
    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-adapter-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.getAdapterInfo());
        }
    }

    /**
     * Get adapter information from the server
     */
    async getAdapterInfo() {
        if (this.refreshInProgress) return;
        this.refreshInProgress = true;
        
        const refreshBtn = document.getElementById('refresh-adapter-btn');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Refreshing...';
        }
        
        try {
            this.logger.log('Getting adapter information');
            
            // Get adapter info from API
            const response = await this.apiClient.getAdapterInfo();
            this.logger.debug('Adapter info response:', response);
            
            if (response && response.adapters && response.adapters.length > 0) {
                this.adapters = response.adapters;
                this.logger.info(`Found ${this.adapters.length} Bluetooth adapter(s)`);
                
                // Check if we have a stored adapter that matches one of the found adapters
                const storedAdapter = this.loadAdapterFromStorage();
                if (storedAdapter && this.adapters.some(a => a.id === storedAdapter.id)) {
                    this.currentAdapter = storedAdapter;
                    this.logger.info(`Using stored adapter: ${storedAdapter.name}`);
                } else {
                    // Default to the first adapter if no stored adapter matches
                    this.currentAdapter = this.adapters[0];
                    this.logger.info(`Using default adapter: ${this.currentAdapter.name}`);
                }
                
                // Update UI with the current adapter
                this.updateAdapterInfoUI(this.currentAdapter);
                return this.currentAdapter;
            } else {
                this.logger.warning('No Bluetooth adapters found, using default adapter');
                // Create a default adapter if none are found
                this.adapters = [{
                    id: 'default-adapter',
                    name: 'Default Adapter',
                    address: '00:00:00:00:00:00',
                    available: true,
                    status: 'active',
                    description: 'Default adapter created when no physical adapters are found',
                    manufacturer: 'System',
                    powered: true,
                    discovering: false,
                    pairable: false,
                    paired_devices: 0,
                    firmware_version: 'N/A',
                    supported_features: ['BLE'],
                    system_info: 'Default'
                }];
                this.currentAdapter = this.adapters[0];
                this.updateAdapterInfoUI(this.currentAdapter);
                return this.currentAdapter;
            }
        } catch (error) {
            this.logger.error(`Error fetching adapter info: ${error.message}`);
            // Create a default adapter on error
            this.adapters = [{
                id: 'default-adapter',
                name: 'Default Adapter',
                address: '00:00:00:00:00:00',
                available: true,
                status: 'active',
                description: 'Default adapter created due to error fetching adapter info',
                manufacturer: 'System',
                powered: true,
                discovering: false,
                pairable: false,
                paired_devices: 0,
                firmware_version: 'N/A',
                supported_features: ['BLE'],
                system_info: 'Default'
            }];
            this.currentAdapter = this.adapters[0];
            this.updateAdapterInfoUI(this.currentAdapter);
            return this.currentAdapter;
        } finally {
            this.refreshInProgress = false;
            
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="fas fa-sync mr-2"></i> Refresh Adapter Info';
            }
        }
    }

    /**
     * Get list of available adapters
     * @returns {Promise<Array>} List of available adapters
     */
    async getAdapters() {
        try {
            const adapterInfo = await this.getAdapterInfo();
            
            if (adapterInfo && adapterInfo.adapters) {
                return adapterInfo.adapters;
            } else {
                // Return a default mock adapter if no adapters found
                console.warn('No adapters found in API response, using mock adapter');
                return [{
                    id: "default-adapter",
                    name: "Default BLE Adapter",
                    address: "00:00:00:00:00:00",
                    available: true,
                    status: "available",
                    manufacturer: "System",
                    platform: "Web"
                }];
            }
        } catch (error) {
            console.error('Error getting adapters:', error);
            
            // Return a mock adapter in case of error
            return [{
                id: "mock-adapter",
                name: "Mock BLE Adapter",
                address: "00:00:00:00:00:00",
                available: true,
                status: "available",
                manufacturer: "Virtual",
                platform: "Web"
            }];
        }
    }

    /**
     * Update the adapter info UI with the given adapter data
     */
    updateAdapterInfoUI(adapter) {
        if (!adapter) return;
        
        console.log('Updating adapter UI with data:', adapter);
        
        // Format address for display - if it's a USB path, make it more readable
        let displayAddress = adapter.address || adapter.id || 'Unknown';
        // If we have a USB path, extract the important parts
        if (displayAddress.startsWith('USB\\')) {
            // Try to extract a MAC-like address if it exists at the end
            const macMatch = displayAddress.match(/([0-9A-F]{12})$/i);
            if (macMatch) {
                // Format as a MAC address with colons
                const mac = macMatch[1];
                displayAddress = mac.replace(/(.{2})(?=.)/g, '$1:');
            } else {
                // Otherwise just clean up the path a bit
                displayAddress = displayAddress.replace(/\\/g, '→');
            }
        }
        
        // Create a detailed description combining multiple fields
        const detailFields = [];
        if (adapter.manufacturer) detailFields.push(adapter.manufacturer);
        if (adapter.description && adapter.description !== adapter.name) detailFields.push(adapter.description);
        if (adapter.platform) detailFields.push(`Platform: ${adapter.platform}`);
        const detailedDescription = detailFields.join(' • ');
        
        // Update UI fields with enhanced information
        const fields = {
            'adapter-name': adapter.name || adapter.id || 'Unknown',
            'adapter-address': displayAddress,
            'adapter-type': adapter.type || adapter.system || 'Bluetooth',
            'adapter-status-text': adapter.status || (adapter.available ? 'Available' : 'Unavailable'),
            'adapter-manufacturer': adapter.manufacturer || 'Unknown',
            'adapter-platform': detailedDescription || adapter.platform || adapter.system || 'Unknown'
        };
        
        Object.entries(fields).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        });
        
        // Update status color
        const statusElement = document.getElementById('adapter-status-text');
        if (statusElement) {
            if (adapter.available || adapter.status === 'active' || adapter.status === 'available' || adapter.status === 'OK') {
                statusElement.className = 'bg-gray-700 border border-gray-600 text-green-400 rounded py-2 px-3';
            } else {
                statusElement.className = 'bg-gray-700 border border-gray-600 text-red-400 rounded py-2 px-3';
            }
        }
        
        // Emit event for other components
        this.events.emit('adapter_updated', adapter);
    }

    /**
     * Update the adapter selection UI
     */
    updateAdapterSelectionUI(adapters) {
        // Check if we need to create or update the adapter selector
        let adapterSelectContainer = document.getElementById('adapter-selector-container');
        
        if (!adapterSelectContainer) {
            // Create container
            adapterSelectContainer = document.createElement('div');
            adapterSelectContainer.id = 'adapter-selector-container';
            adapterSelectContainer.className = 'mb-4';
            
            // Add to adapter info content
            const adapterContent = document.getElementById('adapter-info-content');
            if (adapterContent) {
                adapterContent.insertBefore(adapterSelectContainer, adapterContent.firstChild);
            }
        }
        
        // Populate with adapters
        adapterSelectContainer.innerHTML = `
            <label for="adapter-selector" class="block text-sm text-gray-400 mb-1">Select Adapter</label>
            <select id="adapter-selector" class="w-full bg-gray-700 border border-gray-600 text-white rounded py-2 px-3">
                ${adapters.map(adapter => `
                    <option value="${adapter.address}" ${adapter.address === this.selectedAdapterId ? 'selected' : ''}>
                        ${adapter.name || 'Unknown'} (${adapter.address})
                    </option>
                `).join('')}
            </select>
        `;
        
        // Add event listener for selection change
        const selector = document.getElementById('adapter-selector');
        if (selector) {
            selector.addEventListener('change', (e) => {
                this.selectAdapter(e.target.value);
            });
        }
    }

    /**
     * Select an adapter by ID
     */
    async selectAdapter(adapterId) {
        try {
            console.log('Selecting adapter:', adapterId);
            const response = await this.apiClient.selectAdapter(adapterId);
            
            if (response && response.success) {
                this.selectedAdapterId = adapterId;
                this.logger.info(`Adapter selected successfully: ${adapterId}`);
                this.events.emit(BLE_EVENTS.ADAPTER_SELECTED, { adapterId });
                
                // Store adapter info in local storage
                if (this.currentAdapter && this.currentAdapter.id) {
                    localStorage.setItem('currentBluetoothAdapter', JSON.stringify(this.currentAdapter));
                }
                
                return true;
            } else {
                const errorMessage = (response && response.message) || "Unknown error selecting adapter";
                this.logger.error(`Failed to select adapter: ${errorMessage}`);
                return false;
            }
        } catch (error) {
            this.logger.error(`Error selecting adapter: ${error.message || error}`);
            return false;
        }
    }

    /**
     * Reset the adapter
     */
    async resetAdapter(adapterId = null) {
        try {
            const targetId = adapterId || this.selectedAdapterId;
            if (!targetId) {
                throw new Error('No adapter selected');
            }
            
            this.logger.log(`Resetting adapter: ${targetId}`);
            
            const result = await this.apiClient.resetAdapter(targetId);
            
            if (result.status === "success" || result.success) {
                this.logger.log('Adapter reset successful');
                
                // Refresh adapter info after reset
                await this.getAdapterInfo();
                
                return true;
            } else {
                this.logger.error('Adapter reset failed:', result);
                return false;
            }
        } catch (error) {
            this.logger.error('Error resetting adapter:', error);
            return false;
        }
    }
}

// Singleton instance
export const bleAdapter = new BleAdapter();
export default bleAdapter;
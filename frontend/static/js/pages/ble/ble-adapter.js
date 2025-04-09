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
    }

    /**
     * Initialize the BLE adapter functionality
     */
    async initialize() {
        this.logger.log('Initializing BleAdapter');
        
        try {
            // Get adapter information
            await this.getAdapterInfo();
            
            // Add event listeners
            this.setupEventListeners();
            
            return true;
        } catch (error) {
            this.logger.error('Error initializing BleAdapter:', error);
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
            const adapterData = await this.apiClient.getAdapterInfo();
            
            // Update state with adapter info
            if (adapterData.adapters && adapterData.adapters.length > 0) {
                this.adapters = adapterData.adapters;
                this.selectedAdapterId = adapterData.primary_adapter?.address || adapterData.adapters[0].address;
                
                // Update UI
                this.updateAdapterInfoUI(adapterData.primary_adapter || adapterData.adapters[0]);
                this.updateAdapterSelectionUI();
                
                return adapterData;
            } else {
                throw new Error('No adapters found');
            }
        } catch (error) {
            this.logger.error('Error fetching adapter info:', error);
            
            // Update UI with error state
            const adapterContent = document.getElementById('adapter-info-content');
            if (adapterContent) {
                adapterContent.innerHTML = `
                    <div class="text-red-400 p-4">
                        <i class="fas fa-exclamation-triangle mr-2"></i>
                        Error loading adapter information: ${error.message}
                    </div>
                    <button id="retry-adapter-info" class="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1 rounded text-sm mx-4 mb-4">
                        Retry
                    </button>
                `;
                
                // Add event listener to retry button
                const retryButton = document.getElementById('retry-adapter-info');
                if (retryButton) {
                    retryButton.addEventListener('click', () => this.getAdapterInfo());
                }
            }
            
            throw error;
        } finally {
            this.refreshInProgress = false;
            
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="fas fa-sync mr-2"></i> Refresh Adapter Info';
            }
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
    updateAdapterSelectionUI() {
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
                ${this.adapters.map(adapter => `
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
            if (!adapterId) {
                this.logger.warn("No adapter ID provided");
                return false;
            }
            
            this.logger.info(`Selecting adapter: ${adapterId}`);
            
            // Make sure to include the proper id parameter as required by the backend
            const response = await this.apiClient.selectAdapter({ id: adapterId });
            
            if (response && response.success) {
                this.currentAdapter = response.adapter || { id: adapterId };
                this.logger.info(`Adapter selected successfully: ${adapterId}`);
                BleEvents.emit(BLE_EVENTS.ADAPTER_SELECTED, this.currentAdapter);
                return true;
            } else {
                const errorMessage = (response && response.error) || "Unknown error selecting adapter";
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
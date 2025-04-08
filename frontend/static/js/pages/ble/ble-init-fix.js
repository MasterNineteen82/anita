/**
 * BLE Dashboard Initialization Fix
 * Resolves issues with missing DOM elements and module initialization
 */
(function() {
    console.log("🔧 Applying BLE initialization fixes...");

    // Function to create DOM elements if they don't exist
    function createMissingDOMElements() {
        console.log("Creating missing adapter DOM elements...");

        // Get the adapter-info-card
        const adapterCard = document.getElementById('ble-adapter-info-card');
        if (!adapterCard) {
            console.error("Cannot find adapter card to fix");
            return false;
        }

        // Clear any existing content (which may be malformed)
        const existingContent = adapterCard.querySelector('.space-y-4');
        if (existingContent) {
            existingContent.innerHTML = '';
        }

        // Create adapter-info-content if it doesn't exist
        let adapterInfoContent = document.getElementById('adapter-info-content');
        if (!adapterInfoContent) {
            console.log("Creating adapter-info-content");
            adapterInfoContent = document.createElement('div');
            adapterInfoContent.id = 'adapter-info-content';
            adapterInfoContent.className = 'space-y-4 p-4';
            
            // Add to card
            if (existingContent) {
                existingContent.appendChild(adapterInfoContent);
            } else {
                // If we couldn't find the expected container, add directly to card
                adapterCard.appendChild(adapterInfoContent);
            }
        }
        
        // Create required adapter fields
        const requiredFields = [
            { id: 'adapter-name', label: 'Name' },
            { id: 'adapter-address', label: 'Address' },
            { id: 'adapter-type', label: 'Type' },
            { id: 'adapter-status-text', label: 'Status' },
            { id: 'adapter-manufacturer', label: 'Manufacturer' },
            { id: 'adapter-platform', label: 'Platform' }
        ];
        
        requiredFields.forEach(field => {
            if (!document.getElementById(field.id)) {
                const fieldContainer = document.createElement('div');
                fieldContainer.className = 'mb-3';
                fieldContainer.innerHTML = `
                    <label class="block text-sm text-gray-400 mb-1">${field.label}</label>
                    <div class="bg-gray-700 border border-gray-600 text-white rounded py-2 px-3" id="${field.id}">Loading...</div>
                `;
                adapterInfoContent.appendChild(fieldContainer);
            }
        });
        
        // Create refresh button if it doesn't exist
        if (!document.getElementById('refresh-adapter-btn')) {
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'mt-4 flex justify-end';
            buttonContainer.innerHTML = `
                <button type="button" id="refresh-adapter-btn" class="ble-btn ble-btn-secondary">
                    <i class="fas fa-sync mr-2"></i> Refresh Adapter Info
                </button>
            `;
            
            // Add to card
            adapterCard.appendChild(buttonContainer);
        }
        
        return true;
    }
    
    // Function to initialize BLE modules
    async function initializeModules() {
        console.log("Initializing BLE modules...");
        
        try {
            // 1. First, import and initialize the BleAdapter
            const { BleAdapter } = await import('./ble-adapter.js').catch(err => {
                console.error("Failed to import BleAdapter", err);
                // Create a fallback module
                return {
                    BleAdapter: class BleAdapter {
                        constructor() {
                            this.adapters = [];
                            this.selectedAdapterId = null;
                        }
                        
                        async initialize() {
                            console.log("Initializing fallback BleAdapter");
                            await this.getAdapterInfo();
                            return true;
                        }
                        
                        async getAdapterInfo() {
                            try {
                                const response = await fetch('/api/ble/adapter-info');
                                if (response.ok) {
                                    const data = await response.json();
                                    this.adapters = data.adapters || [];
                                    if (data.primary_adapter) {
                                        this.selectedAdapterId = data.primary_adapter.address;
                                    }
                                    this.updateAdapterInfoUI(data.primary_adapter || (this.adapters[0] || {}));
                                    return data;
                                }
                            } catch (error) {
                                console.error("Error fetching adapter info:", error);
                            }
                            return { adapters: [] };
                        }
                        
                        updateAdapterInfoUI(adapter) {
                            // Update UI fields
                            const fields = {
                                'adapter-name': adapter.name || 'Unknown',
                                'adapter-address': adapter.address || 'Unknown',
                                'adapter-type': adapter.type || 'Unknown',
                                'adapter-status-text': adapter.available ? 'Available' : 'Unavailable',
                                'adapter-manufacturer': adapter.manufacturer || 'Unknown',
                                'adapter-platform': adapter.platform || 'Unknown'
                            };
                            
                            Object.entries(fields).forEach(([id, value]) => {
                                const element = document.getElementById(id);
                                if (element) element.textContent = value;
                            });
                        }
                        
                        async selectAdapter(adapterId) {
                            console.log("Selecting adapter:", adapterId);
                            
                            try {
                                // Try multiple formats
                                const response = await fetch('/api/ble/adapter/select', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ adapter_id: adapterId })
                                });
                                
                                if (response.ok) {
                                    console.log("Adapter selected successfully");
                                    this.selectedAdapterId = adapterId;
                                    
                                    // Find and update selected adapter UI
                                    const selectedAdapter = this.adapters.find(a => a.address === adapterId);
                                    if (selectedAdapter) {
                                        this.updateAdapterInfoUI(selectedAdapter);
                                    }
                                    
                                    return true;
                                } else {
                                    console.warn("Failed to select adapter, server returned:", response.status);
                                }
                            } catch (error) {
                                console.error("Error selecting adapter:", error);
                            }
                            
                            return false;
                        }
                    }
                };
            });
            
            // Initialize the adapter
            window.bleAdapter = new BleAdapter();
            await window.bleAdapter.initialize();
            
            // 2. Initialize other modules or create minimal implementations
            window.BleEvents = window.BleEvents || {
                on: (event, callback) => {
                    document.addEventListener(`ble:${event}`, (e) => callback(e.detail));
                },
                emit: (event, data) => {
                    document.dispatchEvent(new CustomEvent(`ble:${event}`, { detail: data }));
                },
                SCAN_STARTED: 'scan_started',
                SCAN_RESULT: 'scan_result',
                SCAN_COMPLETED: 'scan_completed',
                DEVICE_CONNECTED: 'device_connected',
                DEVICE_DISCONNECTED: 'device_disconnected'
            };
            
            window.BleUI = window.BleUI || {
                showToast: (message, type) => {
                    console.log(`[Toast] ${type}: ${message}`);
                    // Optional: Create a visible toast
                },
                updateElement: (id, content) => {
                    const element = document.getElementById(id);
                    if (element) element.innerHTML = content;
                }
            };
            
            // Set up event listeners for adapter UI
            const refreshBtn = document.getElementById('refresh-adapter-btn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', async () => {
                    refreshBtn.disabled = true;
                    try {
                        await window.bleAdapter.getAdapterInfo();
                        console.log("Adapter info refreshed");
                    } catch (error) {
                        console.error("Error refreshing adapter info:", error);
                    } finally {
                        refreshBtn.disabled = false;
                    }
                });
            }
            
            console.log("BLE modules initialized successfully");
            return true;
        } catch (error) {
            console.error("Error initializing BLE modules:", error);
            return false;
        }
    }
    
    // Run fixes
    async function applyFixes() {
        // 1. Create missing DOM elements
        const elementsCreated = createMissingDOMElements();
        if (!elementsCreated) {
            console.error("Failed to create required DOM elements");
        }
        
        // 2. Initialize modules
        const modulesInitialized = await initializeModules();
        if (!modulesInitialized) {
            console.error("Failed to initialize BLE modules");
        }
        
        console.log("BLE initialization fixes applied:", {
            elementsCreated,
            modulesInitialized
        });
        
        return elementsCreated && modulesInitialized;
    }
    
    // Apply fixes when DOM is loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyFixes);
    } else {
        applyFixes();
    }

    // Create global placeholders for required modules if they don't exist yet
    if (!window.BleUI) {
        console.log('Creating BleUI placeholder');
        window.BleUI = {
            showToast: (message, type = 'info') => {
                console.log(`[Toast ${type}] ${message}`);
                
                // Create a simple toast element
                const toast = document.createElement('div');
                toast.className = `fixed bottom-4 right-4 p-4 rounded-lg shadow-lg z-50 
                                  ${type === 'error' ? 'bg-red-800' : 
                                    type === 'warning' ? 'bg-yellow-800' : 
                                    type === 'success' ? 'bg-green-800' : 'bg-blue-800'} 
                                  text-white`;
                toast.textContent = message;
                document.body.appendChild(toast);
                
                // Remove after 3 seconds
                setTimeout(() => {
                    document.body.removeChild(toast);
                }, 3000);
            },
            updateElement: (id, content) => {
                const element = document.getElementById(id);
                if (element) {
                    element.innerHTML = content;
                }
            }
        };
    }
    
    // Fix module path issues
    const originalImport = window.importShim || window.import || null;
    if (originalImport) {
        window.importShim = function(path, ...args) {
            // Fix common path issues
            if (path === './ble-ui.js') {
                path = './static/js/pages/ble/ble-ui.js';
            }
            
            return originalImport(path, ...args);
        };
    }
    
    // Check for adapter card and create if it doesn't exist
    document.addEventListener('DOMContentLoaded', () => {
        const adapterCard = document.getElementById('ble-adapter-info-card');
        if (!adapterCard) {
            console.warn('Adapter card not found in DOM');
            // Could create one, but better to check template
        }
    });
})();
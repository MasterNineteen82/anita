import { DeviceService } from '../services/device-service.js';

document.addEventListener('DOMContentLoaded', () => {
    const deviceManager = new DeviceManager();
    deviceManager.initialize();
});

class DeviceManager {
    constructor() {
        // DOM elements
        this.readersList = document.getElementById('readers-list');
        this.refreshBtn = document.getElementById('refresh-readers');
        this.simulationToggle = document.getElementById('simulation-toggle');
        this.readerOperations = document.getElementById('reader-operations');
        this.selectedReaderName = document.getElementById('selected-reader-name');
        
        // Action buttons
        this.readCardBtn = document.getElementById('read-card-btn');
        this.writeCardBtn = document.getElementById('write-card-btn');
        this.ejectCardBtn = document.getElementById('eject-card-btn');
        
        // State
        this.readers = [];
        this.selectedReader = null;
    }
    
    async initialize() {
        this.attachEventListeners();
        await this.loadReaders();
    }
    
    attachEventListeners() {
        // Refresh button
        if (this.refreshBtn) {
            this.refreshBtn.addEventListener('click', () => this.loadReaders(true));
        }
        
        // Simulation toggle
        if (this.simulationToggle) {
            this.simulationToggle.addEventListener('change', (e) => this.toggleSimulation(e.target.checked));
            
            // Apply proper styling for toggle
            this.simulationToggle.addEventListener('change', (e) => {
                const toggle = e.target.nextElementSibling.nextElementSibling;
                if (e.target.checked) {
                    toggle.classList.add('bg-blue-500', 'translate-x-5');
                    toggle.classList.remove('bg-gray-400');
                } else {
                    toggle.classList.remove('bg-blue-500', 'translate-x-5');
                    toggle.classList.add('bg-gray-400');
                }
            });
        }
        
        // Card operation buttons
        if (this.readCardBtn) {
            this.readCardBtn.addEventListener('click', () => this.readCard());
        }
        
        if (this.writeCardBtn) {
            this.writeCardBtn.addEventListener('click', () => this.writeCard());
        }
        
        if (this.ejectCardBtn) {
            this.ejectCardBtn.addEventListener('click', () => this.ejectCard());
        }
    }
    
    async loadReaders(forceRefresh = false) {
        try {
            this.showLoading();
            
            const result = await DeviceService.listReaders(forceRefresh);
            
            if (result.status === 'success' && result.data && result.data.readers) {
                this.readers = result.data.readers;
                this.renderReadersList();
                
                // Update simulation toggle if needed
                if (this.readers.length > 0 && this.readers[0].simulation && this.simulationToggle) {
                    this.simulationToggle.checked = true;
                    // Update toggle styling
                    const toggle = this.simulationToggle.nextElementSibling.nextElementSibling;
                    toggle.classList.add('bg-blue-500', 'translate-x-5');
                    toggle.classList.remove('bg-gray-400');
                }
            } else {
                this.showError(result.message || 'Failed to load readers');
            }
        } catch (error) {
            console.error('Error loading readers:', error);
            this.showError(error.message);
        }
    }
    
    renderReadersList() {
        if (!this.readersList) return;
        
        if (!this.readers || this.readers.length === 0) {
            this.readersList.innerHTML = `
                <div class="flex flex-col items-center justify-center h-32">
                    <div class="text-gray-400 mb-2">
                        <i class="fas fa-search mr-2"></i>No readers found
                    </div>
                    <div class="text-sm text-gray-500">
                        Connect a card reader or enable simulation mode
                    </div>
                </div>
            `;
            return;
        }
        
        this.readersList.innerHTML = '';
        
        this.readers.forEach(reader => {
            const readerCard = document.createElement('div');
            readerCard.className = 'bg-gray-800 p-4 rounded shadow mb-4';
            
            // Define icons and badges
            const typeIcon = reader.type === 'nfc' ? 'fa-wifi' : 'fa-credit-card';
            const contactlessBadge = reader.isContactless ? 
                '<span class="bg-blue-900 text-blue-200 text-xs px-2 py-1 rounded ml-2">Contactless</span>' : '';
            const simulationBadge = reader.simulation ? 
                '<span class="bg-purple-900 text-purple-200 text-xs px-2 py-1 rounded ml-2">Simulation</span>' : '';
            
            readerCard.innerHTML = `
                <div class="flex justify-between items-start">
                    <div>
                        <div class="flex items-center">
                            <i class="fas ${typeIcon} text-blue-400 mr-2"></i>
                            <span class="font-medium">${reader.name}</span>
                            ${contactlessBadge}
                            ${simulationBadge}
                        </div>
                        <div class="text-sm text-gray-400 mt-1">
                            Type: ${reader.type.charAt(0).toUpperCase() + reader.type.slice(1)}
                        </div>
                    </div>
                    <div class="flex">
                        <button class="select-reader-btn text-blue-400 hover:text-blue-300 mr-3" 
                                data-reader="${reader.name}">
                            <i class="fas fa-check-circle mr-1"></i> Select
                        </button>
                        <button class="check-health-btn text-green-400 hover:text-green-300" 
                                data-reader="${reader.name}">
                            <i class="fas fa-heartbeat mr-1"></i> Health
                        </button>
                    </div>
                </div>
                <div class="health-status-${reader.name.replace(/\s+/g, '-')} mt-2 hidden"></div>
            `;
            
            this.readersList.appendChild(readerCard);
            
            // Add event listeners
            const selectBtn = readerCard.querySelector('.select-reader-btn');
            if (selectBtn) {
                selectBtn.addEventListener('click', () => this.selectReader(reader.name));
            }
            
            const healthBtn = readerCard.querySelector('.check-health-btn');
            if (healthBtn) {
                healthBtn.addEventListener('click', () => this.checkReaderHealth(reader.name));
            }
        });
    }
    
    async selectReader(readerName) {
        try {
            const result = await DeviceService.selectReader(readerName);
            
            if (result.status === 'success') {
                this.selectedReader = result.data.reader;
                
                // Update UI
                document.querySelectorAll('.select-reader-btn').forEach(btn => {
                    const isSelected = btn.dataset.reader === readerName;
                    btn.innerHTML = isSelected ? 
                        '<i class="fas fa-check-circle mr-1"></i> Selected' : 
                        '<i class="fas fa-check-circle mr-1"></i> Select';
                    
                    if (isSelected) {
                        btn.classList.add('text-green-400');
                        btn.classList.remove('text-blue-400', 'hover:text-blue-300');
                    } else {
                        btn.classList.remove('text-green-400');
                        btn.classList.add('text-blue-400', 'hover:text-blue-300');
                    }
                });
                
                // Show reader operations panel
                if (this.readerOperations) {
                    this.readerOperations.classList.remove('hidden');
                }
                
                // Update selected reader name
                if (this.selectedReaderName) {
                    this.selectedReaderName.textContent = readerName;
                }
                
                // Show success toast
                this.showToast(`Selected reader: ${readerName}`, 'success');
            } else {
                this.showToast(result.message || 'Failed to select reader', 'error');
            }
        } catch (error) {
            console.error('Error selecting reader:', error);
            this.showToast(error.message, 'error');
        }
    }
    
    async checkReaderHealth(readerName) {
        const healthStatusId = `health-status-${readerName.replace(/\s+/g, '-')}`;
        const healthDiv = document.querySelector(`.${healthStatusId}`);
        
        if (!healthDiv) return;
        
        try {
            // Show loading
            healthDiv.innerHTML = `
                <div class="flex items-center justify-center p-2">
                    <div class="animate-spin h-4 w-4 mr-2 border-2 border-t-2 border-blue-500 rounded-full"></div>
                    <span class="text-gray-400 text-sm">Checking health...</span>
                </div>
            `;
            healthDiv.classList.remove('hidden');
            
            const result = await DeviceService.checkReaderHealth(readerName);
            
            if (result.status === 'success' && result.data) {
                const isHealthy = result.data.healthy;
                const healthMessage = result.data.message || 'No additional information';
                
                healthDiv.innerHTML = `
                    <div class="p-2 rounded ${isHealthy ? 'bg-green-900 bg-opacity-50 text-green-200' : 'bg-red-900 bg-opacity-50 text-red-200'}">
                        <div class="flex items-center">
                            <i class="fas ${isHealthy ? 'fa-check-circle text-green-400' : 'fa-exclamation-triangle text-red-400'} mr-2"></i>
                            <span class="font-medium">${isHealthy ? 'Healthy' : 'Unhealthy'}</span>
                        </div>
                        <div class="text-xs mt-1">${healthMessage}</div>
                    </div>
                `;
            } else {
                healthDiv.innerHTML = `
                    <div class="p-2 rounded bg-red-900 bg-opacity-50 text-red-200">
                        <div class="flex items-center">
                            <i class="fas fa-exclamation-triangle text-red-400 mr-2"></i>
                            <span class="font-medium">Health check failed</span>
                        </div>
                        <div class="text-xs mt-1">${result.message || 'Unknown error'}</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error checking reader health:', error);
            
            healthDiv.innerHTML = `
                <div class="p-2 rounded bg-red-900 bg-opacity-50 text-red-200">
                    <div class="flex items-center">
                        <i class="fas fa-exclamation-triangle text-red-400 mr-2"></i>
                        <span class="font-medium">Error</span>
                    </div>
                    <div class="text-xs mt-1">${error.message}</div>
                </div>
            `;
        }
    }
    
    async toggleSimulation(enabled) {
        try {
            const result = await DeviceService.setSimulationMode(enabled);
            
            if (result.status === 'success') {
                // Reload readers to update UI
                await this.loadReaders(true);
                this.showToast(`Simulation mode ${enabled ? 'enabled' : 'disabled'}`, 'success');
            } else {
                this.simulationToggle.checked = !enabled; // Revert toggle
                this.showToast(result.message || 'Failed to change simulation mode', 'error');
            }
        } catch (error) {
            console.error('Error toggling simulation:', error);
            this.simulationToggle.checked = !enabled; // Revert toggle
            this.showToast(error.message, 'error');
        }
    }
    
    // UI Helpers
    showLoading() {
        if (!this.readersList) return;
        
        this.readersList.innerHTML = `
            <div class="flex items-center justify-center h-32">
                <div class="animate-spin h-5 w-5 mr-3 border-2 border-t-2 border-blue-500 rounded-full"></div>
                <span class="text-gray-400">Loading card readers...</span>
            </div>
        `;
    }
    
    showError(message) {
        if (!this.readersList) return;
        
        this.readersList.innerHTML = `
            <div class="bg-red-900 bg-opacity-50 text-red-200 p-4 rounded">
                <div class="flex items-center">
                    <i class="fas fa-exclamation-triangle text-red-400 mr-2"></i>
                    <span class="font-medium">Error</span>
                </div>
                <p class="mt-2 text-sm">${message}</p>
                <button id="retry-load-readers" class="mt-3 px-3 py-1 bg-red-800 hover:bg-red-700 rounded text-sm">
                    Retry
                </button>
            </div>
        `;
        
        // Add retry event listener
        const retryBtn = document.getElementById('retry-load-readers');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => this.loadReaders(true));
        }
    }
    
    showToast(message, type = 'info') {
        // Check if toast container exists, create if not
        let toastContainer = document.getElementById('toast-container');
        
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'fixed bottom-4 right-4 z-50 flex flex-col-reverse items-end space-y-reverse space-y-2';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast
        const toast = document.createElement('div');
        
        // Set classes based on type
        const baseClasses = 'px-4 py-2 rounded shadow-lg flex items-center max-w-xs transform transition-all duration-300 ease-in-out translate-x-full';
        let typeClasses = 'bg-gray-800 text-white';
        let icon = 'fa-info-circle';
        
        switch (type) {
            case 'success':
                typeClasses = 'bg-green-800 text-green-100';
                icon = 'fa-check-circle';
                break;
            case 'error':
                typeClasses = 'bg-red-800 text-red-100';
                icon = 'fa-exclamation-circle';
                break;
            case 'warning':
                typeClasses = 'bg-yellow-800 text-yellow-100';
                icon = 'fa-exclamation-triangle';
                break;
            default:
                typeClasses = 'bg-gray-800 text-white';
                icon = 'fa-info-circle';
                break;
        }
        
        toast.className = `${baseClasses} ${typeClasses}`;
        toast.innerHTML = `
            <i class="fas ${icon} mr-2"></i>
            <span>${message}</span>
        `;
        
        // Add to container
        toastContainer.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.classList.remove('translate-x-full');
        }, 10);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            toast.classList.add('translate-x-full');
            toast.addEventListener('transitionend', () => {
                if (toastContainer.contains(toast)) {
                    toastContainer.removeChild(toast);
                }
            });
        }, 3000);
    }
    
    // Stub methods for card operations (to be implemented)
    async readCard() {
        if (!this.selectedReader) {
            this.showToast('No reader selected', 'error');
            return;
        }
        
        try {
            this.showToast('Reading card...', 'info');
            
            // Show loading indicator
            const resultArea = document.createElement('div');
            resultArea.id = 'card-read-results';
            resultArea.className = 'mt-4 p-4 bg-gray-800 rounded';
            resultArea.innerHTML = `
                <div class="flex items-center justify-center">
                    <div class="animate-spin h-5 w-5 mr-3 border-2 border-t-2 border-blue-500 rounded-full"></div>
                    <span class="text-gray-400">Reading card data...</span>
                </div>
            `;
            
            // Add result area to the operations card if not already there
            const operationsCard = document.getElementById('reader-operations-card');
            let existingResultArea = document.getElementById('card-read-results');
            
            if (existingResultArea) {
                existingResultArea.replaceWith(resultArea);
            } else if (operationsCard) {
                operationsCard.appendChild(resultArea);
            }
            
            // Read options
            const options = {
                sectors: [0, 1, 2, 3],  // First 4 sectors
                use_key: 'A'
            };
            
            // Call the API
            const result = await DeviceService.readCard(this.selectedReader.name, options);
            
            if (result.status === 'success' && result.data) {
                // Format and display the data
                let html = `
                    <div class="space-y-3">
                        <div class="flex justify-between items-center">
                            <h3 class="text-lg font-medium text-white">Card Data</h3>
                            <button id="close-card-data" class="text-gray-400 hover:text-gray-300">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        
                        <div class="grid grid-cols-2 gap-2">
                            <div class="text-gray-400">UID:</div>
                            <div class="font-mono text-green-400">${result.data.uid}</div>
                            
                            <div class="text-gray-400">Type:</div>
                            <div>${result.data.type}</div>
                        </div>
                        
                        <div class="mt-4">
                            <h4 class="text-sm uppercase text-gray-400 mb-2">Sector Data</h4>
                            <div class="space-y-2">
                `;
                
                // Add sector data
                for (const [sector, data] of Object.entries(result.data.sectors)) {
                    html += `
                        <div class="p-2 bg-gray-700 bg-opacity-50 rounded">
                            <div class="font-medium mb-1">Sector ${sector}</div>
                    `;
                    
                    if (data.error) {
                        html += `<div class="text-red-400 text-sm">${data.error}</div>`;
                    } else {
                        html += `<div class="grid grid-cols-1 gap-1">`;
                        
                        for (const [block, blockData] of Object.entries(data)) {
                            html += `
                                <div class="grid grid-cols-6 gap-1">
                                    <div class="text-xs text-gray-400 col-span-1">${block}:</div>
                                    <div class="font-mono text-xs text-gray-200 col-span-5 break-all">${blockData}</div>
                                </div>
                            `;
                        }
                        
                        html += `</div>`;
                    }
                    
                    html += `</div>`;
                }
                
                html += `
                            </div>
                        </div>
                    </div>
                `;
                
                resultArea.innerHTML = html;
                
                // Add close button handler
                const closeBtn = document.getElementById('close-card-data');
                if (closeBtn) {
                    closeBtn.addEventListener('click', () => {
                        resultArea.remove();
                    });
                }
                
                this.showToast('Card read successfully', 'success');
            } else {
                resultArea.innerHTML = `
                    <div class="text-red-400">
                        <i class="fas fa-exclamation-triangle mr-2"></i>
                        ${result.message || 'Failed to read card data'}
                    </div>
                `;
                this.showToast('Failed to read card', 'error');
            }
        } catch (error) {
            console.error('Error in readCard:', error);
            this.showToast(error.message, 'error');
            
            const resultArea = document.getElementById('card-read-results');
            if (resultArea) {
                resultArea.innerHTML = `
                    <div class="text-red-400">
                        <i class="fas fa-exclamation-triangle mr-2"></i>
                        ${error.message}
                    </div>
                `;
            }
        }
    }
    
    async writeCard() {
        this.showToast('Write card functionality not yet implemented', 'warning');
    }
    
    async ejectCard() {
        this.showToast('Eject card functionality not yet implemented', 'warning');
    }
}
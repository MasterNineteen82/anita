/**
 * UI utilities for BLE interfaces
 */
export class BleUI {
    static logContainer = null;

    /**
     * Initialize the UI
     */
    static async initialize() {
        console.log('Initializing BleUI');
        
        // Fix card layouts
        this.fixCardLayouts();
        
        // Set up a mutation observer to fix layouts when DOM changes
        const observer = new MutationObserver(() => {
            this.fixCardLayouts();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        return true;
    }

    /**
     * Initialize the log container
     * @param {string} elementId - ID of the log container element
     */
    static initializeLog(elementId) {
        this.logContainer = document.getElementById(elementId);

        // Set up log controls
        const clearLogBtn = document.getElementById('clear-log-btn');
        if (clearLogBtn) {
            clearLogBtn.addEventListener('click', () => this.clearLog());
        }

        const logLevelSelect = document.getElementById('log-level');
        if (logLevelSelect) {
            logLevelSelect.addEventListener('change', () => this.filterLog(logLevelSelect.value));
        }
    }

    /**
     * Add a message to the log
     * @param {string} message - Message to log
     * @param {string} type - Message type (info, success, warning, error)
     */
    static logMessage(message, type = 'info') {
        if (!this.logContainer) return;

        const timestamp = new Date().toLocaleTimeString();
        const entry = document.createElement('div');

        let icon, textClass;
        switch (type) {
            case 'success':
                icon = 'check-circle';
                textClass = 'text-green-600';
                break;
            case 'warning':
                icon = 'exclamation-triangle';
                textClass = 'text-yellow-600';
                break;
            case 'error':
                icon = 'times-circle';
                textClass = 'text-red-600';
                break;
            default:
                icon = 'info-circle';
                textClass = 'text-blue-600';
        }

        entry.className = `${textClass} mb-1`;
        entry.dataset.logType = type;
        entry.innerHTML = `[${timestamp}] <i class="${icon}"></i> ${message}`;

        this.logContainer.appendChild(entry);
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
    }

    /**
     * Clear the log container
     */
    static clearLog() {
        if (!this.logContainer) return;
        this.logContainer.innerHTML = '';
        this.logMessage('Log cleared', 'info');
    }

    /**
     * Filter log entries by type
     * @param {string} level - Log level to filter (info, error, all)
     */
    static filterLog(level) {
        if (!this.logContainer) return;

        const entries = this.logContainer.querySelectorAll('div');

        entries.forEach(entry => {
            if (level === 'all') {
                entry.classList.remove('hidden');
            } else if (level === 'error') {
                entry.classList.toggle('hidden', entry.dataset.logType !== 'error');
            } else if (level === 'info') {
                entry.classList.toggle('hidden', entry.dataset.logType === 'error');
            }
        });
    }

    /**
     * Initialize toast notifications
     */
    static initializeToasts() {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'fixed top-4 right-4 z-50 flex flex-col space-y-2';
            document.body.appendChild(toastContainer);
        }
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to show
     * @param {string} type - The type of toast (success, error, warning, info)
     * @param {number} duration - Duration to show in ms
     */
    static showToast(message, type = 'info', duration = 3000) {
        // Ensure toasts are initialized
        if (!document.getElementById('toast-container')) {
            this.initializeToasts();
        }

        const toastContainer = document.getElementById('toast-container');

        // Create toast element
        const toast = document.createElement('div');
        toast.className = 'toast p-3 rounded shadow-lg max-w-md transform transition-all duration-300 translate-x-full opacity-0';

        // Add appropriate color based on type
        switch (type) {
            case 'success':
                toast.classList.add('bg-green-600', 'text-white');
                break;
            case 'error':
                toast.classList.add('bg-red-600', 'text-white');
                break;
            case 'warning':
                toast.classList.add('bg-yellow-500', 'text-white');
                break;
            default:
                toast.classList.add('bg-blue-600', 'text-white');
        }

        // Add icon based on type
        let icon;
        switch (type) {
            case 'success':
                icon = 'fas fa-check-circle';
                break;
            case 'error':
                icon = 'fas fa-exclamation-circle';
                break;
            case 'warning':
                icon = 'fas fa-exclamation-triangle';
                break;
            default:
                icon = 'fas fa-info-circle';
        }

        // Add content
        toast.innerHTML = `
            <div class="flex items-center">
                <div class="mr-2"><i class="${icon}"></i></div>
                <div>${message}</div>
            </div>
        `;

        // Add to container
        toastContainer.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.classList.remove('translate-x-full', 'opacity-0');
        }, 10);

        // Animate out and remove after duration
        setTimeout(() => {
            toast.classList.add('translate-x-full', 'opacity-0');

            // Remove after animation
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, duration);
    }

    /**
     * Show a dialog
     * @param {HTMLElement|string} content - The dialog content
     * @param {Object} options - Dialog options
     * @returns {HTMLElement} The dialog element
     */
    static showDialog(content, options = {}) {
        // Create dialog overlay
        const overlay = document.createElement('div');
        overlay.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';

        // Create dialog container
        const dialog = document.createElement('div');
        dialog.className = 'bg-gray-800 rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-auto transform transition-transform duration-200 scale-95 opacity-0';

        // Add content
        if (typeof content === 'string') {
            dialog.innerHTML = content;
        } else {
            dialog.appendChild(content);
        }

        // Add to DOM
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);

        // Add click handler to close on overlay click
        if (options.closeOnOverlayClick !== false) {
            overlay.addEventListener('click', (event) => {
                if (event.target === overlay) {
                    this.closeDialog(overlay);
                }
            });
        }

        // Add keydown handler to close on escape
        if (options.closeOnEscape !== false) {
            const escHandler = (event) => {
                if (event.key === 'Escape') {
                    this.closeDialog(overlay);
                    document.removeEventListener('keydown', escHandler);
                }
            };
            document.addEventListener('keydown', escHandler);
        }

        // Animate in
        setTimeout(() => {
            dialog.classList.remove('scale-95', 'opacity-0');
            dialog.classList.add('scale-100', 'opacity-100');
        }, 10);

        return overlay;
    }

    /**
     * Close a dialog
     * @param {HTMLElement} dialog - The dialog element
     */
    static closeDialog(dialog) {
        const dialogContent = dialog.querySelector('div');

        // Animate out
        dialogContent.classList.remove('scale-100', 'opacity-100');
        dialogContent.classList.add('scale-95', 'opacity-0');

        // Remove after animation
        setTimeout(() => {
            dialog.remove();
        }, 200);
    }

    /**
     * Show a loading indicator
     * @param {string} message - The message to show
     * @returns {HTMLElement} The loading element
     */
    static showLoading(message = 'Loading...') {
        // Create loading overlay
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';

        // Create loading container
        const loading = document.createElement('div');
        loading.className = 'bg-gray-800 rounded-lg shadow-xl p-4 flex flex-col items-center';

        // Add spinner and message
        loading.innerHTML = `
            <div class="inline-block animate-spin text-2xl mb-2">
                <i class="fas fa-spinner"></i>
            </div>
            <div>${message}</div>
        `;

        // Add to DOM
        overlay.appendChild(loading);
        document.body.appendChild(overlay);

        return overlay;
    }

    /**
     * Hide the loading indicator
     */
    static hideLoading() {
        const loading = document.getElementById('loading-overlay');
        if (loading) {
            loading.remove();
        }
    }

    /**
     * Hide all loading spinners
     */
    static hideLoadingSpinners() {
        // Find all loading spinners and hide them
        const spinners = document.querySelectorAll('.loading-spinner');
        spinners.forEach(spinner => {
            spinner.classList.add('hidden');
        });
        
        // Also look for loading indicators in cards
        const loadingIndicators = document.querySelectorAll('.card-loading');
        loadingIndicators.forEach(indicator => {
            indicator.classList.add('hidden');
        });
        
        console.log('All loading spinners hidden');
        
        // Find and remove loading messages
        const loadingElements = document.querySelectorAll('.text-gray-500:contains("Loading")');
        loadingElements.forEach(el => {
            el.style.display = 'none';
        });
    }

    /**
     * Show a loading spinner in a specific element
     * @param {string} elementId - The ID of the element to show the spinner in
     */
    static showLoadingSpinner(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            // Create spinner if it doesn't exist
            let spinner = element.querySelector('.loading-spinner');
            if (!spinner) {
                spinner = document.createElement('div');
                spinner.className = 'loading-spinner';
                spinner.innerHTML = `
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                `;
                element.appendChild(spinner);
            } else {
                spinner.classList.remove('hidden');
            }
        }
    }

    /**
     * Hide a loading spinner in a specific element
     * @param {string} elementId - The ID of the element to hide the spinner in
     */
    static hideLoadingSpinner(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            const spinner = element.querySelector('.loading-spinner');
            if (spinner) {
                spinner.classList.add('hidden');
            }
        }
    }

    /**
     * Format a BLE address for display
     * @param {string} address - The BLE address
     * @returns {string} Formatted address
     */
    static formatAddress(address) {
        if (!address) return '';

        // If already has colons, return as is
        if (address.includes(':')) return address;

        // Add colons between every 2 characters
        return address.match(/.{1,2}/g).join(':');
    }

    /**
     * Format signal strength for display
     * @param {number} rssi - The RSSI value
     * @returns {string} Formatted signal strength with icon
     */
    static formatSignalStrength(rssi) {
        let icon, color;

        if (rssi >= -60) {
            icon = 'fas fa-signal';
            color = 'text-green-500';
        } else if (rssi >= -75) {
            icon = 'fas fa-signal';
            color = 'text-yellow-500';
        } else if (rssi >= -85) {
            icon = 'fas fa-signal';
            color = 'text-orange-500';
        } else {
            icon = 'fas fa-signal';
            color = 'text-red-500';
        }

        return `<span class="${color}"><i class="${icon}"></i> ${rssi} dBm</span>`;
    }

    /**
     * Initialize event listeners with passive option for touch events
     * @param {HTMLElement} element - DOM element to add listeners to
     * @param {string} event - Event name (e.g., 'touchstart')
     * @param {Function} handler - Event handler function
     * @param {Object} options - Additional options
     */
    static addPassiveEventListener(element, event, handler, options = {}) {
        if (!element) return;
        element.addEventListener(event, handler, { passive: true, ...options });
    }

    // Example usage:
    // BleUI.addPassiveEventListener(document.getElementById('my-element'), 'touchstart', myHandler);
    
    /**
     * Creates Adapter Info card content
     */
    createAdapterInfoContent(adapter) {
        if (!adapter) {
            return `
                <div class="text-gray-500 text-center p-4">
                    No adapter information available
                </div>
            `;
        }
        
        return `
            <div class="space-y-4">
                <!-- Adapter Name -->
                <div class="mb-3">
                    <div class="text-sm text-gray-400 mb-1">Name</div>
                    <div id="adapter-name" class="font-medium">${adapter.name || 'Unknown'}</div>
                </div>
                
                <!-- Adapter Address -->
                <div class="mb-3">
                    <div class="text-sm text-gray-400 mb-1">Address</div>
                    <div id="adapter-address" class="font-medium font-mono">${adapter.address || 'Unknown'}</div>
                </div>
                
                <!-- Adapter Type -->
                <div class="mb-3">
                    <div class="text-sm text-gray-400 mb-1">Type</div>
                    <div id="adapter-type" class="font-medium">${adapter.hardware?.model || adapter.description || 'Standard'}</div>
                </div>
                
                <!-- Adapter Status -->
                <div class="mb-3">
                    <div class="text-sm text-gray-400 mb-1">Status</div>
                    <div id="adapter-status" class="font-medium flex items-center">
                        <div class="w-3 h-3 rounded-full ${adapter.available ? 'bg-green-500' : 'bg-red-500'} mr-2"></div>
                        <span id="adapter-status-text">${adapter.available ? 'Available' : 'Unavailable'}</span>
                    </div>
                </div>
                
                <!-- Adapter Manufacturer -->
                <div class="mb-3">
                    <div class="text-sm text-gray-400 mb-1">Manufacturer</div>
                    <div id="adapter-manufacturer" class="font-medium">${adapter.hardware?.vendor || adapter.manufacturer || 'Unknown'}</div>
                </div>
                
                <!-- Adapter Platform -->
                <div class="mb-3">
                    <div class="text-sm text-gray-400 mb-1">Platform</div>
                    <div id="adapter-platform" class="font-medium">${adapter.platform || 'Unknown'}</div>
                </div>
            </div>
        `;
    }

    /**
     * Creates scan controls for Scanner card
     */
    createScanControls() {
        return `
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center">
                    <div id="scan-status" class="flex items-center">
                        <span class="w-3 h-3 rounded-full bg-green-500 mr-2"></span>
                        <span class="text-green-500">Ready</span>
                    </div>
                    <div id="scan-spinner" class="hidden ml-3">
                        <div class="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-blue-500"></div>
                    </div>
                </div>
                
                <div>
                    <span class="text-sm text-gray-400 mr-2">Devices:</span>
                    <span id="device-counter" class="text-white font-medium">0</span>
                </div>
            </div>
            
            <div class="flex items-center justify-between mb-4">
                <div>
                    <button id="scan-btn" class="ble-btn ble-btn-primary">
                        <i class="fas fa-search mr-1"></i> Scan for Devices
                    </button>
                    <button id="stop-scan-btn" class="ble-btn ble-btn-danger hidden">
                        <i class="fas fa-stop mr-1"></i> Stop Scan
                    </button>
                </div>
                
                <div class="flex items-center">
                    <label class="text-sm text-gray-400 mr-2">Time:</label>
                    <input type="number" id="scan-time" min="1" max="30" value="5" 
                        class="w-16 bg-gray-700 border border-gray-600 rounded py-1 px-2 text-center text-white">
                    <span class="text-sm text-gray-400 ml-1">sec</span>
                </div>
            </div>
            
            <div class="mb-4">
                <div class="flex items-center justify-between">
                    <label for="active-scanning" class="flex items-center cursor-pointer">
                        <div class="relative">
                            <input type="checkbox" id="active-scanning" class="sr-only" checked>
                            <div class="block bg-gray-600 w-10 h-6 rounded-full"></div>
                            <div class="dot absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition"></div>
                        </div>
                        <div class="ml-3 text-gray-300 text-sm">Active Scanning</div>
                    </label>
                    
                    <button id="clear-devices-btn" class="text-sm text-gray-400 hover:text-gray-300">
                        <i class="fas fa-trash-alt mr-1"></i> Clear
                    </button>
                </div>
            </div>
            
            <div class="relative h-1 mb-4 bg-gray-700 rounded-full overflow-hidden">
                <div id="scan-progress" class="absolute top-0 left-0 h-full w-0 bg-blue-500 rounded-full"></div>
            </div>
        `;
    }

    /**
     * Creates device info content for Device card
     */
    createDeviceInfoContent(device) {
        if (!device) {
            return `
                <div class="text-gray-500 text-center p-4">
                    Not connected to any device
                </div>
            `;
        }
        
        return `
            <div class="space-y-4">
                <!-- Device Name -->
                <div class="mb-3">
                    <div class="text-sm text-gray-400 mb-1">Name</div>
                    <div id="device-name" class="font-medium">${device.name || 'Unknown Device'}</div>
                </div>
                
                <!-- Device Address -->
                <div class="mb-3">
                    <div class="text-sm text-gray-400 mb-1">Address</div>
                    <div id="device-address" class="font-medium font-mono">${device.address || 'Unknown'}</div>
                </div>
                
                <!-- Device RSSI -->
                <div class="mb-3">
                    <div class="text-sm text-gray-400 mb-1">Signal Strength</div>
                    <div id="device-rssi" class="font-medium flex items-center">
                        ${this.createRssiIndicator(device.rssi || -100)}
                        <span class="ml-2">${device.rssi || 'Unknown'} dBm</span>
                    </div>
                </div>
                
                <!-- Connection Status -->
                <div class="mb-3">
                    <div class="text-sm text-gray-400 mb-1">Status</div>
                    <div id="device-status" class="font-medium flex items-center">
                        <div class="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
                        <span>Connected</span>
                    </div>
                </div>
                
                <!-- Connect/Disconnect Button -->
                <div class="mt-4 flex justify-end">
                    <button id="disconnect-btn" class="ble-btn ble-btn-danger">
                        <i class="fas fa-times mr-1"></i> Disconnect
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Creates RSSI signal indicator
     */
    createRssiIndicator(rssi) {
        const bars = [];
        const maxBars = 4;
        
        // Determine how many bars to show based on RSSI value
        let activeBars;
        if (rssi >= -60) {
            activeBars = 4;
        } else if (rssi >= -70) {
            activeBars = 3;
        } else if (rssi >= -80) {
            activeBars = 2;
        } else if (rssi >= -90) {
            activeBars = 1;
        } else {
            activeBars = 0;
        }
        
        // Determine color based on signal strength
        let color;
        if (activeBars >= 3) {
            color = 'bg-green-500';
        } else if (activeBars >= 2) {
            color = 'bg-yellow-500';
        } else {
            color = 'bg-red-500';
        }
        
        // Create the bars
        let html = `<div class="flex items-end h-4 space-x-1" title="Signal Strength: ${rssi} dBm">`;
        
        for (let i = 0; i < maxBars; i++) {
            const height = 3 + i * 3; // Increasing heights: 3px, 6px, 9px, 12px
            const isActive = i < activeBars;
            html += `<div class="w-1 h-${height}px ${isActive ? color : 'bg-gray-600'}"></div>`;
        }
        
        html += `</div>`;
        return html;
    }

    /**
     * Show a fatal error message that prevents further use of the application
     * @param {string} title - The error title
     * @param {Error|string} error - The error object or message
     */
    static showFatalError(title, error) {
        console.error('Fatal error:', title, error);
        
        // Create error container if it doesn't exist
        let errorContainer = document.getElementById('ble-fatal-error');
        if (!errorContainer) {
            errorContainer = document.createElement('div');
            errorContainer.id = 'ble-fatal-error';
            errorContainer.className = 'fixed inset-0 flex items-center justify-center bg-gray-900 bg-opacity-90 z-50';
            document.body.appendChild(errorContainer);
        }
        
        // Format the error message
        const errorMessage = error instanceof Error ? 
            `${error.message}\n\n${error.stack || ''}` : 
            error;
        
        // Add the error content
        errorContainer.innerHTML = `
            <div class="bg-gray-800 rounded-lg p-6 max-w-lg w-full mx-4 shadow-xl border border-red-700">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-xl font-bold text-red-500">
                        <i class="fas fa-exclamation-triangle mr-2"></i> ${title}
                    </h3>
                    <button id="ble-error-close" class="text-gray-400 hover:text-white focus:outline-none">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="border-t border-gray-700 pt-4">
                    <p class="text-gray-300 mb-4">A critical error has occurred that prevents the BLE dashboard from functioning properly.</p>
                    <div class="bg-gray-900 p-3 rounded font-mono text-sm text-red-400 overflow-auto max-h-60">
                        ${errorMessage.replace(/\n/g, '<br>')}
                    </div>
                    <div class="mt-6 flex justify-between">
                        <button id="ble-retry-btn" class="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded">
                            <i class="fas fa-sync-alt mr-1"></i> Retry
                        </button>
                        <a href="/" class="bg-gray-600 hover:bg-gray-700 text-white py-2 px-4 rounded">
                            <i class="fas fa-home mr-1"></i> Go to Homepage
                        </a>
                    </div>
                </div>
            </div>
        `;
        
        // Add event listeners
        const closeBtn = document.getElementById('ble-error-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                errorContainer.remove();
            });
        }
        
        const retryBtn = document.getElementById('ble-retry-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                errorContainer.remove();
                window.location.reload();
            });
        }
    }
    
    static fixCardLayouts() {
        console.log('Fixing card layouts...');
        
        // Find all cards
        const cards = document.querySelectorAll('.card, [id$="-card"]');
        
        cards.forEach(card => {
            // Ensure card has proper layout classes
            card.classList.add('flex', 'flex-col');
            
            // Find content and footer areas
            const titleArea = card.querySelector('.card-header') || card.querySelector('h3') || null;
            const contentArea = card.querySelector('.card-content') || 
                               card.querySelector('.p-4:not(.card-footer)') || 
                               card.querySelector('div:not(.card-header):not(.card-footer)');
            
            const footerArea = card.querySelector('.card-footer') || card.querySelector('.mt-4.flex.justify-end');
            
            // Fix content area if it exists
            if (contentArea) {
                // Ensure content takes available space
                contentArea.classList.add('flex-1');
                
                // Ensure correct ordering: title -> content -> footer
                if (titleArea && contentArea.previousElementSibling !== titleArea) {
                    titleArea.insertAdjacentElement('afterend', contentArea);
                }
            }
            
            // Move footer to the end if needed
            if (footerArea && footerArea.nextElementSibling) {
                card.appendChild(footerArea);
            }
            
            // Remove loading spinner if there's actual content
            const spinner = card.querySelector('.animate-spin');
            const loadingText = card.querySelector('text-gray-400:contains("Loading")');
            
            if ((spinner || loadingText) && card.textContent.trim().length > 30) {
                if (spinner) spinner.parentElement.remove();
                if (loadingText) loadingText.remove();
            }
        });
    }
}

// Export the logMessage function
export const logMessage = BleUI.logMessage;
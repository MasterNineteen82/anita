/**
 * UI utilities for BLE interfaces
 */
export class BleUI {
    static logContainer = null;

    /**
     * Initialize the UI
     */
    static async initialize() {
        console.log('Initializing BLE UI module');
        // Any UI initialization logic here
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
}

// Export the logMessage function
export const logMessage = BleUI.logMessage;
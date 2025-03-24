import { createElement, getElement } from './dom.js'; // Ensure correct path to dom.js

/**
 * UI Utilities for consistent interface elements
 */
class UIUtils {
    /**
     * Show a toast notification
     * @param {string} message - Message to display
     * @param {string} type - success, error, warning, or info
     * @param {number} duration - How long to show toast in ms
     */
    showToast(message, type = 'success', duration = 3000) {
        // Make sure we have a toast container
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }
        
        // Create the toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        // Add it to the container
        toastContainer.appendChild(toast);
        
        // Use setTimeout to ensure DOM updates
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Remove after duration
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
    
    /**
     * Show loading overlay
     * @param {boolean} show - Whether to show or hide
     * @param {string} message - Optional message to display
     */
    showLoading(show, message = 'Loading...') {
        let overlay = document.getElementById('loading-overlay');
        
        if (show) {
            // Create if it doesn't exist
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = 'loading-overlay';
                const spinner = document.createElement('div');
                spinner.className = 'spinner';
                overlay.appendChild(spinner);
                
                const text = document.createElement('div');
                text.className = 'loading-text';
                text.textContent = message;
                overlay.appendChild(text);
                
                document.body.appendChild(overlay);
            }
            
            // Update message
            const textEl = overlay.querySelector('.loading-text');
            if (textEl) textEl.textContent = message;
            
            // Show
            overlay.classList.add('active');
        } else if (overlay) {
            // Hide
            overlay.classList.remove('active');
        }
    }
}

// Export singleton
export default new UIUtils();
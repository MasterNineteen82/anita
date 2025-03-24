/**
 * UI utility functions
 */
class UIManager {
    /**
     * Show a toast notification
     * @param {string} message - Message to display
     * @param {string} type - Notification type (success, error, warning, info)
     * @param {number} duration - Display duration in ms
     */
    showToast(message, type = 'info', duration = 3000) {
        // Remove existing toasts
        const existingToast = document.querySelector('.toast');
        if (existingToast) {
            existingToast.remove();
        }
        
        // Create new toast
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        // Add to DOM
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Remove after duration
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
    
    /**
     * Display JSON result in a formatted way
     * @param {string} elementId - Target element ID
     * @param {object} data - Data to display
     */
    displayResult(elementId, data) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        // Format based on status
        const status = data.status || 'unknown';
        const statusClass = status === 'success' ? 'success' : 'error';
        
        // Create formatted HTML
        let html = `<div class="result-header ${statusClass}">Status: ${status}</div>`;
        
        if (data.message) {
            html += `<div class="result-message">${data.message}</div>`;
        }
        
        if (data.data) {
            html += '<div class="result-data">';
            html += `<pre>${JSON.stringify(data.data, null, 2)}</pre>`;
            html += '</div>';
        }
        
        element.innerHTML = html;
    }
    
    /**
     * Show a confirmation dialog
     * @param {string} message - Confirmation message
     * @returns {Promise<boolean>} - Promise resolving to user's choice
     */
    async confirm(message) {
        return new Promise(resolve => {
            const dialog = document.createElement('div');
            dialog.className = 'dialog-overlay';
            dialog.innerHTML = `
                <div class="dialog">
                    <div class="dialog-content">${message}</div>
                    <div class="dialog-actions">
                        <button class="btn btn-secondary" id="dialog-cancel">Cancel</button>
                        <button class="btn btn-primary" id="dialog-confirm">Confirm</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(dialog);
            
            document.getElementById('dialog-confirm').addEventListener('click', () => {
                dialog.remove();
                resolve(true);
            });
            
            document.getElementById('dialog-cancel').addEventListener('click', () => {
                dialog.remove();
                resolve(false);
            });
        });
    }
}

// Create singleton instance
const UI = new UIManager();
export default UI;
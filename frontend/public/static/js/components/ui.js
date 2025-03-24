import { getElement } from '../utils/dom.js';
import { escapeHtml } from '../utils/string.js';

/**
 * UI component functionality
 */

class UI {
    /**
     * Show a toast notification
     * @param {string} message - Message to display
     * @param {string} type - Notification type (success, error, warning, info)
     * @param {number} duration - Display duration in ms
     * @param {Object} options - Additional options
     * @returns {HTMLElement} The toast element
     */
    static showToast(message, type = 'info', duration = 3000, options = {}) {
        // Remove existing toast if specified
        if (options.unique) {
            document.querySelectorAll('.toast-notification').forEach(el => el.remove());
        }
        
        // Create toast element with proper ARIA attributes
        const toast = document.createElement('div');
        toast.className = `toast-notification ${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        
        // Add close button if dismissible
        if (options.dismissible) {
            const closeBtn = document.createElement('button');
            closeBtn.className = 'toast-close-btn';
            closeBtn.innerHTML = '&times;';
            closeBtn.setAttribute('aria-label', 'Close notification');
            closeBtn.addEventListener('click', () => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            });
            toast.appendChild(closeBtn);
        }
        
        // Add message content
        const messageEl = document.createElement('div');
        messageEl.className = 'toast-message';
        messageEl.innerText = message;
        toast.appendChild(messageEl);
        
        // Add to container or body
        const container = options.container ? getElement(options.container) : document.body;
        container.appendChild(toast);
        
        // Animation and cleanup
        setTimeout(() => {
            toast.classList.add('show');
            if (!options.dismissible && duration !== Infinity) {
                setTimeout(() => {
                    toast.classList.remove('show');
                    setTimeout(() => toast.remove(), 300);
                }, duration);
            }
        }, 10);
        
        return toast;
    }
    
    /**
     * Create and display a modal dialog
     * @param {string} title - Modal title
     * @param {string|HTMLElement} content - Modal body content
     * @param {Object} callbacks - Callback functions
     * @param {Object} options - Additional options
     * @returns {HTMLElement} The modal element
     */
    static showModal(title, content, callbacks = {}, options = {}) {
        const modal = document.createElement('div');
        modal.className = `modal fade ${options.size ? `modal-${options.size}` : ''}`;
        modal.style.display = 'block';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-labelledby', 'modal-title');
        
        // Allow closing with escape key
        if (options.closeOnEscape !== false) {
            document.addEventListener('keydown', function escHandler(e) {
                if (e.key === 'Escape') {
                    if (callbacks.cancel) callbacks.cancel();
                    document.body.removeChild(modal);
                    document.removeEventListener('keydown', escHandler);
                }
            });
        }
        
        const dialog = document.createElement('div');
        dialog.className = 'modal-dialog';
        if (options.centered) dialog.classList.add('modal-dialog-centered');
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        
        const modalHeader = document.createElement('div');
        modalHeader.className = 'modal-header';
        
        const modalTitle = document.createElement('h5');
        modalTitle.className = 'modal-title';
        modalTitle.id = 'modal-title';
        modalTitle.textContent = title;
        
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('aria-label', 'Close');
        closeButton.addEventListener('click', () => {
            if (callbacks.cancel) callbacks.cancel();
            document.body.removeChild(modal);
        });
        
        modalHeader.appendChild(modalTitle);
        modalHeader.appendChild(closeButton);
        
        const modalBody = document.createElement('div');
        modalBody.className = 'modal-body';
        if (typeof content === 'string') {
            modalBody.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            modalBody.appendChild(content);
        }
        
        const modalFooter = document.createElement('div');
        modalFooter.className = 'modal-footer';
        
        // Only show footer if we have buttons
        if (options.showFooter !== false) {
            // Cancel button
            if (options.showCancel !== false) {
                const cancelButton = document.createElement('button');
                cancelButton.type = 'button';
                cancelButton.className = `btn ${options.cancelClass || 'btn-secondary'}`;
                cancelButton.textContent = callbacks.cancelText || options.cancelText || 'Cancel';
                cancelButton.addEventListener('click', () => {
                    if (callbacks.cancel) callbacks.cancel();
                    document.body.removeChild(modal);
                });
                modalFooter.appendChild(cancelButton);
            }
            
            // Confirm button
            const confirmButton = document.createElement('button');
            confirmButton.type = 'button';
            confirmButton.className = `btn ${options.confirmClass || 'btn-primary'}`;
            confirmButton.textContent = callbacks.confirmText || options.confirmText || 'Confirm';
            confirmButton.addEventListener('click', () => {
                if (callbacks.confirm) callbacks.confirm();
                document.body.removeChild(modal);
            });
            modalFooter.appendChild(confirmButton);
        }
        
        modalContent.appendChild(modalHeader);
        modalContent.appendChild(modalBody);
        if (options.showFooter !== false) {
            modalContent.appendChild(modalFooter);
        }
        
        dialog.appendChild(modalContent);
        modal.appendChild(dialog);
        
        document.body.appendChild(modal);
        
        // Focus first button or close button for accessibility
        setTimeout(() => {
            const firstBtn = modal.querySelector('.modal-footer button');
            if (firstBtn) {
                firstBtn.focus();
            } else {
                closeButton.focus();
            }
        }, 100);
        
        return modal;
    }
    
    /**
     * Show a confirmation dialog
     * @param {string} message - Confirmation message
     * @param {Object} options - Additional options
     * @returns {Promise<boolean>} Whether the user confirmed
     */
    static confirm(message, options = {}) {
        return new Promise(resolve => {
            const content = document.createElement('div');
            content.textContent = message;
            
            this.showModal(
                options.title || 'Confirm',
                content,
                {
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                    confirmText: options.confirmText || 'Yes',
                    cancelText: options.cancelText || 'No',
                },
                options
            );
        });
    }
    
    /**
     * Display results in an element
     * @param {string} elementId - Target element ID
     * @param {Object} data - Data to display
     * @param {Object} options - Display options
     */
    static displayResult(elementId, data, options = {}) {
        const element = getElement(elementId);
        if (!element) return;
        
        element.classList.remove('fade-in');
        setTimeout(() => {
            if (data.status === 'error') {
                element.innerHTML = `<div class="result-error">
                    <div class="error-icon">${options.errorIcon || '⚠️'}</div>
                    <div class="error-message">${escapeHtml(data.message)}</div>
                </div>`;
            } else {
                let contentHtml;
                
                if (options.format === 'table' && typeof data.data === 'object') {
                    contentHtml = UI.formatAsTable(data.data);
                } else if (options.format === 'list' && Array.isArray(data.data)) {
                    contentHtml = UI.formatAsList(data.data);
                } else {
                    contentHtml = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                }
                
                element.innerHTML = `
                    <div class="result-success">
                        ${data.message ? `<div class="result-message">${escapeHtml(data.message)}</div>` : ''}
                        <div class="result-data">${contentHtml}</div>
                    </div>
                `;
            }
            element.classList.add('fade-in');
            
            // Add copy button if requested
            if (options.addCopyButton) {
                const copyBtn = document.createElement('button');
                copyBtn.className = 'copy-result-btn';
                copyBtn.textContent = 'Copy';
                copyBtn.addEventListener('click', () => {
                    const textToCopy = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
                    UI.copyToClipboard(textToCopy);
                });
                element.appendChild(copyBtn);
            }
        }, 50);
    }
    
    /**
     * Format object as HTML table
     * @param {Object} data - Data to format
     * @returns {string} HTML table
     */
    static formatAsTable(data) {
        if (!data || typeof data !== 'object') return '<div>No data</div>';
        
        if (Array.isArray(data)) {
            if (data.length === 0) return '<div>Empty array</div>';
            
            // Get all possible keys from objects in array
            const keys = new Set();
            data.forEach(item => {
                if (item && typeof item === 'object') {
                    Object.keys(item).forEach(key => keys.add(key));
                }
            });
            
            if (keys.size === 0) {
                return `<div>Array with ${data.length} non-object items</div>`;
            }
            
            const keysArray = [...keys];
            
            return `
                <table class="result-table">
                    <thead>
                        <tr>
                            ${keysArray.map(key => `<th>${escapeHtml(key)}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${data.map(row => `
                            <tr>
                                ${keysArray.map(key => `<td>${
                                    row[key] !== undefined && row[key] !== null 
                                        ? escapeHtml(String(row[key]))
                                        : ''
                                }</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } else {
            return `
                <table class="result-table">
                    <tbody>
                        ${Object.entries(data).map(([key, value]) => `
                            <tr>
                                <th>${escapeHtml(key)}</th>
                                <td>${escapeHtml(
                                    typeof value === 'object' && value !== null
                                        ? JSON.stringify(value)
                                        : String(value)
                                )}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
    }
    
    /**
     * Format array as HTML list
     * @param {Array} data - Data to format
     * @returns {string} HTML list
     */
    static formatAsList(data) {
        if (!Array.isArray(data)) return '<div>Not an array</div>';
        if (data.length === 0) return '<div>Empty array</div>';
        
        return `
            <ul class="result-list">
                ${data.map(item => `
                    <li>${escapeHtml(
                        typeof item === 'object' && item !== null
                            ? JSON.stringify(item)
                            : String(item)
                    )}</li>
                `).join('')}
            </ul>
        `;
    }
    
    /**
     * Copy text to clipboard
     * @param {string} text - Text to copy
     * @returns {Promise<boolean>} Success status
     */
    static async copyToClipboard(text) {
        try {
            // Try the modern Clipboard API first
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
                this.showToast('Copied to clipboard', 'success');
                return true;
            }
            
            // Fall back to the older execCommand method
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'absolute';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            
            const successful = document.execCommand('copy');
            document.body.removeChild(textarea);
            
            if (successful) {
                this.showToast('Copied to clipboard', 'success');
                return true;
            } else {
                this.showToast('Failed to copy to clipboard', 'error');
                return false;
            }
        } catch (error) {
            console.error('Error copying to clipboard:', error);
            this.showToast('Failed to copy to clipboard', 'error');
            return false;
        }
    }
    
    /**
     * Show loading spinner
     * @param {string|HTMLElement} target - Target element or ID
     * @param {Object} options - Loading options
     * @returns {Object} Control object with stop() method
     */
    static showLoading(target, options = {}) {
        const element = typeof target === 'string' ? getElement(target) : target;
        if (!element) return { stop: () => {} };
        
        // Save original content
        const originalContent = element.innerHTML;
        const originalPosition = element.style.position;
        
        // Create spinner
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        if (options.size) spinner.style.fontSize = options.size;
        
        // Add overlay if requested
        if (options.overlay) {
            element.style.position = 'relative';
            const overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.appendChild(spinner);
            
            if (options.text) {
                const text = document.createElement('div');
                text.className = 'loading-text';
                text.textContent = options.text;
                overlay.appendChild(text);
            }
            
            element.appendChild(overlay);
        } else {
            element.innerHTML = '';
            element.appendChild(spinner);
            
            if (options.text) {
                const text = document.createElement('div');
                text.className = 'loading-text';
                text.textContent = options.text;
                element.appendChild(text);
            }
        }
        
        // Return control object
        return {
            stop: () => {
                if (options.overlay) {
                    const overlay = element.querySelector('.loading-overlay');
                    if (overlay) element.removeChild(overlay);
                    element.style.position = originalPosition;
                } else {
                    element.innerHTML = originalContent;
                }
            },
            updateText: (newText) => {
                const textEl = element.querySelector('.loading-text');
                if (textEl) textEl.textContent = newText;
            }
        };
    }
}

export default UI;
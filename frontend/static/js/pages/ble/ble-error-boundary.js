/**
 * Enhanced BLE Error Boundary 
 * 
 * Provides fault tolerance for BLE operations with fallbacks and recovery options
 */
export class BleErrorBoundary {
    constructor(options = {}) {
        this.containerId = options.containerId || 'ble-error-container';
        this.maxRetries = options.maxRetries || 3;
        this.retryDelay = options.retryDelay || 2000;
        this.onError = options.onError || null;
        this.errors = new Map();
        this.recoveryStrategies = new Map();
        
        // Initialize recoverable error types
        this.initRecoveryStrategies();
        
        // Create error container if it doesn't exist
        this.ensureErrorContainer();
    }
    
    /**
     * Initialize recovery strategies for different error types
     */
    initRecoveryStrategies() {
        // Connection errors
        this.recoveryStrategies.set('connection_error', {
            retry: true,
            maxRetries: 3,
            action: async (error, context) => {
                if (typeof BleLogger !== 'undefined') {
                    BleLogger.warn('ErrorBoundary', 'connection', 'Attempting to reconnect', { error: error.message });
                }
                
                // Try to reconnect
                if (context && context.deviceId) {
                    await this.delay(1000);
                    
                    try {
                        if (context.bleConnection) {
                            return await context.bleConnection.connectToDevice(context.deviceId);
                        }
                    } catch (e) {
                        return false;
                    }
                }
                return false;
            }
        });
        
        // Scan errors
        this.recoveryStrategies.set('scan_error', {
            retry: true,
            maxRetries: 2,
            action: async (error, context) => {
                if (typeof BleLogger !== 'undefined') {
                    BleLogger.warn('ErrorBoundary', 'scan', 'Attempting to restart scan', { error: error.message });
                }
                
                // Try to scan again with shorter duration
                if (context && context.scanner) {
                    await this.delay(2000);
                    
                    try {
                        // Use a shorter scan time for retry
                        const scanTime = context.scanTime ? Math.max(2, context.scanTime - 1) : 3;
                        return await context.scanner.startScan(scanTime, context.active, false);
                    } catch (e) {
                        return false;
                    }
                }
                return false;
            }
        });
        
        // API errors
        this.recoveryStrategies.set('api_error', {
            retry: true,
            maxRetries: 3,
            action: async (error, context) => {
                if (typeof BleLogger !== 'undefined') {
                    BleLogger.warn('ErrorBoundary', 'api', 'Attempting to retry API call', { 
                        error: error.message,
                        endpoint: context?.endpoint 
                    });
                }
                
                if (context && context.apiClient && context.endpoint) {
                    await this.delay(1500);
                    
                    try {
                        return await context.apiClient.request(context.endpoint, context.options);
                    } catch (e) {
                        return false;
                    }
                }
                return false;
            }
        });
        
        // WebSocket errors
        this.recoveryStrategies.set('websocket_error', {
            retry: true,
            maxRetries: 3,
            action: async (error, context) => {
                if (typeof BleLogger !== 'undefined') {
                    BleLogger.warn('ErrorBoundary', 'websocket', 'Attempting to reconnect WebSocket', { 
                        error: error.message
                    });
                }
                
                if (context && context.websocket) {
                    await this.delay(2000);
                    
                    try {
                        return await context.websocket.connect();
                    } catch (e) {
                        return false;
                    }
                }
                return false;
            }
        });
    }
    
    /**
     * Handle an error with potential recovery
     * @param {Error} error - The error that occurred
     * @param {string} type - Error type (connection_error, scan_error, etc.)
     * @param {Object} context - Additional context for recovery
     * @returns {Promise<Object>} - Recovery result
     */
    async handleError(error, type, context = {}) {
        // Generate unique error ID
        const errorId = Date.now().toString(36) + Math.random().toString(36).substring(2, 7);
        
        // Log the error
        console.error(`BLE Error [${type}]: ${error.message}`, error);
        
        if (typeof BleLogger !== 'undefined') {
            BleLogger.error('ErrorBoundary', type, error.message, {
                errorId,
                stack: error.stack,
                context: JSON.stringify(context)
            });
        }
        
        // Store error
        this.errors.set(errorId, {
            id: errorId,
            type,
            message: error.message,
            stack: error.stack,
            context,
            timestamp: new Date(),
            recovery: {
                attempted: false,
                success: false,
                retries: 0
            }
        });
        
        // Display error in UI
        this.displayError(errorId, error, type);
        
        // Notify error handler if provided
        if (typeof this.onError === 'function') {
            this.onError(error, type, context);
        }
        
        // Check if we have a recovery strategy for this error type
        const strategy = this.recoveryStrategies.get(type);
        if (strategy && strategy.retry) {
            return this.attemptRecovery(errorId, strategy, error, context);
        }
        
        return {
            success: false,
            errorId,
            message: error.message,
            recovered: false
        };
    }
    
    /**
     * Attempt to recover from an error
     * @param {string} errorId - Error ID
     * @param {Object} strategy - Recovery strategy
     * @param {Error} error - The error that occurred
     * @param {Object} context - Additional context for recovery
     * @returns {Promise<Object>} - Recovery result
     */
    async attemptRecovery(errorId, strategy, error, context) {
        const errorInfo = this.errors.get(errorId);
        if (!errorInfo) return { success: false, recovered: false };
        
        // Update error info
        errorInfo.recovery.attempted = true;
        
        // Show recovery attempt in UI
        this.updateErrorDisplay(errorId, 'Attempting to recover...');
        
        // Try recovery up to max retries
        let success = false;
        const maxAttempts = strategy.maxRetries || this.maxRetries;
        
        for (let i = 0; i < maxAttempts; i++) {
            errorInfo.recovery.retries++;
            
            try {
                // Execute recovery action
                const result = await strategy.action(error, context);
                
                if (result) {
                    success = true;
                    break;
                }
                
                // Wait before next attempt
                await this.delay(this.retryDelay);
                
                // Update UI
                this.updateErrorDisplay(errorId, `Recovery attempt ${i + 1}/${maxAttempts} failed, retrying...`);
            } catch (e) {
                console.error(`Recovery attempt ${i + 1} failed:`, e);
                
                if (typeof BleLogger !== 'undefined') {
                    BleLogger.error('ErrorBoundary', 'recovery', `Recovery attempt ${i + 1} failed`, {
                        errorId,
                        error: e.message
                    });
                }
                
                // Wait longer after an error
                await this.delay(this.retryDelay * 1.5);
            }
        }
        
        // Update error info
        errorInfo.recovery.success = success;
        
        // Update UI
        if (success) {
            this.updateErrorDisplay(errorId, 'Successfully recovered!', true);
            
            // Remove error display after a delay
            setTimeout(() => {
                this.removeErrorDisplay(errorId);
            }, 3000);
            
            if (typeof BleLogger !== 'undefined') {
                BleLogger.info('ErrorBoundary', 'recovery', 'Successfully recovered from error', { errorId });
            }
        } else {
            this.updateErrorDisplay(errorId, `Recovery failed after ${maxAttempts} attempts.`);
            
            if (typeof BleLogger !== 'undefined') {
                BleLogger.error('ErrorBoundary', 'recovery', 'Failed to recover after maximum attempts', {
                    errorId,
                    maxAttempts
                });
            }
        }
        
        return {
            success,
            errorId,
            message: error.message,
            recovered: success,
            retries: errorInfo.recovery.retries
        };
    }
    
    /**
     * Helper method to introduce delay
     * @param {number} ms - Milliseconds to delay
     * @returns {Promise<void>}
     */
    async delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Ensure error container exists
     */
    ensureErrorContainer() {
        let container = document.getElementById(this.containerId);
        
        if (!container) {
            container = document.createElement('div');
            container.id = this.containerId;
            container.className = 'ble-error-container fixed bottom-0 right-0 m-4 max-w-md z-50';
            document.body.appendChild(container);
        }
    }
    
    /**
     * Display error in UI
     * @param {string} errorId - Error ID
     * @param {Error} error - The error that occurred
     * @param {string} type - Error type
     */
    displayError(errorId, error, type) {
        const container = document.getElementById(this.containerId);
        if (!container) return;
        
        const errorElement = document.createElement('div');
        errorElement.id = `error-${errorId}`;
        errorElement.className = 'ble-error bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4 rounded shadow-md';
        
        const title = this.getErrorTitle(type);
        const message = error.message || 'Unknown error';
        
        errorElement.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <svg class="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                    </svg>
                </div>
                <div class="ml-3 w-full">
                    <p class="text-sm font-medium">${title}</p>
                    <p class="text-sm mt-1">${message}</p>
                    <div class="recovery-status mt-2 text-xs text-red-600"></div>
                    <div class="mt-2 flex justify-end">
                        <button class="dismiss-btn text-xs text-red-700 hover:text-red-500">Dismiss</button>
                    </div>
                </div>
            </div>
        `;
        
        // Add dismiss button handler
        const dismissBtn = errorElement.querySelector('.dismiss-btn');
        if (dismissBtn) {
            dismissBtn.addEventListener('click', () => {
                this.removeErrorDisplay(errorId);
            });
        }
        
        container.appendChild(errorElement);
    }
    
    /**
     * Get a user-friendly error title
     * @param {string} type - Error type
     * @returns {string} - User-friendly title
     */
    getErrorTitle(type) {
        const titles = {
            'connection_error': 'BLE Connection Error',
            'scan_error': 'BLE Scan Error',
            'api_error': 'API Communication Error',
            'websocket_error': 'WebSocket Connection Error',
            'characteristic_error': 'BLE Characteristic Error',
            'service_error': 'BLE Service Error'
        };
        
        return titles[type] || 'BLE Error';
    }
    
    /**
     * Update error display with recovery status
     * @param {string} errorId - Error ID
     * @param {string} status - Status message
     * @param {boolean} success - Whether recovery was successful
     */
    updateErrorDisplay(errorId, status, success = false) {
        const errorElement = document.getElementById(`error-${errorId}`);
        if (!errorElement) return;
        
        const statusElement = errorElement.querySelector('.recovery-status');
        if (statusElement) {
            statusElement.textContent = status;
            
            if (success) {
                statusElement.className = 'recovery-status mt-2 text-xs text-green-600';
                errorElement.className = 'ble-error bg-green-100 border-l-4 border-green-500 text-green-700 p-4 mb-4 rounded shadow-md';
            }
        }
    }
    
    /**
     * Remove error display from UI
     * @param {string} errorId - Error ID
     */
    removeErrorDisplay(errorId) {
        const errorElement = document.getElementById(`error-${errorId}`);
        if (errorElement) {
            errorElement.classList.add('fade-out');
            
            setTimeout(() => {
                errorElement.remove();
            }, 500);
        }
    }
    
    /**
     * Clear all error displays
     */
    clearAllErrors() {
        const container = document.getElementById(this.containerId);
        if (container) {
            container.innerHTML = '';
        }
        
        this.errors.clear();
    }
    
    /**
     * Get all errors
     * @returns {Array} - All errors
     */
    getAllErrors() {
        return Array.from(this.errors.values());
    }
}

// Create global instance
window.bleErrorBoundary = window.bleErrorBoundary || new BleErrorBoundary();

export default window.bleErrorBoundary;
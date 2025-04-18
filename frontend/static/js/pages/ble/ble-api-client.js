/**
 * BLE API Client
 * Handles all communication with the BLE backend API
 */
export class BleApiClient {
    constructor(options = {}) {
        // Don't add /api/ble to baseUrl - we'll handle this in the request method
        this.baseUrl = options.baseUrl || '';
        this.maxRetries = options.maxRetries || 3;
        this.backoffFactor = options.backoffFactor || 1.5;
        this.initialDelay = options.initialDelay || 500;
        this.mockFallback = options.mockFallback === true; // Default to false unless explicitly true
        // Use provided logger or fallback to console
        this.logger = options.logger || {
            info: console.info,
            debug: console.debug || console.log,
            warning: console.warn,
            error: console.error,
            log: console.log
        };
        // Safely bind log method only if it exists
        this.log = (this.logger.log && typeof this.logger.log.bind === 'function') ? this.logger.log.bind(this.logger) : () => {};
        this.debug = options.debug || false;
        this.defaultRetries = 3;
        this.defaultTimeout = 10000;
    }

    /**
     * Make a request to the API
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Request options
     * @returns {Promise<Object>} - API response
     */
    async request(endpoint, options = {}) {
        const url = this.getEndpointUrl(endpoint);
        const requestOptions = this.prepareRequestOptions(options);
        
        // Retry configuration
        const maxRetries = options.retries || this.defaultRetries;
        const timeout = options.timeout || this.defaultTimeout;
        let attempt = 0;
        let lastError = null;
        
        // Track request for debugging
        const requestId = Math.random().toString(36).substring(2, 10);
        this.logger.info(`[${requestId}] API Request to ${endpoint}`, options.body || {});
        
        // Notify about request start
        if (typeof BleLogger !== 'undefined') {
            BleLogger.debug('API', 'request', `Starting request to ${endpoint}`, { 
                requestId,
                method: requestOptions.method,
                endpoint
            });
        }
        
        // Add timeout controller
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            controller.abort();
        }, timeout);
        
        requestOptions.signal = controller.signal;
        
        // Start retry loop
        while (attempt <= maxRetries) {
            try {
                attempt++;
                
                // Add exponential backoff delay for retries
                if (attempt > 1) {
                    const delay = Math.min(5000, 500 * Math.pow(this.backoffFactor, attempt - 1));
                    
                    if (typeof BleLogger !== 'undefined') {
                        BleLogger.debug('API', 'retry', `Retrying request to ${endpoint} (${attempt}/${maxRetries + 1})`, {
                            requestId,
                            delay
                        });
                    }
                    
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
                
                // Make request
                const startTime = Date.now();
                const response = await fetch(url, requestOptions);
                const endTime = Date.now();
                const duration = endTime - startTime;
                
                // Check status code
                if (!response.ok) {
                    const errorBody = await this.getErrorBody(response);
                    
                    // Log the error
                    if (typeof BleLogger !== 'undefined') {
                        BleLogger.warn('API', 'error', `Error response from ${endpoint}: ${response.status}`, {
                            requestId,
                            status: response.status,
                            statusText: response.statusText,
                            errorBody,
                            duration
                        });
                    }
                    
                    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorBody.detail || errorBody.message || 'No error details'}`);
                }
                
                // Parse response
                let data;
                try {
                    data = await response.json();
                } catch (e) {
                    // Empty response or not JSON
                    this.logger.warn(`[${requestId}] Response is not valid JSON:`, e);
                    
                    if (typeof BleLogger !== 'undefined') {
                        BleLogger.warn('API', 'parse', `Response parsing error for ${endpoint}`, {
                            requestId,
                            error: e.message,
                            status: response.status,
                            duration
                        });
                    }
                    
                    // Return empty success for 204 No Content
                    if (response.status === 204) {
                        return { success: true };
                    }
                    
                    throw new Error(`Failed to parse API response: ${e.message}`);
                }
                
                // Log successful response
                if (typeof BleLogger !== 'undefined') {
                    BleLogger.debug('API', 'success', `Successful response from ${endpoint}`, {
                        requestId,
                        duration,
                        status: response.status
                    });
                }
                
                this.logger.info(`[${requestId}] API Response from ${endpoint} (${duration}ms):`, data);
                
                // Cleanup timeout
                clearTimeout(timeoutId);
                
                return data;
            } catch (error) {
                lastError = error;
                
                // Special handling for abort (timeout)
                if (error.name === 'AbortError') {
                    this.logger.error(`[${requestId}] Request to ${endpoint} timed out after ${timeout}ms`);
                    
                    if (typeof BleLogger !== 'undefined') {
                        BleLogger.error('API', 'timeout', `Request to ${endpoint} timed out`, {
                            requestId,
                            timeout,
                            attempt
                        });
                    }
                    
                    // Don't retry on timeout if this is POST/PUT (mutation)
                    if (requestOptions.method !== 'GET' && requestOptions.method !== 'HEAD') {
                        break;
                    }
                } else {
                    this.logger.error(`[${requestId}] API Error in attempt ${attempt}/${maxRetries + 1}:`, error.message);
                    
                    if (typeof BleLogger !== 'undefined') {
                        BleLogger.error('API', 'error', `Request to ${endpoint} failed: ${error.message}`, {
                            requestId,
                            attempt,
                            method: requestOptions.method
                        });
                    }
                }
                
                // Last attempt, use mock or fail
                if (attempt > maxRetries) {
                    // Clean up timeout
                    clearTimeout(timeoutId);
                    
                    if (this.mockFallback) {
                        this.logger.info(`[${requestId}] Using mock response after ${attempt} failed attempts`);
                        
                        if (typeof BleLogger !== 'undefined') {
                            BleLogger.info('API', 'fallback', `Using mock response for ${endpoint} after ${attempt} failures`, {
                                requestId
                            });
                        }
                        
                        return this.getMockResponse(endpoint, options);
                    } else {
                        throw lastError;
                    }
                }
            }
        }
        
        // Clean up timeout if we somehow exited the loop
        clearTimeout(timeoutId);
        
        // This should not happen, but just in case
        if (lastError) {
            throw lastError;
        }
        
        return { success: false, error: 'Unknown error' };
    }

    /**
     * Get error details from error response
     * @param {Response} response - Fetch response
     * @returns {Object} - Error details
     */
    async getErrorBody(response) {
        try {
            return await response.json();
        } catch (e) {
            // Not a JSON response, return generic error object
            return {
                status: response.status,
                statusText: response.statusText,
                detail: 'Failed to parse error response'
            };
        }
    }

    /**
     * Prepare request options with correct formatting
     * @param {Object} options - Request options
     * @returns {Object} - Prepared options
     */
    prepareRequestOptions(options = {}) {
        const requestOptions = {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            credentials: 'same-origin'
        };
        
        // Add body for non-GET requests
        if (options.body && (requestOptions.method !== 'GET' && requestOptions.method !== 'HEAD')) {
            // Make sure we don't double-stringify the body
            if (typeof options.body === 'string') {
                requestOptions.body = options.body;
            } else {
                requestOptions.body = JSON.stringify(options.body);
            }
        }
        
        return requestOptions;
    }

    /**
     * Get the full URL for the given endpoint
     * @param {string} endpoint - API endpoint
     * @returns {string} - Full URL
     */
    getEndpointUrl(endpoint) {
        // Get rid of any existing /api/ble prefix in the endpoint
        const cleanEndpoint = endpoint.replace(/^\/?(api\/ble\/?)?/, '');
        
        // Make sure the clean endpoint starts with a slash
        const normalizedEndpoint = cleanEndpoint.startsWith('/') ? cleanEndpoint : '/' + cleanEndpoint;
        
        // Construct the full URL
        return `${this.baseUrl}/api/ble${normalizedEndpoint}`;
    }

    /**
     * Get adapter information
     */
    async getAdapterInfo() {
        this.logger.info('Getting adapter information'); // Use logger.info
        try {
            // Correct endpoint: /api/ble/adapter/adapters
            const response = await this.request('/api/ble/adapter/adapters', { method: 'GET' });
            
            // Check if the response structure is as expected
            if (response && Array.isArray(response.adapters)) {
                return response.adapters;
            } else {
                throw new Error('Invalid response structure');
            }
        } catch (error) {
            if (this.mockFallback) {
                this.logger.warn('Falling back to mock adapter info');
                return {
                    adapters: [{
                        id: "mock-adapter",
                        name: "Mock Bluetooth Adapter",
                        address: "00:11:22:33:44:55",
                        available: true,
                        status: "available",
                        manufacturer: "Mock Devices Inc.",
                        platform: "Mock"
                    }],
                    primary_adapter: {
                        id: "mock-adapter",
                        name: "Mock Bluetooth Adapter",
                        address: "00:11:22:33:44:55",
                        available: true,
                        status: "available"
                    }
                };
            }
            throw error;
        }
    }

    /**
     * Select a Bluetooth adapter
     * @param {string} adapterId - The ID of the adapter to select
     */
    async selectAdapter(adapterId) {
        this.logger.info(`Selecting adapter: ${adapterId}`); // Use logger.info
        try {
            // Correct endpoint: /api/ble/adapter/select
            return await this.request('/api/ble/adapter/select', {
                method: 'POST',
                body: JSON.stringify({ adapter_id: adapterId }),
            });
        } catch (error) {
            this.logger.error({ 
                category: 'API Error', 
                message: `Error selecting adapter ${adapterId}: ${error.message}`, 
                details: error 
            });
            throw error; // Re-throw after logging
        }
    }

    /**
     * Reset a Bluetooth adapter
     * @param {string} adapterId - The ID of the adapter to reset
     */
    async resetAdapter(adapterId) {
        try {
            if (!adapterId) {
                throw new Error('Adapter ID is required');
            }
            
            return await this.request('/device/adapter/reset', {
                method: 'POST',
                body: { adapter_id: adapterId }
            });
        } catch (error) {
            if (this.mockFallback) {
                this.logger.warn('Falling back to mock adapter reset');
                return { success: true, message: 'Mock adapter reset' };
            }
            throw error;
        }
    }

    /**
     * Get adapter health status
     */
    async getAdapterHealth() {
        try {
            return await this.request('/device/adapter/health');
        } catch (error) {
            if (this.mockFallback) {
                this.logger.warn('Falling back to mock adapter health');
                return {
                    status: "healthy",
                    details: {
                        scan_count: 42,
                        uptime: 3600,
                        error_count: 0
                    }
                };
            }
            throw error;
        }
    }

    /**
     * Set adapter power state
     * @param {boolean} powerOn Whether to power on or off
     * @param {string} adapterId Optional adapter ID
     */
    async setAdapterPower(powerOn, adapterId = null) {
        try {
            return await this.request('/device/adapter/power', {
                method: 'POST',
                body: {
                    power: powerOn,
                    adapter_id: adapterId
                }
            });
        } catch (error) {
            if (this.mockFallback) {
                this.logger.warn('Falling back to mock adapter power setting');
                return { success: true, state: powerOn ? 'on' : 'off' };
            }
            throw error;
        }
    }

    /**
     * Connect to a BLE device
     * @param {string} address The address of the device to connect to
     * @param {Object} options Optional connection parameters 
     */
    async connectToDevice(address, options = {}) {
        try {
            const connectionParams = {
                address: address,
                timeout: options.timeout || 10, // Default 10 seconds timeout
                retry: options.retry === true,
                auto_reconnect: options.autoReconnect === true
            };
            
            return await this.request('/device/connect', {
                method: 'POST',
                body: connectionParams
            });
        } catch (error) {
            if (this.mockFallback) {
                this.logger.warn(`Falling back to mock device connection: ${address}`);
                return {
                    status: "success",
                    result: {
                        connected: true,
                        device: {
                            address: address,
                            name: "Mock Connected Device",
                            services: [
                                { uuid: "1800", name: "Generic Access" },
                                { uuid: "180F", name: "Battery Service" }
                            ]
                        }
                    }
                };
            }
            throw error;
        }
    }
    
    /**
     * Disconnect from a BLE device
     * @param {string} address The address of the device to disconnect from
     */
    async disconnectDevice(address) {
        try {
            return await this.request('/device/disconnect', {
                method: 'POST',
                body: { address }
            });
        } catch (error) {
            if (this.mockFallback) {
                this.logger.warn(`Falling back to mock device disconnection: ${address}`);
                return {
                    status: "success",
                    result: { disconnected: true }
                };
            }
            throw error;
        }
    }
    
    /**
     * Get the connected device information
     */
    async getConnectedDevices() {
        this.logger.info('Getting connected devices'); // Use logger.info
        try {
            // Correct endpoint: /api/ble/device/info
            const response = await this.request('/api/ble/device/info', { method: 'GET' });
            // Backend /device/info likely returns a single object or null
            // Adapt response handling as needed based on actual backend structure
            // Assuming it returns { status: 'success', device: {...} } or similar
            return response.device ? [response.device] : []; // Return as array for consistency?
        } catch (error) {
            if (this.mockFallback) {
                this.logger.warn('Falling back to mock connected devices');
                return {
                    status: "success",
                    connected: false,
                    devices: []
                };
            }
            throw error;
        }
    }
    
    /**
     * Get device characteristics
     * @param {string} address Device address
     * @param {string} serviceUuid Optional service UUID to filter
     */
    async getDeviceCharacteristics(address, serviceUuid = null) {
        try {
            const endpoint = serviceUuid ? 
                `/device/${address}/service/${serviceUuid}/characteristics` :
                `/device/${address}/characteristics`;
                
            return await this.request(endpoint);
        } catch (error) {
            if (this.mockFallback) {
                this.logger.warn(`Falling back to mock device characteristics: ${address}`);
                return {
                    status: "success",
                    characteristics: [
                        { 
                            uuid: "2A19", 
                            name: "Battery Level", 
                            properties: ["read", "notify"],
                            service_uuid: "180F"
                        }
                    ]
                };
            }
            throw error;
        }
    }

    /**
     * Start scanning for BLE devices
     * @param {Object} options Scan options
     * @param {number} options.scan_time Scan duration in seconds
     * @param {boolean} options.active Use active scanning
     * @param {string} options.name_prefix Filter by name prefix
     * @param {Array} options.service_uuids Filter by service UUIDs
     * @returns {Promise<Object>} Scan result
     */
    async startScan(options = {}) {
        const scanOptions = {
            scan_time: options.scan_time || 5,  // Scan for 5 seconds by default
            active: options.active !== false,   // Use active scanning by default
            name_prefix: options.name_prefix || null,
            service_uuids: options.service_uuids || null,
            mock: false  // Don't use mock devices by default
        };

        try {
            return await this.request('/device/scan', {
                method: 'POST',
                body: scanOptions
            });
        } catch (error) {
            if (this.mockFallback) {
                return this.getMockScanResult();
            }
            throw error;
        }
    }

    /**
     * Get discovered devices
     * @returns {Promise<Object>} List of discovered devices
     */
    async getDiscoveredDevices() {
        try {
            return await this.request('/device/discovered');
        } catch (error) {
            if (this.mockFallback) {
                return this.getMockDiscoveredDevices();
            }
            throw error;
        }
    }

    /**
     * Get mock response for the given endpoint
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Request options
     * @returns {Object} - Mock response
     */
    getMockResponse(endpoint, options) {
        // Implement mock response logic here
        return {};
    }

    /**
     * Get mock scan result
     * @returns {Object} - Mock scan result
     */
    getMockScanResult() {
        // Implement mock scan result logic here
        return {};
    }

    /**
     * Get mock discovered devices
     * @returns {Object} - Mock discovered devices
     */
    getMockDiscoveredDevices() {
        // Implement mock discovered devices logic here
        return {};
    }
}

// Create a singleton instance for use throughout the application
export const bleApiClient = new BleApiClient({
    debug: window.BLE_DEBUG || false,
    mockFallback: false,
    logger: window.BleLogger || console
});

// Export the singleton for use in other modules
export default bleApiClient;
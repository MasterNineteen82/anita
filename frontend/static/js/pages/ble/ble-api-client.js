/**
 * BLE API Client
 * Handles all communication with the BLE backend API
 */
export class BleApiClient {
    constructor(options = {}) {
        this.baseUrl = options.baseUrl || '/api/ble';
        this.mockFallback = options.mockFallback !== false;
        this.logger = options.logger || console;
        this.debug = options.debug || false;
    }

    /**
     * Make a request to the BLE API
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const method = options.method || 'GET';
        const body = options.body;
        
        const requestOptions = {
            method,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };
        
        if (body && (method === 'POST' || method === 'PUT')) {
            requestOptions.body = JSON.stringify(body);
        }
        
        if (this.debug) {
            this.logger.debug(`BLE API Request: ${method} ${url}`, body || '');
        }
        
        try {
            const response = await fetch(url, requestOptions);
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`API Error (${response.status}): ${errorText}`);
            }
            
            // Handle empty responses
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                return data;
            } else {
                const text = await response.text();
                return text || { success: true };
            }
        } catch (error) {
            this.logger.error(`BLE API Error: ${error.message}`);
            throw error;
        }
    }

    /**
     * Get adapter information
     */
    async getAdapterInfo() {
        try {
            return await this.request('/adapter/info');
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
     * Select an adapter
     * @param {string} adapterId The ID or address of the adapter to select
     */
    async selectAdapter(adapterId) {
        try {
            // Use the correct request format expected by the backend
            return await this.request('/adapter/select', {
                method: 'POST',
                body: { id: adapterId } // IMPORTANT: Use 'id', not 'adapter_id'
            });
        } catch (error) {
            if (this.mockFallback) {
                this.logger.warn(`Falling back to mock adapter selection: ${adapterId}`);
                return {
                    status: "success",
                    adapter: {
                        id: adapterId,
                        name: "Mock Bluetooth Adapter",
                        address: adapterId,
                        available: true,
                        status: "available"
                    },
                    message: "Adapter selected successfully (mock)"
                };
            }
            throw error;
        }
    }

    /**
     * Reset an adapter
     * @param {string} adapterId The ID or address of the adapter to reset
     */
    async resetAdapter(adapterId) {
        try {
            return await this.request('/adapter/reset', {
                method: 'POST',
                body: { adapter_id: adapterId, force: true }
            });
        } catch (error) {
            if (this.mockFallback) {
                this.logger.warn('Falling back to mock adapter reset');
                return {
                    status: "success",
                    message: "Adapter reset successfully (mock)",
                    details: {
                        success: true,
                        adapter_address: adapterId,
                        actions_taken: ["Simulated adapter reset"]
                    }
                };
            }
            throw error;
        }
    }

    /**
     * Get adapter health status
     */
    async getAdapterHealth() {
        try {
            return await this.request('/adapter/health');
        } catch (error) {
            if (this.mockFallback) {
                this.logger.warn('Falling back to mock adapter health');
                return {
                    status: "available",
                    issues: [],
                    uptime: 3600,
                    scan_success_rate: 100,
                    connection_success_rate: 95,
                    timestamp: Date.now()
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
            const state = powerOn ? 'on' : 'off';
            const queryParams = adapterId ? `?adapter_id=${adapterId}` : '';
            return await this.request(`/adapter/power/${state}${queryParams}`, {
                method: 'POST'
            });
        } catch (error) {
            if (this.mockFallback) {
                this.logger.warn(`Falling back to mock adapter power: ${powerOn}`);
                return {
                    status: "success",
                    message: `Adapter power set to ${powerOn ? 'on' : 'off'} (mock)`,
                    adapter_id: adapterId || "current"
                };
            }
            throw error;
        }
    }
}

// Create a singleton instance for use throughout the application
export const bleApiClient = new BleApiClient({
    debug: window.BLE_DEBUG || false,
    mockFallback: true,
    logger: window.BleLogger || console
});

// Export the singleton for use in other modules
export default bleApiClient;
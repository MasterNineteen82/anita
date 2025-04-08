/**
 * Helper class for BLE API endpoint resolution and error handling
 */
export class BleApiHelper {
    /**
     * Try multiple possible endpoints for an API call
     * @param {Array<string>} endpoints - Array of possible endpoint paths
     * @param {Object} options - Fetch options
     * @returns {Promise<Object>} - Result object with success status and data
     */
    static async tryEndpoints(endpoints, options = {}) {
        let lastError = null;
        
        for (const endpoint of endpoints) {
            try {
                console.log(`Trying endpoint: ${endpoint}`);
                const response = await fetch(endpoint, options);
                
                if (response.ok) {
                    const data = await response.json();
                    return {
                        success: true,
                        endpoint,
                        data,
                        status: response.status
                    };
                } else {
                    const errorData = await response.json().catch(() => ({ 
                        detail: `HTTP error ${response.status}` 
                    }));
                    
                    console.warn(`Endpoint ${endpoint} failed with status ${response.status}: ${errorData.detail || 'Unknown error'}`);
                    lastError = { 
                        endpoint, 
                        status: response.status, 
                        message: errorData.detail || 'Unknown error' 
                    };
                }
            } catch (error) {
                console.warn(`Error with endpoint ${endpoint}:`, error);
                lastError = { endpoint, error };
            }
        }
        
        // All endpoints failed
        return {
            success: false,
            error: lastError || 'All endpoints failed',
            endpoints
        };
    }
    
    /**
     * Try different WebSocket endpoints
     * @returns {Promise<Object>} - Result with success status and socket
     */
    static async tryWebSocketEndpoints() {
        const endpoints = [
            '/api/ble/ws',
            '/ws/ble',
            '/api/ws/ble',
            '/api/ble/ws/ble'
        ];
        
        let connected = false;
        
        return new Promise((resolve) => {
            let attemptedCount = 0;
            
            endpoints.forEach((endpoint, index) => {
                setTimeout(() => {
                    if (!connected) {
                        try {
                            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                            const wsUrl = `${protocol}//${window.location.host}${endpoint}`;
                            
                            console.log(`Trying WebSocket endpoint: ${wsUrl}`);
                            
                            const socket = new WebSocket(wsUrl);
                            
                            socket.onopen = () => {
                                console.log(`WebSocket connected successfully to ${endpoint}`);
                                connected = true;
                                resolve({ success: true, endpoint, socket });
                                
                                // Close other connections if they open later
                                socket.onclose = () => {};
                            };
                            
                            socket.onerror = () => {
                                attemptedCount++;
                                socket.close();
                                
                                if (attemptedCount === endpoints.length && !connected) {
                                    console.error('All WebSocket endpoints failed');
                                    resolve({ success: false });
                                }
                            };
                        } catch (error) {
                            console.error(`Error trying WebSocket ${endpoint}:`, error);
                            attemptedCount++;
                            
                            if (attemptedCount === endpoints.length && !connected) {
                                resolve({ success: false });
                            }
                        }
                    }
                }, index * 1000); // Stagger attempts to avoid overwhelming the server
            });
        });
    }
    
    /**
     * Get adapter information with fallbacks
     */
    static async getAdapterInfo() {
        const endpoints = [
            '/api/ble/adapter-info',
            '/api/ble/adapter/info',
            '/api/ble/adapters'
        ];
        
        const result = await this.tryEndpoints(endpoints);
        
        if (result.success) {
            return result.data;
        }
        
        // Return mock data if all endpoints fail
        console.warn('Returning mock adapter data after all endpoints failed');
        return {
            adapters: [{
                name: 'Mock Adapter',
                address: '00:00:00:00:00:00',
                type: 'mock',
                available: true,
                manufacturer: 'Mock Manufacturer',
                platform: 'Mock Platform'
            }]
        };
    }
}
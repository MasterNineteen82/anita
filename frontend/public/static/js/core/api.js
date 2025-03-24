/**
 * API client for the ANITA backend
 */
class API {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers,
                },
            });

            const data = await response.json();
            
            // Support the new standardized response format
            if (data.status === 'error') {
                throw new Error(data.message || 'API Error');
            }
            
            return data;
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    // GET request helper
    async get(endpoint) {
        return this.request(endpoint);
    }

    // POST request helper
    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // System APIs
    async getSystemStatus() {
        return this.get('/status');
    }

    // SmartCard APIs
    async getReaders() {
        return this.get('/smartcard/readers');
    }
    
    async getSmartCardStatus() {
        return this.get('/smartcard/status');
    }

    // NFC APIs
    async discoverNFCTags() {
        return this.get('/nfc/discover');
    }
}

export default API;
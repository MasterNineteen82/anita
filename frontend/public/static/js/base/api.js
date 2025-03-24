/**
 * Enhanced API client for backend communication
 */
class ApiClient {
    constructor(baseUrl = '/api', options = {}) {
        this.baseUrl = baseUrl;
        this.defaultOptions = {
            timeout: 30000, // 30 seconds default timeout
            retries: 0,     // Default retry count
            retryDelay: 1000, // Retry delay in ms
            ...options
        };
        
        this.pendingRequests = new Map();
        this.requestInterceptors = [];
        this.responseInterceptors = [];
        this.authToken = localStorage.getItem('auth_token');
    }
    
    /**
     * Add request interceptor
     * @param {Function} interceptor - Function to process request config
     */
    addRequestInterceptor(interceptor) {
        this.requestInterceptors.push(interceptor);
        return () => this.removeRequestInterceptor(interceptor);
    }
    
    /**
     * Add response interceptor
     * @param {Function} interceptor - Function to process response
     */
    addResponseInterceptor(interceptor) {
        this.responseInterceptors.push(interceptor);
        return () => this.removeResponseInterceptor(interceptor);
    }
    
    removeRequestInterceptor(interceptor) {
        const index = this.requestInterceptors.indexOf(interceptor);
        if (index >= 0) this.requestInterceptors.splice(index, 1);
    }
    
    removeResponseInterceptor(interceptor) {
        const index = this.responseInterceptors.indexOf(interceptor);
        if (index >= 0) this.responseInterceptors.splice(index, 1);
    }
    
    /**
     * Set authentication token
     * @param {string} token - Authentication token
     */
    setAuthToken(token) {
        this.authToken = token;
        if (token) {
            localStorage.setItem('auth_token', token);
        } else {
            localStorage.removeItem('auth_token');
        }
    }
    
    /**
     * Create request configuration with defaults and interceptors
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Request options
     * @returns {Object} - Final request configuration
     */
    async createRequestConfig(endpoint, options = {}) {
        // Start with defaults
        const config = {
            url: `${this.baseUrl}${endpoint}`,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        // Add authentication if available
        if (this.authToken && !config.headers['Authorization']) {
            config.headers['Authorization'] = `Bearer ${this.authToken}`;
        }
        
        // Run request interceptors
        for (const interceptor of this.requestInterceptors) {
            await interceptor(config);
        }
        
        return config;
    }
    
    /**
     * Process response through interceptors
     * @param {Object} response - Fetch response
     * @param {Object} config - Request configuration
     * @returns {Object} - Processed response data
     */
    async processResponse(response, config) {
        let result;
        
        // Parse response based on content type
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            result = await response.json();
        } else if (contentType && contentType.includes('text/')) {
            result = await response.text();
        } else {
            result = await response.blob();
        }
        
        // Process through response interceptors
        const responseData = { data: result, status: response.status, headers: response.headers, config };
        
        for (const interceptor of this.responseInterceptors) {
            await interceptor(responseData);
        }
        
        return responseData.data;
    }
    
    /**
     * Make an HTTP request with retry logic
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Request options
     * @returns {Promise} - Response promise
     */
    async request(endpoint, options = {}) {
        const config = await this.createRequestConfig(endpoint, options);
        const maxRetries = options.retries ?? this.defaultOptions.retries;
        const retryDelay = options.retryDelay ?? this.defaultOptions.retryDelay;
        
        // Create abort controller for timeout
        const controller = new AbortController();
        const { signal } = controller;
        config.signal = signal;
        
        // Set timeout
        const timeoutId = setTimeout(() => {
            controller.abort();
        }, options.timeout ?? this.defaultOptions.timeout);
        
        // Track the request
        const requestId = Date.now().toString();
        this.pendingRequests.set(requestId, { controller, config });
        
        try {
            // Support for retries
            for (let attempt = 0; attempt <= maxRetries; attempt++) {
                try {
                    const response = await fetch(config.url, {
                        method: config.method || 'GET',
                        headers: config.headers,
                        body: config.body,
                        signal,
                        mode: config.mode || 'cors',
                        credentials: config.credentials || 'same-origin',
                        redirect: config.redirect || 'follow',
                    });
                    
                    clearTimeout(timeoutId);
                    
                    // Handle HTTP errors
                    if (!response.ok) {
                        const error = new Error(`API error: ${response.status} ${response.statusText}`);
                        error.status = response.status;
                        error.response = response;
                        throw error;
                    }
                    
                    // Process successful response
                    const result = await this.processResponse(response, config);
                    return result;
                    
                } catch (error) {
                    // For non-timeout errors and if we have retries left
                    if (attempt < maxRetries && error.name !== 'AbortError') {
                        console.warn(`Request failed, retrying (${attempt + 1}/${maxRetries})...`, error);
                        await new Promise(resolve => setTimeout(resolve, retryDelay));
                        continue;
                    }
                    throw error;
                }
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        } finally {
            clearTimeout(timeoutId);
            this.pendingRequests.delete(requestId);
        }
    }
    
    /**
     * Cancel all pending requests
     */
    cancelAllRequests() {
        for (const { controller } of this.pendingRequests.values()) {
            controller.abort();
        }
        this.pendingRequests.clear();
    }
    
    /**
     * Make a GET request
     * @param {string} endpoint - API endpoint
     * @param {Object} params - URL parameters
     * @param {Object} options - Request options
     * @returns {Promise} - Response promise
     */
    async get(endpoint, params = {}, options = {}) {
        const queryParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                queryParams.append(key, value);
            }
        });
        
        const queryString = queryParams.toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        
        return this.request(url, { method: 'GET', ...options });
    }
    
    /**
     * Make a POST request
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request payload
     * @param {Object} options - Request options
     * @returns {Promise} - Response promise
     */
    async post(endpoint, data = {}, options = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
            ...options
        });
    }
    
    /**
     * Make a PUT request
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request payload
     * @param {Object} options - Request options
     * @returns {Promise} - Response promise
     */
    async put(endpoint, data = {}, options = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
            ...options
        });
    }
    
    /**
     * Make a DELETE request
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Request options
     * @returns {Promise} - Response promise
     */
    async delete(endpoint, options = {}) {
        return this.request(endpoint, {
            method: 'DELETE',
            ...options
        });
    }
    
    /**
     * Make a PATCH request
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request payload
     * @param {Object} options - Request options
     * @returns {Promise} - Response promise
     */
    async patch(endpoint, data = {}, options = {}) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data),
            ...options
        });
    }
}

// Create and export the API client instance
export const api = (() => {
    const baseUrl = typeof CONFIG !== 'undefined' ? CONFIG.apiBaseUrl : '/api';
    return new ApiClient(baseUrl, {
        // Default configuration options
        retries: 1,  // Retry failed requests once
        timeout: 15000, // 15 second timeout
    });
})();

export default api;
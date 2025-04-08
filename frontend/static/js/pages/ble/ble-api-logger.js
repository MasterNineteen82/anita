import { BleLogger } from './ble-logger.js';
import { BlePerformanceMonitor } from './ble-performance-monitor.js';

export class BleApiLogger {
    static initialize() {
        // Store the original fetch function
        const originalFetch = window.fetch;
        
        // Override the fetch function
        window.fetch = async function(resource, options) {
            const url = resource instanceof Request ? resource.url : resource;
            const method = options?.method || 'GET';
            
            // Only log BLE API calls
            if (!url.includes('/api/ble/')) {
                return originalFetch.apply(this, arguments);
            }
            
            // Log API request
            BleLogger.debug('API', 'request', `${method} ${url}`, {
                headers: options?.headers,
                body: options?.body,
                timestamp: new Date().toISOString()
            });
            
            const startTime = performance.now();
            
            try {
                // Make the actual request
                const response = await originalFetch.apply(this, arguments);
                
                // Calculate request time
                const requestTime = performance.now() - startTime;
                BlePerformanceMonitor.recordApiLatency(url, requestTime);
                
                // Clone the response to read its body (since reading the body consumes it)
                const clonedResponse = response.clone();
                
                // Try to parse response as JSON
                let responseBody;
                try {
                    if (response.headers.get('content-type')?.includes('application/json')) {
                        responseBody = await clonedResponse.json();
                    } else {
                        responseBody = await clonedResponse.text();
                        
                        // Truncate large responses
                        if (responseBody.length > 500) {
                            responseBody = responseBody.substring(0, 500) + '... [truncated]';
                        }
                    }
                } catch (e) {
                    responseBody = '[Error parsing response]';
                }
                
                // Log successful response
                BleLogger.debug('API', 'response', `${method} ${url} completed in ${requestTime.toFixed(2)}ms`, {
                    status: response.status,
                    statusText: response.statusText,
                    body: responseBody,
                    timestamp: new Date().toISOString()
                });
                
                return response;
            } catch (error) {
                // Calculate request time
                const requestTime = performance.now() - startTime;
                
                // Log error
                BleLogger.error('API', 'response', `${method} ${url} failed in ${requestTime.toFixed(2)}ms`, {
                    error: error.message,
                    stack: error.stack,
                    timestamp: new Date().toISOString()
                });
                
                throw error;
            }
        };
        
        BleLogger.info('API', 'initialize', 'API request logging initialized');
    }
}
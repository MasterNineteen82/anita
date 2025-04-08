import { BleLogger } from './ble-logger.js';

export class BlePerformanceMonitor {
    static metrics = {
        scanTime: [],
        connectionTime: [],
        discoveryTime: [],
        apiLatency: {},
        websocketLatency: []
    };
    
    static maxSamples = 20;
    
    /**
     * Record scan duration
     * @param {number} durationMs - Scan duration in ms
     */
    static recordScanTime(durationMs) {
        this.metrics.scanTime.push(durationMs);
        if (this.metrics.scanTime.length > this.maxSamples) {
            this.metrics.scanTime.shift();
        }
        
        // Log the metric
        BleLogger.debug('Performance', 'scan', `Scan completed in ${durationMs}ms`);
        
        // Calculate average
        const avg = this.metrics.scanTime.reduce((sum, time) => sum + time, 0) / this.metrics.scanTime.length;
        BleLogger.info('Performance', 'scan', `Average scan time: ${avg.toFixed(2)}ms`);
    }
    
    /**
     * Record connection time
     * @param {number} durationMs - Connection duration in ms
     */
    static recordConnectionTime(durationMs) {
        this.metrics.connectionTime.push(durationMs);
        if (this.metrics.connectionTime.length > this.maxSamples) {
            this.metrics.connectionTime.shift();
        }
        
        // Log the metric
        BleLogger.debug('Performance', 'connection', `Connection completed in ${durationMs}ms`);
    }
    
    /**
     * Record API request latency
     * @param {string} endpoint - API endpoint
     * @param {number} durationMs - Request duration in ms
     */
    static recordApiLatency(endpoint, durationMs) {
        if (!this.metrics.apiLatency[endpoint]) {
            this.metrics.apiLatency[endpoint] = [];
        }
        
        this.metrics.apiLatency[endpoint].push(durationMs);
        if (this.metrics.apiLatency[endpoint].length > this.maxSamples) {
            this.metrics.apiLatency[endpoint].shift();
        }
        
        // Log the metric
        BleLogger.debug('Performance', 'api', `API request to ${endpoint} completed in ${durationMs}ms`);
    }
    
    /**
     * Get performance report
     * @returns {Object} Performance metrics
     */
    static getReport() {
        const report = {
            scanning: {
                average: this.calculateAverage(this.metrics.scanTime),
                min: Math.min(...this.metrics.scanTime) || 0,
                max: Math.max(...this.metrics.scanTime) || 0,
                samples: this.metrics.scanTime.length
            },
            connection: {
                average: this.calculateAverage(this.metrics.connectionTime),
                min: Math.min(...this.metrics.connectionTime) || 0,
                max: Math.max(...this.metrics.connectionTime) || 0,
                samples: this.metrics.connectionTime.length
            },
            api: {}
        };
        
        // Process API metrics
        for (const [endpoint, times] of Object.entries(this.metrics.apiLatency)) {
            report.api[endpoint] = {
                average: this.calculateAverage(times),
                min: Math.min(...times) || 0,
                max: Math.max(...times) || 0,
                samples: times.length
            };
        }
        
        return report;
    }
    
    static calculateAverage(array) {
        if (array.length === 0) return 0;
        return array.reduce((sum, value) => sum + value, 0) / array.length;
    }
}
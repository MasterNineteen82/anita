import CONFIG from '../core/config.js';
import { debounce } from '../utils/performance.js';

/**
 * Client-side logging utilities
 */

class Logger {
    constructor(api) {
        this.api = api;
        this.enabled = CONFIG.features?.enableLogging ?? true;
        this.minLevel = CONFIG.logging?.minLevel ?? 'info';
        this.batchSize = CONFIG.logging?.batchSize ?? 10;
        this.bufferTimeout = CONFIG.logging?.bufferTimeout ?? 5000;
        
        // Log levels and their priority
        this.logLevels = {
            debug: 0,
            info: 1,
            warning: 2,
            error: 3,
            critical: 4
        };
        
        // Buffer to store logs when offline or until batch size is reached
        this.logBuffer = [];
        
        // Debounced function to send logs
        this.flushLogs = debounce(this._flushLogs.bind(this), this.bufferTimeout);
        
        // Check network status
        this.isOnline = navigator.onLine;
        window.addEventListener('online', () => {
            this.isOnline = true;
            this._flushLogs();
        });
        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
        
        // Override console methods to capture logs
        this.setupConsoleOverrides();
    }
    
    /**
     * Check if a level should be logged based on minimum level setting
     */
    shouldLog(level) {
        if (!this.enabled) return false;
        const levelValue = this.logLevels[level] || 0;
        const minLevelValue = this.logLevels[this.minLevel] || 0;
        return levelValue >= minLevelValue;
    }
    
    /**
     * Log a message with specified level
     */
    log(level, message, context = {}) {
        if (!this.shouldLog(level)) return;
        
        // Add timestamp and formatted message
        const logEntry = {
            level,
            message: typeof message === 'object' ? JSON.stringify(message) : message,
            context: this._sanitizeContext(context),
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent
        };
        
        // Add to buffer
        this.logBuffer.push(logEntry);
        
        // Flush immediately for errors or when buffer is full
        if (level === 'error' || level === 'critical' || this.logBuffer.length >= this.batchSize) {
            this._flushLogs();
        } else {
            this.flushLogs();
        }
    }
    
    /**
     * Sanitize context to prevent circular references
     */
    _sanitizeContext(context) {
        try {
            // Test if context can be stringified
            JSON.stringify(context);
            return context;
        } catch (e) {
            // If circular reference, return simplified version
            return { 
                error: 'Circular reference in context object', 
                keys: Object.keys(context)
            };
        }
    }
    
    /**
     * Send logs to server
     */
    _flushLogs() {
        if (!this.logBuffer.length || !this.isOnline) return;
        
        const logs = [...this.logBuffer];
        this.logBuffer = [];
        
        this.api.post('/log/batch', { logs })
            .catch(error => {
                // Use original console to avoid recursion
                const originalConsole = window.console;
                originalConsole.error('Error sending logs to backend:', error);
                
                // Put logs back in buffer for retry
                this.logBuffer = [...logs, ...this.logBuffer];
                
                // Limit buffer size to prevent memory issues
                if (this.logBuffer.length > 100) {
                    this.logBuffer = this.logBuffer.slice(-100);
                }
            });
    }
    
    /**
     * Debug level logs
     */
    debug(message, context = {}) {
        this.log('debug', message, context);
    }
    
    /**
     * Info level logs
     */
    info(message, context = {}) {
        this.log('info', message, context);
    }
    
    /**
     * Warning level logs
     */
    warn(message, context = {}) {
        this.log('warning', message, context);
    }
    
    /**
     * Error level logs
     */
    error(message, context = {}) {
        this.log('error', message, context);
    }
    
    /**
     * Critical level logs
     */
    critical(message, context = {}) {
        this.log('critical', message, context);
    }
    
    /**
     * Performance measurement
     */
    time(label) {
        if (!this.shouldLog('debug')) return;
        performance.mark(`${label}-start`);
    }
    
    /**
     * End timing and log result
     */
    timeEnd(label) {
        if (!this.shouldLog('debug')) return;
        if (performance.getEntriesByName(`${label}-start`).length === 0) return;
        
        performance.mark(`${label}-end`);
        performance.measure(label, `${label}-start`, `${label}-end`);
        const measure = performance.getEntriesByName(label, 'measure')[0];
        
        this.debug(`Timer [${label}]: ${measure.duration.toFixed(2)}ms`);
        
        // Clean up marks
        performance.clearMarks(`${label}-start`);
        performance.clearMarks(`${label}-end`);
        performance.clearMeasures(label);
    }
    
    /**
     * Enable/disable logging
     */
    setEnabled(enabled) {
        this.enabled = enabled;
    }
    
    /**
     * Set minimum log level
     */
    setMinLevel(level) {
        if (this.logLevels[level] !== undefined) {
            this.minLevel = level;
        }
    }
    
    /**
     * Override console methods to capture logs
     */
    setupConsoleOverrides() {
        // Store original console methods
        const originalMethods = {
            log: console.log,
            info: console.info,
            debug: console.debug,
            warn: console.warn,
            error: console.error
        };
        
        // Override console.log
        console.log = (...args) => {
            this.debug(args[0], { additionalArgs: args.slice(1) });
            originalMethods.log.apply(console, args);
        };
        
        // Override console.debug
        console.debug = (...args) => {
            this.debug(args[0], { additionalArgs: args.slice(1) });
            originalMethods.debug.apply(console, args);
        };
        
        // Override console.info
        console.info = (...args) => {
            this.info(args[0], { additionalArgs: args.slice(1) });
            originalMethods.info.apply(console, args);
        };
        
        // Override console.warn
        console.warn = (...args) => {
            this.warn(args[0], { additionalArgs: args.slice(1) });
            originalMethods.warn.apply(console, args);
        };
        
        // Override console.error
        console.error = (...args) => {
            this.error(args[0], { additionalArgs: args.slice(1) });
            originalMethods.error.apply(console, args);
        };
        
        // Set up global error handler
        window.addEventListener('error', (event) => {
            this.error(event.message, {
                source: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                stack: event.error ? event.error.stack : null
            });
        });
        
        // Unhandled promise rejection handler
        window.addEventListener('unhandledrejection', (event) => {
            this.error('Unhandled Promise Rejection', {
                reason: event.reason?.toString(),
                stack: event.reason?.stack
            });
        });
    }
}

// Create logger factory instead of direct instance
export default {
    /**
     * Create a logger instance with the given API client
     */
    createLogger(api) {
        return new Logger(api);
    }
};
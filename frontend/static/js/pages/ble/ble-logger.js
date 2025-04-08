/**
 * Enhanced BLE Logging System
 */
export class BleLogger {
    static LOG_LEVELS = {
        TRACE: 0,    // Finest granular information
        DEBUG: 1,    // Detailed information
        INFO: 2,     // Normal application behavior
        WARN: 3,     // Potential issues that aren't errors
        ERROR: 4,    // Errors that don't crash the application
        FATAL: 5     // Severe errors that crash the application
    };
    
    static MIN_LOG_LEVEL = BleLogger.LOG_LEVELS.DEBUG; // Configure minimum level to output
    
    static logHistory = [];
    static maxLogHistory = 1000;
    
    /**
     * Log a message with structured data
     * @param {string} level - Log level
     * @param {string} component - Component name (adapter, scanner, etc.)
     * @param {string} operation - Operation being performed
     * @param {string} message - Log message
     * @param {Object} data - Additional contextual data
     */
    static log(level, component, operation, message, data = {}) {
        // Skip if below minimum log level
        if (BleLogger.LOG_LEVELS[level] < BleLogger.MIN_LOG_LEVEL) return;
        
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            level,
            component,
            operation,
            message,
            data
        };
        
        // Add to history
        BleLogger.logHistory.push(logEntry);
        if (BleLogger.logHistory.length > BleLogger.maxLogHistory) {
            BleLogger.logHistory.shift();
        }
        
        // Format for console/UI
        const formattedMsg = `[${component}] [${operation}] ${message}`;
        const consoleFn = level === 'ERROR' || level === 'FATAL' ? 'error' :
                         level === 'WARN' ? 'warn' :
                         level === 'DEBUG' ? 'debug' : 'log';
        
        // Log to console
        console[consoleFn](formattedMsg, data);
        
        // Log to UI through existing system
        const uiLevel = level === 'ERROR' || level === 'FATAL' ? 'error' :
                       level === 'WARN' ? 'warn' :
                       level === 'DEBUG' ? 'debug' : 'info';
        window.bleLog(formattedMsg, uiLevel);
        
        return logEntry;
    }
    
    // Convenience methods
    static trace(component, operation, message, data) {
        return BleLogger.log('TRACE', component, operation, message, data);
    }
    
    static debug(component, operation, message, data) {
        return BleLogger.log('DEBUG', component, operation, message, data);
    }
    
    static info(component, operation, message, data) {
        return BleLogger.log('INFO', component, operation, message, data);
    }
    
    static warn(component, operation, message, data) {
        return BleLogger.log('WARN', component, operation, message, data);
    }
    
    static error(component, operation, message, data) {
        return BleLogger.log('ERROR', component, operation, message, data);
    }
    
    static fatal(component, operation, message, data) {
        return BleLogger.log('FATAL', component, operation, message, data);
    }
    
    /**
     * Export logs to JSON
     */
    static exportLogs() {
        return JSON.stringify(BleLogger.logHistory);
    }
    
    /**
     * Clear log history
     */
    static clearHistory() {
        BleLogger.logHistory = [];
    }

    /**
     * Create a method decorator that logs entry and exit
     * @param {string} component - Component name
     * @param {boolean} includeArgs - Whether to include arguments in logs
     * @param {boolean} includeReturn - Whether to include return value in logs
     * @returns {Function} - Decorator function
     */
    static logMethod(component, includeArgs = true, includeReturn = true) {
        return function(target, propertyKey, descriptor) {
            const originalMethod = descriptor.value;
            
            descriptor.value = function(...args) {
                const methodName = propertyKey;
                const argsData = includeArgs ? 
                    args.map(arg => typeof arg === 'object' ? 
                        (arg instanceof Error ? { message: arg.message, stack: arg.stack } : arg) 
                        : arg) 
                    : 'args hidden';
                
                BleLogger.debug(component, methodName, `BEGIN`, includeArgs ? { arguments: argsData } : {});
                
                try {
                    // Track execution time
                    const startTime = performance.now();
                    const result = originalMethod.apply(this, args);
                    
                    // Handle promises
                    if (result instanceof Promise) {
                        return result.then(value => {
                            const executionTime = performance.now() - startTime;
                            const logData = {
                                executionTime: `${executionTime.toFixed(2)}ms`,
                                ...(includeReturn && { result: value })
                            };
                            BleLogger.debug(component, methodName, `END (Promise)`, logData);
                            return value;
                        }).catch(error => {
                            const executionTime = performance.now() - startTime;
                            BleLogger.error(component, methodName, `ERROR (Promise)`, {
                                executionTime: `${executionTime.toFixed(2)}ms`,
                                error: error.message,
                                stack: error.stack
                            });
                            throw error;
                        });
                    }
                    
                    // Handle synchronous methods
                    const executionTime = performance.now() - startTime;
                    const logData = {
                        executionTime: `${executionTime.toFixed(2)}ms`,
                        ...(includeReturn && { result })
                    };
                    BleLogger.debug(component, methodName, `END`, logData);
                    return result;
                } catch (error) {
                    BleLogger.error(component, methodName, `ERROR`, {
                        error: error.message,
                        stack: error.stack
                    });
                    throw error;
                }
            };
            
            return descriptor;
        };
    }
}
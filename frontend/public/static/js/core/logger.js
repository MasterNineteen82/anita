/**
 * Logging functionality for the frontend
 */
import api from './api.js';

class Logger {
    constructor() {
        // Override console methods to capture logs
        this.overrideConsole();
    }
    
    overrideConsole() {
        const originalConsole = {
            log: console.log,
            info: console.info,
            warn: console.warn,
            error: console.error
        };
        
        console.log = (...args) => {
            originalConsole.log(...args);
            this.captureLog('info', args);
        };
        
        console.info = (...args) => {
            originalConsole.info(...args);
            this.captureLog('info', args);
        };
        
        console.warn = (...args) => {
            originalConsole.warn(...args);
            this.captureLog('warning', args);
        };
        
        console.error = (...args) => {
            originalConsole.error(...args);
            this.captureLog('error', args);
        };
        
        // Capture global errors
        window.addEventListener('error', (event) => {
            this.error(event.message, {
                source: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                error: event.error ? event.error.stack : null
            });
            return false;
        });
    }
    
    captureLog(level, args) {
        // Convert args to a string
        let message = args.map(arg => {
            if (typeof arg === 'object') {
                try {
                    return JSON.stringify(arg);
                } catch (e) {
                    return String(arg);
                }
            }
            return String(arg);
        }).join(' ');
        
        // Send to server if enabled
        if (CONFIG.features.enableLogging) {
            this.sendToServer(level, message);
        }
    }
    
    info(message, context = {}) {
        console.info(message);
        this.sendToServer('info', message, context);
    }
    
    warning(message, context = {}) {
        console.warn(message);
        this.sendToServer('warning', message, context);
    }
    
    error(message, context = {}) {
        console.error(message);
        this.sendToServer('error', message, context);
    }
    
    async sendToServer(level, message, context = {}) {
        if (!CONFIG.features.enableLogging) return;
        
        try {
            await api.post('/log', {
                level: level,
                message: message,
                context: context,
                timestamp: new Date().toISOString()
            });
        } catch (error) {
            // Don't use console.error here to avoid infinite loops
            console.warn('Failed to send log to server:', error);
        }
    }
}

// Create singleton instance
const logger = new Logger();
export default logger;
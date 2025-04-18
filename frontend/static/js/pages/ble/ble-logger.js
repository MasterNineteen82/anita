/**
 * BLE Logger - Enhanced logging utility for BLE operations
 */
export class BleLogger {
    static LOG_LEVELS = {
        TRACE: 0,
        DEBUG: 1,
        INFO: 2,
        WARN: 3,
        ERROR: 4,
        FATAL: 5
    };
    
    static LOG_LEVEL_NAMES = ['TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL'];
    
    static currentLevel = BleLogger.LOG_LEVELS.INFO;
    static history = [];
    static maxHistorySize = 1000;
    static consoleOutput = true;
    static persistLogs = true;
    static logListeners = [];
    
    /**
     * Initialize the logger
     * @param {Object} options - Logger configuration
     */
    static initialize(options = {}) {
        console.log('Initializing BLE Logger');
        
        // Set options
        if (options.level !== undefined) {
            this.setLevel(options.level);
        }
        
        if (options.maxHistorySize !== undefined) {
            this.maxHistorySize = options.maxHistorySize;
        }
        
        if (options.consoleOutput !== undefined) {
            this.consoleOutput = options.consoleOutput;
        }
        
        if (options.persistLogs !== undefined) {
            this.persistLogs = options.persistLogs;
        }
        
        // Load persisted logs if enabled
        if (this.persistLogs) {
            this.loadHistory();
        }
        
        // Add window error handler
        window.addEventListener('error', (event) => {
            this.error('Global', 'uncaught', 'Uncaught error', {
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                error: event.error?.stack || 'No stack available'
            });
        });
        
        // Add unhandled promise rejection handler
        window.addEventListener('unhandledrejection', (event) => {
            this.error('Global', 'promise', 'Unhandled promise rejection', {
                reason: event.reason?.message || String(event.reason),
                stack: event.reason?.stack || 'No stack available'
            });
        });
        
        console.log('BLE Logger initialized');
        return true;
    }
    
    /**
     * Set the minimum log level to display
     * @param {string|number} level - Log level name or number
     */
    static setLevel(level) {
        if (typeof level === 'string') {
            const upperLevel = level.toUpperCase();
            if (this.LOG_LEVELS[upperLevel] !== undefined) {
                this.currentLevel = this.LOG_LEVELS[upperLevel];
                console.log(`Log level set to ${upperLevel}`);
            } else {
                console.warn(`Invalid log level: ${level}`);
            }
        } else if (typeof level === 'number' && level >= 0 && level <= 5) {
            this.currentLevel = level;
            console.log(`Log level set to ${this.LOG_LEVEL_NAMES[level]}`);
        } else {
            console.warn(`Invalid log level: ${level}`);
        }
    }
    
    /**
     * Add a log entry
     * @param {number} level - Log level (0-5)
     * @param {string} category - Log category 
     * @param {string} action - Log action
     * @param {string} message - Log message
     * @param {Object} data - Additional data to log
     */
    static log(level, category, action, message, data = {}) {
        // Check if level is enabled
        if (level < this.currentLevel) {
            return;
        }
        
        const timestamp = new Date();
        const entry = {
            level,
            levelName: this.LOG_LEVEL_NAMES[level],
            timestamp,
            category,
            action,
            message,
            data
        };
        
        // Add to history
        this.history.push(entry);
        
        // Trim history if needed
        if (this.history.length > this.maxHistorySize) {
            this.history = this.history.slice(-this.maxHistorySize);
        }
        
        // Console output if enabled
        if (this.consoleOutput) {
            this.outputToConsole(entry);
        }
        
        // Persist logs if enabled
        if (this.persistLogs) {
            this.persistHistory();
        }
        
        // Notify listeners
        this.notifyListeners(entry);
        
        return entry;
    }
    
    /**
     * Output log entry to console
     * @param {Object} entry - Log entry
     */
    static outputToConsole(entry) {
        const timeString = entry.timestamp.toISOString();
        const prefix = `[${timeString}] [${entry.levelName}] [${entry.category}:${entry.action}]`;
        
        switch (entry.level) {
            case this.LOG_LEVELS.TRACE:
                console.debug(`${prefix} ${entry.message}`, entry.data);
                break;
            case this.LOG_LEVELS.DEBUG:
                console.debug(`${prefix} ${entry.message}`, entry.data);
                break;
            case this.LOG_LEVELS.INFO:
                console.info(`${prefix} ${entry.message}`, entry.data);
                break;
            case this.LOG_LEVELS.WARN:
                console.warn(`${prefix} ${entry.message}`, entry.data);
                break;
            case this.LOG_LEVELS.ERROR:
            case this.LOG_LEVELS.FATAL:
                console.error(`${prefix} ${entry.message}`, entry.data);
                break;
        }
    }
    
    /**
     * Persist log history to local storage
     */
    static persistHistory() {
        try {
            // Only store latest 500 entries to avoid exceeding storage limits
            const toStore = this.history.slice(-500);
            localStorage.setItem('ble_log_history', JSON.stringify(toStore));
        } catch (error) {
            console.error('Error persisting log history:', error);
        }
    }
    
    /**
     * Load log history from local storage
     */
    static loadHistory() {
        try {
            const stored = localStorage.getItem('ble_log_history');
            if (stored) {
                const parsed = JSON.parse(stored);
                // Convert string timestamps back to Date objects
                this.history = parsed.map(entry => ({
                    ...entry,
                    timestamp: new Date(entry.timestamp)
                }));
                console.log(`Loaded ${this.history.length} log entries from storage`);
            }
        } catch (error) {
            console.error('Error loading log history:', error);
        }
    }
    
    /**
     * Clear log history
     */
    static clearHistory() {
        this.history = [];
        
        // Clear persisted logs if enabled
        if (this.persistLogs) {
            try {
                localStorage.removeItem('ble_log_history');
            } catch (error) {
                console.error('Error clearing persisted log history:', error);
            }
        }
        
        // Notify listeners
        this.notifyListeners({ type: 'clear' });
    }
    
    /**
     * Add a log listener
     * @param {Function} callback - Callback function
     * @returns {number} Listener ID
     */
    static addListener(callback) {
        if (typeof callback !== 'function') {
            console.warn('Invalid log listener callback');
            return -1;
        }
        
        const id = Date.now() + Math.random();
        this.logListeners.push({ id, callback });
        return id;
    }
    
    /**
     * Remove a log listener
     * @param {number} id - Listener ID
     */
    static removeListener(id) {
        const index = this.logListeners.findIndex(listener => listener.id === id);
        if (index !== -1) {
            this.logListeners.splice(index, 1);
            return true;
        }
        return false;
    }
    
    /**
     * Notify all log listeners
     * @param {Object} entry - Log entry
     */
    static notifyListeners(entry) {
        for (const listener of this.logListeners) {
            try {
                listener.callback(entry);
            } catch (error) {
                console.error('Error in log listener:', error);
            }
        }
    }
    
    /**
     * Get filtered log history
     * @param {Object} options - Filter options
     * @returns {Array} Filtered log entries
     */
    static getFilteredHistory(options = {}) {
        let filtered = [...this.history];
        
        // Filter by level
        if (options.level !== undefined) {
            const minLevel = typeof options.level === 'string' 
                ? this.LOG_LEVELS[options.level.toUpperCase()] 
                : options.level;
                
            filtered = filtered.filter(entry => entry.level >= minLevel);
        }
        
        // Filter by category
        if (options.category) {
            filtered = filtered.filter(entry => entry.category === options.category);
        }
        
        // Filter by action
        if (options.action) {
            filtered = filtered.filter(entry => entry.action === options.action);
        }
        
        // Filter by time range
        if (options.startTime) {
            const startTime = new Date(options.startTime);
            filtered = filtered.filter(entry => entry.timestamp >= startTime);
        }
        
        if (options.endTime) {
            const endTime = new Date(options.endTime);
            filtered = filtered.filter(entry => entry.timestamp <= endTime);
        }
        
        // Filter by search text
        if (options.search) {
            const searchLower = options.search.toLowerCase();
            filtered = filtered.filter(entry => 
                entry.message.toLowerCase().includes(searchLower) ||
                entry.category.toLowerCase().includes(searchLower) ||
                entry.action.toLowerCase().includes(searchLower) ||
                JSON.stringify(entry.data).toLowerCase().includes(searchLower)
            );
        }
        
        // Apply limit
        if (options.limit && filtered.length > options.limit) {
            filtered = filtered.slice(-options.limit);
        }
        
        return filtered;
    }
    
    /**
     * Export log history to JSON
     * @returns {string} JSON string of log history
     */
    static exportToJson() {
        return JSON.stringify(this.history, null, 2);
    }
    
    /**
     * Trace level log
     * @param {string} category - Log category
     * @param {string} action - Log action 
     * @param {string} message - Log message
     * @param {Object} data - Additional data
     */
    static trace(category, action, message, data = {}) {
        return this.log(this.LOG_LEVELS.TRACE, category, action, message, data);
    }
    
    /**
     * Debug level log
     * @param {string} category - Log category
     * @param {string} action - Log action 
     * @param {string} message - Log message
     * @param {Object} data - Additional data
     */
    static debug(category, action, message, data = {}) {
        return this.log(this.LOG_LEVELS.DEBUG, category, action, message, data);
    }
    
    /**
     * Info level log
     * @param {string} category - Log category
     * @param {string} action - Log action 
     * @param {string} message - Log message
     * @param {Object} data - Additional data
     */
    static info(category, action, message, data = {}) {
        return this.log(this.LOG_LEVELS.INFO, category, action, message, data);
    }
    
    /**
     * Warn level log
     * @param {string} category - Log category
     * @param {string} action - Log action 
     * @param {string} message - Log message
     * @param {Object} data - Additional data
     */
    static warn(category, action, message, data = {}) {
        return this.log(this.LOG_LEVELS.WARN, category, action, message, data);
    }
    
    /**
     * Error level log
     * @param {string} category - Log category
     * @param {string} action - Log action 
     * @param {string} message - Log message
     * @param {Object} data - Additional data
     */
    static error(category, action, message, data = {}) {
        return this.log(this.LOG_LEVELS.ERROR, category, action, message, data);
    }
    
    /**
     * Fatal level log
     * @param {string} category - Log category
     * @param {string} action - Log action 
     * @param {string} message - Log message
     * @param {Object} data - Additional data
     */
    static fatal(category, action, message, data = {}) {
        return this.log(this.LOG_LEVELS.FATAL, category, action, message, data);
    }
}

// Initialize on script load with default settings
BleLogger.initialize();
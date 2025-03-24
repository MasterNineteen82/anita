/**
 * Storage utility functions for managing browser storage operations
 * Provides an enhanced interface for localStorage with support for
 * namespacing, expiration, and improved error handling.
 */

/**
 * Save data to local storage with optional expiration
 * @param {string} key - Storage key
 * @param {*} data - Data to store
 * @param {Object} [options={}] - Storage options
 * @param {number} [options.expiry] - Expiration time in milliseconds
 * @param {string} [options.namespace] - Namespace for the key
 * @returns {boolean} Success status
 */
export function saveToStorage(key, data, options = {}) {
    try {
        if (!key) {
            console.warn('Storage key cannot be empty.');
            return false;
        }

        const storageKey = options.namespace ? `${options.namespace}:${key}` : key;
        const storageData = {
            data,
            timestamp: Date.now()
        };

        // Add expiration if specified
        if (options.expiry && typeof options.expiry === 'number' && options.expiry > 0) {
            storageData.expiry = Date.now() + options.expiry;
        } else if (options.expiry) {
            console.warn('Invalid expiry value. Expiry must be a positive number in milliseconds.');
        }

        localStorage.setItem(storageKey, JSON.stringify(storageData));
        return true;
    } catch (error) {
        console.error(`Error saving to storage: ${key}`, error);
        return false;
    }
}

/**
 * Load data from local storage
 * @param {string} key - Storage key
 * @param {Object} [options={}] - Storage options
 * @param {string} [options.namespace] - Namespace for the key
 * @param {*} [defaultValue=null] - Default value if not found or expired
 * @returns {*} Retrieved data or default value
 */
export function loadFromStorage(key, options = {}, defaultValue = null) {
    try {
        if (!key) {
            console.warn('Storage key cannot be empty.');
            return defaultValue;
        }

        const storageKey = options.namespace ? `${options.namespace}:${key}` : key;
        const item = localStorage.getItem(storageKey);

        if (!item) {
            return defaultValue;
        }

        const storageData = JSON.parse(item);

        if (storageData.expiry && Date.now() > storageData.expiry) {
            // Item has expired, remove it
            localStorage.removeItem(storageKey);
            return defaultValue;
        }

        return storageData.data;
    } catch (error) {
        console.error(`Error loading from storage: ${key}`, error);
        return defaultValue;
    }
}

/**
 * Remove data from local storage
 * @param {string} key - Storage key
 * @param {Object} [options={}] - Storage options
 * @param {string} [options.namespace] - Namespace for the key
 * @returns {boolean} Success status
 */
export function removeFromStorage(key, options = {}) {
    try {
        if (!key) {
            console.warn('Storage key cannot be empty.');
            return false;
        }
        const storageKey = options.namespace ? `${options.namespace}:${key}` : key;
        localStorage.removeItem(storageKey);
        return true;
    } catch (error) {
        console.error(`Error removing from storage: ${key}`, error);
        return false;
    }
}

/**
 * Clear all data from local storage within a namespace
 * @param {Object} [options={}] - Storage options
 * @param {string} [options.namespace] - Namespace to clear
 */
export function clearNamespace(options = {}) {
    try {
        const namespace = options.namespace;
        if (!namespace) {
            console.warn('Namespace cannot be empty when clearing namespace.');
            return;
        }

        for (let i = localStorage.length - 1; i >= 0; i--) {
            const key = localStorage.key(i);
            if (key && key.startsWith(`${namespace}:`)) {
                localStorage.removeItem(key);
            }
        }
    } catch (error) {
        console.error(`Error clearing namespace: ${options.namespace}`, error);
    }
}

/**
 * Clear all data from local storage. Use with caution!
 */
export function clearAllStorage() {
    try {
        localStorage.clear();
    } catch (error) {
        console.error('Error clearing all storage:', error);
    }
}
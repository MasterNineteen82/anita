/**
 * Utility functions for the application
 */

/**
 * Get DOM element by ID with error handling
 * @param {string} id - Element ID
 * @returns {HTMLElement} - The found element
 */
export function getElement(id) {
    const element = document.getElementById(id);
    if (!element) {
        throw new Error(`Element with id '${id}' not found`);
    }
    return element;
}

/**
 * Save data to local storage
 * @param {string} key - Storage key
 * @param {any} value - Value to store
 */
export function saveToStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
        console.error(`Error saving to storage: ${key}`, error);
    }
}

/**
 * Load data from local storage
 * @param {string} key - Storage key
 * @param {any} defaultValue - Default value if not found
 * @returns {any} - Retrieved value or default
 */
export function loadFromStorage(key, defaultValue = null) {
    try {
        const value = localStorage.getItem(key);
        return value ? JSON.parse(value) : defaultValue;
    } catch (error) {
        console.error(`Error loading from storage: ${key}`, error);
        return defaultValue;
    }
}

/**
 * Format byte array to hex string
 * @param {Uint8Array} bytes - Byte array
 * @returns {string} - Hex string
 */
export function bytesToHex(bytes) {
    return Array.from(bytes)
        .map(b => b.toString(16).padStart(2, '0'))
        .join(' ');
}

/**
 * Parse hex string to byte array
 * @param {string} hexString - Hex string
 * @returns {Uint8Array} - Byte array
 */
export function hexToBytes(hexString) {
    const cleanedString = hexString.replace(/\s/g, '');
    const bytes = [];
    
    for (let i = 0; i < cleanedString.length; i += 2) {
        const byteValue = parseInt(cleanedString.substr(i, 2), 16);
        if (isNaN(byteValue)) {
            throw new Error(`Invalid hex string at position ${i}`);
        }
        bytes.push(byteValue);
    }
    
    return new Uint8Array(bytes);
}
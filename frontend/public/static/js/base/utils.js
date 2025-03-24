/**
 * Enhanced utility functions
 */

/**
 * Safely parse JSON with error handling
 * @param {string} str - JSON string to parse
 * @param {*} fallback - Value to return if parsing fails
 * @returns {*} Parsed object or fallback value
 */
export function safeJsonParse(str, fallback = null) {
    if (!str) return fallback;
    try {
        return JSON.parse(str);
    } catch (error) {
        console.error('Error parsing JSON:', error);
        return fallback;
    }
}

/**
 * Safely stringify JSON with error handling
 * @param {*} obj - Object to stringify
 * @param {string} fallback - String to return if stringification fails
 * @returns {string} JSON string or fallback
 */
export function safeJsonStringify(obj, fallback = '{}') {
    try {
        return JSON.stringify(obj);
    } catch (error) {
        console.error('Error stringifying object:', error);
        return fallback;
    }
}

/**
 * Escape HTML to prevent XSS
 * @param {string} string - String to escape
 * @returns {string} Escaped HTML string
 */
export function escapeHtml(string) {
    if (!string) return '';
    const entityMap = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
        '/': '&#x2F;',
        '`': '&#x60;',
        '=': '&#x3D;'
    };
    return String(string).replace(/[&<>"'`=\/]/g, s => entityMap[s]);
}

/**
 * Convert hex string to ASCII
 * @param {string} hexString - Hex string to convert
 * @returns {string} ASCII representation
 */
export function hexToAscii(hexString) {
    if (!hexString) return '';
    hexString = hexString.replace(/\s/g, ''); // Remove spaces
    
    let ascii = '';
    for (let i = 0; i < hexString.length; i += 2) {
        const hex = hexString.substr(i, 2);
        const decimal = parseInt(hex, 16);
        ascii += (decimal >= 32 && decimal <= 126) ? String.fromCharCode(decimal) : '.';
    }
    return ascii;
}

/**
 * Convert ASCII string to hex
 * @param {string} asciiString - ASCII string to convert
 * @param {boolean} addSpaces - Whether to add spaces between bytes
 * @returns {string} Hex representation
 */
export function asciiToHex(asciiString, addSpaces = false) {
    if (!asciiString) return '';
    
    let hex = '';
    for (let i = 0; i < asciiString.length; i++) {
        const charCode = asciiString.charCodeAt(i);
        const hexValue = charCode.toString(16).padStart(2, '0');
        hex += hexValue + (addSpaces ? ' ' : '');
    }
    return addSpaces ? hex.trim() : hex;
}

/**
 * Get element by ID with error handling
 * @param {string} id - Element ID
 * @returns {HTMLElement|null} Found element or null
 */
export function getElement(id) {
    const element = document.getElementById(id);
    if (!element) {
        console.warn(`Element with ID "${id}" not found`);
    }
    return element;
}

/**
 * Create DOM element with properties
 * @param {string} tag - Element tag name
 * @param {Object} props - Element properties and attributes
 * @param {Array} children - Child elements or text content
 * @returns {HTMLElement} Created element
 */
export function createElement(tag, props = {}, children = []) {
    const element = document.createElement(tag);
    
    // Apply properties and attributes
    Object.entries(props).forEach(([key, value]) => {
        if (key === 'className') {
            element.className = value;
        } else if (key === 'style' && typeof value === 'object') {
            Object.assign(element.style, value);
        } else if (key.startsWith('on') && typeof value === 'function') {
            element.addEventListener(key.substring(2).toLowerCase(), value);
        } else if (key === 'dataset' && typeof value === 'object') {
            Object.entries(value).forEach(([dataKey, dataValue]) => {
                element.dataset[dataKey] = dataValue;
            });
        } else {
            element.setAttribute(key, value);
        }
    });
    
    // Add children
    if (Array.isArray(children)) {
        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child instanceof Node) {
                element.appendChild(child);
            }
        });
    } else if (typeof children === 'string') {
        element.textContent = children;
    }
    
    return element;
}

/**
 * Save data to local storage
 * @param {string} key - Storage key
 * @param {*} data - Data to store
 * @returns {boolean} Success status
 */
export function saveToStorage(key, data) {
    try {
        localStorage.setItem(key, typeof data === 'string' ? data : JSON.stringify(data));
        return true;
    } catch (error) {
        console.error('Error saving to local storage:', error);
        return false;
    }
}

/**
 * Load data from local storage
 * @param {string} key - Storage key
 * @param {*} defaultValue - Default value if not found
 * @returns {*} Retrieved data or default value
 */
export function loadFromStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        if (item === null) return defaultValue;
        return safeJsonParse(item, defaultValue);
    } catch (error) {
        console.error('Error loading from local storage:', error);
        return defaultValue;
    }
}

/**
 * Debounce function to limit how often a function is called
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

/**
 * Throttle function execution
 * @param {Function} func - Function to throttle
 * @param {number} limit - Throttle time in milliseconds
 * @returns {Function} Throttled function
 */
export function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Format date as string
 * @param {Date|string|number} date - Date to format
 * @param {string} format - Format string (simple)
 * @returns {string} Formatted date string
 */
export function formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
    const d = date instanceof Date ? date : new Date(date);
    
    if (isNaN(d.getTime())) {
        console.error('Invalid date provided to formatDate');
        return '';
    }
    
    const pad = (num) => String(num).padStart(2, '0');
    
    const replacements = {
        YYYY: d.getFullYear(),
        MM: pad(d.getMonth() + 1),
        DD: pad(d.getDate()),
        HH: pad(d.getHours()),
        mm: pad(d.getMinutes()),
        ss: pad(d.getSeconds())
    };
    
    return format.replace(/YYYY|MM|DD|HH|mm|ss/g, match => replacements[match]);
}

/**
 * Parse URL query parameters
 * @param {string} [queryString=window.location.search] - Query string
 * @returns {Object} Object containing query parameters
 */
export function getQueryParams(queryString = window.location.search) {
    const params = {};
    new URLSearchParams(queryString).forEach((value, key) => {
        // Handle array parameters (param[]=value1&param[]=value2)
        if (key.endsWith('[]')) {
            const arrayKey = key.slice(0, -2);
            if (!params[arrayKey]) {
                params[arrayKey] = [];
            }
            params[arrayKey].push(value);
        } else {
            params[key] = value;
        }
    });
    return params;
}

/**
 * Type checking utilities
 */
export const typeChecks = {
    isString: value => typeof value === 'string',
    isNumber: value => typeof value === 'number' && !isNaN(value),
    isBoolean: value => typeof value === 'boolean',
    isFunction: value => typeof value === 'function',
    isObject: value => value !== null && typeof value === 'object' && !Array.isArray(value),
    isArray: value => Array.isArray(value),
    isNumeric: value => !isNaN(parseFloat(value)) && isFinite(value),
    isHexString: value => /^[0-9A-Fa-f\s]*$/.test(value)
};

/**
 * Format bytes to human-readable string
 * @param {number} bytes - Bytes to format
 * @param {number} [decimals=2] - Decimal places
 * @returns {string} Formatted string
 */
export function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
}

/**
 * Generate a random string
 * @param {number} length - Length of string
 * @param {string} [charset] - Character set
 * @returns {string} Random string
 */
export function randomString(length, charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789') {
    let result = '';
    const charsetLength = charset.length;
    for (let i = 0; i < length; i++) {
        result += charset.charAt(Math.floor(Math.random() * charsetLength));
    }
    return result;
}

// Export all as default object for non-ES module environments
export default {
    safeJsonParse,
    safeJsonStringify,
    escapeHtml,
    hexToAscii,
    asciiToHex,
    getElement,
    createElement,
    saveToStorage,
    loadFromStorage,
    debounce,
    throttle,
    formatDate,
    getQueryParams,
    typeChecks,
    formatBytes,
    randomString
};
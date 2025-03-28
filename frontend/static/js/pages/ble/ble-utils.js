/**
 * Safely get a DOM element with error handling
 * @param {string} id - Element ID to find
 * @param {boolean} required - Whether to log an error if not found
 * @returns {HTMLElement|null} - The found element or null
 */
export function getElement(id, required = false) {
    const element = document.getElementById(id);
    if (!element && required) {
        console.warn(`Required DOM element not found: ${id}`);
    }
    return element;
}

/**
 * Safely set text content on an element
 * @param {string} id - Element ID
 * @param {string} text - Text to set
 * @returns {boolean} - Whether the operation was successful
 */
export function setElementText(id, text) {
    const element = getElement(id);
    if (element) {
        element.textContent = text;
        return true;
    }
    return false;
}
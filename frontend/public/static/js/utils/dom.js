/**
 * DOM utility functions
 */

/**
 * Get an element by ID with type safety
 * @param {string} id - Element ID
 * @returns {HTMLElement} The DOM element
 * @throws {Error} If element not found
 */
export function getElement(id) {
    const element = document.getElementById(id);
    if (!element) {
        throw new Error(`Element with ID '${id}' not found`);
    }
    return element;
}

/**
 * Query for an element with a CSS selector
 * @param {string} selector - CSS selector
 * @param {Element|Document} [parent=document] - Parent element
 * @returns {Element|null} The first matching element or null
 */
export function querySelector(selector, parent = document) {
    return parent.querySelector(selector);
}

/**
 * Query for all elements matching a CSS selector
 * @param {string} selector - CSS selector
 * @param {Element|Document} [parent=document] - Parent element
 * @returns {NodeListOf<Element>} List of matching elements
 */
export function querySelectorAll(selector, parent = document) {
    return parent.querySelectorAll(selector);
}

/**
 * Create a new element with optional attributes and children
 * @param {string} tag - HTML tag name
 * @param {Object} [attrs={}] - Element attributes
 * @param {(string|Node)[]} [children=[]] - Child nodes or strings
 * @returns {HTMLElement} The created element
 */
export function createElement(tag, attrs = {}, children = []) {
    const element = document.createElement(tag);
    
    // Set attributes
    Object.entries(attrs).forEach(([key, value]) => {
        if (key === 'className') {
            element.className = value;
        } else if (key === 'style' && typeof value === 'object') {
            Object.assign(element.style, value);
        } else if (key.startsWith('on') && typeof value === 'function') {
            element.addEventListener(key.substring(2).toLowerCase(), value);
        } else {
            element.setAttribute(key, value);
        }
    });
    
        // Add children
        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child instanceof Node) {
                element.appendChild(child);
            }
        });
        
        return element;
    }

// Add this helper function to create styled buttons
export function createStyledButton(text, options = {}) {
  const { id, className, small, secondary, icon, onClick, disabled } = options;
  
  const btn = document.createElement('button');
  if (id) btn.id = id;
  
  btn.className = `btn ${small ? 'btn-sm' : ''} ${secondary ? 'btn-secondary' : ''} ${className || ''}`;
  if (disabled) btn.disabled = true;
  
  const content = document.createElement('span');
  content.className = 'btn-content';
  
  if (icon) {
    const iconSpan = document.createElement('span');
    iconSpan.className = 'btn-icon';
    iconSpan.innerHTML = icon;
    content.appendChild(iconSpan);
    
    if (text) {
      content.appendChild(document.createTextNode(' ' + text));
    }
  } else {
    content.textContent = text;
  }
  
  btn.appendChild(content);
  
  if (onClick) {
    btn.addEventListener('click', onClick);
  }
  
  return btn;
}
/**
 * Simple event emitter implementation
 */
class EventEmitter {
    constructor() {
        this.events = {};
    }
    
    /**
     * Subscribe to an event
     * @param {string} event - Event name
     * @param {function} listener - Event handler function
     * @returns {function} Unsubscribe function
     */
    on(event, listener) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        
        this.events[event].push(listener);
        
        // Return a function to remove this listener
        return () => this.off(event, listener);
    }
    
    /**
     * Subscribe to an event for a single execution
     * @param {string} event - Event name
     * @param {function} listener - Event handler function
     * @returns {function} Unsubscribe function
     */
    once(event, listener) {
        const onceListener = (...args) => {
            this.off(event, onceListener);
            listener.apply(this, args);
        };
        
        return this.on(event, onceListener);
    }
    
    /**
     * Unsubscribe from an event
     * @param {string} event - Event name
     * @param {function} listenerToRemove - Event handler function to remove
     * @returns {boolean} Whether the listener was found and removed
     */
    off(event, listenerToRemove) {
        if (!this.events[event]) {
            return false;
        }
        
        const index = this.events[event].indexOf(listenerToRemove);
        
        if (index !== -1) {
            this.events[event].splice(index, 1);
            return true;
        }
        
        return false;
    }
    
    /**
     * Emit an event
     * @param {string} event - Event name
     * @param {...any} args - Arguments to pass to listeners
     */
    emit(event, ...args) {
        if (!this.events[event]) {
            return;
        }
        
        // Create a copy of listeners array to allow for listeners
        // to unsubscribe during event emission
        const listeners = [...this.events[event]];
        
        listeners.forEach(listener => {
            try {
                listener(...args);
            } catch (error) {
                console.error(`Error in event listener for ${event}:`, error);
            }
        });
    }
    
    /**
     * Remove all listeners for an event or all events
     * @param {string} [event] - Event name (omit to clear all events)
     */
    clear(event) {
        if (event) {
            this.events[event] = [];
        } else {
            this.events = {};
        }
    }
}

export default EventEmitter;
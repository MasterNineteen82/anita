// Export all BLE modules from one file for easier imports
export * from './ble-ui.js';
export * from './ble-events.js';
export * from './ble-connection.js';
export * from './ble-scanning.js';

// Initialize BLE system on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    // Import the initialization function from ble.js
    import('./ble.js').then(module => {
        if (typeof module.initializeBleManager === 'function') {
            module.initializeBleManager();
        } else {
            console.error('BLE manager initialization function not found');
        }
    }).catch(error => {
        console.error('Failed to load BLE manager:', error);
    });
});
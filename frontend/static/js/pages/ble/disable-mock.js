/**
 * Disable BLE Mock API Script
 * This script disables the mock API interceptor by modifying the original fetch function
 */

(function() {
    console.log('🛑 Disabling BLE API Mock interceptor...');
    
    // Flag to indicate we've prevented the mock interceptor
    window.BLE_MOCK_DISABLED = true;
    
    // Set the original fetch to the global scope before the mock can intercept it
    window.originalFetch = window.fetch;
    
    // Add a flag to the global object to completely disable mock API
    window.DISABLE_BLE_MOCK = true;
    
    console.log('✅ BLE API Mock interceptor disabled - using real API endpoints');
})();

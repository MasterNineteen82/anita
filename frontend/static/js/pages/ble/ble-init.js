/**
 * BLE Dashboard Initialization Script
 * Orchestrates the initialization of all BLE dashboard components
 */

import { BLE } from './ble.js';
import { BleAdapter } from './ble-adapter.js';
import { BleScanner } from './ble-scanner.js';
import { BleDevice } from './ble-device.js';
import { BleServices } from './ble-services.js';
import { BleNotifications } from './ble-notifications.js';
import { BleChart } from './ble-chart.js';
import { BleUI } from './ble-ui.js';
import { BleWebSocket } from './ble-websocket.js';
import { BleEvents } from './ble-events.js';
import { BleMetrics } from './ble-metrics.js';
import { BleConnection } from './ble-connection.js';
import { BleRecovery } from './ble-recovery.js';
import { MessageType } from './ble-constants.js';

/**
 * Initialize the BLE Dashboard
 */
async function initialize() {
    console.log('Initializing BLE Dashboard...');
    
    try {
        // Initialize BLE Toast Notifications
        BleUI.initializeToasts();
        
        // Initialize shared application state with event types from backend
        const appState = {
            adapter: null,
            connectedDevice: null,
            selectedService: null,
            selectedCharacteristic: null,
            services: [],
            characteristics: {},
            subscribedCharacteristics: new Set(),
            deviceCache: new Map(),
            lastScanResults: [],
            notificationHistory: {},
            isScanning: false,
            messageTypes: MessageType // Add the message types
        };
        
        // Initialize UI components first
        await BleUI.initialize();
        
        // Initialize events system
        BleEvents.initialize();
        
        // Initialize the WebSocket connection with updated endpoint
        const bleWebSocket = new BleWebSocket('/api/ble/ws');
        await bleWebSocket.initialize();
        
        // Initialize BLE modules with shared state
        const bleAdapter = new BleAdapter(appState);
        const bleScanner = new BleScanner(appState);
        const bleDevice = new BleDevice(appState);
        const bleServices = new BleServices(appState);
        const bleNotifications = new BleNotifications(appState);
        const bleConnection = new BleConnection(appState);
        const bleChart = new BleChart(appState);
        const bleMetrics = new BleMetrics(appState);
        const bleRecovery = new BleRecovery(appState);
        
        // Initialize each module in sequence
        await bleAdapter.initialize();
        await bleScanner.initialize();
        await bleDevice.initialize();
        await bleServices.initialize();
        await bleNotifications.initialize();
        await bleConnection.initialize();
        await bleChart.initialize();
        await bleMetrics.initialize();
        await bleRecovery.initialize();
        
        // Set up global references for debugging
        window.BleEvents = BleEvents;
        window.BleState = appState;
        
        // Setup log system
        const logContainer = document.getElementById('ble-log-container');
        if (logContainer) {
            BleUI.logMessage('BLE Dashboard initialized successfully', 'success');
        }
        
        console.log('BLE Dashboard initialization complete');
        
        // Load initial adapter info
        try {
            await bleAdapter.loadAdapterInfo();
        } catch (error) {
            console.warn('Could not load adapter info:', error);
            BleUI.showToast('Could not load BLE adapter info. Some features may be limited.', 'warning');
        }
        
        // Show initialization success message
        BleUI.showToast('BLE Dashboard Ready', 'success');
        
        // Register error handler for unhandled exceptions
        window.addEventListener('error', (event) => {
            console.error('Unhandled error:', event.error);
            BleUI.showToast(`Error: ${event.error?.message || 'Unknown error'}`, 'error');
            BleUI.logMessage(`Unhandled error: ${event.error?.message || 'Unknown error'}`, 'error');
        });
        
        // Register promise rejection handler
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            BleUI.showToast(`Error: ${event.reason?.message || 'Promise rejected'}`, 'error');
            BleUI.logMessage(`Unhandled promise rejection: ${event.reason?.message || 'Unknown reason'}`, 'error');
        });
        
    } catch (error) {
        console.error('Error initializing BLE Dashboard:', error);
        
        // Display error on UI
        const errorContainer = document.createElement('div');
        errorContainer.className = 'bg-red-500 text-white p-4 rounded mb-4';
        errorContainer.innerHTML = `
            <h3 class="text-lg font-bold mb-2">Dashboard Initialization Failed</h3>
            <p>${error.message}</p>
            <button id="retry-init-btn" class="mt-2 px-4 py-2 bg-white text-red-600 rounded">
                <i class="fas fa-sync mr-1"></i> Retry Initialization
            </button>
        `;
        
        // Add to page
        const container = document.querySelector('.container');
        if (container) {
            container.prepend(errorContainer);
            
            // Add retry button functionality
            document.getElementById('retry-init-btn').addEventListener('click', () => {
                errorContainer.remove();
                initialize();
            });
        }
    }
}

// Initialize when DOM is fully loaded
document.addEventListener('DOMContentLoaded', initialize);

// Export initialize function for direct calling
export { initialize };
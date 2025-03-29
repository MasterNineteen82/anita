/**
 * BLE Dashboard Initialization Script
 * Orchestrates the initialization of all BLE dashboard components
 */

import { BLE } from './ble.js';
import { BleScanner } from './ble-scanner.js';
import { BleServices } from './ble-services.js';
import { BleDevice } from './ble-device.js';
import { BleAdapter } from './ble-adapter.js';
import { BleNotifications } from './ble-notifications.js';
import { BleEvents } from './ble-events.js';
import { BleUI } from './ble-ui.js';
import { BleRecovery } from './ble-recovery.js';
import { BleWebSocket } from './ble-websocket.js';
import { BleConnection } from './ble-connection.js';
import { BleMetrics } from './ble-metrics.js';
import { BleChart } from './ble-chart.js';

// Initialize all the modules
const ble = BLE;
const bleScanner = new BleScanner();
const bleServices = new BleServices();
const bleDevice = new BleDevice();
const bleAdapter = new BleAdapter();
const bleNotifications = new BleNotifications();
const bleEvents = BleEvents; // No need to instantiate, it's static
const bleUI = BleUI; // No need to instantiate, it's static
const bleRecovery = new BleRecovery();
const bleWebSocket = new BleWebSocket();
const bleConnection = new BleConnection();
const bleMetrics = new BleMetrics();
const bleChart = new BleChart();

async function initialize() {
    try {
        console.log('Initializing BLE Dashboard...');

        // Initialize BLE UI
        await bleUI.initialize();

        // Initialize BLE Events
        bleEvents.initialize();

        // Initialize BLE WebSocket
        await bleWebSocket.initialize();

        // Initialize BLE Adapter
        await bleAdapter.initialize();

        // Initialize BLE Scanner
        await bleScanner.initialize();

        // Initialize BLE Device component
        await bleDevice.initialize();

        // Initialize BLE Services module
        await bleServices.initialize();

        // Initialize BLE Notifications module
        await bleNotifications.initialize();

        // Initialize BLE Connection module
        await bleConnection.initialize();

        // Initialize BLE Chart module
        await bleChart.initialize();

        // Initialize BLE Metrics module
        await bleMetrics.initialize();

        // Initialize BLE Recovery module
        await bleRecovery.initialize();

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
            BleUI.showToast(`Promise Rejection: ${event.reason?.message || 'Unknown reason'}`, 'error');
            BleUI.logMessage(`Promise Rejection: ${event.reason?.message || 'Unknown reason'}`, 'error');
        });
    } catch (error) {
        console.error('Error initializing BLE Dashboard:', error);
        BleUI.showToast(`Error initializing BLE Dashboard: ${error.message}`, 'error');
    }
}

// Initialize when DOM is fully loaded
document.addEventListener('DOMContentLoaded', initialize);

// Export initialize function for direct calling
export { initialize };
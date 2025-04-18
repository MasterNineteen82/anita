/**
 * BLE Dashboard Initialization Script
 * Orchestrates the initialization of all BLE dashboard components
 */

import { BleAdapter } from './ble-adapter.js';
import { BleScanner } from './ble-scanner.js';
import { BleDevice } from './ble-device.js';
import { BleServices } from './ble-services.js';
import { BleNotifications } from './ble-notifications.js';
import { BleChart } from './ble-chart.js';
import { BleUI } from './ble-ui.js';
import { BleWebSocket } from './ble-websocket.js';
import { BleEvents, BLE_EVENTS } from './ble-events.js';
import { BleMetrics } from './ble-metrics.js';
import { BleConnection } from './ble-connection.js';
import { BleRecovery } from './ble-recovery.js';
import { MessageType } from './ble-constants.js';
import { BleLogger } from './ble-logger.js';
import { BleLogDashboard } from './ble-log-dashboard.js';
import { BlePerformanceMonitor } from './ble-performance-monitor.js';
import { BleApiLogger } from './ble-api-logger.js';
import { BleStateTracker } from './ble-state-tracker.js';
import { BleData } from './ble-data.js';
import { BlePerformance } from './ble-performance.js';
import { BleApiHelper } from './ble-api-helper.js';
import { bleApiClient } from './ble-api-client.js';
import { bleAdapter } from './ble-adapter.js';

// Define bleLog early to ensure it's available
window.bleLog = function(message, level = 'info') {
    const timestamp = new Date().toISOString().substr(11, 8);
    const formattedMessage = `[${timestamp}] ${message}`;

    // Write to console based on level
    switch (level) {
        case 'error':
            console.error(formattedMessage);
        break;
        case 'warn':
            console.warn(formattedMessage);
        break;
        case 'debug':
            console.debug(formattedMessage);
        break;
        default:
            console.log(formattedMessage);
    }

    // Write to UI log if available
    const logContainer = document.getElementById('ble-log-container');
    if (logContainer) {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${level} mb-1 text-sm`;

        // Color based on level
        let textColor = 'text-gray-300';
        if (level === 'error') textColor = 'text-red-400';
        if (level === 'warn') textColor = 'text-yellow-400';
        if (level === 'success') textColor = 'text-green-400';
        if (level === 'debug') textColor = 'text-blue-400';

        logEntry.className += ` ${textColor}`;

        // Add timestamp in muted color
        logEntry.innerHTML = `<span class="text-gray-500">[${timestamp}]</span> ${message}`;

        // Add to container and scroll to bottom
        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;

        // Limit entries to prevent memory issues
        while (logContainer.children.length > 100) {
            logContainer.removeChild(logContainer.firstChild);
        }
    }
};

/**
 * Set up centralized logging
 */
function setupLogging() {
    // Create a log function that writes to console and UI if available
    window.bleLog = function(message, level = 'info') {
        const timestamp = new Date().toISOString().substr(11, 8);
        const formattedMessage = `[${timestamp}] ${message}`;

        // Write to console based on level
        switch (level) {
            case 'error':
                console.error(formattedMessage);
                break;
            case 'warn':
                console.warn(formattedMessage);
                break;
            case 'debug':
                console.debug(formattedMessage);
                break;
            default:
                console.log(formattedMessage);
        }

        // Write to UI log if available
        const logContainer = document.getElementById('ble-log-container');
        if (logContainer) {
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry log-${level} mb-1 text-sm`;

            // Color based on level
            let textColor = 'text-gray-300';
            if (level === 'error') textColor = 'text-red-400';
            if (level === 'warn') textColor = 'text-yellow-400';
            if (level === 'success') textColor = 'text-green-400';
            if (level === 'debug') textColor = 'text-blue-400';

            logEntry.className += ` ${textColor}`;

            // Add timestamp in muted color
            logEntry.innerHTML = `<span class="text-gray-500">[${timestamp}]</span> ${message}`;

            // Add to container and scroll to bottom
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;

            // Limit entries to prevent memory issues
            while (logContainer.children.length > 100) {
                logContainer.removeChild(logContainer.firstChild);
            }
        }
    };

    // Override console methods only in development
    const isDevelopment = window.location.hostname === 'localhost' ||
                         window.location.hostname === '127.0.0.1';

    if (isDevelopment) {
        // Save original console methods
        const originalConsole = {
            log: console.log,
            error: console.error,
            warn: console.warn,
            debug: console.debug
        };
        
        // Helper function to decide if we should log to UI
        const shouldLogToBleLog = (args, functionName) => {
            // IMPORTANT: Don't log if the message came from bleLog itself
            return args[0] && 
                   typeof args[0] === 'string' && 
                   args[0].includes('BLE') && 
                   !args[0].includes('[') && // This filters out bleLog-formatted messages
                   functionName !== 'bleLog';
        };

        // Override console methods
        console.log = function() {
            // Call original first
            originalConsole.log.apply(this, arguments);
            // Only then maybe log to UI
            if (shouldLogToBleLog(arguments, 'console.log')) {
                window.bleLog(arguments[0], 'info');
            }
        };

        console.error = function() {
            originalConsole.error.apply(this, arguments);
            if (shouldLogToBleLog(arguments, 'console.error')) {
                window.bleLog(arguments[0], 'error');
            }
        };

        console.warn = function() {
            originalConsole.warn.apply(this, arguments);
            if (shouldLogToBleLog(arguments, 'console.warn')) {
                window.bleLog(arguments[0], 'warn');
            }
        };

        console.debug = function() {
            originalConsole.debug.apply(this, arguments);
            if (shouldLogToBleLog(arguments, 'console.debug')) {
                window.bleLog(arguments[0], 'debug');
            }
        };
    }
}

/**
 * Initialize the BLE Dashboard
 */
async function initialize() {
    console.log('[Init] Initializing BLE Dashboard');
    window.bleLog('[Init] Starting initialization');
    
    try {
        // Always use real API, no mock fallback
        console.log('[Init] Using real API endpoints only (mock disabled)');
        
        // Initialize app state
        const appState = {
            initialized: false,
            isConnected: false,
            isScanning: false,
            selectedDevice: null,
            adapters: [],
            selectedAdapter: null
        };
        
        // Call setupLogging to initialize logging
        setupLogging();
        
        // Create missing components if needed
        createPlaceholderContent();
        
        // Fix UI layout issues
        fixCardLayouts();
        
        // Initialize BLE components
        const components = initializeComponents(appState);
        
        // Mark as initialized
        appState.initialized = true;
        window.BLE_APP_STATE = appState;
        
        console.log('[Init] [complete] BLE Dashboard initialization complete', {
            moduleCount: Object.keys(components).length,
            initTime: performance.now() - window.bleInitStartTime
        });
        
        window.bleLog('[Init] BLE Dashboard initialized successfully');
        
    } catch (error) {
        console.error('BLE Dashboard initialization failed:', error);
        window.bleLog('[Init] Initialization failed: ' + error.message, 'error');
        
        // Show error message to user
        const mainContainer = document.querySelector('.ble-container');
        if (mainContainer) {
            mainContainer.innerHTML = `
                <div class="p-4 bg-red-900 bg-opacity-30 rounded-lg text-white">
                    <h3 class="text-lg font-medium mb-2">BLE Dashboard Initialization Failed</h3>
                    <p class="text-red-300">${error.message}</p>
                    <button class="mt-4 bg-red-700 hover:bg-red-600 px-4 py-2 rounded" onclick="location.reload()">
                        Reload Page
                    </button>
                </div>
            `;
        }
    }
}

/**
 * Create placeholder content with loading spinners for all cards
 */
function createPlaceholderContent() {
    const cards = [
        'ble-adapter-info-card',
        'ble-scanner-card',
        'ble-device-card',
        'ble-services-card',
        'ble-characteristics-card',
        'ble-notifications-card',
        'ble-data-card',
        'ble-log-card',
        'ble-debug-card',
        'ble-metrics-card'
    ];
    
    cards.forEach(cardId => {
        const card = document.getElementById(cardId);
        if (card) {
            // Find the content area of the card (may be different based on your card structure)
            const contentArea = card.querySelector('.card-content') || card;
            
            // Check if content area is empty or has only whitespace
            if (contentArea && (!contentArea.innerHTML.trim() || contentArea.innerHTML.includes('Fetching'))) {
                contentArea.innerHTML = `
                    <div class="flex justify-center items-center p-6">
                        <div class="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
                        <span class="ml-3 text-gray-400">Loading ${card.getAttribute('data-title') || 'component'}...</span>
                    </div>
                `;
            }
        }
    });
}

/**
 * Check if all required DOM elements exist
 * @returns {Array} Array of missing elements
 */
function checkRequiredElements() {
    const requiredElements = [
        // Adapter elements
        'adapter-info-content', 
        'refresh-adapter-btn',
        
        // Scanner elements
        'scan-container', 
        'devices-list',
        'scan-btn',
        'stop-scan-btn',
        
        // Device elements
        'device-info-content', 
        'battery-container',
        'battery-level',
        
        // Services elements
        'services-list',
        
        // Characteristics elements
        'characteristics-list',
        
        // Notifications elements
        'notifications-list',
        
        // Data elements
        'data-display',
        
        // Log elements
        'ble-log-container',
        
        // Debug elements
        'debug-panel',
        
        // Metrics elements
        'metrics-container',
        
        // Status elements
        'ble-status-alert'
    ];
    
    // Check for missing elements
    const missingElements = requiredElements.filter(id => !document.getElementById(id));
    
    if (missingElements.length > 0) {
        console.warn('Missing required DOM elements:', missingElements);
        
        // For each missing element, create a placeholder if possible
        missingElements.forEach(elementId => {
            createPlaceholderElement(elementId);
        });
        
        BleUI.showToast(`Some UI elements were missing and have been created. Functionality may be limited.`, 'warning');
    }
    
    return missingElements;
}

/**
 * Initialize the BleLogger
 */
function initializeBleLogger() {
    // Check if BleLogger is already initialized
    if (window.bleLog) {
        console.log('BleLogger already initialized.');
        return;
    }

    // Default logging level
    let logLevel = 'info';

    // Override with localStorage setting if available
    try {
        const storedLogLevel = localStorage.getItem('bleLogLevel');
        if (storedLogLevel) {
            logLevel = storedLogLevel;
        }
    } catch (error) {
        console.warn('Error reading bleLogLevel from localStorage:', error);
    }

    // Set up centralized logging
    window.bleLog = function(message, level = 'info') {
        // Respect the configured log level
        const levelMap = {
            'error': 4,
            'warn': 3,
            'info': 2,
            'debug': 1
        };

        if (levelMap[level] === undefined) {
            level = 'info'; // Default to info if invalid
        }

        if (levelMap[level] < levelMap[logLevel]) {
            return; // Don't log if below current level
        }

        const timestamp = new Date().toISOString().substr(11, 8);
        const formattedMessage = `[${timestamp}] ${message}`;

        // Write to console based on level
        switch (level) {
            case 'error':
                console.error(formattedMessage);
                break;
            case 'warn':
                console.warn(formattedMessage);
                break;
            case 'debug':
                console.debug(formattedMessage);
                break;
            default:
                console.log(formattedMessage);
        }

        // Write to UI log if available
        const logContainer = document.getElementById('ble-log-container');
        if (logContainer) {
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry log-${level} mb-1 text-sm`;

            // Color based on level
            let textColor = 'text-gray-300';
            if (level === 'error') textColor = 'text-red-400';
            if (level === 'warn') textColor = 'text-yellow-400';
            if (level === 'success') textColor = 'text-green-400';
            if (level === 'debug') textColor = 'text-blue-400';

            logEntry.className += ` ${textColor}`;

            // Add timestamp in muted color
            logEntry.innerHTML = `<span class="text-gray-500">[${timestamp}]</span> ${message}`;

            // Add to container and scroll to bottom
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;

            // Limit entries to prevent memory issues
            while (logContainer.children.length > 100) {
                logContainer.removeChild(logContainer.firstChild);
            }
        }
    };

    console.log('BleLogger initialized with level:', logLevel);
}

/**
 * Create placeholder elements for missing required elements
 */
function createPlaceholderElement(elementId) {
    let parentElement = null;
    let elementHTML = '';
    
    // Determine parent and HTML based on element ID
    switch (elementId) {
        case 'adapter-info-content':
            parentElement = document.getElementById('ble-adapter-info-card');
            elementHTML = `<div id="adapter-info-content" class="p-4 space-y-3">
                <div class="text-gray-500">Adapter information will appear here</div>
            </div>`;
            break;
            
        case 'refresh-adapter-btn':
            parentElement = document.getElementById('ble-adapter-info-card');
            elementHTML = `<div class="card-footer">
                <button id="refresh-adapter-btn" class="ble-btn ble-btn-secondary">
                    <i class="fas fa-sync-alt mr-1"></i> Refresh
                </button>
            </div>`;
            break;
            
        case 'scan-container':
            parentElement = document.getElementById('ble-scanner-card');
            elementHTML = `<div id="scan-container" class="p-4">
                <div class="flex justify-between mb-4">
                    <button id="scan-btn" class="ble-btn ble-btn-primary">
                        <i class="fas fa-search mr-1"></i> Scan for Devices
                    </button>
                    <button id="stop-scan-btn" class="ble-btn ble-btn-danger hidden">
                        <i class="fas fa-stop mr-1"></i> Stop Scan
                    </button>
                </div>
                <div id="devices-list" class="mt-4 bg-gray-800 rounded-md p-2 max-h-60 overflow-y-auto">
                    <div class="text-gray-500 text-center p-4">No devices found</div>
                </div>
            </div>`;
            break;
            
        case 'devices-list':
            parentElement = document.getElementById('scan-container') || document.getElementById('ble-scanner-card');
            elementHTML = `<div id="devices-list" class="mt-4 bg-gray-800 rounded-md p-2 max-h-60 overflow-y-auto">
                <div class="text-gray-500 text-center p-4">No devices found</div>
            </div>`;
            break;
            
        case 'device-info-content':
            parentElement = document.getElementById('ble-device-card');
            elementHTML = `<div id="device-info-content" class="p-4">
                <div class="text-gray-500 text-center p-4">Connect to a device to see information</div>
            </div>`;
            break;
            
        case 'battery-container':
            parentElement = document.getElementById('ble-device-card');
            elementHTML = `<div id="battery-container" class="mt-4 p-4 hidden">
                <div class="text-sm text-gray-400 mb-1">Battery Level</div>
                <div class="flex items-center">
                    <div id="battery-level" class="w-full bg-gray-700 rounded-full h-4 overflow-hidden">
                        <div class="bg-green-500 h-full rounded-full" style="width: 0%"></div>
                    </div>
                    <span class="ml-2 text-sm text-white">0%</span>
                </div>
            </div>`;
            break;
            
        case 'services-list':
            parentElement = document.getElementById('ble-services-card');
            elementHTML = `<div id="services-list" class="p-4">
                <div class="text-gray-500 text-center p-4">Connect to a device to see services</div>
            </div>`;
            break;
            
        case 'ble-status-alert':
            parentElement = document.querySelector('.ble-container');
            elementHTML = `<div id="ble-status-alert" class="mb-4 p-3 bg-red-900 bg-opacity-30 rounded-md flex items-center">
                <div class="w-3 h-3 rounded-full bg-red-500 mr-2"></div>
                <span class="text-red-400">Not connected to any device</span>
            </div>`;
            break;
            
        default:
            console.warn(`Unknown element ID: ${elementId}`);
            break;
    }
    
    // Create the element if we have a parent and HTML
    if (parentElement && elementHTML) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = elementHTML;
        
        // Insert at beginning or end based on element type
        if (['adapter-info-content', 'scan-container', 'device-info-content', 'services-list'].includes(elementId)) {
            parentElement.insertBefore(tempDiv.firstChild, parentElement.firstChild);
        } else {
            parentElement.appendChild(tempDiv.firstChild);
        }
        
        console.log(`Created placeholder for missing element: ${elementId}`);
    }
}

/**
 * Initialize WebSocket connection
 */
async function initializeWebSocket(appState) {
    BleLogger.info('WebSocket', 'initialize', 'Initializing WebSocket connection');
    
    const startTime = performance.now();
    
    try {
        // Try different WebSocket endpoints
        const wsResult = await BleApiHelper.tryWebSocketEndpoints();
        
        if (wsResult.success) {
            console.log(`WebSocket connected to ${wsResult.endpoint}`);
            
            const ws = wsResult.socket;
            
            // Set up event listeners here
            ws.addEventListener('message', (event) => {
                try {
                    const message = JSON.parse(event.data);
                    console.log('WebSocket message received:', message);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            });
            
            // Return a simple wrapper
            return {
                socket: ws,
                isConnected: true,
                sendCommand: (type, payload = {}) => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({
                            type,
                            ...payload
                        }));
                    }
                }
            };
        } else {
            console.error('All WebSocket endpoints failed');
            return null;
        }
    } catch (error) {
        BleLogger.error('WebSocket', 'initialize', 'WebSocket connection failed', {
            error: error.message
        });
        
        console.warn('WebSocket connection failed:', error);
        
        // Return null to indicate failure
        return null;
    }
}

/**
 * Initialize BLE components
 */
function initializeComponents(appState) {
    const bleUI = new BleUI(); // Initialize BleUI first
    const bleEvents = new BleEvents();
    const bleWebSocket = new BleWebSocket(); // Initialize WebSocket first
    const bleAdapter = new BleAdapter();
    const bleScanner = new BleScanner();
    const bleConnection = new BleConnection();
    const bleServices = new BleServices();
    const bleNotifications = new BleNotifications();
    const bleData = new BleData();
    const blePerformance = new BlePerformance();
    
    // Import and initialize debug module
    import('./ble-debug.js').then(module => {
        const bleDebug = module.default;
        bleDebug.initialize().then(success => {
            if (success) {
                console.log('BLE Debug module initialized');
            } else {
                console.warn('BLE Debug module initialization failed');
            }
        });
    }).catch(error => {
        console.error('Error importing BLE Debug module:', error);
    });
    
    return {
        bleUI, // Ensure BleUI is first
        bleEvents,
        bleWebSocket, // Ensure WebSocket is initialized
        bleAdapter,
        bleScanner,
        bleConnection,
        bleServices,
        bleNotifications,
        bleData,
        blePerformance
    };
}

/**
 * Initialize components in sequence
 */
async function initializeInSequence(components, appState) {
    for (const key in components) {
        if (components.hasOwnProperty(key) && components[key] && typeof components[key].initialize === 'function') {
            try {
                console.log(`Initializing ${key}...`);
                await components[key].initialize();
                console.log(`${key} initialized successfully.`);
            } catch (error) {
                console.error(`Failed to initialize ${key}:`, error);
            }
        }
    }
}

/**
 * Register global error handlers
 */
function registerErrorHandlers() {
    // Global unhandled rejection handler
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        
        // Check if this is a BLE related error
        if (event.reason && (
            event.reason.toString().includes('BLE') || 
            event.reason.toString().includes('Bluetooth') ||
            event.reason.toString().includes('WebSocket')
        )) {
            window.bleLog(`Unhandled error: ${event.reason}`, 'error');
            BleUI.showToast(`An error occurred: ${event.reason}`, 'error');
        }
    });
    
    // Global error handler
    window.addEventListener('error', function(event) {
        console.error('Global error:', event.error);
        
        // Check if this is a BLE related error
        if (event.error && (
            event.error.toString().includes('BLE') || 
            event.error.toString().includes('Bluetooth') ||
            event.error.toString().includes('WebSocket')
        )) {
            window.bleLog(`Global error: ${event.error}`, 'error');
            BleUI.showToast(`An error occurred: ${event.error}`, 'error');
        }
    });
}

/**
 * Restore UI state from localStorage
 */
function restoreUIState() {
    try {
        // Restore scan time setting
        const scanTimeInput = document.getElementById('scan-time');
        if (scanTimeInput) {
            const savedScanTime = localStorage.getItem('bleScanTime');
            if (savedScanTime) {
                scanTimeInput.value = savedScanTime;
            }
        }
        
        // Restore active scanning setting
        const activeScanningCheckbox = document.getElementById('active-scanning');
        if (activeScanningCheckbox) {
            const activeScanSetting = localStorage.getItem('bleActiveScan');
            if (activeScanSetting !== null) {
                activeScanningCheckbox.checked = activeScanSetting === 'true';
            }
        }
        
        // Restore other UI preferences here...
        
    } catch (error) {
        console.warn('Error restoring UI state:', error);
    }
}

// Initialize the BLE Dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', initialize);

/**
 * Initialize DOM references
 */
function initializeDomReferences() {
    const elements = {
        scanButton: document.getElementById('scan-btn'),
        stopScanButton: document.getElementById('stop-scan-btn'),
        deviceList: document.getElementById('devices-list'),
        adapterInfoContent: document.getElementById('adapter-info-content'),
        refreshAdapterBtn: document.getElementById('refresh-adapter-btn'),
        deviceInfoContent: document.getElementById('device-info-content'),
        batteryContainer: document.getElementById('battery-container'),
        batteryLevel: document.getElementById('battery-level'),
        batteryIcon: document.getElementById('battery-icon'),
        refreshBatteryBtn: document.getElementById('refresh-battery-btn'),
        servicesList: document.getElementById('services-list'),
        characteristicsList: document.getElementById('characteristics-list'),
        notificationsContainer: document.getElementById('notifications-container'),
        dataDisplay: document.getElementById('data-display'),
        bleLogContainer: document.getElementById('ble-log-container'),
        clearLogBtn: document.getElementById('clear-log-btn'),
        debugPanel: document.getElementById('debug-panel'),
        debugToggleBtn: document.getElementById('debug-toggle'),
        debugSendBtn: document.getElementById('debug-send'),
        debugEndpointSelect: document.getElementById('debug-endpoint'),
        debugResponseContainer: document.getElementById('debug-response'),
        metricsContainer: document.getElementById('metrics-container'),
        bleStatusAlert: document.getElementById('ble-status-alert'),
        scanTimeInput: document.getElementById('scan-time'),
        activeScanningCheckbox: document.getElementById('active-scanning'),
        serviceUuidInput: document.getElementById('service-uuid-input')
    };

    // Log if any elements are missing
    Object.keys(elements).forEach(key => {
        if (!elements[key]) {
            console.warn(`DOM element with id '${key}' not found.`);
        }
    });

    return elements;
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    const dom = initializeDomReferences();

    // Clear log button
    if (dom.clearLogBtn) {
        dom.clearLogBtn.addEventListener('click', () => {
            if (dom.bleLogContainer) {
                dom.bleLogContainer.innerHTML = '';
            }
        });
    }

    // Refresh adapter button
    if (dom.refreshAdapterBtn) {
        dom.refreshAdapterBtn.addEventListener('click', () => {
            // Implement refresh adapter logic here
            console.log('Refresh adapter button clicked');
        });
    }

    // Scan button
    if (dom.scanButton) {
        dom.scanButton.addEventListener('click', () => {
            // Implement scan logic here
            console.log('Scan button clicked');
        });
    }

    // Stop scan button
    if (dom.stopScanButton) {
        dom.stopScanButton.addEventListener('click', () => {
            // Implement stop scan logic here
            console.log('Stop scan button clicked');
        });
    }

    // Refresh battery button
    if (dom.refreshBatteryBtn) {
        dom.refreshBatteryBtn.addEventListener('click', () => {
            // Implement refresh battery logic here
            console.log('Refresh battery button clicked');
        });
    }

    // Debug toggle button
    if (dom.debugToggleBtn) {
        dom.debugToggleBtn.addEventListener('click', () => {
            // Implement debug panel toggle logic here
            console.log('Debug toggle button clicked');
        });
    }

    // Debug send button
    if (dom.debugSendBtn) {
        dom.debugSendBtn.addEventListener('click', () => {
            // Implement debug send logic here
            console.log('Debug send button clicked');
        });
    }

    // Scan time input
    if (dom.scanTimeInput) {
        dom.scanTimeInput.addEventListener('change', (event) => {
            const scanTime = event.target.value;
            localStorage.setItem('bleScanTime', scanTime);
            console.log('Scan time changed to:', scanTime);
        });
    }

    // Active scanning checkbox
    if (dom.activeScanningCheckbox) {
        dom.activeScanningCheckbox.addEventListener('change', (event) => {
            const activeScan = event.target.checked;
            localStorage.setItem('bleActiveScan', activeScan);
            console.log('Active scanning changed to:', activeScan);
        });
    }

    // Service UUID input
    if (dom.serviceUuidInput) {
        dom.serviceUuidInput.addEventListener('change', (event) => {
            const serviceUuids = event.target.value;
            localStorage.setItem('bleServiceUuids', serviceUuids);
            console.log('Service UUIDs changed to:', serviceUuids);
        });
    }
}

// Add function to fix card layouts
function fixCardLayouts() {
    console.log('Fixing card layouts...');
    
    // Find all cards
    const cards = document.querySelectorAll('.card, [id$="-card"]');
    
    cards.forEach(card => {
        // Ensure card has proper layout classes
        card.classList.add('flex', 'flex-col');
        
        // Fix missing content areas
        if (!card.querySelector('.card-content') && !card.querySelector('.p-4:not(.card-footer)')) {
            const contentDiv = document.createElement('div');
            contentDiv.className = 'card-content p-4 flex-grow';
            
            // Add the content div after the header if it exists, or as first child
            const header = card.querySelector('.card-header') || card.querySelector('h3');
            if (header) {
                // Check to avoid circular reference
                if (header.parentElement === card) {
                    header.insertAdjacentElement('afterend', contentDiv);
                } else {
                    card.prepend(contentDiv);
                }
            } else {
                card.prepend(contentDiv);
            }
        }
        
        // Find content and footer areas
        const titleArea = card.querySelector('.card-header') || card.querySelector('h3') || null;
        const contentArea = card.querySelector('.card-content') || 
                           card.querySelector('.p-4:not(.card-footer)') || 
                           card.querySelector('div:not(.card-header):not(.card-footer)');
        
        const footerArea = card.querySelector('.card-footer') || card.querySelector('.mt-4.flex.justify-end');
        
        // Fix content area if it exists
        if (contentArea) {
            // Ensure content takes available space
            contentArea.classList.add('flex-1', 'flex-grow');
            
            // Ensure correct ordering: title -> content -> footer
            if (titleArea && contentArea.previousElementSibling !== titleArea) {
                // Safety check to prevent circular reference
                if (contentArea !== titleArea && 
                    !contentArea.contains(titleArea) && 
                    contentArea.parentElement === card && 
                    titleArea.parentElement === card) {
                    titleArea.insertAdjacentElement('afterend', contentArea);
                }
            }
        }
        
        // Move footer to the end if needed
        if (footerArea && footerArea.nextElementSibling && 
            footerArea.parentElement === card && 
            !footerArea.contains(card)) {
            card.appendChild(footerArea);
        }
    });
}

// Export the initialize function for external use
export { initialize };
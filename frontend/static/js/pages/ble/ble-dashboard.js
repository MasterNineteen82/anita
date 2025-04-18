// ble-dashboard.js - Main BLE Dashboard controller

// Import modules
import { BleLogger } from './ble-logger.js';
import { BleApiClient } from './ble-api-client.js';
import { BleAdapter } from './ble-adapter.js';
import { BleScanner } from './ble-scanner.js';
import { BleDevice } from './ble-device.js';
import { BleEvents, BLE_EVENTS } from './ble-events.js';

/**
 * Main Dashboard Controller for the BLE Dashboard.
 * Manages all UI components and integrates with the BLE modules.
 */
class BleDashboardController {
    constructor() {
        // Check if already initialized
        if (window.bleDashboard) {
            console.log('BLE Dashboard already initialized, returning existing instance');
            return window.bleDashboard;
        }
        
        console.log('Creating BLE Dashboard Controller');
        
        // Initialize logger
        this.logger = window.bleLogger || new BleLogger();
        window.bleLogger = this.logger; // Store logger globally if not already present
        
        // UI state
        this.isScanning = false;
        this.selectedDevice = null;
        this.connectedDevices = new Map();
        this.deviceCache = new Map();
        this.bondedDevices = new Map();
        this.performanceData = {
            scanSuccess: 0,
            scanAttempts: 0,
            connectionSuccess: 0,
            connectionAttempts: 0,
            avgConnectionTime: 0,
            uptime: 0
        };
        
        // Charts
        this.performanceChart = null;
        
        // Check if API client already exists from ble-init.js
        if (window.bleApiClient) {
            console.log('Using existing BLE API client');
            this.apiClient = window.bleApiClient;
        } else {
            console.log('Creating new BLE API client');
            this.apiClient = new BleApiClient({ logger: this.logger }); // Pass logger
        }
        
        // Check if modules already exist
        if (window.bleAdapter) {
            console.log('Using existing BLE adapter module');
            this.bleAdapter = window.bleAdapter;
        } else {
            this.bleAdapter = new BleAdapter(this.apiClient);
        }
        
        if (window.bleScanner) {
            console.log('Using existing BLE scanner module');
            this.bleScanner = window.bleScanner;
        } else {
            this.bleScanner = new BleScanner(this.apiClient);
        }
        
        if (window.bleDevice) {
            console.log('Using existing BLE device module');
            this.bleDevice = window.bleDevice;
        } else {
            this.bleDevice = new BleDevice(this.apiClient);
        }
        
        // Use the singleton instance of BleEvents
        if (window.bleEvents) {
            console.log('Using existing BLE events module');
            this.bleEvents = window.bleEvents;
        } else {
            console.log('Creating new BLE events module');
            this.bleEvents = BleEvents.getInstance();
            window.bleEvents = this.bleEvents;
        }
        
        // Load settings
        this.settings = this.loadSettings();
        this.initTime = this.settings.initTime || Date.now();
        
        // Check if dashboard should be initialized
        if (!window.BLE_DASHBOARD_INITIALIZED) {
            this.init();
        } else {
            console.log('Dashboard already initialized by another script, attaching to existing elements');
            this.attachToExistingUI();
        }
    }
    
    /**
     * Initialize dashboard
     */
    init() {
        console.log('Initializing BLE Dashboard');
        
        // Load required external libraries and handle missing dependencies
        this.loadExternalDependencies();
        
        // Set up feature detection
        this.detectFeatures();
        
        // Apply settings
        this.applySettings();
        
        // Initialize toast notification system
        this.initToastNotifications();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Initialize UI components
        this.initTabNavigation();
        this.initDeviceScanner();
        this.initDeviceSection();
        this.initAdapterSection();
        this.initConsoleSection();
        this.initSettingsSection();
        this.initMacAddressSearch();
        
        // Start with adapter initialization
        this.initializeAdapter();
        
        // Check for previously connected devices on page load
        this.loadConnectedDevices();
        
        // Set up periodic updates
        this.performanceUpdateInterval = setInterval(this.updatePerformanceMetrics.bind(this), 5000); // Bind 'this'
        
        // Log initialization
        this.logOperation('System', 'BLE Dashboard initialized', 'info');
        console.log('BLE Dashboard initialized');
    }
    
    /**
     * Load and verify external dependencies
     */
    loadExternalDependencies() {
        // Check for Chart.js
        if (typeof Chart === 'undefined') {
            // Use a fallback logger or console if this.logger is not fully initialized
            const logWarn = this.logger && typeof this.logger.warn === 'function' ? this.logger.warn : console.warn;
            logWarn('Chart.js is not loaded - performance charts will not be available');
            
            // Create a function that logs warnings when chart methods are called
            window.Chart = class MockChart {
                constructor() {
                    console.warn('Attempted to create a chart, but Chart.js is not available');
                    return {
                        update: () => {},
                        data: { datasets: [{ data: [] }], labels: [] }
                    };
                }
            };
        }
        
        // Check for Feather Icons
        if (typeof feather === 'undefined') {
            console.warn('Feather Icons not loaded - using fallback icons');
            if (this.logger) {
                this.logger.warn({ category: 'Dependency', message: 'Feather Icons failed to load' });
            } else {
                console.warn('[Dependency] (warning) Feather Icons failed to load');
            }
            
            // Create a mock feather object with replace method
            window.feather = {
                replace: function() {
                    console.warn('Feather icons replacement attempted but library not available');
                    
                    // Find all [data-feather] elements and use text fallbacks
                    document.querySelectorAll('[data-feather]').forEach(icon => {
                        const iconType = icon.getAttribute('data-feather');
                        const fallbackText = this.getFallbackIcon(iconType);
                        
                        // Replace with text icon
                        icon.textContent = fallbackText;
                        icon.style.fontFamily = 'monospace';
                        
                        // Keep the same size
                        if (icon.style.width) {
                            icon.style.display = 'inline-block';
                            icon.style.textAlign = 'center';
                        }
                    });
                },
                
                // Simple text fallbacks for common icons
                getFallbackIcon: function(iconType) {
                    const fallbacks = {
                        'bluetooth': 'BT',
                        'wifi': 'Wi',
                        'settings': '⚙️',
                        'refresh': '⟳',
                        'search': '🔍',
                        'info': 'ℹ️',
                        'alert-circle': '⚠️',
                        'check': '✓',
                        'x': '✗',
                        'chevron-right': '❯',
                        'chevron-left': '❮',
                        'chevron-down': '▼',
                        'chevron-up': '▲',
                        'plus': '+',
                        'minus': '-',
                        'trash': '🗑️',
                    };
                    
                    return fallbacks[iconType] || '■';
                }
            };
        }
    }
    
    /**
     * Attach to existing UI elements if already initialized by another script
     */
    attachToExistingUI() {
        // Just add event listeners to important elements
        this.setupEventListeners();
        
        // Set up periodic updates
        this.performanceUpdateInterval = setInterval(this.updatePerformanceMetrics.bind(this), 5000); // Bind 'this'
        
        console.log('Attached to existing UI elements');
    }
    
    /**
     * Load any connected devices from the API
     */
    async loadConnectedDevices() {
        try {
            const response = await this.apiClient.request('/api/ble/device/connected', { method: 'GET' });
            
            if (response && response.devices && Array.isArray(response.devices)) {
                for (const device of response.devices) {
                    // Add to connected devices
                    this.connectedDevices.set(device.address, device);
                    
                    // Update UI to show the device is connected
                    this.renderConnectedDevice(device);
                }
                
                // Log the number of devices loaded
                if (response.devices.length > 0) {
                    this.logOperation('Device', `Loaded ${response.devices.length} previously connected devices`, 'info');
                }
            }
        } catch (error) {
            console.error('Failed to load connected devices:', error);
            this.logOperation('Device', 'Failed to load connected devices', 'error');
        }
    }
    
    /**
     * Detect browser and system features
     */
    detectFeatures() {
        // Check for Web Bluetooth API
        this.hasWebBluetooth = 'bluetooth' in navigator;
        
        // Check for File API
        this.hasFileApi = 'FileReader' in window;
        
        // Apply feature detection classes to body
        document.body.classList.toggle('has-web-bluetooth', this.hasWebBluetooth);
        document.body.classList.toggle('has-file-api', this.hasFileApi);
        
        // Log feature detection
        console.log('Feature detection:', {
            webBluetooth: this.hasWebBluetooth,
            fileApi: this.hasFileApi
        });
    }
    
    /**
     * Set up event listeners for BLE events
     */
    setupEventListeners() {
        // Listen for adapter events
        this.bleEvents.on(BLE_EVENTS.ADAPTER_CHANGED, (adapter) => {
            this.updateAdapterInfo(adapter);
        });
        
        // Listen for device events
        this.bleEvents.on(BLE_EVENTS.DEVICE_CONNECTED, (device) => {
            this.onDeviceConnected(device);
        });
        
        this.bleEvents.on(BLE_EVENTS.DEVICE_DISCONNECTED, (device) => {
            this.onDeviceDisconnected(device);
        });
        
        // Listen for scan events
        this.bleEvents.on(BLE_EVENTS.SCAN_STARTED, () => {
            this.onScanStarted();
        });
        
        this.bleEvents.on(BLE_EVENTS.SCAN_COMPLETED, () => {
            this.onScanStopped();
        });
        
        this.bleEvents.on(BLE_EVENTS.SCAN_RESULT, (device) => {
            this.onDeviceDiscovered(device);
        });
        
        this.bleEvents.on(BLE_EVENTS.SCAN_ERROR, (error) => {
            this.logOperation('Error', `Scan error: ${error.message}`, 'error');
        });
        
        // Listen for characteristic events
        this.bleEvents.on(BLE_EVENTS.CHARACTERISTIC_READ, (data) => {
            this.logOperation('Characteristic', `Read: ${data.value} from ${data.uuid}`);
        });
        
        this.bleEvents.on(BLE_EVENTS.CHARACTERISTIC_WRITTEN, (data) => {
            this.logOperation('Characteristic', `Written: ${data.value} to ${data.uuid}`);
        });
        
        this.bleEvents.on(BLE_EVENTS.CHARACTERISTIC_NOTIFICATION, (data) => {
            this.logOperation('Notification', `Received: ${data.value} from ${data.uuid}`);
        });
        
        // Listen for error events
        this.bleEvents.on(BLE_EVENTS.ERROR, (error) => {
            this.logOperation('Error', error.message, 'error');
        });
        
        // Set up UI event listeners
        this.setupUIEventListeners();
        
        console.log('Event listeners set up');
    }
    
    /**
     * Set up UI event listeners for DOM elements
     */
    setupUIEventListeners() {
        // Scan buttons handled in initDeviceScanner()
        
        // Tab navigation
        const tabButtons = document.querySelectorAll('.tab-btn');
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const targetTab = e.target.closest('.tab-btn').dataset.tab;
                this.switchTab(targetTab);
            });
        });
        
        // Console tab buttons
        const consoleTabButtons = document.querySelectorAll('.console-tab-btn');
        consoleTabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const targetTab = e.target.closest('.console-tab-btn').dataset.tab;
                this.switchConsoleTab(targetTab);
            });
        });
        
        // Clear console buttons
        const clearConsoleBtn = document.getElementById('clear-console-btn');
        if (clearConsoleBtn) {
            clearConsoleBtn.addEventListener('click', () => {
                this.clearConsoleOutput();
            });
        }
        
        const clearOperationsBtn = document.getElementById('clear-operations-btn');
        if (clearOperationsBtn) {
            clearOperationsBtn.addEventListener('click', () => {
                this.clearOperationsLog();
            });
        }
        
        // Debug console
        const debugCommandInput = document.getElementById('debug-command-input');
        const debugCommandParams = document.getElementById('debug-command-params');
        const runCommandBtn = document.getElementById('run-command-btn');
        
        if (runCommandBtn && debugCommandInput) {
            runCommandBtn.addEventListener('click', () => {
                const command = debugCommandInput.value;
                const params = debugCommandParams?.value || '';
                if (command) {
                    this.executeDebugCommand(command, params);
                }
            });
        }
        
        // Settings form
        const settingsForm = document.getElementById('settings-form');
        if (settingsForm) {
            settingsForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveSettings();
            });
        }
    }
    
    /**
     * Initialize tab navigation for the main sections
     */
    initTabNavigation() {
        // Device scanner tabs
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabName = btn.getAttribute('data-tab');
                
                // Update active state on buttons
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Show/hide tab content
                document.querySelectorAll('.tab-pane').forEach(tab => {
                    if (tab.id === tabName) {
                        tab.classList.remove('hidden');
                    } else {
                        tab.classList.add('hidden');
                    }
                });
            });
        });
        
        // Console tabs
        const consoleTabs = document.querySelectorAll('.console-tab-btn');
        consoleTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.getAttribute('data-tab');
                
                // Update active state
                consoleTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                // Show/hide tab content
                document.querySelectorAll('.console-tab-content').forEach(content => {
                    if (content.id === tabName) {
                        content.classList.remove('hidden');
                    } else {
                        content.classList.add('hidden');
                    }
                });
            });
        });
    }
    
    /**
     * Initialize adapter section
     */
    initAdapterSection() {
        // Get adapter selector container
        const adapterSelectorContainer = document.getElementById('adapter-selector-container');
        
        // Adapter refresh button
        const refreshBtn = document.getElementById('adapter-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshAdapterInfo();
            });
        }
        
        // Adapter reset button
        const resetBtn = document.getElementById('adapter-reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetAdapter();
            });
        }
    }
    
    /**
     * Initialize the adapter with available information
     */
    async initializeAdapter() {
        try {
            // Load adapters
            const adapters = await this.bleAdapter.getAdapters();
            this.renderAdapterSelector(adapters);
            
            // Get selected adapter from localStorage or use the first one
            const savedAdapter = localStorage.getItem('selectedAdapter');
            const selectedAdapter = savedAdapter ? JSON.parse(savedAdapter) : (adapters.length > 0 ? adapters[0] : null);
            
            if (selectedAdapter) {
                await this.bleAdapter.selectAdapter(selectedAdapter.address);
                this.updateAdapterInfo(selectedAdapter);
            }
        } catch (error) {
            this.logOperation('Error', `Failed to initialize adapter: ${error.message}`, 'error');
            console.error('Failed to initialize adapter:', error);
        }
    }
    
    /**
     * Render the adapter selector dropdown
     * @param {Array} adapters - List of available adapters
     */
    renderAdapterSelector(adapters) {
        const container = document.getElementById('adapter-selector-container');
        if (!container || adapters.length === 0) return;
        
        // Create select element
        const select = document.createElement('select');
        select.id = 'adapter-selector';
        select.className = 'w-full bg-gray-700 border border-gray-600 text-white rounded py-2 px-3';
        
        // Add options for each adapter
        adapters.forEach(adapter => {
            const option = document.createElement('option');
            option.value = adapter.address;
            option.textContent = `${adapter.name || 'Unknown'} (${adapter.address})`;
            select.appendChild(option);
        });
        
        // Add change event listener
        select.addEventListener('change', async (e) => {
            const selectedAddress = e.target.value;
            const selectedAdapter = adapters.find(a => a.address === selectedAddress);
            
            if (selectedAdapter) {
                await this.bleAdapter.selectAdapter(selectedAddress);
                this.updateAdapterInfo(selectedAdapter);
                
                // Save to localStorage
                localStorage.setItem('selectedAdapter', JSON.stringify(selectedAdapter));
                
                this.logOperation('Adapter', `Selected adapter: ${selectedAdapter.name || 'Unknown'} (${selectedAdapter.address})`);
            }
        });
        
        // Append to container
        container.innerHTML = '';
        container.appendChild(select);
    }
    
    /**
     * Update the adapter information display
     * @param {Object} adapter - Adapter information
     */
    updateAdapterInfo(adapter) {
        if (!adapter) return;
        
        // Update adapter name and address
        const nameElement = document.getElementById('adapter-name');
        const addressElement = document.getElementById('adapter-address');
        
        if (nameElement) {
            nameElement.textContent = adapter.name || 'Unknown Adapter';
        }
        
        if (addressElement) {
            addressElement.textContent = adapter.address || '';
        }
        
        // Update adapter status
        const statusIndicator = document.getElementById('adapter-status-indicator');
        const statusText = document.getElementById('adapter-status-text');
        
        if (statusIndicator && statusText) {
            const isActive = adapter.status === 'active' || adapter.status === 'poweredOn';
            
            statusIndicator.classList.toggle('connected', isActive);
            statusIndicator.classList.toggle('disconnected', !isActive);
            statusText.textContent = isActive ? 'Active' : 'Inactive';
        }
        
        // Update adapter type and platform
        const typeElement = document.getElementById('adapter-type');
        const manufacturerElement = document.getElementById('adapter-manufacturer');
        const platformElement = document.getElementById('adapter-platform');
        
        if (typeElement) {
            typeElement.textContent = adapter.type || 'Unknown';
        }
        
        if (manufacturerElement) {
            manufacturerElement.textContent = adapter.manufacturer || 'Unknown';
        }
        
        if (platformElement) {
            platformElement.textContent = adapter.platform || 'Unknown';
        }
        
        // Update adapter selector if it exists
        const adapterSelector = document.getElementById('adapter-selector');
        if (adapterSelector) {
            adapterSelector.value = adapter.address;
        }
    }
    
    /**
     * Refresh adapter information
     */
    async refreshAdapterInfo() {
        try {
            const adapter = await this.bleAdapter.getCurrentAdapter();
            if (adapter) {
                this.updateAdapterInfo(adapter);
                this.logOperation('Adapter', 'Adapter information refreshed');
            }
        } catch (error) {
            this.logOperation('Error', `Failed to refresh adapter: ${error.message}`, 'error');
            console.error('Failed to refresh adapter:', error);
        }
    }
    
    /**
     * Reset the Bluetooth adapter
     */
    async resetAdapter() {
        try {
            await this.bleAdapter.resetAdapter();
            this.logOperation('Adapter', 'Adapter reset successful');
            
            // Refresh adapter info after reset
            setTimeout(() => {
                this.refreshAdapterInfo();
            }, 1000);
        } catch (error) {
            this.logOperation('Error', `Failed to reset adapter: ${error.message}`, 'error');
            console.error('Failed to reset adapter:', error);
        }
    }
    
    /**
     * Initialize scanner section
     */
    initDeviceScanner() {
        // Scan button
        const scanBtn = document.getElementById('scan-btn');
        const stopScanBtn = document.getElementById('stop-scan-btn');
        
        if (scanBtn) {
            scanBtn.addEventListener('click', () => {
                this.startScan();
            });
        }
        
        if (stopScanBtn) {
            stopScanBtn.addEventListener('click', () => {
                this.stopScan();
            });
        }
        
        // Add device filter functionality
        this.initDeviceFilter();
        
        // Clear devices button
        const clearDevicesBtn = document.getElementById('clear-devices-btn');
        if (clearDevicesBtn) {
            clearDevicesBtn.addEventListener('click', () => {
                this.clearDiscoveredDevices();
            });
        }
        
        // Scan options
        const scanOptionsToggle = document.getElementById('scan-options-toggle');
        const scanOptionsPanel = document.getElementById('scan-options-panel');
        
        if (scanOptionsToggle && scanOptionsPanel) {
            scanOptionsToggle.addEventListener('click', () => {
                const isVisible = scanOptionsPanel.classList.toggle('hidden');
                scanOptionsToggle.innerHTML = isVisible ? 
                    '<i data-feather="chevron-down"></i> Show Options' : 
                    '<i data-feather="chevron-up"></i> Hide Options';
                feather.replace();
            });
        }
    }
    
    /**
     * Initialize device filter functionality
     */
    initDeviceFilter() {
        const deviceFilter = document.getElementById('device-filter');
        const devicesList = document.getElementById('discovered-devices-list');
        const filterByName = document.getElementById('filter-by-name');
        const filterByAddress = document.getElementById('filter-by-address');
        const filterBySignal = document.getElementById('filter-by-signal');
        
        // Add search input handler
        if (deviceFilter) {
            deviceFilter.addEventListener('input', () => {
                this.filterDevices(
                    deviceFilter.value, 
                    filterByName?.checked, 
                    filterByAddress?.checked,
                    filterBySignal?.checked ? parseInt(filterBySignal.value) : -100
                );
            });
        }
        
        // Add radio button change handlers
        if (filterByName) {
            filterByName.addEventListener('change', () => {
                if (deviceFilter) {
                    this.filterDevices(
                        deviceFilter.value, 
                        true, 
                        false,
                        filterBySignal?.checked ? parseInt(filterBySignal.value) : -100
                    );
                }
            });
        }
        
        if (filterByAddress) {
            filterByAddress.addEventListener('change', () => {
                if (deviceFilter) {
                    this.filterDevices(
                        deviceFilter.value, 
                        false, 
                        true,
                        filterBySignal?.checked ? parseInt(filterBySignal.value) : -100
                    );
                }
            });
        }
        
        // Add signal strength filter handler
        if (filterBySignal) {
            filterBySignal.addEventListener('input', () => {
                const signalValue = parseInt(filterBySignal.value);
                const signalValueDisplay = document.getElementById('signal-filter-value');
                
                if (signalValueDisplay) {
                    signalValueDisplay.textContent = `${signalValue} dBm`;
                }
                
                if (deviceFilter) {
                    this.filterDevices(
                        deviceFilter.value, 
                        filterByName?.checked, 
                        filterByAddress?.checked,
                        signalValue
                    );
                }
            });
        }
    }
    
    /**
     * Filter discovered devices by name, address or signal strength
     * @param {string} query - The search query
     * @param {boolean} byName - Whether to filter by device name
     * @param {boolean} byAddress - Whether to filter by device address
     * @param {number} minSignal - Minimum signal strength in dBm
     */
    filterDevices(query = '', byName = true, byAddress = true, minSignal = -100) {
        const devicesList = document.getElementById('discovered-devices-list');
        if (!devicesList) return;
        
        const devices = devicesList.querySelectorAll('.device-item');
        const lowerQuery = query.toLowerCase();
        
        // Count total and visible devices
        let totalDevices = 0;
        let visibleDevices = 0;
        
        devices.forEach(device => {
            const deviceName = device.querySelector('.font-medium')?.textContent?.toLowerCase() || '';
            const deviceAddress = device.getAttribute('data-address')?.toLowerCase() || '';
            const signalStrength = device.querySelector('.signal-strength');
            const rssiValue = signalStrength ? 
                parseInt(signalStrength.querySelector('.tooltip-text')?.textContent?.match(/-\d+/) || '-100') : 
                -100;
            
            // Apply filters
            const matchesName = byName && deviceName.includes(lowerQuery);
            const matchesAddress = byAddress && deviceAddress.includes(lowerQuery);
            const meetsSignalThreshold = rssiValue >= minSignal;
            
            // Display logic - text match AND signal threshold
            const shouldShow = (query === '' || matchesName || matchesAddress) && meetsSignalThreshold;
            
            // Apply visibility
            device.style.display = shouldShow ? 'block' : 'none';
            
            // Count devices
            totalDevices++;
            if (shouldShow) visibleDevices++;
        });
        
        // Update device count display
        const deviceCount = document.getElementById('device-count');
        if (deviceCount) {
            deviceCount.textContent = totalDevices > 0 ?
                `Showing ${visibleDevices} of ${totalDevices} devices` :
                'No devices found';
        }
        
        // Show/hide "no devices" message
        const noDevicesMessage = document.getElementById('no-devices-message');
        if (noDevicesMessage) {
            noDevicesMessage.style.display = (totalDevices === 0 || visibleDevices === 0) ? 'block' : 'none';
            
            // Update message for filter results
            if (totalDevices > 0 && visibleDevices === 0) {
                noDevicesMessage.textContent = 'No devices match your filter criteria';
            } else {
                noDevicesMessage.textContent = 'No devices found. Start scanning to discover BLE devices.';
            }
        }
    }
    
    /**
     * Clear the discovered devices list
     */
    clearDiscoveredDevices() {
        const devicesList = document.getElementById('discovered-devices-list');
        if (!devicesList) return;
        
        // Confirm with user
        if (devicesList.children.length > 0) {
            const confirmed = confirm('Are you sure you want to clear all discovered devices?');
            if (!confirmed) return;
        }
        
        // Clear the list
        devicesList.innerHTML = '';
        
        // Show no devices message
        const noDevicesMessage = document.getElementById('no-devices-message');
        if (noDevicesMessage) {
            noDevicesMessage.style.display = 'block';
        }
        
        // Update device count
        const deviceCount = document.getElementById('device-count');
        if (deviceCount) {
            deviceCount.textContent = 'No devices found';
        }
        
        // Log and show toast
        this.logOperation('Scanner', 'Cleared discovered devices list');
        this.showToast('Cleared discovered devices list', 'info');
    }
    
    /**
     * Initialize device section
     */
    initDeviceSection() {
        // Disconnect button
        const disconnectBtn = document.getElementById('disconnect-btn');
        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => {
                if (this.selectedDevice) {
                    this.disconnectFromDevice(this.selectedDevice.address);
                }
            });
        }
    }
    
    /**
     * Connect to a BLE device using the correct API endpoint
     * @param {string} address - The address of the device to connect to
     */
    async connectToDevice(address) {
        // Already connecting or connected
        if (this.isConnecting || (this.selectedDevice && this.selectedDevice.address === address)) {
            return;
        }
        
        this.isConnecting = true;
        this.updateDeviceConnectionState('connecting');
        this.showToast(`Connecting to device ${address}...`, 'info');
        
        try {
            // Increment metrics
            this.performanceData.connectionAttempts++;
            
            // Record start time for latency measurement
            const startTime = performance.now();
            
            // Connect to the device using the API client
            const response = await this.apiClient.request(`/api/ble/device/connect`, {
                method: 'POST',
                body: {
                    address: address,
                    timeout: this.settings.connectionTimeout || 10,
                    auto_reconnect: this.settings.autoReconnect || false
                }
            });
            
            // Calculate connection time for metrics
            const connectionTime = Math.round(performance.now() - startTime);
            
            if (response.success) {
                // Connection successful
                this.updateConnectionMetrics(true, connectionTime);
                
                // Update state
                this.selectedDevice = response.device;
                this.connectedDevices.set(address, response.device);
                
                // Update UI
                this.updateDeviceConnectionState('connected', response.device);
                this.updateScannedDeviceConnection(address, true);
                
                // Show success notification
                this.showToast(`Connected to ${response.device.name || address}`, 'success');
                
                // Log the success
                this.logOperation('Device', `Connected to ${response.device.name || address}`, 'success');
                
                // Get device services if available
                if (response.services) {
                    this.renderDeviceServices(response.services);
                } else {
                    this.getDeviceServices(address);
                }
            } else {
                // Failed connection
                this.updateDeviceConnectionState('disconnected');
                this.updateConnectionMetrics(false, 0);
                throw new Error(response.error || 'Connection failed');
            }
        } catch (error) {
            console.error('Connection error:', error);
            this.logOperation('Device', `Connection failed: ${error.message}`, 'error');
            this.showToast(`Connection failed: ${error.message}`, 'error');
            this.updateConnectionMetrics(false, 0);
        } finally {
            this.isConnecting = false;
        }
    }
    
    /**
     * Disconnect from a BLE device using the correct API endpoint
     * @param {string} address - The address of the device to disconnect
     */
    async disconnectFromDevice(address) {
        if (!address) return;
        
        try {
            this.showToast(`Disconnecting from device...`, 'info');
            
            // Disconnect from device using the API client
            const response = await this.apiClient.request(`/api/ble/device/disconnect`, {
                method: 'POST',
                body: {
                    address: address
                }
            });
            
            if (response.success) {
                // Update UI
                this.updateScannedDeviceConnection(address, false);
                this.updateDeviceConnectionState('disconnected');
                
                // Remove from connected devices
                this.connectedDevices.delete(address);
                
                // Clear selected device if this was the selected one
                if (this.selectedDevice && this.selectedDevice.address === address) {
                    this.selectedDevice = null;
                }
                
                this.showToast(`Disconnected from device`, 'success');
                this.logOperation('Device', `Disconnected from ${address}`, 'info');
            } else {
                throw new Error(response.error || 'Disconnect failed');
            }
        } catch (error) {
            console.error('Disconnect error:', error);
            this.logOperation('Device', `Disconnect failed: ${error.message}`, 'error');
            this.showToast(`Disconnect failed: ${error.message}`, 'error');
        }
    }
    
    /**
     * Event handler for device connected event
     * @param {Object} device - The connected device
     */
    onDeviceConnected(device) {
        if (!device || !device.address) return;
        
        // Update local state
        this.connectedDevices.set(device.address, device);
        
        // Update UI if this is the current selected device
        if (this.selectedDevice && this.selectedDevice.address === device.address) {
            this.updateDeviceConnectionState('connected', device);
        }
        
        // Update scanned devices list
        this.updateScannedDeviceConnection(device.address, true);
        
        // Update connected devices list
        this.renderConnectedDevice(device);
        
        // Log
        this.logOperation('Device', `Device connected: ${device.name || device.address}`);
    }
    
    /**
     * Event handler for device disconnected event
     * @param {Object} device - The disconnected device
     */
    onDeviceDisconnected(device) {
        if (!device || !device.address) return;
        
        // Update local state
        this.connectedDevices.delete(device.address);
        
        // Update UI if this is the current selected device
        if (this.selectedDevice && this.selectedDevice.address === device.address) {
            this.selectedDevice = null;
            this.updateDeviceConnectionState('disconnected');
        }
        
        // Update scanned devices list
        this.updateScannedDeviceConnection(device.address, false);
        
        // Update connected devices list
        this.updateConnectedDevicesList();
        
        // Log
        this.logOperation('Device', `Device disconnected: ${device.name || device.address}`);
    }
    
    /**
     * Update the connection state UI for a device
     * @param {string} state - The connection state ('connecting', 'connected', 'disconnected')
     * @param {Object} device - The device information (optional)
     */
    updateDeviceConnectionState(state, device = null) {
        // Get UI elements
        const connectCard = document.getElementById('ble-device-info-card');
        const noDeviceMessage = document.getElementById('no-device-message');
        const deviceInfo = document.getElementById('device-info');
        const deviceStatusIndicator = document.getElementById('device-status-indicator');
        const deviceStatusText = document.getElementById('device-status-text');
        
        if (!connectCard || !noDeviceMessage || !deviceInfo) return;
        
        switch (state) {
            case 'connecting':
                // Update visible sections
                noDeviceMessage.style.display = 'none';
                deviceInfo.style.display = 'block';
                
                // Update status indicator
                if (deviceStatusIndicator) {
                    deviceStatusIndicator.className = 'connection-status status-connecting';
                }
                if (deviceStatusText) {
                    deviceStatusText.textContent = 'Connecting...';
                    deviceStatusText.className = 'text-yellow-500';
                }
                
                // Show connecting animation
                this.showToast('Connecting to device...', 'info');
                break;
                
            case 'connected':
                if (!device) return;
                
                // Update visible sections
                noDeviceMessage.style.display = 'none';
                deviceInfo.style.display = 'block';
                
                // Update device details
                this.renderConnectedDevice(device);
                
                // Update status indicator
                if (deviceStatusIndicator) {
                    deviceStatusIndicator.className = 'connection-status status-connected';
                }
                if (deviceStatusText) {
                    deviceStatusText.textContent = 'Connected';
                    deviceStatusText.className = 'text-green-500';
                }
                
                // Show success toast
                this.showToast(`Connected to ${device.name || device.address}`, 'success');
                break;
                
            case 'disconnected':
                // Update visible sections if no device is selected
                if (!this.selectedDevice) {
                    noDeviceMessage.style.display = 'flex';
                    deviceInfo.style.display = 'none';
                }
                
                // Update status indicator
                if (deviceStatusIndicator) {
                    deviceStatusIndicator.className = 'connection-status status-disconnected';
                }
                if (deviceStatusText) {
                    deviceStatusText.textContent = 'Disconnected';
                    deviceStatusText.className = 'text-red-500';
                }
                break;
        }
    }
    
    /**
     * Update the connected state of a device in the scanned list
     * @param {string} address - Device address
     * @param {boolean} isConnected - Whether the device is connected
     */
    updateScannedDeviceConnection(address, isConnected) {
        const deviceElement = document.getElementById(`device-${address.replace(/:/g, '-')}`);
        if (!deviceElement) return;
        
        const connectBtn = deviceElement.querySelector('.connect-btn');
        const disconnectBtn = deviceElement.querySelector('.disconnect-btn');
        
        if (connectBtn) {
            connectBtn.classList.toggle('hidden', isConnected);
        }
        
        if (disconnectBtn) {
            disconnectBtn.classList.toggle('hidden', !isConnected);
        }
    }
    
    /**
     * Render a connected device in the connected devices list
     * @param {Object} device - The connected device
     */
    renderConnectedDevice(device) {
        const connectedDevicesList = document.getElementById('connected-devices-list');
        if (!connectedDevicesList) return;
        
        // Remove "No connected devices" message if it exists
        const noDevicesMsg = connectedDevicesList.querySelector('.text-center.text-gray-400');
        if (noDevicesMsg && connectedDevicesList.children.length === 1) {
            noDevicesMsg.remove();
        }
        
        // Check if device already exists in the list
        const deviceId = `connected-${device.address.replace(/:/g, '-')}`;
        let deviceItem = document.getElementById(deviceId);
        
        if (!deviceItem) {
            // Create new device item
            deviceItem = document.createElement('div');
            deviceItem.id = deviceId;
            deviceItem.className = 'device-item hover:bg-gray-700';
            connectedDevicesList.appendChild(deviceItem);
        }
        
        // Update device item content
        deviceItem.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    <div class="w-8 h-8 bg-green-900 rounded-full flex items-center justify-center mr-3">
                        <i data-feather="smartphone" class="w-4 h-4 text-green-300"></i>
                    </div>
                    <div>
                        <div class="font-medium">${device.name || 'Unknown Device'}</div>
                        <div class="text-sm text-gray-400">${device.address}</div>
                    </div>
                </div>
                <div class="flex items-center">
                    <button class="view-device-btn bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded-lg text-sm mr-2">
                        Details
                    </button>
                    <button class="disconnect-btn bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded-lg text-sm">
                        Disconnect
                    </button>
                </div>
            </div>
        `;
        
        // Add event listeners
        setTimeout(() => {
            // Replace feather icons
            feather.replace();
            
            // Add view button listener
            const viewBtn = deviceItem.querySelector('.view-device-btn');
            if (viewBtn) {
                viewBtn.addEventListener('click', () => {
                    // Switch to the connected device info display
                    this.selectedDevice = device;
                    this.updateDeviceConnectionState('connected', device);
                });
            }
            
            // Add disconnect button listener
            const disconnectBtn = deviceItem.querySelector('.disconnect-btn');
            if (disconnectBtn) {
                disconnectBtn.addEventListener('click', () => {
                    this.disconnectFromDevice(device.address);
                });
            }
        }, 0);
    }
    
    /**
     * Update the connected devices list
     */
    updateConnectedDevicesList() {
        const connectedDevicesList = document.getElementById('connected-devices-list');
        if (!connectedDevicesList) return;
        
        // If no connected devices, show message
        if (this.connectedDevices.size === 0) {
            connectedDevicesList.innerHTML = '<div class="text-center py-4 text-gray-400">No connected devices</div>';
            return;
        }
        
        // Remove devices that are no longer connected
        Array.from(connectedDevicesList.children).forEach(child => {
            if (child.id && child.id.startsWith('connected-')) {
                const address = child.id.replace('connected-', '').replace(/-/g, ':');
                if (!this.connectedDevices.has(address)) {
                    child.remove();
                }
            }
        });
    }
    
    /**
     * Update connection metrics
     * @param {boolean} success - Whether the connection attempt was successful
     * @param {number} connectionTime - Time taken for connection in ms
     */
    updateConnectionMetrics(success, connectionTime) {
        if (success) {
            this.performanceData.connectionSuccess++;
            
            // Update average connection time
            const prevTotal = this.performanceData.avgConnectionTime * (this.performanceData.connectionSuccess - 1);
            this.performanceData.avgConnectionTime = (prevTotal + connectionTime) / this.performanceData.connectionSuccess;
        }
        
        // Update success rate
        const successRate = Math.round((this.performanceData.connectionSuccess / this.performanceData.connectionAttempts) * 100);
        
        // Update UI elements
        const successRateElement = document.getElementById('connection-success-rate');
        const successBarElement = document.getElementById('connection-success-bar');
        
        if (successRateElement) {
            successRateElement.textContent = `${successRate}%`;
        }
        
        if (successBarElement) {
            successBarElement.style.width = `${successRate}%`;
        }
    }
    
    /**
     * Initialize console section
     */
    initConsoleSection() {
        console.log('Initializing console section');
        const consoleSection = document.getElementById('console-section');
        
        if (!consoleSection) {
            console.warn('Console section not found in DOM');
            return;
        }
        
        // Add tab switching functionality to console buttons
        const logTabBtn = document.getElementById('log-tab-btn');
        const debugTabBtn = document.getElementById('debug-tab-btn');
        const metricsTabBtn = document.getElementById('metrics-tab-btn');
        
        if (logTabBtn) {
            logTabBtn.addEventListener('click', () => this.switchConsoleTab('log'));
        }
        
        if (debugTabBtn) {
            debugTabBtn.addEventListener('click', () => this.switchConsoleTab('debug'));
        }
        
        if (metricsTabBtn) {
            metricsTabBtn.addEventListener('click', () => this.switchConsoleTab('metrics'));
        }
        
        // Initialize the debug console command execution
        const debugCommandInput = document.getElementById('debug-command-input');
        const debugCommandBtn = document.getElementById('debug-command-btn');
        
        if (debugCommandBtn && debugCommandInput) {
            // Execute command when clicking the button
            debugCommandBtn.addEventListener('click', () => {
                const command = debugCommandInput.value.trim();
                if (command) {
                    this.executeDebugCommand(command);
                    debugCommandInput.value = '';
                }
            });
            
            // Execute command on Enter key
            debugCommandInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    const command = debugCommandInput.value.trim();
                    if (command) {
                        this.executeDebugCommand(command);
                        debugCommandInput.value = '';
                    }
                    e.preventDefault();
                }
            });
        }
        
        // Initialize performance chart
        this.initPerformanceChart();
    }
    
    /**
     * Switch between console tabs (log, debug, metrics)
     * @param {string} tabName - Name of tab to switch to ('log', 'debug', 'metrics')
     */
    switchConsoleTab(tabName) {
        console.log(`Switching console tab to ${tabName}`);
        
        // Handle legacy tab name mapping
        if (tabName === 'debug-console') {
            tabName = 'debug';
        }
        
        // Get tab button and content elements
        const tabButtons = {
            log: document.getElementById('log-tab-btn'),
            debug: document.getElementById('debug-tab-btn'),
            metrics: document.getElementById('metrics-tab-btn')
        };
        
        const tabContents = {
            log: document.getElementById('log-tab-content'),
            debug: document.getElementById('debug-tab-content'),
            metrics: document.getElementById('metrics-tab-content')
        };
        
        // Check if elements exist
        if (!tabButtons[tabName] || !tabContents[tabName]) {
            console.warn(`Tab elements for ${tabName} not found, creating fallback elements`);
            
            // Create console section if it doesn't exist
            let consoleSection = document.getElementById('console-section');
            if (!consoleSection) {
                consoleSection = document.createElement('div');
                consoleSection.id = 'console-section';
                consoleSection.className = 'mt-4 bg-gray-800 rounded-lg shadow-lg p-4';
                
                const mainContent = document.querySelector('.main-content') || document.body;
                mainContent.appendChild(consoleSection);
            }
            
            // Create tab buttons if they don't exist
            const tabButtonContainer = document.getElementById('console-tab-buttons') || 
                (() => {
                    const container = document.createElement('div');
                    container.id = 'console-tab-buttons';
                    container.className = 'flex border-b border-gray-700 mb-4';
                    consoleSection.appendChild(container);
                    return container;
                })();
            
            // Create tab content containers if they don't exist
            const tabContentContainer = document.getElementById('console-tab-contents') || 
                (() => {
                    const container = document.createElement('div');
                    container.id = 'console-tab-contents';
                    consoleSection.appendChild(container);
                    return container;
                })();
            
            // Create missing tab buttons
            for (const tab of ['log', 'debug', 'metrics']) {
                if (!tabButtons[tab]) {
                    const btn = document.createElement('button');
                    btn.id = `${tab}-tab-btn`;
                    btn.className = 'px-4 py-2 mx-1 rounded-t text-gray-400';
                    btn.textContent = tab.charAt(0).toUpperCase() + tab.slice(1);
                    btn.addEventListener('click', () => this.switchConsoleTab(tab));
                    tabButtonContainer.appendChild(btn);
                    tabButtons[tab] = btn;
                }
                
                if (!tabContents[tab]) {
                    const content = document.createElement('div');
                    content.id = `${tab}-tab-content`;
                    content.className = 'hidden';
                    
                    // Add specific content for each tab type
                    if (tab === 'log') {
                        content.innerHTML = `
                            <div id="operations-log" class="bg-gray-900 p-2 rounded h-64 overflow-y-auto text-sm">
                                <div class="text-gray-400">Operations log is empty</div>
                            </div>
                            <button id="clear-log-btn" class="mt-2 bg-gray-700 hover:bg-gray-600 text-white rounded px-3 py-1">Clear Log</button>
                        `;
                    } else if (tab === 'debug') {
                        content.innerHTML = `
                            <div id="debug-output" class="bg-gray-900 p-2 rounded h-64 overflow-y-auto text-sm">
                                <div class="text-gray-400">Debug console ready. Type 'help' for available commands.</div>
                            </div>
                            <div class="mt-2 flex">
                                <input id="debug-command-input" type="text" placeholder="Enter command" 
                                       class="flex-1 bg-gray-700 text-white rounded px-3 py-1">
                                <button id="debug-command-btn" class="ml-2 bg-blue-600 hover:bg-blue-500 text-white rounded px-3 py-1">Execute</button>
                            </div>
                        `;
                    } else if (tab === 'metrics') {
                        content.innerHTML = `
                            <div class="grid grid-cols-2 gap-4 mb-4">
                                <div class="bg-gray-900 rounded p-3">
                                    <div class="text-gray-400 text-sm mb-1">Scan Success Rate</div>
                                    <div id="scan-success-rate" class="text-2xl text-blue-400">0%</div>
                                </div>
                                <div class="bg-gray-900 rounded p-3">
                                    <div class="text-gray-400 text-sm mb-1">Connection Success Rate</div>
                                    <div id="connection-success-rate" class="text-2xl text-blue-400">0%</div>
                                </div>
                                <div class="bg-gray-900 rounded p-3">
                                    <div class="text-gray-400 text-sm mb-1">Avg. Connection Time</div>
                                    <div id="avg-connection-time" class="text-2xl text-blue-400">0ms</div>
                                </div>
                                <div class="bg-gray-900 rounded p-3">
                                    <div class="text-gray-400 text-sm mb-1">Uptime</div>
                                    <div id="uptime" class="text-2xl text-blue-400">0m</div>
                                </div>
                            </div>
                            <div class="bg-gray-900 rounded p-3">
                                <div class="text-gray-400 text-sm mb-2">Connection Performance</div>
                                <div class="h-40">
                                    <canvas id="ble-performance-chart"></canvas>
                                </div>
                            </div>
                        `;
                    }
                    
                    tabContentContainer.appendChild(content);
                    tabContents[tab] = content;
                }
            }
            
            // Initialize event handlers for the newly created elements
            const debugCommandBtn = document.getElementById('debug-command-btn');
            const debugCommandInput = document.getElementById('debug-command-input');
            
            if (debugCommandBtn && debugCommandInput) {
                debugCommandBtn.addEventListener('click', () => {
                    const command = debugCommandInput.value.trim();
                    if (command) {
                        this.executeDebugCommand(command);
                        debugCommandInput.value = '';
                    }
                });
                
                debugCommandInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        const command = debugCommandInput.value.trim();
                        if (command) {
                            this.executeDebugCommand(command);
                            debugCommandInput.value = '';
                        }
                        e.preventDefault();
                    }
                });
            }
            
            const clearLogBtn = document.getElementById('clear-log-btn');
            if (clearLogBtn) {
                clearLogBtn.addEventListener('click', () => {
                    const operationsLog = document.getElementById('operations-log');
                    if (operationsLog) {
                        operationsLog.innerHTML = '';
                    }
                });
            }
            
            // Initialize performance chart if we're switching to metrics tab
            if (tabName === 'metrics') {
                setTimeout(() => this.initPerformanceChart(), 0);
            }
        }
        
        // Hide all tab contents and deactivate all buttons
        Object.values(tabContents).forEach(el => {
            if (el) el.style.display = 'none';
        });
        
        Object.values(tabButtons).forEach(el => {
            if (el) {
                el.classList.remove('bg-blue-600');
                el.classList.add('bg-gray-700');
            }
        });
        
        // Show selected tab content and activate button
        if (tabContents[tabName]) {
            tabContents[tabName].style.display = 'block';
        }
        
        if (tabButtons[tabName]) {
            tabButtons[tabName].classList.remove('bg-gray-700');
            tabButtons[tabName].classList.add('bg-blue-600');
        }
        
        // If switching to metrics tab, refresh the chart
        if (tabName === 'metrics') {
            this.updatePerformanceChart();
        }
        
        // Log operation
        this.logOperation('Console', `Switched to ${tabName} tab`);
    }
    
    /**
     * Execute a debug command
     * @param {string} command - The command to execute
     */
    executeDebugCommand(command) {
        console.log(`Executing debug command: ${command}`);
        
        const debugOutput = document.getElementById('debug-output');
        if (!debugOutput) return;
        
        try {
            // Parse command and arguments
            const parts = command.split(' ');
            const cmd = parts[0].toLowerCase();
            const args = parts.slice(1);
            
            // Add command to output
            const cmdEl = document.createElement('div');
            cmdEl.className = 'mb-1 text-blue-400';
            cmdEl.textContent = `> ${command}`;
            debugOutput.appendChild(cmdEl);
            
            // Execute appropriate command
            switch (cmd) {
                case 'help':
                    this.outputDebugInfo('Available commands:\n' +
                        'help - Show this help\n' +
                        'clear - Clear debug output\n' +
                        'status - Show system status\n' +
                        'scan <time> - Scan for devices for specified time\n' +
                        'connect <addr> - Connect to a device\n' +
                        'disconnect <addr> - Disconnect from a device\n' +
                        'reset - Reset the BLE adapter\n' +
                        'list - List connected devices\n' +
                        'info - Show system information');
                    break;
                
                case 'clear':
                    debugOutput.innerHTML = '';
                    break;
                
                case 'status':
                    this.outputDebugInfo(`System status:
Adapter: ${this.bleAdapter?.currentAdapter?.name || 'Unknown'}
Scanning: ${this.isScanning ? 'Yes' : 'No'}
Connected devices: ${this.connectedDevices.size}
WebSocket: ${this.bleEvents?.isConnected ? 'Connected' : 'Disconnected'}`);
                    break;
                
                case 'scan':
                    const scanTime = args[0] ? parseInt(args[0]) : 5;
                    this.outputDebugInfo(`Scanning for ${scanTime} seconds...`);
                    this.startScan(scanTime, true)
                        .then(devices => {
                            this.outputDebugInfo(`Found ${devices.length} devices`);
                        })
                        .catch(error => {
                            this.outputDebugInfo(`Scan error: ${error.message}`, 'error');
                        });
                    break;
                
                case 'connect':
                    if (!args[0]) {
                        this.outputDebugInfo('Error: Device address required', 'error');
                        break;
                    }
                    this.outputDebugInfo(`Connecting to ${args[0]}...`);
                    this.connectToDevice(args[0])
                        .then(() => {
                            this.outputDebugInfo(`Connected to ${args[0]}`);
                        })
                        .catch(error => {
                            this.outputDebugInfo(`Connection error: ${error.message}`, 'error');
                        });
                    break;
                
                case 'disconnect':
                    if (!args[0]) {
                        this.outputDebugInfo('Error: Device address required', 'error');
                        break;
                    }
                    this.outputDebugInfo(`Disconnecting from ${args[0]}...`);
                    this.disconnectFromDevice(args[0])
                        .catch(error => {
                            this.outputDebugInfo(`Disconnect error: ${error.message}`, 'error');
                        });
                    break;
                
                case 'reset':
                    this.outputDebugInfo('Resetting adapter...');
                    this.resetAdapter()
                        .then(() => {
                            this.outputDebugInfo('Adapter reset successful');
                        })
                        .catch(error => {
                            this.outputDebugInfo(`Reset error: ${error.message}`, 'error');
                        });
                    break;
                
                case 'list':
                    if (this.connectedDevices.size === 0) {
                        this.outputDebugInfo('No connected devices');
                    } else {
                        let deviceList = 'Connected devices:\n';
                        this.connectedDevices.forEach((device, address) => {
                            deviceList += `- ${device.name || 'Unknown'} (${address})\n`;
                        });
                        this.outputDebugInfo(deviceList);
                    }
                    break;
                
                case 'info':
                    this.outputDebugInfo(`BLE Dashboard Info:
Version: 1.2.0
Build time: ${new Date().toISOString()}
Framework: Web
Uptime: ${this.getUptime()} minutes
Scan success rate: ${this.performanceData.scanAttempts > 0 ? 
                     Math.round((this.performanceData.scanSuccess / this.performanceData.scanAttempts) * 100) : 0}%
Connection success rate: ${this.performanceData.connectionAttempts > 0 ? 
                         Math.round((this.performanceData.connectionSuccess / this.performanceData.connectionAttempts) * 100) : 0}%`);
                    break;
                
                default:
                    this.outputDebugInfo(`Unknown command: ${cmd}. Type 'help' for available commands.`, 'warning');
            }
            
            // Scroll to bottom
            debugOutput.scrollTop = debugOutput.scrollHeight;
            
        } catch (error) {
            console.error('Error executing debug command:', error);
            this.outputDebugInfo(`Error: ${error.message}`, 'error');
        }
        
        // Log operation
        this.logOperation('Debug', `Executed command: ${command}`);
    }
    
    /**
     * Output information to the debug console
     * @param {string} text - The text to output
     * @param {string} type - The type of output ('info', 'error', 'success', 'warning')
     */
    outputDebugInfo(text, type = 'info') {
        const debugOutput = document.getElementById('debug-output');
        if (!debugOutput) return;
        
        const outputEl = document.createElement('div');
        outputEl.className = 'mb-2 whitespace-pre-wrap';
        
        // Set color based on type
        switch (type) {
            case 'error':
                outputEl.className += ' text-red-400';
                break;
            case 'warning':
                outputEl.className += ' text-yellow-400';
                break;
            case 'success':
                outputEl.className += ' text-green-400';
                break;
            default:
                outputEl.className += ' text-gray-300';
        }
        
        outputEl.textContent = text;
        debugOutput.appendChild(outputEl);
        
        // Scroll to bottom
        debugOutput.scrollTop = debugOutput.scrollHeight;
    }
    
    /**
     * Get uptime in minutes
     * @returns {number} Uptime in minutes
     */
    getUptime() {
        return Math.round((Date.now() - this.initTime) / 60000);
    }
    
    /**
     * Initialize settings section
     */
    initSettingsSection() {
        // Connection timeout range
        const timeoutRange = document.getElementById('connection-timeout');
        const timeoutValue = document.getElementById('timeout-value');
        
        if (timeoutRange && timeoutValue) {
            // Initialize with current value
            timeoutRange.value = this.settings.connectionTimeout || 10;
            timeoutValue.textContent = `${timeoutRange.value}s`;
            
            // Add event listener
            timeoutRange.addEventListener('input', () => {
                timeoutValue.textContent = `${timeoutRange.value}s`;
                this.settings.connectionTimeout = parseInt(timeoutRange.value, 10);
            });
        }
        
        // Auto-connect toggle
        const autoConnectToggle = document.getElementById('auto-connect-toggle');
        if (autoConnectToggle) {
            // Initialize with current value
            autoConnectToggle.checked = this.settings.autoConnect;
            
            // Add event listener
            autoConnectToggle.addEventListener('change', () => {
                this.settings.autoConnect = autoConnectToggle.checked;
            });
        }
        
        // Auto-reconnect toggle
        const autoReconnectToggle = document.getElementById('auto-reconnect-toggle');
        if (autoReconnectToggle) {
            // Initialize with current value
            autoReconnectToggle.checked = this.settings.autoReconnect;
            
            // Add event listener
            autoReconnectToggle.addEventListener('change', () => {
                this.settings.autoReconnect = autoReconnectToggle.checked;
            });
        }
        
        // Show technical details toggle
        const technicalToggle = document.getElementById('show-technical-toggle');
        if (technicalToggle) {
            // Initialize with current value
            technicalToggle.checked = this.settings.showTechnicalDetails;
            
            // Add event listener
            technicalToggle.addEventListener('change', () => {
                this.settings.showTechnicalDetails = technicalToggle.checked;
                
                // Apply the setting immediately
                document.body.classList.toggle('show-technical', technicalToggle.checked);
            });
        }
        
        // Log level selection
        const logLevelSelect = document.getElementById('settings-log-level');
        if (logLevelSelect) {
            // Initialize with current value
            logLevelSelect.value = this.settings.logLevel;
            
            // Add event listener
            logLevelSelect.addEventListener('change', () => {
                this.settings.logLevel = logLevelSelect.value;
                this.setLogLevel(logLevelSelect.value);
            });
        }
        
        // Save settings button
        const saveSettingsBtn = document.getElementById('save-settings-btn');
        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => {
                this.saveSettings();
                this.logOperation('Settings', 'Settings saved successfully', 'success');
            });
        }
    }
    
    /**
     * Save settings to localStorage
     */
    saveSettings() {
        localStorage.setItem('bleDashboardSettings', JSON.stringify(this.settings));
    }
    
    /**
     * Load settings from localStorage
     * @returns {Object} The loaded settings or default settings
     */
    loadSettings() {
        const defaultSettings = {
            autoConnect: false,
            connectionTimeout: 10,
            autoReconnect: true,
            showTechnicalDetails: false,
            logLevel: 'info',
            initTime: Date.now()
        };
        
        const savedSettings = localStorage.getItem('bleDashboardSettings');
        if (!savedSettings) return defaultSettings;
        
        try {
            return { ...defaultSettings, ...JSON.parse(savedSettings) };
        } catch (error) {
            console.error('Failed to parse saved settings:', error);
            return defaultSettings;
        }
    }
    
    /**
     * Apply settings to the BLE subsystem
     */
    applySettings() {
        // Record initialization time if not already set
        if (!this.initTime) {
            this.initTime = Date.now();
        }
        
        // Set log level
        this.setLogLevel(this.settings.logLevel);
        
        // Apply show technical details
        document.body.classList.toggle('show-technical', this.settings.showTechnicalDetails);
    }
    
    /**
     * Set the current log level
     * @param {string} level - The log level to set
     */
    setLogLevel(level) {
        // Apply log level to API client if it supports it
        if (this.apiClient && typeof this.apiClient.setLogLevel === 'function') {
            this.apiClient.setLogLevel(level);
        }
        
        // Store in settings
        this.settings.logLevel = level;
    }
    
    /**
     * Initialize advanced device features
     * To be called after a successful device connection
     * @param {string} deviceAddress - The address of the connected device
     */
    initDeviceFeatures(deviceAddress) {
        // Get the device from the connected devices map
        const device = this.connectedDevices.get(deviceAddress);
        if (!device) {
            console.error(`Device not found: ${deviceAddress}`);
            return;
        }
        
        this.initBondingSection(deviceAddress);
        this.initMtuSettings(deviceAddress);
        this.initFileTransfer(deviceAddress);
        this.initOtaUpgrade(deviceAddress);
        
        // Log the initialization
        this.logOperation('Device', `Initialized features for device ${deviceAddress}`, 'info');
    }
    
    /**
     * Initialize the bonding section
     * @param {string} deviceAddress - The address of the connected device
     */
    initBondingSection(deviceAddress) {
        // Bond toggle
        const bondToggle = document.getElementById('bond-device-toggle');
        const bondStatusText = document.getElementById('bond-status-text');
        
        if (!bondToggle || !bondStatusText) return;
        
        // Check initial bond status
        this.getBondingStatus(deviceAddress).then(isBonded => {
            // Update the toggle without triggering the event
            bondToggle.checked = isBonded;
            
            // Update status text
            bondStatusText.textContent = isBonded ? 'Bonded' : 'Not Bonded';
            bondStatusText.className = isBonded ? 'text-green-500' : 'text-gray-400';
        });
        
        // Set up event listener
        bondToggle.addEventListener('change', async () => {
            const shouldBond = bondToggle.checked;
            
            try {
                // Show loading state
                bondStatusText.textContent = shouldBond ? 'Bonding...' : 'Removing bond...';
                bondStatusText.className = 'text-yellow-400';
                
                // Perform the action
                if (shouldBond) {
                    await this.bondWithDevice(deviceAddress);
                    bondStatusText.textContent = 'Bonded';
                    bondStatusText.className = 'text-green-500';
                    this.logOperation('Bonding', `Successfully bonded with ${deviceAddress}`, 'success');
                } else {
                    await this.removeBond(deviceAddress);
                    bondStatusText.textContent = 'Not Bonded';
                    bondStatusText.className = 'text-gray-400';
                    this.logOperation('Bonding', `Removed bond with ${deviceAddress}`, 'info');
                }
            } catch (error) {
                // Handle error
                console.error('Bonding operation failed:', error);
                bondToggle.checked = !shouldBond; // Revert the toggle
                bondStatusText.textContent = `Error: ${error.message}`;
                bondStatusText.className = 'text-red-500';
                this.logOperation('Bonding', `Failed to change bond state: ${error.message}`, 'error');
            }
        });
    }
    
    /**
     * Get bonding status for a device
     * @param {string} deviceAddress - The address of the device
     * @returns {Promise<boolean>} Whether the device is bonded
     */
    async getBondingStatus(deviceAddress) {
        try {
            const response = await this.apiClient.request(`/api/ble/device/${deviceAddress}/bonding_status`, {
                method: 'GET'
            });
            
            return response.bonded === true;
        } catch (error) {
            console.error('Failed to get bonding status:', error);
            return false;
        }
    }
    
    /**
     * Bond with a device
     * @param {string} deviceAddress - The address of the device to bond with
     * @returns {Promise<void>}
     */
    async bondWithDevice(deviceAddress) {
        try {
            await this.apiClient.request(`/api/ble/device/${deviceAddress}/bond`, {
                method: 'POST'
            });
        } catch (error) {
            console.error('Bonding failed:', error);
            throw new Error(error.message || 'Failed to bond with device');
        }
    }
    
    /**
     * Remove bond with a device
     * @param {string} deviceAddress - The address of the device to remove bond from
     * @returns {Promise<void>}
     */
    async removeBond(deviceAddress) {
        try {
            await this.apiClient.request(`/api/ble/device/${deviceAddress}/bond`, {
                method: 'DELETE'
            });
        } catch (error) {
            console.error('Remove bond failed:', error);
            throw new Error(error.message || 'Failed to remove bond with device');
        }
    }
    
    /**
     * Initialize MTU settings section
     * @param {string} deviceAddress - The address of the connected device
     */
    initMtuSettings(deviceAddress) {
        const mtuRangeInput = document.getElementById('mtu-size-range');
        const mtuValueText = document.getElementById('mtu-value');
        const setMtuBtn = document.getElementById('set-mtu-btn');
        
        if (!mtuRangeInput || !mtuValueText || !setMtuBtn) return;
        
        // Get the current MTU
        this.getCurrentMtu(deviceAddress).then(mtu => {
            mtuRangeInput.value = mtu;
            mtuValueText.textContent = `${mtu} bytes`;
        });
        
        // Update the value text when the range is changed
        mtuRangeInput.addEventListener('input', () => {
            mtuValueText.textContent = `${mtuRangeInput.value} bytes`;
        });
        
        // Set up the set MTU button
        setMtuBtn.addEventListener('click', async () => {
            const newMtu = parseInt(mtuRangeInput.value, 10);
            
            try {
                // Show loading state
                setMtuBtn.textContent = 'Setting...';
                setMtuBtn.disabled = true;
                
                // Set the MTU
                await this.setMtu(deviceAddress, newMtu);
                
                // Update UI
                this.logOperation('MTU', `Set MTU to ${newMtu} bytes for ${deviceAddress}`, 'success');
                
                // Reset button
                setMtuBtn.textContent = 'Set MTU';
                setMtuBtn.disabled = false;
            } catch (error) {
                console.error('Set MTU failed:', error);
                this.logOperation('MTU', `Failed to set MTU: ${error.message}`, 'error');
                
                // Reset button
                setMtuBtn.textContent = 'Set MTU';
                setMtuBtn.disabled = false;
            }
        });
    }
    
    /**
     * Get the current MTU for a device
     * @param {string} deviceAddress - The address of the device
     * @returns {Promise<number>} The current MTU size
     */
    async getCurrentMtu(deviceAddress) {
        try {
            const response = await this.apiClient.request(`/api/ble/device/${deviceAddress}/mtu`, {
                method: 'GET'
            });
            
            return response.mtu || 23; // Default BLE MTU is 23
        } catch (error) {
            console.error('Failed to get current MTU:', error);
            return 23; // Default to standard MTU
        }
    }
    
    /**
     * Set the MTU for a device
     * @param {string} deviceAddress - The address of the device
     * @param {number} mtuSize - The MTU size to set
     * @returns {Promise<void>}
     */
    async setMtu(deviceAddress, mtuSize) {
        try {
            await this.apiClient.request(`/api/ble/device/${deviceAddress}/mtu`, {
                method: 'POST',
                body: { mtu: mtuSize }
            });
        } catch (error) {
            console.error('Set MTU failed:', error);
            throw new Error(error.message || 'Failed to set MTU');
        }
    }
    
    /**
     * Initialize file transfer section
     * @param {string} deviceAddress - The address of the connected device
     */
    initFileTransfer(deviceAddress) {
        const fileInput = document.getElementById('file-input');
        const sendFileBtn = document.getElementById('send-file-btn');
        const fileProgressBar = document.getElementById('file-progress-bar');
        const fileProgressText = document.getElementById('file-progress-text');
        const receiveFileBtn = document.getElementById('receive-file-btn');
        
        if (!fileInput || !sendFileBtn || !fileProgressBar || !fileProgressText) return;
        
        // Update file selection info
        fileInput.addEventListener('change', () => {
            const file = fileInput.files[0];
            if (file) {
                fileProgressText.textContent = `Selected: ${file.name} (${this.formatBytes(file.size)})`;
            } else {
                fileProgressText.textContent = 'No file selected';
            }
        });
        
        // Set up send file button
        sendFileBtn.addEventListener('click', async () => {
            const file = fileInput.files[0];
            
            if (!file) {
                this.logOperation('File Transfer', 'No file selected', 'error');
                return;
            }
            
            try {
                // Set UI to sending state
                sendFileBtn.disabled = true;
                fileProgressText.textContent = 'Preparing file...';
                fileProgressBar.style.width = '0%';
                
                // Send the file
                await this.sendFile(deviceAddress, file, (progress) => {
                    // Update progress bar
                    fileProgressBar.style.width = `${progress}%`;
                    fileProgressText.textContent = `Sending: ${progress}%`;
                });
                
                // Success state
                fileProgressText.textContent = `Sent: ${file.name}`;
                this.logOperation('File Transfer', `Successfully sent ${file.name}`, 'success');
                
                // Reset file input
                fileInput.value = '';
                sendFileBtn.disabled = false;
            } catch (error) {
                console.error('File transfer failed:', error);
                fileProgressText.textContent = `Error: ${error.message}`;
                this.logOperation('File Transfer', `Failed to send file: ${error.message}`, 'error');
                sendFileBtn.disabled = false;
            }
        });
        
        // Set up receive file button if it exists
        if (receiveFileBtn) {
            receiveFileBtn.addEventListener('click', async () => {
                try {
                    // Set UI to receiving state
                    receiveFileBtn.disabled = true;
                    fileProgressText.textContent = 'Waiting for file...';
                    fileProgressBar.style.width = '0%';
                    
                    // Receive the file
                    const fileInfo = await this.receiveFile(deviceAddress, (progress) => {
                        // Update progress bar
                        fileProgressBar.style.width = `${progress}%`;
                        fileProgressText.textContent = `Receiving: ${progress}%`;
                    });
                    
                    // Success state
                    fileProgressText.textContent = `Received: ${fileInfo.name}`;
                    this.logOperation('File Transfer', `Successfully received ${fileInfo.name}`, 'success');
                    
                    // Reset state
                    receiveFileBtn.disabled = false;
                } catch (error) {
                    console.error('File reception failed:', error);
                    fileProgressText.textContent = `Error: ${error.message}`;
                    this.logOperation('File Transfer', `Failed to receive file: ${error.message}`, 'error');
                    receiveFileBtn.disabled = false;
                }
            });
        }
    }
    
    /**
     * Format bytes to human-readable size
     * @param {number} bytes - The size in bytes
     * @returns {string} Formatted string
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    /**
     * Send a file to a device
     * @param {string} deviceAddress - The address of the device
     * @param {File} file - The file to send
     * @param {Function} progressCallback - Callback for progress updates
     * @returns {Promise<void>}
     */
    async sendFile(deviceAddress, file, progressCallback) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = async (e) => {
                const fileData = new Uint8Array(e.target.result);
                const chunkSize = 512; // Default chunk size
                const totalChunks = Math.ceil(fileData.length / chunkSize);
                
                try {
                    // Start file transfer session
                    await this.apiClient.request(`/api/ble/device/${deviceAddress}/file_transfer/start`, {
                        method: 'POST',
                        body: {
                            filename: file.name,
                            size: fileData.length,
                            type: file.type
                        }
                    });
                    
                    // Send file in chunks
                    for (let i = 0; i < totalChunks; i++) {
                        const start = i * chunkSize;
                        const end = Math.min(fileData.length, start + chunkSize);
                        const chunk = fileData.slice(start, end);
                        
                        await this.apiClient.request(`/api/ble/device/${deviceAddress}/file_transfer/chunk`, {
                            method: 'POST',
                            body: {
                                chunk_index: i,
                                data: Array.from(chunk), // Convert to regular array for JSON
                                is_last: i === totalChunks - 1
                            }
                        });
                        
                        // Update progress
                        const progress = Math.round(((i + 1) / totalChunks) * 100);
                        if (progressCallback) {
                            progressCallback(progress);
                        }
                    }
                    
                    // Complete transfer
                    await this.apiClient.request(`/api/ble/device/${deviceAddress}/file_transfer/complete`, {
                        method: 'POST'
                    });
                    
                    resolve();
                } catch (error) {
                    console.error('File transfer error:', error);
                    reject(error);
                }
            };
            
            reader.onerror = (error) => {
                reject(new Error('File reading failed'));
            };
            
            // Start reading the file
            reader.readAsArrayBuffer(file);
        });
    }
    
    /**
     * Receive a file from a device
     * @param {string} deviceAddress - The address of the device
     * @param {Function} progressCallback - Callback for progress updates
     * @returns {Promise<Object>} Information about the received file
     */
    async receiveFile(deviceAddress, progressCallback) {
        try {
            // Start waiting for file
            const session = await this.apiClient.request(`/api/ble/device/${deviceAddress}/file_transfer/receive`, {
                method: 'POST'
            });
            
            const { transfer_id, filename, size } = session;
            
            // Poll for status until complete
            return new Promise((resolve, reject) => {
                const checkStatus = async () => {
                    try {
                        const status = await this.apiClient.request(
                            `/api/ble/device/${deviceAddress}/file_transfer/${transfer_id}/status`, 
                            { method: 'GET' }
                        );
                        
                        // Update progress
                        if (progressCallback) {
                            progressCallback(status.progress);
                        }
                        
                        if (status.complete) {
                            // Transfer complete, resolve with file info
                            resolve({
                                name: filename,
                                size: size,
                                path: status.file_path
                            });
                        } else if (status.error) {
                            // Transfer failed
                            reject(new Error(status.error));
                        } else {
                            // Continue polling
                            setTimeout(checkStatus, 500);
                        }
                    } catch (error) {
                        reject(error);
                    }
                };
                
                // Start polling
                checkStatus();
            });
        } catch (error) {
            console.error('File reception error:', error);
            throw error;
        }
    }
    
    /**
     * Initialize OTA firmware upgrade section
     * @param {string} deviceAddress - The address of the connected device
     */
    initOtaUpgrade(deviceAddress) {
        const firmwareFileInput = document.getElementById('firmware-file');
        const firmwareVersionInput = document.getElementById('firmware-version');
        const upgradeFirmwareBtn = document.getElementById('upgrade-firmware-btn');
        const otaProgressBar = document.getElementById('ota-progress-bar');
        const otaStatusText = document.getElementById('ota-status-text');
        const currentFirmwareText = document.getElementById('current-firmware-text');
        
        if (!firmwareFileInput || !firmwareVersionInput || !upgradeFirmwareBtn || 
            !otaProgressBar || !otaStatusText) return;
        
        // Get current firmware version
        this.getCurrentFirmwareVersion(deviceAddress).then(version => {
            if (currentFirmwareText) {
                currentFirmwareText.textContent = version || 'Unknown';
            }
        });
        
        // Update file selection info
        firmwareFileInput.addEventListener('change', () => {
            const file = firmwareFileInput.files[0];
            if (file) {
                otaStatusText.textContent = `Selected: ${file.name} (${this.formatBytes(file.size)})`;
            } else {
                otaStatusText.textContent = 'No firmware file selected';
            }
        });
        
        // Set up upgrade button
        upgradeFirmwareBtn.addEventListener('click', async () => {
            const file = firmwareFileInput.files[0];
            const version = firmwareVersionInput.value.trim();
            
            if (!file) {
                this.logOperation('OTA Upgrade', 'No firmware file selected', 'error');
                return;
            }
            
            if (!version) {
                this.logOperation('OTA Upgrade', 'No version specified', 'error');
                return;
            }
            
            try {
                // Set UI to upgrading state
                upgradeFirmwareBtn.disabled = true;
                otaStatusText.textContent = 'Preparing firmware upgrade...';
                otaProgressBar.style.width = '0%';
                
                // Start the upgrade
                await this.performOtaUpgrade(deviceAddress, file, version, (progress) => {
                    // Update progress bar
                    otaProgressBar.style.width = `${progress}%`;
                    otaStatusText.textContent = `Upgrading: ${progress}%`;
                });
                
                // Success state
                otaStatusText.textContent = 'Firmware upgraded successfully';
                this.logOperation('OTA Upgrade', `Successfully upgraded firmware to ${version}`, 'success');
                
                // Update displayed firmware version
                if (currentFirmwareText) {
                    currentFirmwareText.textContent = version;
                }
                
                // Reset form
                firmwareFileInput.value = '';
                firmwareVersionInput.value = '';
                upgradeFirmwareBtn.disabled = false;
            } catch (error) {
                console.error('OTA upgrade failed:', error);
                otaStatusText.textContent = `Error: ${error.message}`;
                this.logOperation('OTA Upgrade', `Failed to upgrade firmware: ${error.message}`, 'error');
                upgradeFirmwareBtn.disabled = false;
            }
        });
    }
    
    /**
     * Get current firmware version of a device
     * @param {string} deviceAddress - The address of the device
     * @returns {Promise<string>} The current firmware version
     */
    async getCurrentFirmwareVersion(deviceAddress) {
        try {
            const response = await this.apiClient.request(`/api/ble/device/${deviceAddress}/firmware_version`, {
                method: 'GET'
            });
            
            return response.version || 'Unknown';
        } catch (error) {
            console.error('Failed to get firmware version:', error);
            return 'Unknown';
        }
    }
    
    /**
     * Perform an OTA firmware upgrade
     * @param {string} deviceAddress - The address of the device
     * @param {File} firmwareFile - The firmware file
     * @param {string} version - The firmware version
     * @param {Function} progressCallback - Callback for progress updates
     * @returns {Promise<void>}
     */
    async performOtaUpgrade(deviceAddress, firmwareFile, version, progressCallback) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = async (e) => {
                const firmwareData = new Uint8Array(e.target.result);
                
                try {
                    // Start OTA session
                    const response = await this.apiClient.request(`/api/ble/device/${deviceAddress}/ota/start`, {
                        method: 'POST',
                        body: {
                            size: firmwareData.length,
                            version: version
                        }
                    });
                    
                    const { ota_id, chunk_size } = response;
                    const totalChunks = Math.ceil(firmwareData.length / chunk_size);
                    
                    // Send firmware in chunks
                    for (let i = 0; i < totalChunks; i++) {
                        const start = i * chunk_size;
                        const end = Math.min(firmwareData.length, start + chunk_size);
                        const chunk = firmwareData.slice(start, end);
                        
                        await this.apiClient.request(`/api/ble/device/${deviceAddress}/ota/${ota_id}/chunk`, {
                            method: 'POST',
                            body: {
                                chunk_index: i,
                                data: Array.from(chunk), // Convert to regular array for JSON
                                is_last: i === totalChunks - 1
                            }
                        });
                        
                        // Update progress
                        const progress = Math.round(((i + 1) / totalChunks) * 100);
                        if (progressCallback) {
                            progressCallback(progress);
                        }
                    }
                    
                    // Wait for verification and commit
                    progressCallback(100);
                    
                    // Poll for OTA status until complete
                    let otaComplete = false;
                    while (!otaComplete) {
                        const status = await this.apiClient.request(
                            `/api/ble/device/${deviceAddress}/ota/${ota_id}/status`, 
                            { method: 'GET' }
                        );
                        
                        if (status.complete) {
                            otaComplete = true;
                        } else if (status.error) {
                            throw new Error(status.error);
                        } else {
                            // Wait before polling again
                            await new Promise(resolve => setTimeout(resolve, 1000));
                        }
                    }
                    
                    resolve();
                } catch (error) {
                    console.error('OTA upgrade error:', error);
                    reject(error);
                }
            };
            
            reader.onerror = (error) => {
                reject(new Error('Firmware file reading failed'));
            };
            
            // Start reading the firmware file
            reader.readAsArrayBuffer(firmwareFile);
        });
    }
    
    /**
     * Initialize MAC address search
     */
    initMacAddressSearch() {
        const macAddressInput = document.getElementById('mac-address-input');
        const searchMacBtn = document.getElementById('search-mac-btn');
        const macSearchResults = document.getElementById('mac-search-results');
        
        if (!macAddressInput || !searchMacBtn || !macSearchResults) return;
        
        // Set up search button
        searchMacBtn.addEventListener('click', async () => {
            const macAddress = macAddressInput.value.trim();
            
            if (!macAddress) {
                this.appendMacSearchResult('Please enter a MAC address', 'error');
                return;
            }
            
            try {
                // Show loading state
                searchMacBtn.disabled = true;
                this.appendMacSearchResult('Searching...', 'info');
                
                // Search for device
                const device = await this.findDeviceByMac(macAddress);
                
                // Handle results
                if (device) {
                    this.appendMacSearchResult(`Device found: ${device.name || 'Unnamed device'}`, 'success');
                    this.renderMacSearchDevice(device);
                } else {
                    this.appendMacSearchResult('No device found with this MAC address', 'warning');
                }
                
                // Reset button
                searchMacBtn.disabled = false;
            } catch (error) {
                console.error('MAC address search failed:', error);
                this.appendMacSearchResult(`Error: ${error.message}`, 'error');
                searchMacBtn.disabled = false;
            }
        });
    }
    
    /**
     * Find a device by MAC address
     * @param {string} macAddress - The MAC address to search for
     * @returns {Promise<Object>} The device if found, null otherwise
     */
    async findDeviceByMac(macAddress) {
        try {
            // First check connected devices
            for (const device of this.connectedDevices.values()) {
                if (device.address.toLowerCase() === macAddress.toLowerCase()) {
                    return device;
                }
            }
            
            // Then try to discover the device directly
            const response = await this.apiClient.request('/api/ble/device/discover_by_address', {
                method: 'POST',
                body: { address: macAddress, timeout: 10 }
            });
            
            return response.device || null;
        } catch (error) {
            console.error('Find device by MAC failed:', error);
            return null;
        }
    }
    
    /**
     * Append a result to the MAC address search results
     * @param {string} message - The message to append
     * @param {string} type - The type of message ('info', 'error', 'success', 'warning')
     */
    appendMacSearchResult(message, type = 'info') {
        const resultsContainer = document.getElementById('mac-search-results');
        if (!resultsContainer) return;
        
        // Create result entry
        const resultEntry = document.createElement('div');
        resultEntry.className = 'mb-2';
        
        // Set color based on type
        switch (type) {
            case 'error':
                resultEntry.className += ' text-red-400';
                break;
            case 'success':
                resultEntry.className += ' text-green-400';
                break;
            case 'warning':
                resultEntry.className += ' text-yellow-400';
                break;
            case 'info':
            default:
                resultEntry.className += ' text-blue-400';
                break;
        }
        
        // Set content
        resultEntry.textContent = message;
        
        // Clear previous results if this is a new search
        if (type === 'info' && message === 'Searching...') {
            resultsContainer.innerHTML = '';
        }
        
        // Add to container
        resultsContainer.appendChild(resultEntry);
    }
    
    /**
     * Render a device found by MAC address search
     * @param {Object} device - The device to render
     */
    renderMacSearchDevice(device) {
        const resultsContainer = document.getElementById('mac-search-results');
        if (!resultsContainer) return;
        
        // Create device card
        const deviceCard = document.createElement('div');
        deviceCard.className = 'bg-gray-800 rounded-lg p-3 mt-3';
        
        // Set device content
        deviceCard.innerHTML = `
            <div class="flex justify-between items-center">
                <div>
                    <div class="text-white font-semibold">${device.name || 'Unnamed Device'}</div>
                    <div class="text-gray-400 text-sm">${device.address}</div>
                    ${device.connected ? '<span class="text-green-500 text-xs">Connected</span>' : ''}
                </div>
                <div>
                    ${!device.connected ? 
                        `<button class="btn btn-primary btn-sm connect-mac-btn" data-address="${device.address}">
                            Connect
                        </button>` : 
                        `<button class="btn btn-outline-danger btn-sm disconnect-mac-btn" data-address="${device.address}">
                            Disconnect
                        </button>`
                    }
                </div>
            </div>
        `;
        
        // Add to container
        resultsContainer.appendChild(deviceCard);
        
        // Set up connect/disconnect button event listeners
        const connectBtn = deviceCard.querySelector('.connect-mac-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => {
                this.connectToDevice({ address: connectBtn.getAttribute('data-address') });
            });
        }
        
        const disconnectBtn = deviceCard.querySelector('.disconnect-mac-btn');
        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => {
                this.disconnectFromDevice(disconnectBtn.getAttribute('data-address'));
            });
        }
    }
    
    // More methods to follow in subsequent edits...
}

// Initialize the dashboard when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.bleDashboard = new BleDashboardController();
});

/**
 * Initialize toast notification system
 */
BleDashboardController.prototype.initToastNotifications = function() {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of notification (info, success, warning, error)
 * @param {number} duration - Duration in ms to show the toast
 */
BleDashboardController.prototype.showToast = function(message, type = 'info', duration = 3000) {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) return;
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    // Add toast content
    toast.innerHTML = `
        <div class="toast-content">${message}</div>
        <button class="toast-close">&times;</button>
    `;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Add close button event listener
    const closeBtn = toast.querySelector('.toast-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            toast.remove();
        });
    }
    
    // Auto-remove after duration
    setTimeout(() => {
        // Add fade-out animation
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'opacity 0.3s, transform 0.3s';
        
        // Remove after animation
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, duration);
}

/**
 * Connect to a BLE device
 * @param {Object|string} deviceInfo - Device object or MAC address
 * @returns {Promise<Object>} Connection result
 */
BleDashboardController.prototype.connectToDevice = async function(deviceInfo) {
    if (!deviceInfo) {
        console.error('Invalid device info for connection');
        this.showToast('Invalid device information', 'error');
        return Promise.reject(new Error('Invalid device information'));
    }
    
    // Extract the device address from different possible formats
    let address;
    if (typeof deviceInfo === 'string') {
        address = deviceInfo;
    } else if (deviceInfo.address) {
        address = deviceInfo.address;
    } else if (deviceInfo.mac) {
        address = deviceInfo.mac;
    } else {
        console.error('Unable to determine device address', deviceInfo);
        this.showToast('Unable to determine device address', 'error');
        return Promise.reject(new Error('Unable to determine device address'));
    }
    
    console.log(`Connecting to device: ${address}`);
    this.logOperation('Connection', `Connecting to device: ${address}`);
    this.showToast(`Connecting to ${address}...`, 'info');
    
    // Track connection attempt for metrics
    this.performanceData.connectionAttempts++;
    
    // Store connection start time for metrics
    const connectionStartTime = Date.now();
    
    try {
        // Update UI to show connecting state
        this.updateDeviceConnectionState(address, 'connecting');
        
        // Make the connection request
        const response = await this.apiClient.request('/api/ble/device/connect', {
            method: 'POST',
            body: {
                address: address
            }
        });
        
        // Calculate connection time for metrics
        const connectionTime = (Date.now() - connectionStartTime) / 1000;
        this.performanceData.totalConnectionTime += connectionTime;
        this.performanceData.connectionSuccess++;
        
        // Update connection time average
        if (this.performanceData.connectionSuccess > 0) {
            this.performanceData.avgConnectionTime = 
                this.performanceData.totalConnectionTime / this.performanceData.connectionSuccess;
        }
        
        // Update metrics display
        this.updatePerformanceMetrics();
        
        // Handle successful connection
        if (response && (response.status === 'success' || response.success === true)) {
            console.log(`Successfully connected to ${address}`);
            this.logOperation('Connection', `Connected to ${address}`, 'success');
            this.showToast(`Connected to ${address}`, 'success');
            
            // Update UI to show connected state
            this.updateDeviceConnectionState(address, 'connected');
            
            // Update connected devices list
            this.addConnectedDevice(address, response.device || { address });
            
            return response;
        } else {
            // Handle error in connection response
            const errorMessage = response?.error || response?.message || 'Connection failed';
            throw new Error(errorMessage);
        }
    } catch (error) {
        console.error(`Connection error for ${address}:`, error);
        
        // Log the error
        this.logOperation('Connection', `Connection failed for ${address}: ${error.message}`, 'error');
        this.showToast(`Connection failed: ${error.message}`, 'error');
        
        // Update UI to show disconnected state
        this.updateDeviceConnectionState(address, 'disconnected');
        
        throw error;
    }
};

/**
 * Disconnect from a BLE device
 * @param {string} address - Device address
 * @returns {Promise<Object>} Disconnection result
 */
BleDashboardController.prototype.disconnectFromDevice = async function(address) {
    if (!address) {
        console.error('Invalid device address for disconnection');
        this.showToast('Invalid device address', 'error');
        return Promise.reject(new Error('Invalid device address'));
    }
    
    console.log(`Disconnecting from device: ${address}`);
    this.logOperation('Connection', `Disconnecting from device: ${address}`);
    this.showToast(`Disconnecting from ${address}...`, 'info');
    
    try {
        // Update UI to show disconnecting state
        this.updateDeviceConnectionState(address, 'disconnecting');
        
        // Make the disconnection request
        const response = await this.apiClient.request('/api/ble/device/disconnect', {
            method: 'POST',
            body: {
                address: address
            }
        });
        
        // Handle successful disconnection
        if (response && (response.status === 'success' || response.success === true)) {
            console.log(`Successfully disconnected from ${address}`);
            this.logOperation('Connection', `Disconnected from ${address}`, 'success');
            this.showToast(`Disconnected from ${address}`, 'success');
            
            // Update UI to show disconnected state
            this.updateDeviceConnectionState(address, 'disconnected');
            
            // Remove from connected devices list
            this.removeConnectedDevice(address);
            
            return response;
        } else {
            // Handle error in disconnection response
            const errorMessage = response?.error || response?.message || 'Disconnection failed';
            throw new Error(errorMessage);
        }
    } catch (error) {
        console.error(`Disconnection error for ${address}:`, error);
        
        // Log the error
        this.logOperation('Connection', `Disconnection failed for ${address}: ${error.message}`, 'error');
        this.showToast(`Disconnection failed: ${error.message}`, 'error');
        
        // Force UI update to disconnected state in case of API error
        this.updateDeviceConnectionState(address, 'disconnected');
        this.removeConnectedDevice(address);
        
        throw error;
    }
};

/**
 * Update the scanning state in the UI
 * @param {boolean} isScanning - Whether we're currently scanning
 */
BleDashboardController.prototype.updateScanningState = function(isScanning) {
    // Set the internal state
    this.isScanning = isScanning;
    
    // Update UI elements
    const scanBtn = document.getElementById('scan-btn');
    const stopScanBtn = document.getElementById('stop-scan-btn');
    const scanStatus = document.getElementById('scan-status');
    const scanProgressBar = document.getElementById('scan-progress-bar');
    const scanTimeRemaining = document.getElementById('scan-time-remaining');
    
    // Update button visibility
    if (scanBtn) scanBtn.classList.toggle('hidden', isScanning);
    if (stopScanBtn) stopScanBtn.classList.toggle('hidden', !isScanning);
    
    // Show/hide scan status
    if (scanStatus) scanStatus.classList.toggle('hidden', !isScanning);
    
    // Animate progress bar if scanning
    if (isScanning && scanProgressBar) {
        scanProgressBar.style.width = '0%';
        
        // Get scan time
        const scanTimeInput = document.getElementById('scan-time');
        const scanTime = parseInt(scanTimeInput?.value || '5', 10);
        const totalTime = scanTime * 1000; // Convert to ms
        
        // Animate progress
        const startTime = Date.now();
        const updateProgress = () => {
            if (!this.isScanning) return;
            
            const elapsed = Date.now() - startTime;
            const remaining = Math.max(0, totalTime - elapsed);
            const progress = Math.min(100, (elapsed / totalTime) * 100);
            
            if (scanProgressBar) scanProgressBar.style.width = `${progress}%`;
            
            if (scanTimeRemaining) {
                scanTimeRemaining.textContent = `${Math.ceil(remaining / 1000)}s`;
            }
            
            if (progress < 100 && this.isScanning) {
                requestAnimationFrame(updateProgress);
            }
        };
        
        updateProgress();
    }
};

/**
 * Log an operation
 * @param {string} category - Category of the operation
 * @param {string} message - Message to log
 * @param {string} level - Log level (info, error, success, warning)
 */
BleDashboardController.prototype.logOperation = function(category, message, level = 'info') {
    if (this.logger) {
        this.logger.log({ category, message, level });
    } else {
        console.log(`[${category}] (${level}) ${message}`);
    }
};

/**
 * Update performance metrics display
 */
BleDashboardController.prototype.updatePerformanceMetrics = function() {
    // Update scan metrics
    const scanSuccessRate = document.getElementById('scan-success-rate');
    const scanSuccessBar = document.getElementById('scan-success-bar');
    
    if (scanSuccessRate && scanSuccessBar) {
        const scanSuccessRateValue = Math.round((this.performanceData.scanSuccess / this.performanceData.scanAttempts) * 100);
        scanSuccessRate.textContent = `${scanSuccessRateValue}%`;
        scanSuccessBar.style.width = `${scanSuccessRateValue}%`;
    }
    
    // Update connection metrics
    const connectionSuccessRate = document.getElementById('connection-success-rate');
    const connectionSuccessBar = document.getElementById('connection-success-bar');
    const avgConnectionTime = document.getElementById('avg-connection-time');
    const uptime = document.getElementById('uptime');
    
    if (connectionSuccessRate && connectionSuccessBar) {
        const connectionSuccessRateValue = Math.round((this.performanceData.connectionSuccess / this.performanceData.connectionAttempts) * 100);
        connectionSuccessRate.textContent = `${connectionSuccessRateValue}%`;
        connectionSuccessBar.style.width = `${connectionSuccessRateValue}%`;
    }
    
    if (avgConnectionTime) {
        avgConnectionTime.textContent = `${this.performanceData.avgConnectionTime}ms`;
    }
    
    if (uptime) {
        uptime.textContent = `${Math.round((Date.now() - this.initTime) / 60000)}m`;
    }
    
    // Update performance chart
    this.updatePerformanceChart();
};

/**
 * Update the performance chart
 */
BleDashboardController.prototype.updatePerformanceChart = function() {
    if (!this.performanceChart) return;
    
    // Get chart data
    const chartData = {
        labels: Array.from({ length: 10 }, (_, i) => i),
        datasets: [{
            label: 'Scan Success Rate',
            data: Array.from({ length: 10 }, (_, i) => Math.random() * 100),
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
        }]
    };
    
    // Update chart
    this.performanceChart.data = chartData;
    this.performanceChart.update();
};

import { BleUI } from '/static/js/pages/ble/ble-ui.js';

/**
 * Run BLE system diagnostics
 * @returns {Promise<Object>} Diagnostic results
 */
export async function runDiagnostics() {
    BleUI.showToast('Running BLE diagnostics...', 'info');
    
    try {
        // Use the new health diagnostics endpoint
        const response = await fetch('/api/ble/health/diagnostics', {
            method: 'POST'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Diagnostics failed');
        }
        
        const result = await response.json();
        
        // Display diagnostics in UI
        const diagContent = document.createElement('div');
        diagContent.className = 'bg-gray-800 p-4 rounded-lg';
        
        const statusClass = result.status === 'ok' ? 'text-green-400' : 'text-red-400';
        
        diagContent.innerHTML = `
            <div class="mb-3">
                <span class="font-bold">Status:</span> 
                <span class="${statusClass}">${result.status.toUpperCase()}</span>
            </div>
            <div class="mb-3">
                <span class="font-bold">Adapter:</span> 
                <span>${result.adapter_status || "Unknown"}</span>
            </div>
            <div class="mb-3">
                <span class="font-bold">Bluetooth Stack:</span> 
                <span>${result.stack_status || "Unknown"}</span>
            </div>
            <div class="mb-3">
                <span class="font-bold">Issues Found:</span> 
                <span>${result.issues_found || 0}</span>
            </div>
        `;
        
        // Add recommendations if available
        if (result.recommendations && result.recommendations.length > 0) {
            const recList = document.createElement('ul');
            recList.className = 'list-disc pl-5 mt-2 text-yellow-400';
            
            result.recommendations.forEach(rec => {
                const item = document.createElement('li');
                item.textContent = rec;
                recList.appendChild(item);
            });
            
            const recTitle = document.createElement('div');
            recTitle.className = 'font-bold mt-3 mb-2';
            recTitle.textContent = 'Recommendations:';
            
            diagContent.appendChild(recTitle);
            diagContent.appendChild(recList);
        }
        
        // Display in modal
        BleUI.showModal('BLE Diagnostics Results', diagContent);
        
        return result;
    } catch (error) {
        console.error('Diagnostics error:', error);
        BleUI.showToast(`Diagnostics failed: ${error.message}`, 'error');
        return null;
    }
}

/**
 * BLE Debug & Development Tools
 * Provides comprehensive debugging and development utilities for the BLE Dashboard
 */
export class BleDebug {
    constructor() {
        this.diagRunning = false;
        this.mockDetected = false;
        this.apiRequestTemplates = {
            "/api/ble/adapter/select": { id: "00:11:22:33:44:55" },
            "/api/ble/scan/start": { scan_time: 5, active: true },
            "/api/ble/device/connect": { address: "00:11:22:33:44:55" }
        };
        
        // Element references
        this.elements = {};
    }

    /**
     * Initialize the debug module
     */
    async initialize() {
        console.log('Initializing BLE Debug module');
        
        try {
            // Initialize DOM references
            this.initDomReferences();
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Detect environment
            await this.detectEnvironment();
            
            return true;
        } catch (error) {
            console.error('Error initializing BLE Debug module:', error);
            return false;
        }
    }

    /**
     * Initialize DOM references
     */
    initDomReferences() {
        this.elements = {
            // Main container
            debugCard: document.getElementById('ble-debug-card'),
            
            // Diagnostic elements
            runDiagnosticsBtn: document.getElementById('run-diagnostics-btn'),
            diagnosticsResults: document.getElementById('diagnostics-results'),
            saveDiagnosticsBtn: document.getElementById('save-diagnostics-btn'),
            
            // API testing elements
            apiEndpointSelect: document.getElementById('api-endpoint-select'),
            testApiBtn: document.getElementById('test-api-btn'),
            viewRequestBtn: document.getElementById('view-request-btn'),
            apiRequestEditor: document.getElementById('api-request-editor'),
            apiRequestBody: document.getElementById('api-request-body'),
            apiResponse: document.getElementById('api-response'),
            
            // Quick action buttons
            resetBleStateBtn: document.getElementById('reset-ble-state-btn'),
            checkAdapterBtn: document.getElementById('check-adapter-btn'),
            testWebsocketBtn: document.getElementById('test-websocket-btn'),
            clearCacheBtn: document.getElementById('clear-cache-btn'),
            
            // Environment info
            debugBrowserInfo: document.getElementById('debug-browser-info'),
            debugApiStatus: document.getElementById('debug-api-status'),
            debugWebsocketStatus: document.getElementById('debug-websocket-status'),
            debugMockStatus: document.getElementById('debug-mock-status'),
            
            // Additional actions
            openDebugConsoleBtn: document.getElementById('open-debug-console-btn')
        };
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Check if elements exist before adding listeners
        if (this.elements.runDiagnosticsBtn) {
            this.elements.runDiagnosticsBtn.addEventListener('click', () => this.runDiagnostics());
        }
        
        if (this.elements.saveDiagnosticsBtn) {
            this.elements.saveDiagnosticsBtn.addEventListener('click', () => this.saveDiagnostics());
        }
        
        if (this.elements.testApiBtn) {
            this.elements.testApiBtn.addEventListener('click', () => this.testApiEndpoint());
        }
        
        if (this.elements.viewRequestBtn) {
            this.elements.viewRequestBtn.addEventListener('click', () => this.toggleRequestEditor());
        }
        
        if (this.elements.apiEndpointSelect) {
            this.elements.apiEndpointSelect.addEventListener('change', () => this.updateRequestBody());
        }
        
        if (this.elements.resetBleStateBtn) {
            this.elements.resetBleStateBtn.addEventListener('click', () => this.resetBleState());
        }
        
        if (this.elements.checkAdapterBtn) {
            this.elements.checkAdapterBtn.addEventListener('click', () => this.checkAdapter());
        }
        
        if (this.elements.testWebsocketBtn) {
            this.elements.testWebsocketBtn.addEventListener('click', () => this.testWebSocket());
        }
        
        if (this.elements.clearCacheBtn) {
            this.elements.clearCacheBtn.addEventListener('click', () => this.clearCache());
        }
        
        if (this.elements.openDebugConsoleBtn) {
            this.elements.openDebugConsoleBtn.addEventListener('click', () => this.openDebugConsole());
        }
    }

    /**
     * Detect the current environment
     */
    async detectEnvironment() {
        // Detect browser
        if (this.elements.debugBrowserInfo) {
            const browser = this.detectBrowser();
            this.elements.debugBrowserInfo.textContent = browser;
        }
        
        // Check API status
        if (this.elements.debugApiStatus) {
            try {
                const response = await fetch('/api/ble/adapter/adapters').catch(() => null);
                const apiStatus = response?.ok ? 'Available' : 'Unavailable';
                this.elements.debugApiStatus.textContent = apiStatus;
                this.elements.debugApiStatus.classList.add(response?.ok ? 'text-green-400' : 'text-red-400');
            } catch (error) {
                this.elements.debugApiStatus.textContent = 'Error';
                this.elements.debugApiStatus.classList.add('text-red-400');
            }
        }
        
        // Check WebSocket status
        if (this.elements.debugWebsocketStatus) {
            const wsStatus = window.bleWebSocket?.isConnected ? 'Connected' : 'Disconnected';
            this.elements.debugWebsocketStatus.textContent = wsStatus;
            this.elements.debugWebsocketStatus.classList.add(window.bleWebSocket?.isConnected ? 'text-green-400' : 'text-red-400');
        }
        
        // Check for mock API
        if (this.elements.debugMockStatus) {
            // Check if the mock API handler is installed by testing if fetch is overridden
            this.mockDetected = window.fetch.toString().includes('handleApiRequest');
            this.elements.debugMockStatus.textContent = this.mockDetected ? 'Active' : 'Inactive';
            this.elements.debugMockStatus.classList.add(this.mockDetected ? 'text-yellow-400' : 'text-gray-400');
        }
    }

    /**
     * Detect browser name and version
     */
    detectBrowser() {
        const userAgent = navigator.userAgent;
        
        if (userAgent.includes('Chrome')) {
            return `Chrome ${userAgent.match(/Chrome\/(\d+)/)[1]}`;
        } else if (userAgent.includes('Firefox')) {
            return `Firefox ${userAgent.match(/Firefox\/(\d+)/)[1]}`;
        } else if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) {
            return `Safari ${userAgent.match(/Version\/(\d+)/)[1]}`;
        } else if (userAgent.includes('Edge') || userAgent.includes('Edg')) {
            return `Edge ${userAgent.match(/Edge\/(\d+)|Edg\/(\d+)/)[1] || userAgent.match(/Edge\/(\d+)|Edg\/(\d+)/)[2]}`;
        } else {
            return 'Unknown Browser';
        }
    }

    /**
     * Run diagnostics
     */
    async runDiagnostics() {
        if (this.diagRunning) return;
        
        this.diagRunning = true;
        this.updateDiagnosticsButton(true);
        
        try {
            // Show results container
            if (this.elements.diagnosticsResults) {
                this.elements.diagnosticsResults.classList.remove('hidden');
                this.elements.diagnosticsResults.textContent = 'Running diagnostics...';
            }
            
            // Run comprehensive diagnostics
            const diagnosticResults = await this.collectDiagnostics();
            
            // Format and display results
            const formattedResults = JSON.stringify(diagnosticResults, null, 2);
            if (this.elements.diagnosticsResults) {
                this.elements.diagnosticsResults.innerHTML = `<pre class="text-green-400">${formattedResults}</pre>`;
                
                // Add copy button
                const copyBtn = document.createElement('button');
                copyBtn.className = 'ble-btn ble-btn-tertiary ble-btn-xs absolute top-2 right-2';
                copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
                copyBtn.addEventListener('click', () => {
                    navigator.clipboard.writeText(formattedResults);
                    this.showToast('Diagnostic results copied to clipboard!');
                });
                
                this.elements.diagnosticsResults.style.position = 'relative';
                this.elements.diagnosticsResults.appendChild(copyBtn);
            }
            
            // Update environment display
            await this.detectEnvironment();
            
            // Log diagnostics to console as well
            console.info('BLE Diagnostics completed:', diagnosticResults);
            
            // Save to window for easy access in console
            window.bleDiagnostics = diagnosticResults;
            
            this.showToast('Diagnostics completed successfully');
            
            return diagnosticResults;
        } catch (error) {
            console.error('Error running diagnostics:', error);
            
            if (this.elements.diagnosticsResults) {
                this.elements.diagnosticsResults.innerHTML = `
                    <div class="text-red-400">
                        Error running diagnostics: ${error.message}
                    </div>
                `;
            }
            
            this.showToast('Error running diagnostics', 'error');
        } finally {
            this.diagRunning = false;
            this.updateDiagnosticsButton(false);
        }
    }

    /**
     * Collect diagnostic information
     */
    async collectDiagnostics() {
        const results = {
            timestamp: new Date().toISOString(),
            environment: {
                browser: this.detectBrowser(),
                userAgent: navigator.userAgent,
                windowSize: `${window.innerWidth}x${window.innerHeight}`,
                url: window.location.href,
                mocked: this.mockDetected
            },
            bleState: await this.getBleState(),
            adapters: await this.getAdapterInfo(),
            devices: await this.getDevicesInfo(),
            domChecks: this.checkRequiredElements(),
            apiStatus: await this.testApiEndpoints(),
            wsStatus: this.getWebSocketStatus(),
            localStorage: this.getLocalStorageItems()
        };
        
        return results;
    }

    /**
     * Get current BLE state
     */
    async getBleState() {
        const state = {
            appState: window.BLE_APP_STATE || 'Not available',
            bleAdapter: window.bleAdapter ? {
                initialized: !!window.bleAdapter.initialized,
                selectedAdapterId: window.bleAdapter.selectedAdapterId || null,
                adapterCount: window.bleAdapter.adapters?.length || 0
            } : 'Not available',
            bleScanner: window.bleScanner ? {
                initialized: !!window.bleScanner.initialized,
                scanning: !!window.bleScanner.scanning
            } : 'Not available',
            bleEvents: window.BleEvents ? 'Available' : 'Not available'
        };
        
        return state;
    }

    /**
     * Get adapter information
     */
    async getAdapterInfo() {
        try {
            if (window.bleAdapter) {
                return {
                    current: window.bleAdapter.selectedAdapterId || 'None',
                    all: window.bleAdapter.adapters || []
                };
            } else {
                const response = await fetch('/api/ble/adapter-info').catch(() => null);
                if (response?.ok) {
                    return await response.json();
                }
            }
        } catch (error) {
            return { error: error.message };
        }
        
        return 'Not available';
    }

    /**
     * Get devices information
     */
    async getDevicesInfo() {
        try {
            const devices = [];
            
            // Check if window.bleScanner.devices exists
            if (window.bleScanner && window.bleScanner.devices) {
                return window.bleScanner.devices;
            }
            
            // Try to get from deviceCache
            if (window.deviceCache) {
                return window.deviceCache.getAll();
            }
            
            // Try to get from DOM
            const devicesList = document.getElementById('devices-list');
            if (devicesList) {
                const deviceElements = devicesList.querySelectorAll('[data-address]');
                deviceElements.forEach(element => {
                    devices.push({
                        address: element.dataset.address,
                        name: element.querySelector('.device-name')?.textContent || 'Unknown',
                        rssi: element.querySelector('.device-rssi')?.textContent || 'Unknown'
                    });
                });
            }
            
            return devices;
        } catch (error) {
            return { error: error.message };
        }
    }

    /**
     * Check required DOM elements
     */
    checkRequiredElements() {
        const requiredElements = [
            // Adapter elements
            'adapter-info-content', 'adapter-name', 'adapter-address', 
            'adapter-type', 'adapter-status-text', 'refresh-adapter-btn',
            
            // Scanner elements
            'scan-container', 'scan-btn', 'devices-list',
            
            // Device elements
            'device-info-content', 'battery-container',
            
            // Services elements
            'services-list', 
            
            // Log elements
            'ble-log-container'
        ];
        
        const results = {
            missingElements: [],
            foundElements: []
        };
        
        requiredElements.forEach(id => {
            if (document.getElementById(id)) {
                results.foundElements.push(id);
            } else {
                results.missingElements.push(id);
            }
        });
        
        return results;
    }

    /**
     * Test API endpoints
     */
    async testApiEndpoints() {
        const endpoints = [
            '/api/ble/adapter/adapters',
            '/api/ble/adapter/info',
            '/api/ble/adapter/health'
        ];
        
        const results = {};
        
        for (const endpoint of endpoints) {
            try {
                const startTime = performance.now();
                const response = await fetch(endpoint);
                const endTime = performance.now();
                
                results[endpoint] = {
                    status: response.status,
                    ok: response.ok,
                    time: Math.round(endTime - startTime) + 'ms'
                };
                
                // Only try to parse JSON if response is OK
                if (response.ok) {
                    try {
                        const data = await response.json();
                        // Just record that we got valid JSON, don't include whole payload
                        results[endpoint].hasData = !!data;
                    } catch (e) {
                        results[endpoint].jsonError = e.message;
                    }
                }
            } catch (error) {
                results[endpoint] = {
                    error: error.message
                };
            }
        }
        
        return results;
    }

    /**
     * Get WebSocket status
     */
    getWebSocketStatus() {
        if (!window.bleWebSocket) {
            return 'Not available';
        }
        
        const wsState = {
            isConnected: window.bleWebSocket.isConnected,
            readyState: window.bleWebSocket.socket ? 
                ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][window.bleWebSocket.socket.readyState] : 'Unknown'
        };
        
        return wsState;
    }

    /**
     * Get localStorage items related to BLE
     */
    getLocalStorageItems() {
        const bleItems = {};
        
        try {
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key.toLowerCase().includes('ble')) {
                    try {
                        bleItems[key] = localStorage.getItem(key);
                    } catch (e) {
                        bleItems[key] = 'Error reading value';
                    }
                }
            }
        } catch (error) {
            return { error: error.message };
        }
        
        return bleItems;
    }

    /**
     * Save diagnostics to file
     */
    async saveDiagnostics() {
        try {
            // Run diagnostics if we haven't already
            if (!window.bleDiagnostics) {
                await this.runDiagnostics();
            }
            
            const diagnosticData = window.bleDiagnostics;
            const jsonString = JSON.stringify(diagnosticData, null, 2);
            const blob = new Blob([jsonString], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const timestamp = new Date().toISOString().replace(/:/g, '-').substring(0, 19);
            const filename = `ble-diagnostics-${timestamp}.json`;
            
            // Create link and trigger download
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            // Cleanup
            URL.revokeObjectURL(url);
            
            this.showToast('Diagnostics saved to file');
        } catch (error) {
            console.error('Error saving diagnostics:', error);
            this.showToast('Error saving diagnostics', 'error');
        }
    }

    /**
     * Test API endpoint
     */
    async testApiEndpoint() {
        const endpoint = this.elements.apiEndpointSelect.value;
        
        if (!endpoint) {
            this.showToast('Please select an endpoint', 'error');
            return;
        }
        
        try {
            // Show response container
            this.elements.apiResponse.classList.remove('hidden');
            this.elements.apiResponse.innerHTML = '<div class="text-blue-400">Sending request...</div>';
            
            // Prepare request
            const method = endpoint.includes('select') || 
                          endpoint.includes('start') || 
                          endpoint.includes('connect') || 
                          endpoint.includes('reset') ? 'POST' : 'GET';
            
            let body = null;
            let headers = {
                'Content-Type': 'application/json'
            };
            
            // Parse request body if the editor is visible
            if (!this.elements.apiRequestEditor.classList.contains('hidden') && 
                this.elements.apiRequestBody.value.trim()) {
                try {
                    body = JSON.parse(this.elements.apiRequestBody.value);
                } catch (error) {
                    this.elements.apiResponse.innerHTML = `
                        <div class="text-red-400">
                            Invalid JSON in request body: ${error.message}
                        </div>
                    `;
                    return;
                }
            } else if (this.apiRequestTemplates[endpoint]) {
                // Use template if available
                body = this.apiRequestTemplates[endpoint];
            }
            
            // Build request options
            const options = {
                method,
                headers
            };
            
            if (body && (method === 'POST' || method === 'PUT')) {
                options.body = JSON.stringify(body);
            }
            
            // Make the request
            const startTime = performance.now();
            const response = await fetch(endpoint, options);
            const duration = (performance.now() - startTime).toFixed(1);
            
            // Handle response
            let responseContent = '';
            const statusStyle = response.ok ? 'text-green-400' : 'text-red-400';
            
            try {
                const contentType = response.headers.get('content-type');
                
                if (contentType && contentType.includes('application/json')) {
                    const jsonData = await response.json();
                    responseContent = `<pre class="text-white">${JSON.stringify(jsonData, null, 2)}</pre>`;
                } else {
                    const text = await response.text();
                    responseContent = `<div class="text-white">${text}</div>`;
                }
            } catch (error) {
                responseContent = `<div class="text-red-400">Error parsing response: ${error.message}</div>`;
            }
            
            this.elements.apiResponse.innerHTML = `
                <div class="mb-2 flex justify-between">
                    <span class="${statusStyle}">Status: ${response.status} ${response.statusText}</span>
                    <span class="text-blue-400">${duration}ms</span>
                </div>
                ${responseContent}
            `;
        } catch (error) {
            this.elements.apiResponse.innerHTML = `
                <div class="text-red-400">
                    Request error: ${error.message}
                </div>
            `;
        }
    }

    /**
     * Toggle request editor
     */
    toggleRequestEditor() {
        if (this.elements.apiRequestEditor.classList.contains('hidden')) {
            this.elements.apiRequestEditor.classList.remove('hidden');
            this.elements.viewRequestBtn.innerHTML = '<i class="fas fa-times mr-1"></i> Hide Editor';
            this.updateRequestBody();
        } else {
            this.elements.apiRequestEditor.classList.add('hidden');
            this.elements.viewRequestBtn.innerHTML = '<i class="fas fa-edit mr-1"></i> Edit Body';
        }
    }

    /**
     * Update request body based on selected endpoint
     */
    updateRequestBody() {
        const endpoint = this.elements.apiEndpointSelect.value;
        
        if (endpoint && this.apiRequestTemplates[endpoint]) {
            this.elements.apiRequestBody.value = JSON.stringify(this.apiRequestTemplates[endpoint], null, 2);
        } else {
            this.elements.apiRequestBody.value = '{}';
        }
    }

    /**
     * Reset BLE state
     */
    async resetBleState() {
        try {
            if (window.confirm('This will reset all BLE state. Continue?')) {
                this.showToast('Resetting BLE state...');
                
                // Clear localStorage items related to BLE
                const bleKeys = [];
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    if (key.toLowerCase().includes('ble')) {
                        bleKeys.push(key);
                    }
                }
                
                bleKeys.forEach(key => localStorage.removeItem(key));
                
                // Reset state in memory
                if (window.bleAdapter) {
                    await window.bleAdapter.initialize();
                }
                
                if (window.bleScanner) {
                    await window.bleScanner.initialize();
                }
                
                // Refresh the page for a clean state
                if (window.confirm('BLE state reset. Reload the page to apply changes?')) {
                    window.location.reload();
                } else {
                    this.showToast('BLE state reset. Some components may need a page reload.', 'warn');
                }
            }
        } catch (error) {
            console.error('Error resetting BLE state:', error);
            this.showToast('Error resetting BLE state', 'error');
        }
    }

    /**
     * Check adapter status
     */
    async checkAdapter() {
        try {
            this.showToast('Checking adapter status...');
            
            // Try to get adapter info
            const adapterInfo = await this.getAdapterInfo();
            
            // Create popup with detailed info
            const detailsHTML = `
                <div class="bg-gray-800 p-4 rounded-lg shadow-lg max-w-lg mx-auto">
                    <h3 class="text-xl mb-3 text-white">Adapter Status</h3>
                    <div class="mb-3">
                        <div class="text-sm text-gray-400 mb-1">Selected Adapter:</div>
                        <div class="bg-gray-700 p-2 rounded text-white">${adapterInfo.current || 'None'}</div>
                    </div>
                    <div>
                        <div class="text-sm text-gray-400 mb-1">Available Adapters (${adapterInfo.all?.length || 0}):</div>
                        <div class="bg-gray-700 p-2 rounded text-white overflow-auto max-h-40">
                            <pre>${JSON.stringify(adapterInfo.all, null, 2)}</pre>
                        </div>
                    </div>
                    <div class="mt-3 flex justify-end">
                        <button id="close-adapter-detail" class="ble-btn ble-btn-secondary">Close</button>
                        <button id="refresh-adapter-detail" class="ble-btn ble-btn-primary ml-2">Refresh Adapter</button>
                    </div>
                </div>
            `;
            
            // Create and show modal
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 flex items-center justify-center bg-black bg-opacity-75 z-50';
            modal.innerHTML = detailsHTML;
            document.body.appendChild(modal);
            
            // Add event listeners to buttons
            modal.querySelector('#close-adapter-detail').addEventListener('click', () => {
                document.body.removeChild(modal);
            });
            
            modal.querySelector('#refresh-adapter-detail').addEventListener('click', async () => {
                if (window.bleAdapter && typeof window.bleAdapter.getAdapterInfo === 'function') {
                    try {
                        await window.bleAdapter.getAdapterInfo();
                        document.body.removeChild(modal);
                        this.checkAdapter(); // Reopen with fresh data
                    } catch (error) {
                        console.error('Error refreshing adapter:', error);
                        this.showToast('Error refreshing adapter', 'error');
                    }
                } else {
                    this.showToast('Adapter refresh not available', 'error');
                }
            });
            
        } catch (error) {
            console.error('Error checking adapter status:', error);
            this.showToast('Error checking adapter status', 'error');
        }
    }

    /**
     * Test WebSocket connection
     */
    async testWebSocket() {
        if (!window.bleWebSocket) {
            this.showToast('WebSocket service not available', 'error');
            return;
        }
        
        try {
            this.showToast('Testing WebSocket connection...');
            
            // Create status window
            const statusWindow = document.createElement('div');
            statusWindow.className = 'fixed inset-0 flex items-center justify-center bg-black bg-opacity-75 z-50';
            statusWindow.innerHTML = `
                <div class="bg-gray-800 p-4 rounded-lg shadow-lg max-w-lg mx-auto w-full">
                    <h3 class="text-xl mb-3 text-white">WebSocket Test</h3>
                    
                    <div class="mb-3">
                        <div class="text-sm text-gray-400 mb-1">Status:</div>
                        <div id="ws-test-status" class="bg-gray-700 p-2 rounded text-yellow-400">Testing...</div>
                    </div>
                    
                    <div class="mb-3">
                        <div class="text-sm text-gray-400 mb-1">Messages:</div>
                        <div id="ws-test-messages" class="bg-gray-700 p-2 rounded text-white h-40 overflow-auto"></div>
                    </div>
                    
                    <div class="mb-3 flex items-center">
                        <select id="ws-test-message-type" class="bg-gray-700 border border-gray-600 text-white rounded py-2 px-3 mr-2">
                            <option value="ping">Ping</option>
                            <option value="status">Status Request</option>
                            <option value="custom">Custom</option>
                        </select>
                        <button id="ws-test-send" class="ble-btn ble-btn-primary flex-grow">Send Message</button>
                    </div>
                    
                    <div id="ws-test-custom-container" class="mb-3 hidden">
                        <div class="text-sm text-gray-400 mb-1">Custom Message:</div>
                        <textarea id="ws-test-custom-message" class="w-full bg-gray-700 border border-gray-600 text-white rounded py-2 px-3 text-xs font-mono h-20">{"type": "custom", "message": "Hello from dashboard"}</textarea>
                    </div>
                    
                    <div class="flex justify-end">
                        <button id="ws-test-close" class="ble-btn ble-btn-secondary">Close</button>
                        <button id="ws-test-reconnect" class="ble-btn ble-btn-primary ml-2">Reconnect</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(statusWindow);
            
            // Get elements
            const statusEl = document.getElementById('ws-test-status');
            const messagesEl = document.getElementById('ws-test-messages');
            const messageTypeEl = document.getElementById('ws-test-message-type');
            const sendBtn = document.getElementById('ws-test-send');
            const closeBtn = document.getElementById('ws-test-close');
            const reconnectBtn = document.getElementById('ws-test-reconnect');
            const customContainer = document.getElementById('ws-test-custom-container');
            const customMessageEl = document.getElementById('ws-test-custom-message');
            
            // Update status
            const updateStatus = () => {
                if (!window.bleWebSocket) {
                    statusEl.textContent = 'WebSocket service not available';
                    statusEl.className = 'bg-gray-700 p-2 rounded text-red-400';
                    return;
                }
                
                const isConnected = window.bleWebSocket.isConnected;
                const readyState = window.bleWebSocket.socket ? 
                    ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][window.bleWebSocket.socket.readyState] : 'Unknown';
                
                statusEl.textContent = `${isConnected ? 'Connected' : 'Disconnected'} (${readyState})`;
                statusEl.className = `bg-gray-700 p-2 rounded ${isConnected ? 'text-green-400' : 'text-red-400'}`;
            };
            
            // Add message to log
            const addMessage = (direction, message) => {
                const msgEl = document.createElement('div');
                msgEl.className = `text-xs mb-1 ${direction === 'out' ? 'text-blue-400' : 'text-green-400'}`;
                
                const timestamp = new Date().toISOString().substr(11, 12);
                const icon = direction === 'out' ? '↑' : '↓';
                
                msgEl.textContent = `[${timestamp}] ${icon} ${typeof message === 'string' ? message : JSON.stringify(message)}`;
                messagesEl.appendChild(msgEl);
                messagesEl.scrollTop = messagesEl.scrollHeight;
            };
            
            // Toggle custom message container
            messageTypeEl.addEventListener('change', () => {
                customContainer.classList.toggle('hidden', messageTypeEl.value !== 'custom');
            });
            
            // Send message button
            sendBtn.addEventListener('click', () => {
                if (!window.bleWebSocket || !window.bleWebSocket.socket || window.bleWebSocket.socket.readyState !== WebSocket.OPEN) {
                    addMessage('system', 'Cannot send message: WebSocket not connected');
                    return;
                }
                
                try {
                    let message;
                    
                    switch (messageTypeEl.value) {
                        case 'ping':
                            message = { type: 'ping', timestamp: Date.now() };
                            break;
                        case 'status':
                            message = { type: 'status_request' };
                            break;
                        case 'custom':
                            message = JSON.parse(customMessageEl.value);
                            break;
                        default:
                            message = { type: 'unknown', value: messageTypeEl.value };
                            break;
                    }
                    
                    window.bleWebSocket.socket.send(JSON.stringify(message));
                    addMessage('out', message);
                } catch (error) {
                    addMessage('system', `Error sending message: ${error.message}`);
                }
            });
            
            // Set up WebSocket message handler
            const originalOnMessage = window.bleWebSocket.socket.onmessage;
            
            window.bleWebSocket.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    addMessage('in', data);
                } catch (e) {
                    addMessage('in', event.data);
                }
                
                // Call original handler
                if (originalOnMessage) {
                    originalOnMessage(event);
                }
            };
            
            // Close button
            closeBtn.addEventListener('click', () => {
                // Restore original message handler
                if (window.bleWebSocket && window.bleWebSocket.socket) {
                    window.bleWebSocket.socket.onmessage = originalOnMessage;
                }
                
                document.body.removeChild(statusWindow);
            });
            
            // Reconnect button
            reconnectBtn.addEventListener('click', async () => {
                if (!window.bleWebSocket) {
                    addMessage('system', 'WebSocket service not available');
                    return;
                }
                
                try {
                    addMessage('system', 'Reconnecting WebSocket...');
                    
                    // Close existing connection
                    if (window.bleWebSocket.socket) {
                        window.bleWebSocket.socket.close();
                    }
                    
                    // Reconnect
                    if (typeof window.bleWebSocket.connect === 'function') {
                        await window.bleWebSocket.connect();
                        
                        // Re-attach message handler
                        window.bleWebSocket.socket.onmessage = (event) => {
                            try {
                                const data = JSON.parse(event.data);
                                addMessage('in', data);
                            } catch (e) {
                                addMessage('in', event.data);
                            }
                            
                            // Call original handler
                            if (originalOnMessage) {
                                originalOnMessage(event);
                            }
                        };
                        
                        addMessage('system', 'WebSocket reconnected');
                    } else {
                        addMessage('system', 'Reconnect method not available');
                    }
                    
                    updateStatus();
                } catch (error) {
                    addMessage('system', `Error reconnecting WebSocket: ${error.message}`);
                }
            });
            
            // Initial status update
            updateStatus();
            addMessage('system', 'WebSocket test started');
            
        } catch (error) {
            console.error('Error testing WebSocket:', error);
            this.showToast('Error testing WebSocket', 'error');
        }
    }

    /**
     * Clear device and localStorage cache
     */
    clearCache() {
        try {
            if (window.confirm('This will clear all cached devices and settings. Continue?')) {
                // Clear BLE-related localStorage items
                const bleKeys = [];
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    if (key.toLowerCase().includes('ble') || key.toLowerCase().includes('device')) {
                        bleKeys.push(key);
                    }
                }
                
                bleKeys.forEach(key => {
                    localStorage.removeItem(key);
                    console.log(`Removed from localStorage: ${key}`);
                });
                
                // Clear device cache if it exists
                if (window.deviceCache && typeof window.deviceCache.clear === 'function') {
                    window.deviceCache.clear();
                }
                
                // Clear devices list UI
                const devicesList = document.getElementById('devices-list');
                if (devicesList) {
                    devicesList.innerHTML = `<div class="text-gray-500">No devices found. Click the scan button to start scanning.</div>`;
                }
                
                this.showToast('Cache cleared successfully');
            }
        } catch (error) {
            console.error('Error clearing cache:', error);
            this.showToast('Error clearing cache', 'error');
        }
    }

    /**
     * Open interactive debug console
     */
    openDebugConsole() {
        try {
            // Create console window
            const consoleWindow = document.createElement('div');
            consoleWindow.className = 'fixed inset-0 flex items-center justify-center bg-black bg-opacity-75 z-50';
            consoleWindow.innerHTML = `
                <div class="bg-gray-800 p-4 rounded-lg shadow-lg max-w-xl mx-auto w-full h-3/4 flex flex-col">
                    <div class="flex justify-between items-center mb-3">
                        <h3 class="text-xl text-white">BLE Debug Console</h3>
                        <button id="debug-console-close" class="text-gray-400 hover:text-white">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <div id="debug-console-output" class="bg-gray-900 p-2 rounded text-green-400 font-mono text-sm flex-grow overflow-auto mb-3"></div>
                    
                    <div class="flex">
                        <div class="text-green-400 mr-2">></div>
                        <input type="text" id="debug-console-input" class="bg-gray-900 text-green-400 font-mono text-sm flex-grow border-none" placeholder="Enter command (type 'help' for available commands)">
                    </div>
                </div>
            `;
            
            document.body.appendChild(consoleWindow);
            
            // Get elements
            const outputEl = document.getElementById('debug-console-output');
            const inputEl = document.getElementById('debug-console-input');
            const closeBtn = document.getElementById('debug-console-close');
            
            // Focus input
            inputEl.focus();
            
            // Command history
            const commandHistory = [];
            let historyIndex = -1;
            
            // Available commands
            const commands = {
                help: {
                    desc: 'Show available commands',
                    fn: () => {
                        writeOutput('Available commands:', 'white');
                        Object.entries(commands).forEach(([name, cmd]) => {
                            writeOutput(`  ${name} - ${cmd.desc}`, 'gray');
                        });
                    }
                },
                clear: {
                    desc: 'Clear console output',
                    fn: () => {
                        outputEl.innerHTML = '';
                    }
                },
                adapter: {
                    desc: 'Show adapter information',
                    fn: async () => {
                        writeOutput('Getting adapter info...', 'yellow');
                        try {
                            const info = await this.getAdapterInfo();
                            writeOutput(JSON.stringify(info, null, 2), 'cyan');
                        } catch (error) {
                            writeOutput(`Error: ${error.message}`, 'red');
                        }
                    }
                },
                devices: {
                    desc: 'Show cached devices',
                    fn: async () => {
                        writeOutput('Getting devices...', 'yellow');
                        try {
                            const devices = await this.getDevicesInfo();
                            writeOutput(JSON.stringify(devices, null, 2), 'cyan');
                        } catch (error) {
                            writeOutput(`Error: ${error.message}`, 'red');
                        }
                    }
                },
                state: {
                    desc: 'Show current BLE state',
                    fn: async () => {
                        writeOutput('Getting BLE state...', 'yellow');
                        try {
                            const state = await this.getBleState();
                            writeOutput(JSON.stringify(state, null, 2), 'cyan');
                        } catch (error) {
                            writeOutput(`Error: ${error.message}`, 'red');
                        }
                    }
                },
                ws: {
                    desc: 'Show WebSocket status',
                    fn: () => {
                        const status = this.getWebSocketStatus();
                        writeOutput(JSON.stringify(status, null, 2), 'cyan');
                    }
                },
                scan: {
                    desc: 'Start a BLE scan',
                    fn: async () => {
                        if (!window.bleScanner) {
                            writeOutput('BLE Scanner not available', 'red');
                            return;
                        }
                        
                        writeOutput('Starting scan...', 'yellow');
                        try {
                            if (typeof window.bleScanner.startScan === 'function') {
                                const results = await window.bleScanner.startScan(5, true);
                                writeOutput(`Scan complete. Found ${results?.length || 0} devices.`, 'green');
                            } else {
                                writeOutput('Start scan method not available', 'red');
                            }
                        } catch (error) {
                            writeOutput(`Error: ${error.message}`, 'red');
                        }
                    }
                },
                reset: {
                    desc: 'Reset adapter',
                    fn: async () => {
                        if (!window.bleAdapter) {
                            writeOutput('BLE Adapter not available', 'red');
                            return;
                        }
                        
                        writeOutput('Resetting adapter...', 'yellow');
                        try {
                            if (typeof window.bleAdapter.resetAdapter === 'function') {
                                await window.bleAdapter.resetAdapter();
                                writeOutput('Adapter reset complete', 'green');
                            } else {
                                writeOutput('Reset adapter method not available', 'red');
                            }
                        } catch (error) {
                            writeOutput(`Error: ${error.message}`, 'red');
                        }
                    }
                }
            };
            
            // Write output to console
            const writeOutput = (text, color = 'green') => {
                const line = document.createElement('div');
                line.className = `mb-1 ${
                    color === 'red' ? 'text-red-400' : 
                    color === 'green' ? 'text-green-400' : 
                    color === 'yellow' ? 'text-yellow-400' : 
                    color === 'cyan' ? 'text-blue-400' : 
                    color === 'white' ? 'text-white' : 
                    color === 'gray' ? 'text-gray-400' : 
                    'text-green-400' // Default case
                }`;
                line.textContent = text;
                outputEl.appendChild(line);
                outputEl.scrollTop = outputEl.scrollHeight;
            };
            
            // Process command
            const processCommand = async (command) => {
                writeOutput(`> ${command}`);
                
                // Add to history
                commandHistory.push(command);
                historyIndex = commandHistory.length;
                
                // Split command and args
                const [cmd, ...args] = command.trim().split(/\s+/);
                
                if (commands[cmd]) {
                    try {
                        await commands[cmd].fn(...args);
                    } catch (error) {
                        writeOutput(`Error executing command: ${error.message}`, 'red');
                    }
                } else if (cmd === '') {
                    // Ignore empty command
                } else {
                    writeOutput(`Unknown command: ${cmd}. Type 'help' for available commands.`, 'red');
                }
            };
            
            // Handle input
            inputEl.addEventListener('keydown', async (e) => {
                if (e.key === 'Enter') {
                    const command = inputEl.value;
                    inputEl.value = '';
                    await processCommand(command);
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    if (historyIndex > 0) {
                        historyIndex--;
                        inputEl.value = commandHistory[historyIndex];
                    }
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    if (historyIndex < commandHistory.length - 1) {
                        historyIndex++;
                        inputEl.value = commandHistory[historyIndex];
                    } else {
                        historyIndex = commandHistory.length;
                        inputEl.value = '';
                    }
                }
            });
            
            // Close button
            closeBtn.addEventListener('click', () => {
                document.body.removeChild(consoleWindow);
            });
            
            // Initial welcome message
            writeOutput('BLE Debug Console', 'white');
            writeOutput('Type "help" for a list of commands', 'gray');
            writeOutput('');
            
        } catch (error) {
            console.error('Error opening debug console:', error);
            this.showToast('Error opening debug console', 'error');
        }
    }

    /**
     * Update the diagnostics button state
     */
    updateDiagnosticsButton(running) {
        if (this.elements.runDiagnosticsBtn) {
            if (running) {
                this.elements.runDiagnosticsBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Running Diagnostics...';
                this.elements.runDiagnosticsBtn.disabled = true;
            } else {
                this.elements.runDiagnosticsBtn.innerHTML = '<i class="fas fa-stethoscope mr-1"></i> Run BLE Diagnostics';
                this.elements.runDiagnosticsBtn.disabled = false;
            }
        }
    }

    /**
     * Show a toast notification
     */
    showToast(message, type = 'success') {
        if (window.BleUI && typeof window.BleUI.showToast === 'function') {
            window.BleUI.showToast(message, type);
            return;
        }
        
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 left-1/2 transform -translate-x-1/2 px-4 py-2 rounded-lg shadow-lg z-50 ${
            type === 'error' ? 'bg-red-900 text-white' : 
            type === 'warn' ? 'bg-yellow-900 text-white' : 
            'bg-green-900 text-white'
        }`;
        toast.textContent = message;
        
        // Add to body
        document.body.appendChild(toast);
        
        // Remove after timeout
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 3000);
    }
}

// Create singleton instance
export const bleDebug = new BleDebug();

// Add to window for console access
window.bleDebug = bleDebug;

// Export singleton
export default bleDebug;
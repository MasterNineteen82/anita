/**
 * Mock API handler for BLE functionality
 * Provides fallbacks when backend services are unavailable
 */
export class BleApiMock {
    constructor() {
        // Check if mocking should be disabled
        if (window.DISABLE_BLE_MOCK === true) {
            console.log('BLE API Mock disabled by global flag');
            return; // Exit constructor early, don't set up mock data or interceptor
        }
        
        this.mockDevices = [
            {
                address: "00:11:22:33:44:55",
                name: "Mock Heart Rate Monitor",
                rssi: -67,
                type: "public",
                connectable: true,
                services: ["0000180d-0000-1000-8000-00805f9b34fb"]
            },
            {
                address: "AA:BB:CC:DD:EE:FF",
                name: "Mock Blood Pressure Monitor",
                rssi: -72,
                type: "public",
                connectable: true,
                services: ["00001810-0000-1000-8000-00805f9b34fb"]
            },
            {
                address: "12:34:56:78:90:AB",
                name: "Mock Thermometer",
                rssi: -80,
                type: "public",
                connectable: true,
                services: ["00001809-0000-1000-8000-00805f9b34fb"]
            }
        ];
        
        this.mockAdapters = [
            {
                address: "USB\\VID_0489&PID_E0E2&MI_00\\7&219397DC&0&0000",
                name: "Intel Wireless Bluetooth",
                type: "usb",
                available: true,
                manufacturer: "Intel Corporation",
                platform: "Windows"
            },
            {
                address: "USB\\VID_0BDA&PID_A728\\00E04C239987",
                name: "Realtek Bluetooth 5.0 Adapter",
                type: "usb",
                available: true,
                manufacturer: "Realtek",
                platform: "Windows"
            }
        ];
        
        this.selectedAdapter = this.mockAdapters[0];
        this.isScanning = false;
        this.scanTimeoutId = null;
        
        // Initialize the interceptor
        this.installFetchInterceptor();
    }
    
    /**
     * Install fetch interceptor to mock API responses
     */
    installFetchInterceptor() {
        // Check if mocking should be disabled
        if (window.DISABLE_BLE_MOCK === true) {
            console.log('BLE API Mock interceptor disabled by global flag');
            return; // Don't install interceptor
        }

        const self = this;
        const originalFetch = window.fetch;
        
        window.fetch = function(...args) {
            const url = args[0];
            const options = args[1] || {};
            
            // Only intercept BLE API calls
            if (typeof url === 'string' && url.includes('/api/ble/')) {
                return self.handleApiRequest(url, options);
            }
            
            // Otherwise, use the original fetch
            return originalFetch.apply(this, arguments);
        };
        
        console.log('BLE API Mock: Fetch interceptor installed');
    }
    
    /**
     * Handle API requests and return mock responses
     */
    async handleApiRequest(url, options = {}) {
        console.log(`BLE API Mock: Intercepted request to ${url}`, options);
        
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 300));
        
        // Parse the URL to determine the endpoint
        const endpoint = url.split('/api/ble/')[1];
        
        // Handle different endpoints
        let responseData;
        let status = 200;
        
        try {
            if (endpoint.includes('adapter-info') || endpoint.includes('adapter/info') || endpoint.includes('adapters')) {
                responseData = {
                    adapters: this.mockAdapters,
                    primary_adapter: this.selectedAdapter
                };
            }
            else if (endpoint.includes('adapter/select') || endpoint.includes('adapter-select') || endpoint.includes('select-adapter')) {
                // Parse request body
                let adapterId;
                if (options.body) {
                    try {
                        const body = JSON.parse(options.body);
                        adapterId = body.adapter_id;
                    } catch (e) {
                        status = 400;
                        responseData = {
                            detail: "Invalid request body"
                        };
                    }
                }
                
                if (adapterId) {
                    // Find the adapter
                    const adapter = this.mockAdapters.find(a => a.address === adapterId);
                    if (adapter) {
                        this.selectedAdapter = adapter;
                        responseData = {
                            success: true,
                            adapter: adapter
                        };
                    } else {
                        status = 404;
                        responseData = {
                            detail: "Adapter not found"
                        };
                    }
                }
            }
            else if (endpoint.includes('scan/start')) {
                // Parse request body for scan parameters
                let scanTime = 5;
                let active = true;
                
                if (options.body) {
                    try {
                        const body = JSON.parse(options.body);
                        scanTime = body.scan_time || scanTime;
                        active = body.active !== undefined ? body.active : active;
                    } catch (e) {
                        // Use defaults if parsing fails
                    }
                }
                
                // Start mock scan
                this.startMockScan(scanTime);
                
                responseData = {
                    success: true,
                    message: "Scan started",
                    scan_time: scanTime,
                    active: active
                };
            }
            else if (endpoint.includes('scan/results')) {
                // Return mock scan results
                responseData = {
                    devices: this.isScanning ? [] : this.mockDevices,
                    count: this.isScanning ? 0 : this.mockDevices.length,
                    timestamp: Date.now()
                };
            }
            else if (endpoint.includes('scan/stop')) {
                // Stop mock scan if active
                if (this.isScanning) {
                    clearTimeout(this.scanTimeoutId);
                    this.isScanning = false;
                }
                
                responseData = {
                    success: true,
                    message: "Scan stopped"
                };
            }
            else if (endpoint.includes('connect')) {
                // Mock device connection
                responseData = {
                    success: true,
                    message: "Connected to device",
                    device: {
                        address: options.body ? JSON.parse(options.body).address : "00:00:00:00:00:00",
                        name: "Mock Device",
                        services: [
                            "0000180f-0000-1000-8000-00805f9b34fb", // Battery Service
                            "0000180a-0000-1000-8000-00805f9b34fb"  // Device Information Service
                        ]
                    }
                };
            }
            else if (endpoint.includes('services')) {
                // Mock services for a device
                responseData = {
                    services: [
                        {
                            uuid: "0000180f-0000-1000-8000-00805f9b34fb",
                            name: "Battery Service",
                            characteristics: [
                                {
                                    uuid: "00002a19-0000-1000-8000-00805f9b34fb",
                                    name: "Battery Level",
                                    properties: ["read", "notify"]
                                }
                            ]
                        },
                        {
                            uuid: "0000180a-0000-1000-8000-00805f9b34fb",
                            name: "Device Information Service",
                            characteristics: [
                                {
                                    uuid: "00002a29-0000-1000-8000-00805f9b34fb",
                                    name: "Manufacturer Name String",
                                    properties: ["read"]
                                },
                                {
                                    uuid: "00002a24-0000-1000-8000-00805f9b34fb",
                                    name: "Model Number String",
                                    properties: ["read"]
                                }
                            ]
                        }
                    ]
                };
            }
            else {
                // Unknown endpoint
                status = 404;
                responseData = {
                    detail: "Endpoint not found"
                };
            }
            
            // Create mock response
            return new Response(JSON.stringify(responseData), {
                status: status,
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
        } catch (error) {
            console.error('BLE API Mock: Error handling request', error);
            
            return new Response(JSON.stringify({
                detail: "Internal server error"
            }), {
                status: 500,
                headers: {
                    'Content-Type': 'application/json'
                }
            });
        }
    }
    
    /**
     * Start a mock scan process
     */
    startMockScan(scanTime) {
        // Clear any existing scan
        if (this.scanTimeoutId) {
            clearTimeout(this.scanTimeoutId);
        }
        
        this.isScanning = true;
        
        // Set timeout to complete the scan
        this.scanTimeoutId = setTimeout(() => {
            this.isScanning = false;
            
            // Emit scan completed event if BleEvents is available
            if (window.BleEvents) {
                window.BleEvents.emit('SCAN_COMPLETED', {
                    devices: this.mockDevices,
                    timestamp: Date.now()
                });
            }
            
        }, scanTime * 1000);
    }
}

// Initialize the mock API handler
const bleApiMock = new BleApiMock();
export default bleApiMock;
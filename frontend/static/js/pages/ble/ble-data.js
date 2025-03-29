import { BleEvents } from './ble-events.js';
import { BleUI } from './ble-ui.js';

/**
 * BLE Data module for handling data visualization and analysis
 */
export class BleData {
    /**
     * Create a new BLE Data instance
     * @param {Object} appState - Shared application state
     */
    constructor(appState = {}) {
        this.state = appState;
        this.dataLogElement = null;
        this.dataHistoryElement = null;
        this.dataVisualElement = null;
        this.dataControlsElement = null;
        this.maxLogEntries = 100;
        this.dataHistory = {};
        this.activeVisualizations = {};
        this.chartInstances = {};
        this.decoders = this.initializeDecoders();
        this.initialized = false;
        
        // Check if Chart.js is available
        this.chartJsAvailable = typeof window.Chart !== 'undefined';
        if (!this.chartJsAvailable) {
            console.warn('Chart.js is not available. Data visualization features will be limited.');
        }
    }

    /**
     * Initialize the BLE Data module
     */
    initialize() {
        if (this.initialized) return;

        console.log('Initializing BLE Data module');
        
        // Find necessary DOM elements
        this.dataLogElement = document.getElementById('data-log');
        this.dataHistoryElement = document.getElementById('data-history');
        this.dataVisualElement = document.getElementById('data-visualization');
        this.dataControlsElement = document.getElementById('data-controls');
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Initialize UI
        this.initializeUI();
        
        this.initialized = true;
        console.log('BLE Data module initialized');
    }
    
    /**
     * Set up event listeners for BLE data events
     */
    setupEventListeners() {
        // Listen for BLE notification events to log data
        BleEvents.on('notification', (data) => {
            this.handleNotificationData(data);
        });
        
        // Handle device disconnection
        BleEvents.on('device_disconnected', () => {
            // Optional: keep history or clear it on disconnect
            // this.clearDataHistory();
        });
        
        // Add event listeners to UI controls if they exist
        if (this.dataControlsElement) {
            // Find export button
            const exportBtn = this.dataControlsElement.querySelector('#export-data-btn');
            if (exportBtn) {
                exportBtn.addEventListener('click', () => this.exportData());
            }
            
            // Find clear button
            const clearBtn = this.dataControlsElement.querySelector('#clear-data-btn');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => this.clearDataHistory());
            }
            
            // Find visualization type selector
            const visTypeSelect = this.dataControlsElement.querySelector('#visualization-type');
            if (visTypeSelect) {
                visTypeSelect.addEventListener('change', (e) => {
                    const charUuid = visTypeSelect.getAttribute('data-characteristic');
                    if (charUuid) {
                        this.updateVisualization(charUuid, e.target.value);
                    }
                });
            }
        }
    }
    
    /**
     * Initialize the UI components
     */
    initializeUI() {
        // Initialize data log if element exists
        if (this.dataLogElement) {
            this.dataLogElement.innerHTML = `
                <div class="p-4 text-center text-gray-500">
                    <i class="fas fa-info-circle mb-2"></i>
                    <p>No data logged yet. Connect to a device and enable notifications to see data.</p>
                </div>
            `;
        }
        
        // Initialize data visualization if element exists
        if (this.dataVisualElement) {
            this.dataVisualElement.innerHTML = `
                <div class="p-4 text-center text-gray-500">
                    <i class="fas fa-chart-line mb-2"></i>
                    <p>Select a characteristic to visualize data.</p>
                </div>
            `;
        }
    }
    
    /**
     * Initialize data decoders
     * @returns {Object} Map of decoder functions
     */
    initializeDecoders() {
        return {
            // Decode integer values (8, 16, 32 bits)
            'int8': (hex) => {
                const value = parseInt(hex.slice(0, 2), 16);
                return value > 127 ? value - 256 : value;
            },
            'uint8': (hex) => parseInt(hex.slice(0, 2), 16),
            'int16': (hex) => {
                const value = parseInt(hex.slice(0, 4), 16);
                return value > 32767 ? value - 65536 : value;
            },
            'uint16': (hex) => parseInt(hex.slice(0, 4), 16),
            'int32': (hex) => {
                const value = parseInt(hex.slice(0, 8), 16);
                return value > 2147483647 ? value - 4294967296 : value;
            },
            'uint32': (hex) => parseInt(hex.slice(0, 8), 16),
            
            // Decode floating point values
            'float': (hex) => {
                // Convert hex to a 32-bit float
                const bytes = new Uint8Array(4);
                for (let i = 0; i < 4; i++) {
                    bytes[i] = parseInt(hex.slice(i*2, i*2+2), 16);
                }
                const view = new DataView(bytes.buffer);
                return view.getFloat32(0, true); // true = little endian
            },
            
            // Decode ASCII string
            'ascii': (hex) => {
                let str = '';
                for (let i = 0; i < hex.length; i += 2) {
                    const charCode = parseInt(hex.slice(i, i+2), 16);
                    str += String.fromCharCode(charCode);
                }
                return str;
            },
            
            // Decode UTF-8 string
            'utf8': (hex) => {
                try {
                    const bytes = new Uint8Array(hex.length / 2);
                    for (let i = 0; i < hex.length; i += 2) {
                        bytes[i/2] = parseInt(hex.slice(i, i+2), 16);
                    }
                    const decoder = new TextDecoder('utf-8');
                    return decoder.decode(bytes);
                } catch (e) {
                    console.error('Error decoding UTF-8:', e);
                    return '(invalid UTF-8)';
                }
            },
            
            // Bitmap decoder for boolean flags
            'bitmap': (hex) => {
                const byte = parseInt(hex.slice(0, 2), 16);
                const bits = [];
                for (let i = 0; i < 8; i++) {
                    bits.push((byte >> i) & 1);
                }
                return bits.join('');
            },
            
            // Temperature decoder (assumes format used by many BLE temperature sensors)
            'temperature': (hex) => {
                // Many BLE temperature sensors use 2 bytes in little endian, units of 0.01°C
                const val = parseInt(hex.slice(0, 4), 16);
                return (val / 100).toFixed(2) + '°C';
            },
            
            // Heart rate decoder
            'heartrate': (hex) => {
                // First byte contains flags
                const flags = parseInt(hex.slice(0, 2), 16);
                // Check if heart rate value is in 8 or 16 bit format
                if ((flags & 0x01) === 0) {
                    // 8-bit format
                    return parseInt(hex.slice(2, 4), 16) + " bpm";
                } else {
                    // 16-bit format (little endian)
                    return parseInt(hex.slice(2, 6), 16) + " bpm";
                }
            },
            
            // Battery level decoder
            'battery': (hex) => {
                return parseInt(hex.slice(0, 2), 16) + "%";
            }
        };
    }
    
    /**
     * Handle notification data from a BLE characteristic
     * @param {Object} data - Notification data object
     */
    handleNotificationData(data) {
        const { characteristic, value, encoding, device } = data;
        console.log(`Notification from device: ${device}, characteristic: ${characteristic}`);
        
        // Skip if no characteristic or value
        if (!characteristic || !value) return;
        
        // Store in history
        this.addToHistory(characteristic, value, encoding);
        
        // Update log UI
        this.updateDataLog(characteristic, value, encoding);
        
        // Update visualization if active
        this.updateDataVisualization(characteristic, value, encoding);
    }
    
    /**
     * Add data to history
     * @param {string} uuid - Characteristic UUID 
     * @param {string} value - Value (usually hex)
     * @param {string} encoding - Encoding of the value (hex, utf8, etc)
     */
    addToHistory(uuid, value, encoding) {
        const timestamp = new Date();
        
        // Initialize array for this characteristic if it doesn't exist
        if (!this.dataHistory[uuid]) {
            this.dataHistory[uuid] = [];
        }
        
        // Add to history
        this.dataHistory[uuid].push({
            timestamp,
            value,
            encoding
        });
        
        // Limit history size
        if (this.dataHistory[uuid].length > this.maxLogEntries) {
            this.dataHistory[uuid].shift();
        }
    }
    
    /**
     * Update the data log UI
     * @param {string} uuid - Characteristic UUID
     * @param {string} value - Value (usually hex)
     * @param {string} encoding - Encoding of the value
     */
    updateDataLog(uuid, value, encoding) {
        if (!this.dataLogElement) return;
        
        // Create a new log entry
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry p-2 border-b border-gray-700 text-sm';
        
        // Format the UUID for display (shortened)
        const shortUuid = uuid.length > 8 ? uuid.substr(-8) : uuid;
        
        // Format the timestamp
        const timestamp = new Date().toLocaleTimeString();
        
        // Format value based on encoding
        let displayValue = value;
        try {
            // Try to auto-detect and provide alternative views
            if (encoding === 'hex') {
                // Show both hex and potential numeric interpretations
                const numericValue = this.interpretNumericValue(value);
                displayValue = `
                    <div class="font-mono">${value}</div>
                    <div class="text-xs text-gray-400 mt-1">
                        ${numericValue.map(nv => `${nv.name}: ${nv.value}`).join(' | ')}
                    </div>
                `;
            } else if (encoding === 'base64') {
                // Show base64 and try to interpret as UTF-8
                try {
                    const decoded = atob(value);
                    displayValue = `
                        <div class="font-mono">${value}</div>
                        <div class="text-xs text-gray-400 mt-1">UTF-8: "${decoded}"</div>
                    `;
                } catch (e) {
                    // Use as-is if decoding fails
                    displayValue = `<div class="font-mono">${value}</div>`;
                }
            }
        } catch (e) {
            console.error('Error formatting value:', e);
            displayValue = `<div class="font-mono">${value}</div>`;
        }
        
        // Assemble the log entry
        logEntry.innerHTML = `
            <div class="flex items-start">
                <div class="text-gray-400 mr-2 w-20 flex-shrink-0">${timestamp}</div>
                <div class="flex-grow">
                    <div class="flex justify-between">
                        <div class="font-mono text-blue-400">${shortUuid}</div>
                        <div class="text-xs text-gray-500">${encoding}</div>
                    </div>
                    <div class="mt-1">${displayValue}</div>
                </div>
            </div>
        `;
        
        // Add tools/actions for this entry
        const toolsDiv = document.createElement('div');
        toolsDiv.className = 'flex mt-2 space-x-2 text-xs';
        toolsDiv.innerHTML = `
            <button class="decode-btn px-2 py-1 bg-blue-800 text-blue-100 rounded hover:bg-blue-700" data-uuid="${uuid}" data-value="${value}">
                <i class="fas fa-code mr-1"></i> Decode
            </button>
            <button class="visualize-btn px-2 py-1 bg-purple-800 text-purple-100 rounded hover:bg-purple-700" data-uuid="${uuid}">
                <i class="fas fa-chart-line mr-1"></i> Visualize
            </button>
        `;
        
        // Add event listeners to buttons
        const decodeBtn = toolsDiv.querySelector('.decode-btn');
        decodeBtn.addEventListener('click', () => {
            this.showDecodeDialog(uuid, value, encoding);
        });
        
        const visualizeBtn = toolsDiv.querySelector('.visualize-btn');
        visualizeBtn.addEventListener('click', () => {
            this.setupVisualization(uuid);
        });
        
        logEntry.appendChild(toolsDiv);
        
        // Add to log (prepend so newest is at top)
        this.dataLogElement.prepend(logEntry);
        
        // Limit number of visible entries
        while (this.dataLogElement.children.length > this.maxLogEntries) {
            this.dataLogElement.removeChild(this.dataLogElement.lastChild);
        }
    }
    
    /**
     * Interpret numeric values from hex
     * @param {string} hexValue - Hex string
     * @returns {Array} Array of interpretations
     */
    interpretNumericValue(hexValue) {
        const interpretations = [];
        
        try {
            // Remove any spaces or 0x prefix
            hexValue = hexValue.replace(/\s+/g, '').replace(/^0x/i, '');
            
            // Start with simple numeric interpretations
            if (hexValue.length >= 2) {
                // 8-bit interpretations
                interpretations.push({
                    name: 'uint8',
                    value: this.decoders.uint8(hexValue)
                });
                interpretations.push({
                    name: 'int8',
                    value: this.decoders.int8(hexValue)
                });
            }
            
            if (hexValue.length >= 4) {
                // 16-bit interpretations
                interpretations.push({
                    name: 'uint16',
                    value: this.decoders.uint16(hexValue)
                });
                interpretations.push({
                    name: 'int16',
                    value: this.decoders.int16(hexValue)
                });
            }
            
            if (hexValue.length >= 8) {
                // 32-bit interpretations
                interpretations.push({
                    name: 'uint32',
                    value: this.decoders.uint32(hexValue)
                });
                interpretations.push({
                    name: 'int32',
                    value: this.decoders.int32(hexValue)
                });
                interpretations.push({
                    name: 'float',
                    value: this.decoders.float(hexValue).toFixed(2)
                });
            }
            
            // Always try to interpret as ASCII if it looks like text
            // Only include ASCII interpretation if it contains mostly printable chars
            const asciiValue = this.decoders.ascii(hexValue);
            const printableCharCount = asciiValue.replace(/[^\x20-\x7E]/g, '').length;
            if (printableCharCount > asciiValue.length * 0.7) {
                interpretations.push({
                    name: 'ASCII',
                    value: `"${asciiValue}"`
                });
            }
        } catch (e) {
            console.error('Error interpreting numeric values:', e);
        }
        
        return interpretations;
    }
    
    /**
     * Show a dialog with various decoding options
     * @param {string} uuid - Characteristic UUID
     * @param {string} value - Value to decode
     * @param {string} encoding - Original encoding
     */
    showDecodeDialog(uuid, value, encoding) {
        // Create dialog content
        const dialogContent = document.createElement('div');
        dialogContent.className = 'p-4';
        
        // Dialog header
        dialogContent.innerHTML = `
            <div class="mb-4 pb-2 border-b border-gray-700">
                <h3 class="text-lg font-semibold">Decode Value</h3>
                <div class="text-sm text-gray-400">Characteristic: ${uuid}</div>
                <div class="text-sm text-gray-400">Original encoding: ${encoding}</div>
            </div>
            
            <div class="mb-4">
                <div class="text-sm text-gray-400 mb-1">Original value:</div>
                <div class="bg-gray-900 p-2 rounded font-mono">${value}</div>
            </div>
            
            <div class="mb-4">
                <div class="text-sm text-gray-400 mb-1">Decode as:</div>
                <div class="grid grid-cols-1 gap-2">
                    <select id="decode-type" class="bg-gray-800 border border-gray-700 rounded p-2">
                        <option value="int8">8-bit Integer (signed)</option>
                        <option value="uint8">8-bit Integer (unsigned)</option>
                        <option value="int16">16-bit Integer (signed)</option>
                        <option value="uint16">16-bit Integer (unsigned)</option>
                        <option value="int32">32-bit Integer (signed)</option>
                        <option value="uint32">32-bit Integer (unsigned)</option>
                        <option value="float">32-bit Float</option>
                        <option value="ascii">ASCII string</option>
                        <option value="utf8">UTF-8 string</option>
                        <option value="bitmap">Bitmap (flags)</option>
                        <option value="temperature">Temperature</option>
                        <option value="heartrate">Heart Rate</option>
                        <option value="battery">Battery Level</option>
                    </select>
                </div>
            </div>
            
            <div class="mb-4">
                <div class="text-sm text-gray-400 mb-1">Result:</div>
                <div id="decode-result" class="bg-gray-900 p-2 rounded min-h-12 flex items-center"></div>
            </div>
            
            <div class="flex justify-end space-x-2">
                <button id="decode-btn" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-500">
                    Decode
                </button>
                <button id="close-decode-dialog" class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-500">
                    Close
                </button>
            </div>
        `;
        
        // Show the dialog
        const dialog = BleUI.showDialog(dialogContent);
        
        // Set up event handlers
        const decodeBtn = dialog.querySelector('#decode-btn');
        const closeBtn = dialog.querySelector('#close-decode-dialog');
        const decodeTypeSelect = dialog.querySelector('#decode-type');
        const decodeResult = dialog.querySelector('#decode-result');
        
        // Close button
        closeBtn.addEventListener('click', () => {
            BleUI.closeDialog(dialog);
        });
        
        // Decode button
        decodeBtn.addEventListener('click', () => {
            const decoder = decodeTypeSelect.value;
            this.decodeAndDisplay(value, decoder, decodeResult);
        });
        
        // Automatically decode with first option
        this.decodeAndDisplay(value, decodeTypeSelect.value, decodeResult);
    }
    
    /**
     * Decode value and update result element
     * @param {string} value - Value to decode
     * @param {string} decoder - Decoder type
     * @param {HTMLElement} resultElement - Element to update with result
     */
    decodeAndDisplay(value, decoder, resultElement) {
        try {
            // Normalize value - remove spaces, 0x prefix
            const normalizedValue = value.replace(/\s+/g, '').replace(/^0x/i, '');
            
            // Check if the decoder exists
            if (!this.decoders[decoder]) {
                resultElement.textContent = `Decoder '${decoder}' not found`;
                return;
            }
            
            // Apply the decoder
            const decodedValue = this.decoders[decoder](normalizedValue);
            
            // Format the result
            let formattedResult;
            
            if (Array.isArray(decodedValue)) {
                formattedResult = decodedValue.join(', ');
            } else if (typeof decodedValue === 'object') {
                formattedResult = JSON.stringify(decodedValue, null, 2);
            } else {
                formattedResult = decodedValue?.toString() || 'null';
            }
            
            // Update the result element
            resultElement.textContent = formattedResult;
        } catch (error) {
            resultElement.textContent = `Error: ${error.message}`;
        }
    }
    
    /**
     * Set up visualization for a characteristic
     * @param {string} uuid - Characteristic UUID
     */
    setupVisualization(uuid) {
        if (!this.dataVisualElement) return;
        
        // Check if we have data for this characteristic
        if (!this.dataHistory[uuid] || this.dataHistory[uuid].length === 0) {
            BleUI.showToast('No data available for visualization', 'warning');
            return;
        }
        
        // Determine best visualization type based on data
        const visType = this.determineBestVisualization(uuid);
        
        // Record that this characteristic is being visualized
        this.activeVisualizations[uuid] = visType;
        
        // Create visualization container
        this.dataVisualElement.innerHTML = `
            <div class="p-4">
                <div class="flex justify-between items-center mb-4">
                    <div>
                        <h3 class="text-lg font-semibold">Data Visualization</h3>
                        <div class="text-sm text-gray-400">Characteristic: ${uuid}</div>
                    </div>
                    <div>
                        <select id="visualization-type" data-characteristic="${uuid}" class="bg-gray-800 border border-gray-700 rounded p-2">
                            <option value="line" ${visType === 'line' ? 'selected' : ''}>Line Chart</option>
                            <option value="bar" ${visType === 'bar' ? 'selected' : ''}>Bar Chart</option>
                            <option value="gauge" ${visType === 'gauge' ? 'selected' : ''}>Gauge</option>
                            <option value="realtime" ${visType === 'realtime' ? 'selected' : ''}>Real-time</option>
                            <option value="raw" ${visType === 'raw' ? 'selected' : ''}>Raw Data</option>
                        </select>
                    </div>
                </div>
                
                <div class="visualization-container h-64 bg-gray-900 rounded">
                    <canvas id="visualization-chart"></canvas>
                </div>
                
                <div class="mt-2 text-xs text-gray-400">
                    <span id="data-point-count"></span> data points
                </div>
            </div>
        `;
        
        // Set up the visualization
        this.updateVisualization(uuid, visType);
        
        // Update visualization type when changed
        const visTypeSelect = this.dataVisualElement.querySelector('#visualization-type');
        visTypeSelect.addEventListener('change', (event) => {
            this.updateVisualization(uuid, event.target.value);
        });
    }
    
    /**
     * Determine the best visualization type for a characteristic
     * @param {string} uuid - Characteristic UUID
     * @returns {string} Visualization type
     */
    determineBestVisualization(uuid) {
        const history = this.dataHistory[uuid];
        if (!history || history.length === 0) return 'raw';
        
        // Check the last few values to determine data type
        const sampleSize = Math.min(5, history.length);
        const samples = history.slice(-sampleSize);
        
        // Check if all samples are numeric
        const numericSamples = samples.map(sample => {
            const value = sample.value;
            // Try to convert hex to number
            if (sample.encoding === 'hex') {
                // Try 8-bit first
                if (value.length <= 2) {
                    return this.decoders.uint8(value);
                } else if (value.length <= 4) {
                    return this.decoders.uint16(value);
                } else {
                    return NaN; // Too long for simple numeric
                }
            } else if (sample.encoding === 'utf8' || sample.encoding === 'ascii') {
                // Try parsing as number
                return parseFloat(value);
            }
            return NaN;
        });
        
        const allNumeric = numericSamples.every(n => !isNaN(n));
        
        // For time-series numeric data, line chart is best
        if (allNumeric && history.length > 2) {
            return 'line';
        }
        
        // For numeric data with few points, bar chart
        if (allNumeric) {
            return 'bar';
        }
        
        // Default to raw data view
        return 'raw';
    }
    
    /**
     * Update the visualization for a characteristic
     * @param {string} uuid - Characteristic UUID
     * @param {string} visType - Visualization type
     */
    updateVisualization(uuid, visType) {
        if (!this.dataVisualElement) return;
        
        // Update active visualization type
        this.activeVisualizations[uuid] = visType;
        
        // Get data for this characteristic
        const history = this.dataHistory[uuid] || [];
        
        // Update data point count
        const dataPointCount = this.dataVisualElement.querySelector('#data-point-count');
        if (dataPointCount) {
            dataPointCount.textContent = history.length;
        }
        
        // Clear any existing chart
        if (this.chartInstances[uuid]) {
            this.chartInstances[uuid].destroy();
            delete this.chartInstances[uuid];
        }
        
        // Render based on visualization type
        if (visType === 'raw') {
            this.renderRawData(uuid, history);
        } else if (visType === 'line' || visType === 'bar') {
            this.renderChart(uuid, history, visType);
        } else if (visType === 'gauge') {
            this.renderGauge(uuid, history);
        } else if (visType === 'realtime') {
            this.renderRealtime(uuid, history);
        }
    }
    
    /**
     * Render raw data visualization
     * @param {string} uuid - Characteristic UUID
     * @param {Array} history - Data history
     */
    renderRawData(uuid, history) {
        const container = this.dataVisualElement.querySelector('.visualization-container');
        if (!container) return;
        
        // Remove canvas
        const canvas = container.querySelector('canvas');
        if (canvas) canvas.remove();
        
        // Create raw data display
        container.innerHTML = `
            <div class="overflow-auto h-full p-2">
                <table class="w-full">
                    <thead>
                        <tr class="text-left text-xs text-gray-400">
                            <th class="p-2">Time</th>
                            <th class="p-2">Value</th>
                            <th class="p-2">Encoding</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${history.map((item, index) => `
                            <tr class="border-t border-gray-800 ${index % 2 === 0 ? 'bg-gray-800' : ''}">
                                <td class="p-2 text-xs">${item.timestamp.toLocaleTimeString()}</td>
                                <td class="p-2 font-mono">${item.value}</td>
                                <td class="p-2 text-xs">${item.encoding}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    /**
     * Render real-time data visualization
     * @param {string} uuid - Characteristic UUID
     * @param {Array} history - Data history
     */
    renderRealtime(uuid, history) {
        const container = this.dataVisualElement.querySelector('.visualization-container');
        if (!container) return;
        
        // Remove previous canvas if exists
        const oldCanvas = container.querySelector('canvas');
        if (oldCanvas) oldCanvas.remove();
        
        // Create a real-time visualization container
        container.innerHTML = `
            <div class="h-full p-3 flex flex-col">
                <div class="flex-grow relative" id="realtime-chart-container">
                    <canvas id="realtime-chart"></canvas>
                </div>
                <div class="flex items-center justify-between mt-2">
                    <div class="text-sm">
                        <span class="text-blue-400 mr-2">Latest:</span>
                        <span id="realtime-value" class="font-mono">--</span>
                    </div>
                    <div class="flex space-x-2">
                        <button id="pause-realtime" class="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded">
                            <i class="fas fa-pause mr-1"></i> Pause
                        </button>
                        <button id="clear-realtime" class="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded">
                            <i class="fas fa-trash-alt mr-1"></i> Clear
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Get the canvas and create a chart
        const canvas = container.querySelector('#realtime-chart');
        const ctx = canvas.getContext('2d');
        
        // Prepare data for chart
        const chartData = history.map(item => {
            // Try to convert to number based on encoding
            let value;
            if (item.encoding === 'hex') {
                // Use the length to determine how to interpret
                if (item.value.length <= 2) {
                    value = this.decoders.uint8(item.value);
                } else if (item.value.length <= 4) {
                    value = this.decoders.uint16(item.value);
                } else {
                    // Try first byte as simple value
                    value = this.decoders.uint8(item.value);
                }
            } else {
                // For other encodings, try parsing as number
                value = parseFloat(item.value);
                if (isNaN(value)) {
                    value = 0; // Default to 0 if not numeric
                }
            }
            
            return {
                x: item.timestamp,
                y: value
            };
        });
        
        // Set up real-time chart using Chart.js if available
        if (this.chartJsAvailable && typeof window.Chart !== 'undefined') {
            this.chartInstances[uuid] = new window.Chart(ctx, {
                type: 'line',
                data: {
                    datasets: [{
                        label: 'Value',
                        data: chartData,
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1,
                        pointRadius: 0,
                        pointHitRadius: 5,
                        pointHoverRadius: 5,
                        pointBackgroundColor: 'rgba(54, 162, 235, 1)',
                        lineTension: 0.2,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'second',
                                displayFormats: {
                                    second: 'HH:mm:ss'
                                }
                            },
                            ticks: {
                                maxRotation: 0,
                                maxTicksLimit: 5,
                                autoSkip: true
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        }
                    },
                    animation: {
                        duration: 0  // No animation for better real-time performance
                    },
                    elements: {
                        line: {
                            tension: 0.4  // Smoother line
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        }
                    }
                }
            });
            
            // If we have data, update the latest value display
            if (history.length > 0) {
                const latestItem = history[history.length - 1];
                const valueDisplay = container.querySelector('#realtime-value');
                if (valueDisplay) {
                    valueDisplay.textContent = latestItem.value;
                }
            }
            
            // Setup pause/resume functionality
            const pauseButton = container.querySelector('#pause-realtime');
            if (pauseButton) {
                pauseButton.addEventListener('click', () => {
                    const isPaused = pauseButton.getAttribute('data-paused') === 'true';
                    pauseButton.setAttribute('data-paused', !isPaused);
                    
                    if (isPaused) {
                        // Resume
                        pauseButton.innerHTML = '<i class="fas fa-pause mr-1"></i> Pause';
                    } else {
                        // Pause
                        pauseButton.innerHTML = '<i class="fas fa-play mr-1"></i> Resume';
                    }
                });
            }
            
            // Setup clear functionality
            const clearButton = container.querySelector('#clear-realtime');
            if (clearButton) {
                clearButton.addEventListener('click', () => {
                    // Clear the chart data
                    this.chartInstances[uuid].data.datasets[0].data = [];
                    this.chartInstances[uuid].update();
                    
                    // Clear the specific characteristic history
                    this.dataHistory[uuid] = [];
                    
                    // Update value display
                    const valueDisplay = container.querySelector('#realtime-value');
                    if (valueDisplay) {
                        valueDisplay.textContent = '--';
                    }
                });
            }
        } else {
            // Fallback if Chart.js is not available
            container.innerHTML = `
                <div class="flex items-center justify-center h-full">
                    <div class="text-center">
                        <div class="text-gray-400 mb-2">
                            <i class="fas fa-exclamation-circle text-3xl"></i>
                        </div>
                        <div>Chart.js is required for real-time visualization</div>
                    </div>
                </div>
            `;
        }
    }

    /**
     * Update data visualization with new data
     * @param {string} uuid - Characteristic UUID
     * @param {string} value - New value
     * @param {string} encoding - Encoding of the value
     */
    updateDataVisualization(uuid, value, encoding) {
        // Check if this characteristic is being visualized
        if (!this.activeVisualizations[uuid]) return;
        
        const visType = this.activeVisualizations[uuid];
        const chart = this.chartInstances[uuid];
        
        // If we have a chart instance, update it
        if (chart && (visType === 'line' || visType === 'bar' || visType === 'realtime')) {
            // Convert the new value
            let numericValue;
            if (encoding === 'hex') {
                // Convert hex to number based on length
                if (value.length <= 2) {
                    numericValue = this.decoders.uint8(value);
                } else if (value.length <= 4) {
                    numericValue = this.decoders.uint16(value);
                } else {
                    numericValue = this.decoders.uint8(value);
                }
            } else {
                numericValue = parseFloat(value) || 0;
            }
            
            // Update chart with new data point
            chart.data.datasets[0].data.push({
                x: new Date(),
                y: numericValue
            });
            
            // Limit number of points for performance
            const maxPoints = 100;
            if (chart.data.datasets[0].data.length > maxPoints) {
                chart.data.datasets[0].data.shift();
            }
            
            // For real-time, update the value display
            if (visType === 'realtime') {
                const container = this.dataVisualElement.querySelector('.visualization-container');
                const valueDisplay = container?.querySelector('#realtime-value');
                
                if (valueDisplay) {
                    valueDisplay.textContent = value;
                }
                
                // Check if visualization is paused
                const pauseButton = container?.querySelector('#pause-realtime');
                if (pauseButton && pauseButton.getAttribute('data-paused') !== 'true') {
                    chart.update();
                }
            } else {
                // Always update for non-realtime charts
                chart.update();
            }
        } else if (visType === 'gauge') {
            // For gauge, we need to re-render with the latest data
            this.renderGauge(uuid, this.dataHistory[uuid]);
        } else if (visType === 'raw') {
            // For raw display, we could prepend to the table, but it's simpler to just re-render
            this.renderRawData(uuid, this.dataHistory[uuid]);
        }
    }
       
        /**
         * Export data history to a file
         */
        exportData() {
            // Check if we have any data
            if (Object.keys(this.dataHistory).length === 0) {
                BleUI.showToast('No data to export', 'warning');
                return;
            }
            
            // Prepare data for export
            const exportData = {
                timestamp: new Date().toISOString(),
                device: this.state.connectedDevice || 'unknown',
                data: {}
            };
            
            // Format each characteristic's data
            Object.keys(this.dataHistory).forEach(uuid => {
                exportData.data[uuid] = this.dataHistory[uuid].map(item => ({
                    timestamp: item.timestamp.toISOString(),
                    value: item.value,
                    encoding: item.encoding
                }));
            });
            
            // Convert to JSON
            const jsonData = JSON.stringify(exportData, null, 2);
            
            // Create a blob and download link
            const blob = new Blob([jsonData], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            // Create download link
            const a = document.createElement('a');
            a.href = url;
            a.download = `ble-data-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
            document.body.appendChild(a);
            a.click();
            
            // Clean up
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }, 0);
            
            BleUI.showToast('Data exported successfully', 'success');
        }
        
        /**
         * Clear all data history
         */
        clearDataHistory() {
            // Ask for confirmation with a custom dialog
            const dialogContent = document.createElement('div');
            dialogContent.className = 'p-4';
            dialogContent.innerHTML = `
                <div class="mb-4">
                    <h3 class="text-lg font-semibold">Confirm Clear Data</h3>
                    <p class="text-gray-400 mt-2">Are you sure you want to clear all data history?</p>
                </div>
                <div class="flex justify-end space-x-2">
                    <button id="confirm-clear" class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-500">
                        Clear Data
                    </button>
                    <button id="cancel-clear" class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-500">
                        Cancel
                    </button>
                </div>
            `;
            
            const dialog = BleUI.showDialog(dialogContent);
            
            // Set up event listeners for confirmation
            dialog.querySelector('#confirm-clear').addEventListener('click', () => {
                BleUI.closeDialog(dialog);
                
                // Clear all data
                this.dataHistory = {};
                
                // Clear log UI
                if (this.dataLogElement) {
                    this.dataLogElement.innerHTML = `
                        <div class="p-4 text-center text-gray-500">
                            <i class="fas fa-info-circle mb-2"></i>
                            <p>No data logged yet. Connect to a device and enable notifications to see data.</p>
                        </div>
                    `;
                }
                
                // Clear visualization
                if (this.dataVisualElement) {
                    this.dataVisualElement.innerHTML = `
                        <div class="p-4 text-center text-gray-500">
                            <i class="fas fa-chart-line mb-2"></i>
                            <p>Select a characteristic to visualize data.</p>
                        </div>
                    `;
                }
                
                // Clear chart instances
                Object.values(this.chartInstances).forEach(chart => chart.destroy());
                this.chartInstances = {};
                this.activeVisualizations = {};
                
                BleUI.showToast('Data history cleared', 'success');
            });
            
            // Add event listener for cancel button
            dialog.querySelector('#cancel-clear').addEventListener('click', () => {
                BleUI.closeDialog(dialog);
            });
        }
    }
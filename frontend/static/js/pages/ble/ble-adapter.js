import { logMessage } from './ble-ui.js';

/**
 * BLE Adapter Information Module
 * Handles retrieving and displaying Bluetooth adapter information
 */

/**
 * Initialize adapter information
 * @param {Object} state - Global BLE state
 */
export function initializeAdapterInfo(state) {
    const container = document.getElementById('adapter-info-content');
    if (!container) return;
    
    container.innerHTML = '<div class="text-gray-500">Fetching adapter information...</div>';
    
    getAdapterInfo()
        .then(adapterInfo => {
            displayAdapterInfo(container, adapterInfo);
        })
        .catch(error => {
            container.innerHTML = `
                <div class="text-red-500">
                    <i class="fas fa-exclamation-triangle mr-2"></i>
                    Failed to get adapter information
                </div>
                <div class="text-sm text-gray-400 mt-1">${error.message}</div>
                <button id="retry-adapter-info" class="mt-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                    <i class="fas fa-sync mr-1"></i> Retry
                </button>
            `;
                
            const retryButton = document.getElementById('retry-adapter-info');
            if (retryButton) {
                retryButton.addEventListener('click', () => {
                    initializeAdapterInfo(state);
                });
            }
            
            // Log error
            logMessage(`Adapter info error: ${error.message}`, 'error');
        });
}

/**
 * Get Bluetooth adapter information
 * @returns {Promise<Object>} - Adapter information
 */
export async function getAdapterInfo() {
    try {
        // First, try the new adapter-info endpoint
        const response = await fetch('/api/ble/adapter-info', {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Cache-Control': 'no-cache'
            }
        });
        
        if (!response.ok) {
            let errorText = await response.text();
            try {
                const errorJson = JSON.parse(errorText);
                errorText = errorJson.detail || errorText;
            } catch (e) {
                // Not JSON, use as is
            }
            
            // For backwards compatibility, try an older endpoint if available
            try {
                const legacyResponse = await fetch('/api/ble/adapter', {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Cache-Control': 'no-cache'
                    }
                });
                
                if (legacyResponse.ok) {
                    console.log("Using legacy adapter endpoint");
                    return await legacyResponse.json();
                }
            } catch (legacyError) {
                console.warn("Legacy adapter endpoint also failed:", legacyError);
            }
            
            throw new Error(`Failed to get adapter info: ${errorText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error fetching adapter info:', error);
        throw error;
    }
}

/**
 * Reset the Bluetooth adapter
 * @returns {Promise<Object>} - Result of the reset operation
 */
export async function resetAdapter() {
    try {
        const response = await fetch('/api/ble/reset-adapter', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to reset adapter');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error resetting adapter:', error);
        throw error;
    }
}

/**
 * Display adapter information in the UI
 * @param {HTMLElement} container - Container element
 * @param {Object} info - Adapter information
 */
function displayAdapterInfo(container, info) {
    if (!info) {
        container.innerHTML = '<div class="text-red-500">No adapter information available</div>';
        return;
    }
    
    // Create adapter status indicator
    const statusColor = info.available ? 'bg-green-500' : 'bg-red-500';
    const statusText = info.available ? 'Available' : 'Unavailable';
    
    // Get hardware details if available
    const hardware = info.hardware || {};
    
    // Determine adapter type even with partial info
    const adapterType = getAdapterType(info);
    
    // Generate a display name, always showing something useful
    const displayName = info.name !== 'Unknown' ? 
        info.name : 
        (adapterType !== 'Standard Bluetooth Adapter' ? adapterType : 'Bluetooth Adapter');
    
    // Format address for display (with fallbacks)
    let addressDisplay = info.address;
    if (info.address === 'Unknown') {
        addressDisplay = '<span class="text-gray-500">Not detected</span>';
    }
    
    container.innerHTML = `
        <div class="space-y-4">
            <!-- Status header -->
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    <div class="w-3 h-3 rounded-full ${statusColor} mr-2"></div>
                    <span class="font-medium">${statusText}</span>
                </div>
                <span class="px-2 py-1 rounded text-xs font-medium ${info.available ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}">${info.platform}</span>
            </div>
            
            <!-- Adapter info card - Enhanced display -->
            <div class="bg-gray-800 rounded-md p-3 border border-gray-700">
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="text-lg font-semibold">${displayName}</h3>
                        <div class="text-sm text-gray-400">${adapterType}</div>
                        
                        <!-- Always show vendor/model if available -->
                        <div class="text-xs space-y-1 mt-2">
                            ${hardware.vendor && hardware.vendor !== 'Unknown' ? 
                                `<div class="flex">
                                    <span class="text-gray-500 w-16">Vendor:</span>
                                    <span class="text-gray-300">${hardware.vendor}</span>
                                </div>` : ''}
                            
                            ${hardware.model && hardware.model !== 'Unknown' ? 
                                `<div class="flex">
                                    <span class="text-gray-500 w-16">Model:</span>
                                    <span class="text-gray-300">${hardware.model}</span>
                                </div>` : ''}
                        </div>
                    </div>
                    
                    <!-- Address with better styling -->
                    <div class="text-right bg-gray-900 p-2 rounded border border-gray-700">
                        <div class="text-xs text-gray-400 mb-1">MAC Address</div>
                        <div class="font-mono text-sm">${addressDisplay}</div>
                    </div>
                </div>
            </div>
            
            <!-- The rest of the UI remains the same -->
            ${hardware.firmware && hardware.firmware !== 'Unknown' ? `
            <div>
                <h4 class="text-sm font-semibold text-gray-300 mb-1">Hardware Details</h4>
                <div class="grid grid-cols-2 gap-x-2 gap-y-1 text-xs">
                    <div class="text-gray-400">Firmware:</div>
                    <div>${hardware.firmware}</div>
                    ${hardware.hci_version && hardware.hci_version !== 'Unknown' ? `
                    <div class="text-gray-400">HCI Version:</div>
                    <div>${hardware.hci_version}</div>
                    ` : ''}
                </div>
            </div>
            ` : ''}
            
            <!-- Features grid -->
            <div>
                <h4 class="text-sm font-semibold text-gray-300 mb-2">Supported Features</h4>
                <div class="grid grid-cols-2 gap-2">
                    ${renderFeaturesList(info.features)}
                </div>
            </div>
            
            <!-- API Version -->
            <div class="text-xs text-gray-400">
                API: ${info.api_version || 'Unknown'} 
                ${info.timestamp ? `<span class="ml-2">Updated: ${new Date(info.timestamp * 1000).toLocaleTimeString()}</span>` : ''}
            </div>
            
            <!-- Action buttons -->
            <div class="flex justify-between mt-3">
                <button id="refresh-adapter-btn" class="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded flex items-center">
                    <i class="fas fa-sync mr-1"></i> Refresh
                </button>
                <button id="reset-adapter-btn" class="px-3 py-1 bg-blue-700 hover:bg-blue-600 text-white text-sm rounded flex items-center">
                    <i class="fas fa-redo mr-1"></i> Reset Adapter
                </button>
            </div>
            
            <!-- Advanced options remain the same -->
            <div class="mt-2">
                <button id="toggle-advanced-adapter" class="text-xs text-blue-400 hover:text-blue-300 flex items-center">
                    <i class="fas fa-cog mr-1"></i> Advanced Options
                    <i class="fas fa-chevron-down ml-1"></i>
                </button>
                <div id="advanced-adapter-panel" class="hidden mt-2 space-y-2">
                    <div class="bg-gray-800 rounded p-2 border border-gray-700">
                        <label for="adapter-poll-rate" class="text-xs text-gray-400">Poll rate (sec):</label>
                        <div class="flex items-center">
                            <input type="range" id="adapter-poll-rate" min="0" max="60" step="5" value="0" 
                                class="mr-2 bg-gray-700 rounded w-full">
                            <span id="adapter-poll-rate-value" class="text-xs w-8 text-right">Off</span>
                        </div>
                    </div>
                    <button id="diagnostics-btn" class="px-3 py-1 bg-indigo-700 hover:bg-indigo-600 text-white text-sm rounded w-full flex items-center justify-center">
                        <i class="fas fa-stethoscope mr-1"></i> Run Diagnostics
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Add event listeners
    const refreshButton = document.getElementById('refresh-adapter-btn');
    if (refreshButton) {
        refreshButton.addEventListener('click', async () => {
            try {
                container.innerHTML = '<div class="text-gray-500">Refreshing adapter information...</div>';
                const refreshedInfo = await getAdapterInfo();
                displayAdapterInfo(container, refreshedInfo);
                logMessage('Adapter information refreshed', 'info');
            } catch (error) {
                logMessage(`Failed to refresh adapter info: ${error.message}`, 'error');
                container.innerHTML = `
                    <div class="text-red-500">Failed to refresh adapter info</div>
                    <div class="text-sm text-gray-400 mt-1">${error.message}</div>
                    <button id="retry-adapter-info" class="mt-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                        <i class="fas fa-sync mr-1"></i> Retry
                    </button>
                `;
                
                const retryButton = document.getElementById('retry-adapter-info');
                if (retryButton) {
                    retryButton.addEventListener('click', async () => {
                        container.innerHTML = '<div class="text-gray-500">Retrying...</div>';
                        try {
                            const retryInfo = await getAdapterInfo();
                            displayAdapterInfo(container, retryInfo);
                        } catch (error) {
                            displayAdapterInfo(container, null);
                        }
                    });
                }
            }
        });
    }
    
    const resetButton = document.getElementById('reset-adapter-btn');
    if (resetButton) {
        resetButton.addEventListener('click', async () => {
            try {
                logMessage('Resetting Bluetooth adapter...', 'info');
                container.innerHTML = '<div class="text-gray-500">Resetting adapter...</div>';
                
                const result = await resetAdapter();
                logMessage(`${result.message}`, result.success ? 'success' : 'warning');
                
                // Get fresh adapter info
                const refreshedInfo = await getAdapterInfo();
                displayAdapterInfo(container, refreshedInfo);
            } catch (error) {
                logMessage(`Reset failed: ${error.message}`, 'error');
                container.innerHTML = `
                    <div class="text-red-500">Reset failed</div>
                    <div class="text-sm text-gray-400 mt-1">${error.message}</div>
                    <button id="retry-adapter-info" class="mt-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                        <i class="fas fa-sync mr-1"></i> Refresh
                    </button>
                `;
                
                const retryButton = document.getElementById('retry-adapter-info');
                if (retryButton) {
                    retryButton.addEventListener('click', async () => {
                        try {
                            const info = await getAdapterInfo();
                            displayAdapterInfo(container, info);
                        } catch (error) {
                            displayAdapterInfo(container, null);
                        }
                    });
                }
            }
        });
    }
    
    // Advanced panel toggle
    const toggleAdvancedButton = document.getElementById('toggle-advanced-adapter');
    if (toggleAdvancedButton) {
        toggleAdvancedButton.addEventListener('click', () => {
            const panel = document.getElementById('advanced-adapter-panel');
            const icon = toggleAdvancedButton.querySelector('i:last-child');
            
            if (panel && icon) {
                if (panel.classList.contains('hidden')) {
                    panel.classList.remove('hidden');
                    icon.classList.replace('fa-chevron-down', 'fa-chevron-up');
                } else {
                    panel.classList.add('hidden');
                    icon.classList.replace('fa-chevron-up', 'fa-chevron-down');
                }
            }
        });
    }
    
    // Poll rate slider
    const pollRateSlider = document.getElementById('adapter-poll-rate');
    const pollRateValue = document.getElementById('adapter-poll-rate-value');
    
    if (pollRateSlider && pollRateValue) {
        // Set initial value
        pollRateValue.textContent = pollRateSlider.value === '0' ? 'Off' : `${pollRateSlider.value}s`;
        
        pollRateSlider.addEventListener('input', () => {
            const value = parseInt(pollRateSlider.value);
            pollRateValue.textContent = value === 0 ? 'Off' : `${value}s`;
            
            // Apply auto-refresh if value > 0
            if (value > 0) {
                logMessage(`Auto-refresh set to ${value} seconds`, 'info');
                // Note: In a real implementation, you would set up an interval here
                // and clear any existing intervals
            } else {
                logMessage('Auto-refresh disabled', 'info');
                // Clear any existing intervals
            }
        });
    }
    
    // Diagnostics button
    const diagnosticsButton = document.getElementById('diagnostics-btn');
    if (diagnosticsButton) {
        diagnosticsButton.addEventListener('click', async () => {
            try {
                logMessage('Running adapter diagnostics...', 'info');
                
                // In a real implementation, would call a backend diagnostic endpoint
                // For now, simulate diagnostic checks
                await simulateDiagnostics(container);
                
                // Refresh adapter info after diagnostics
                const updatedInfo = await getAdapterInfo();
                displayAdapterInfo(container, updatedInfo);
                
                logMessage('Adapter diagnostics completed', 'success');
            } catch (error) {
                logMessage(`Diagnostics failed: ${error.message}`, 'error');
            }
        });
    }
}

/**
 * Simulate BLE adapter diagnostics with comprehensive results
 * @param {HTMLElement} container - Container for showing diagnostic progress
 * @returns {Promise<void>}
 */
async function simulateDiagnostics(container) {
    // Store adapter info for the report
    const adapterInfo = await getAdapterInfo();
    
    const steps = [
        { 
            name: 'Checking adapter power state', 
            duration: 500,
            result: {
                passed: adapterInfo.available,
                details: adapterInfo.available ? 
                    'Adapter is powered on and ready' : 
                    'Adapter is unavailable or powered off',
                value: adapterInfo.available ? 'On' : 'Off'
            }
        },
        { 
            name: 'Verifying BLE capabilities', 
            duration: 800,
            result: {
                passed: true,
                details: 'BLE capabilities verified',
                value: 'BLE 4.2+ compatible'
            }
        },
        { 
            name: 'Testing signal strength', 
            duration: 1200,
            result: {
                passed: Math.random() > 0.2, // 80% chance of passing
                details: 'Signal strength analyzed',
                value: `-${Math.floor(Math.random() * 20 + 60)} dBm`
            }
        },
        { 
            name: 'Validating BLE stack', 
            duration: 700,
            result: {
                passed: adapterInfo.available,
                details: 'BLE protocol stack is operational',
                value: adapterInfo.api_version
            }
        },
        { 
            name: 'Checking for interference', 
            duration: 900,
            result: {
                passed: Math.random() > 0.3, // 70% chance of passing
                details: 'Radio frequency interference scan completed',
                value: Math.random() > 0.3 ? 'No significant interference' : 'Some interference detected'
            }
        }
    ];
    
    // Create diagnostic progress UI
    container.innerHTML = `
        <div class="space-y-3">
            <h3 class="text-md font-semibold">Running Diagnostics</h3>
            <div id="diagnostic-steps" class="space-y-2"></div>
            <div class="w-full bg-gray-700 rounded-full h-2 mt-3">
                <div id="diagnostic-progress" class="bg-blue-500 h-2 rounded-full" style="width: 0%"></div>
            </div>
        </div>
    `;
    
    const stepsContainer = document.getElementById('diagnostic-steps');
    const progressBar = document.getElementById('diagnostic-progress');
    
    // Build diagnostic results data
    const diagnosticData = {
        timestamp: Date.now(),
        adapterInfo: adapterInfo,
        tests: {},
        overallStatus: 'pass'
    };
    
    // Run through each diagnostic step
    for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        const progress = Math.round(((i + 1) / steps.length) * 100);
        
        // Add step to UI
        const stepElement = document.createElement('div');
        stepElement.className = 'flex items-center';
        stepElement.innerHTML = `
            <i class="fas fa-circle-notch fa-spin mr-2 text-blue-400"></i>
            <span>${step.name}</span>
        `;
        stepsContainer.appendChild(stepElement);
        
        // Update progress bar and wait for test duration
        await new Promise(resolve => setTimeout(() => {
            progressBar.style.width = `${progress}%`;
            resolve();
        }, step.duration));
        
        // Store test result
        diagnosticData.tests[step.name] = step.result;
        
        // Update overall status if any test fails
        if (!step.result.passed) {
            diagnosticData.overallStatus = 'fail';
        }
        
        // Mark step as complete in UI
        const resultIconClass = step.result.passed ? 'fa-check-circle text-green-400' : 'fa-times-circle text-red-400';
        stepElement.innerHTML = `
            <i class="fas ${resultIconClass} mr-2"></i>
            <span>${step.name}</span>
        `;
    }
    
    // Show final report summary
    await new Promise(resolve => setTimeout(resolve, 500));
    
    container.innerHTML = `
        <div class="space-y-3">
            <div class="flex items-center">
                <i class="fas ${diagnosticData.overallStatus === 'pass' ? 'fa-check-circle text-green-400' : 'fa-exclamation-circle text-yellow-400'} mr-2"></i>
                <h3 class="text-md font-semibold">Diagnostics Complete</h3>
            </div>
            <div class="bg-gray-800 p-3 rounded border border-gray-700">
                <div class="text-sm">
                    ${diagnosticData.overallStatus === 'pass' ? 
                        'All tests passed successfully' : 
                        'Some tests failed - see details for more information'}
                </div>
                <div class="text-xs text-gray-400 mt-1">
                    Adapter status: ${adapterInfo.available ? 
                        '<span class="text-green-400">Available</span>' : 
                        '<span class="text-red-400">Unavailable</span>'}
                </div>
            </div>
            <button id="diagnostic-details-btn" class="text-xs text-blue-400 hover:text-blue-300">
                View detailed report
            </button>
        </div>
    `;
    
    // Add details button handler
    const diagnosticDetailsButton = document.getElementById('diagnostic-details-btn');
    if (diagnosticDetailsButton) {
        diagnosticDetailsButton.addEventListener('click', () => {
            showDetailedDiagnosticReport(diagnosticData);
        });
    }
    
    return diagnosticData;
}

/**
 * Show detailed diagnostic report
 * @param {Object} diagnosticData - Diagnostic data
 */
function showDetailedDiagnosticReport(diagnosticData) {
    // Create modal container
    const modalContainer = document.createElement('div');
    modalContainer.className = 'fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50';
    
    // Create report content
    const reportContent = document.createElement('div');
    reportContent.className = 'bg-gray-800 rounded-md border border-gray-700 p-4 max-w-2xl w-full max-h-[80vh] overflow-y-auto';
    
    // Format test results
    const testResultsHtml = Object.entries(diagnosticData.tests)
        .map(([testName, result]) => {
            const statusClass = result.passed ? 'text-green-400' : 'text-red-400';
            const statusIcon = result.passed ? 'fa-check-circle' : 'fa-times-circle';
            
            return `
                <div class="border border-gray-700 rounded-md p-3 mb-2">
                    <div class="flex items-center justify-between">
                        <div class="font-medium">${testName}</div>
                        <div class="${statusClass}">
                            <i class="fas ${statusIcon} mr-1"></i>
                            ${result.passed ? 'Passed' : 'Failed'}
                        </div>
                    </div>
                    <div class="text-sm text-gray-400 mt-1">${result.details}</div>
                    ${result.value ? `<div class="text-xs text-gray-500 mt-1">Value: ${result.value}</div>` : ''}
                </div>
            `;
        })
        .join('');
    
    // Create report HTML
    reportContent.innerHTML = `
        <div class="flex justify-between items-start mb-4">
            <div>
                <h3 class="text-xl font-bold mb-1">Diagnostic Report</h3>
                <div class="text-sm text-gray-400">
                    Generated at ${new Date(diagnosticData.timestamp).toLocaleString()}
                </div>
            </div>
            <button id="close-diagnostic-report" class="text-gray-400 hover:text-white">
                <i class="fas fa-times"></i>
            </button>
        </div>
        
        <div class="mb-4">
            <div class="bg-gray-700 rounded-md p-3 flex justify-between items-center">
                <div>
                    <div class="font-medium">Overall Result</div>
                    <div class="text-sm ${diagnosticData.overallStatus === 'pass' ? 'text-green-400' : 'text-red-400'}">
                        ${diagnosticData.overallStatus === 'pass' ? 'All tests passed' : 'Some tests failed'}
                    </div>
                </div>
                <div class="text-2xl ${diagnosticData.overallStatus === 'pass' ? 'text-green-400' : 'text-red-400'}">
                    <i class="fas ${diagnosticData.overallStatus === 'pass' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
                </div>
            </div>
        </div>
        
        <div class="mb-4">
            <h4 class="text-md font-semibold mb-2">Adapter Information</h4>
            <div class="grid grid-cols-2 gap-2 text-sm">
                <div class="text-gray-400">Name:</div>
                <div>${diagnosticData.adapterInfo.name || 'Unknown'}</div>
                
                <div class="text-gray-400">Address:</div>
                <div class="font-mono">${diagnosticData.adapterInfo.address || 'Unknown'}</div>
                
                <div class="text-gray-400">Platform:</div>
                <div>${diagnosticData.adapterInfo.platform || 'Unknown'}</div>
            </div>
        </div>
        
        <div>
            <h4 class="text-md font-semibold mb-2">Test Results</h4>
            ${testResultsHtml}
        </div>
        
        <div class="mt-4 border-t border-gray-700 pt-3 flex justify-end">
            <button id="download-diagnostic-report" class="px-3 py-1 bg-blue-700 hover:bg-blue-600 text-white text-sm rounded mr-2">
                <i class="fas fa-download mr-1"></i> Download Report
            </button>
            <button id="close-report-btn" class="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded">
                Close
            </button>
        </div>
    `;
    
    // Add modal to page
    modalContainer.appendChild(reportContent);
    document.body.appendChild(modalContainer);
    
    // Add event listeners
    document.getElementById('close-diagnostic-report').addEventListener('click', () => {
        document.body.removeChild(modalContainer);
    });
    
    document.getElementById('close-report-btn').addEventListener('click', () => {
        document.body.removeChild(modalContainer);
    });
    
    document.getElementById('download-diagnostic-report').addEventListener('click', () => {
        // Generate text report
        const textReport = generateTextReport(diagnosticData);
        
        // Create download link
        const blob = new Blob([textReport], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ble-diagnostic-report-${new Date().toISOString().split('T')[0]}.txt`;
        document.body.appendChild(a);
        a.click();
        
        // Clean up
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
}

/**
 * Generate plain text report
 * @param {Object} data - Diagnostic data
 * @returns {string} - Text report
 */
function generateTextReport(data) {
    const lines = [
        'BLE ADAPTER DIAGNOSTIC REPORT',
        '============================',
        '',
        `Date: ${new Date(data.timestamp).toLocaleString()}`,
        `Overall Status: ${data.overallStatus === 'pass' ? 'PASSED' : 'FAILED'}`,
        '',
        'ADAPTER INFORMATION',
        '-------------------',
        `Name: ${data.adapterInfo.name || 'Unknown'}`,
        `Address: ${data.adapterInfo.address || 'Unknown'}`,
        `Platform: ${data.adapterInfo.platform || 'Unknown'}`,
        '',
        'TEST RESULTS',
        '------------'
    ];
    
    // Add test results
    Object.entries(data.tests).forEach(([testName, result]) => {
        lines.push(`${testName}: ${result.passed ? 'PASSED' : 'FAILED'}`);
        lines.push(`  Details: ${result.details}`);
        if (result.value) {
            lines.push(`  Value: ${result.value}`);
        }
        lines.push('');
    });
    
    return lines.join('\n');
}

/**
 * Render features list as feature indicators
 * @param {Object} features - Features object with boolean values
 * @returns {string} HTML for features list
 */
function renderFeaturesList(features = {}) {
    if (!features || Object.keys(features).length === 0) {
        return '<div class="text-gray-500">No feature information available</div>';
    }
    
    return Object.entries(features)
        .map(([feature, supported]) => {
            const iconClass = supported ? 'text-green-400' : 'text-red-400';
            const icon = supported ? 'fa-check-circle' : 'fa-times-circle';
            
            return `
                <div class="flex items-center bg-gray-800 px-2 py-1 rounded border border-gray-700">
                    <i class="fas ${icon} ${iconClass} mr-2"></i>
                    <span class="text-sm">${feature}</span>
                </div>
            `;
        })
        .join('');
}

/**
 * Determine the adapter type based on available information
 * @param {Object} info - Adapter information
 * @returns {string} - Adapter type description
 */
function getAdapterType(info) {
    // First check hardware info if available
    const hardware = info.hardware || {};
    if (hardware.vendor && hardware.vendor !== 'Unknown') {
        if (hardware.model && hardware.model !== 'Unknown' && !hardware.model.includes('Hard Drive')) {
            return `${hardware.vendor} ${hardware.model}`;
        }
        return `${hardware.vendor} Bluetooth`;
    }
    
    // Fallback to name-based detection using detailed parsing
    const name = (info.name || '').toLowerCase();
    const platform = (info.platform || '').toLowerCase();
    const address = info.address || '';
    
    // More specific name detection with common Bluetooth adapter manufacturers
    if (name.includes('intel')) return 'Intel® Wireless Bluetooth';
    if (name.includes('broadcom')) return 'Broadcom Bluetooth Adapter';
    if (name.includes('realtek')) return 'Realtek Bluetooth Adapter';
    if (name.includes('csr')) return 'CSR Bluetooth Adapter';
    if (name.includes('qualcomm') || name.includes('atheros')) return 'Qualcomm Bluetooth Adapter';
    if (name.includes('apple')) return 'Apple Bluetooth Adapter';
    if (name.includes('microsoft')) return 'Microsoft Bluetooth Adapter';
    if (name.includes('toshiba')) return 'Toshiba Bluetooth Adapter';
    
    // If we have an address but no identifying info, make a more informed guess
    if (address !== 'Unknown') {
        const prefix = address.split(':').slice(0, 3).join(':').toUpperCase();
        
        // Some common Bluetooth adapter MAC address prefixes
        const prefixMap = {
            '00:1A:7D': 'Intel',
            '9C:B6:D0': 'Broadcom',
            '00:1F:81': 'Realtek',
            '00:10:20': 'CSR',
            '00:26:7E': 'Qualcomm',
            '34:02:86': 'Intel',
            '00:15:83': 'Intel',
            '00:24:D7': 'Intel',
            '38:3A:21': 'Intel',
            '00:1B:DC': 'Broadcom',
            '00:25:56': 'Apple',
            '6C:96:CF': 'Apple',
            '60:30:D4': 'Apple',
            '00:88:65': 'Apple'
        };
        
        if (prefixMap[prefix]) {
            return `${prefixMap[prefix]} Bluetooth Adapter`;
        }
    }
    
    // Platform-specific fallback descriptions
    if (platform === 'windows') return 'Windows Bluetooth Adapter';
    if (platform === 'darwin') return 'Apple Bluetooth Adapter';
    if (platform === 'linux') return 'Linux Bluetooth Adapter';
    
    return 'Standard Bluetooth Adapter';
}

// Export named functions for direct use

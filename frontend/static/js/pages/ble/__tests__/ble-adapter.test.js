import { logMessage } from './ble-ui.js';

/**
 * Initialize the Bluetooth adapter info card
 * @param {Object} state - Application state
 */
export function initializeAdapterInfo(state) {
    // Get adapter info container
    const adapterInfoContent = document.getElementById('adapter-info-content');
    if (!adapterInfoContent) {
        console.error('Adapter info content element not found');
        return;
    }
    
    // Initially show loading state
    adapterInfoContent.innerHTML = '<div class="animate-pulse text-gray-500">Loading adapter information...</div>';
    
    // Fetch adapter information
    getAdapterInfo()
        .then(info => {
            displayAdapterInfo(adapterInfoContent, info);
        })
        .catch(error => {
            console.error('Error getting adapter info:', error);
            adapterInfoContent.innerHTML = `
                <div class="text-red-500">Failed to get adapter information</div>
                <div class="text-sm text-gray-400 mt-1">${error.message}</div>
                <button id="retry-adapter-info" class="mt-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                    <i class="fas fa-sync mr-1"></i> Retry
                </button>
            `;
            
            // Add retry button handler
            const retryBtn = document.getElementById('retry-adapter-info');
            if (retryBtn) {
                retryBtn.addEventListener('click', () => initializeAdapterInfo(state));
            }
        });
}

/**
 * Get Bluetooth adapter information
 * @returns {Promise<Object>} - Adapter information
 */
export async function getAdapterInfo() {
    try {
        const response = await fetch('/api/ble/adapter-info');
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to get adapter info: ${errorText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error fetching adapter info:', error);
        throw error;
    }
}

/**
 * Display adapter information
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
    
    container.innerHTML = `
        <div class="space-y-3">
            <div class="flex items-center">
                <div class="w-3 h-3 rounded-full ${statusColor} mr-2"></div>
                <span class="font-medium">${statusText}</span>
            </div>
            
            <div class="grid grid-cols-2 gap-y-2 text-sm">
                <div class="text-gray-400">Name:</div>
                <div class="text-white">${info.name || 'Unknown'}</div>
                
                <div class="text-gray-400">Address:</div>
                <div class="text-white">${info.address || 'Unknown'}</div>
                
                <div class="text-gray-400">Platform:</div>
                <div class="text-white">${info.platform || 'Unknown'}</div>
                
                <div class="text-gray-400">API Version:</div>
                <div class="text-white">${info.api_version || 'Unknown'}</div>
            </div>
            
            <div class="mt-2">
                <div class="text-gray-400 text-sm mb-1">Supported Features:</div>
                <div class="flex flex-wrap gap-1">
                    ${renderFeatureBadges(info.features)}
                </div>
            </div>
            
            <button id="refresh-adapter-info" class="mt-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                <i class="fas fa-sync mr-1"></i> Refresh
            </button>
        </div>
    `;
    
    // Add refresh button handler
    const refreshBtn = document.getElementById('refresh-adapter-info');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            try {
                container.innerHTML = '<div class="animate-pulse text-gray-500">Refreshing adapter information...</div>';
                const info = await getAdapterInfo();
                displayAdapterInfo(container, info);
                logMessage('Adapter information refreshed', 'info');
            } catch (error) {
                logMessage(`Failed to refresh adapter info: ${error.message}`, 'error');
                container.innerHTML = `
                    <div class="text-red-500">Failed to refresh adapter information</div>
                    <div class="text-sm text-gray-400 mt-1">${error.message}</div>
                    <button id="retry-adapter-info" class="mt-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                        <i class="fas fa-sync mr-1"></i> Retry
                    </button>
                `;
            }
        });
    }
}

/**
 * Render feature badges based on supported features
 * @param {Object} features - Supported features
 * @returns {String} - HTML for feature badges
 */
function renderFeatureBadges(features) {
    if (!features || Object.keys(features).length === 0) {
        return '<span class="text-gray-500">No information available</span>';
    }
    
    return Object.entries(features)
        .map(([feature, supported]) => {
            const color = supported ? 'bg-green-700' : 'bg-gray-700';
            const icon = supported ? 'fa-check' : 'fa-times';
            return `
                <span class="${color} px-2 py-1 rounded text-xs">
                    <i class="fas ${icon} mr-1"></i>${feature}
                </span>
            `;
        })
        .join('');
}

/**
 * Reset the Bluetooth adapter
 * @returns {Promise<boolean>} - Success status
 */
export async function resetAdapter() {
    try {
        logMessage('Attempting to reset Bluetooth adapter...', 'info');
        
        const response = await fetch('/api/ble/recovery/reset-adapter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to reset adapter: ${errorText}`);
        }
        
        const result = await response.json();
        logMessage(`Adapter reset ${result.status === 'success' ? 'successful' : 'failed'}`, 
                  result.status === 'success' ? 'success' : 'error');
        
        return result.status === 'success';
    } catch (error) {
        console.error('Error resetting adapter:', error);
        logMessage(`Adapter reset failed: ${error.message}`, 'error');
        return false;
    }
}
import { BleUI } from '/static/js/ble-ui.js';

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
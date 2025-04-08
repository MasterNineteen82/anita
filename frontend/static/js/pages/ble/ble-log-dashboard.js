import { BleLogger } from './ble-logger.js';

export class BleLogDashboard {
    static initialize() {
        const logContainer = document.getElementById('ble-log-container');
        if (!logContainer) return;
        
        // Add log controls
        const controls = document.createElement('div');
        controls.className = 'log-controls flex space-x-2 mb-2';
        controls.innerHTML = `
            <select id="log-level-filter" class="bg-gray-800 text-white px-2 py-1 text-sm rounded">
                <option value="ALL">All Levels</option>
                <option value="TRACE">Trace & Above</option>
                <option value="DEBUG">Debug & Above</option>
                <option value="INFO">Info & Above</option>
                <option value="WARN">Warnings & Above</option>
                <option value="ERROR">Errors Only</option>
            </select>
            <select id="log-component-filter" class="bg-gray-800 text-white px-2 py-1 text-sm rounded">
                <option value="ALL">All Components</option>
            </select>
            <button id="export-logs-btn" class="bg-blue-600 text-white px-2 py-1 text-sm rounded">
                Export Logs
            </button>
            <button id="clear-logs-btn" class="bg-red-600 text-white px-2 py-1 text-sm rounded">
                Clear Logs
            </button>
        `;
        
        logContainer.parentNode.insertBefore(controls, logContainer);
        
        // Setup event listeners
        document.getElementById('log-level-filter').addEventListener('change', this.applyFilters);
        document.getElementById('log-component-filter').addEventListener('change', this.applyFilters);
        document.getElementById('export-logs-btn').addEventListener('click', this.exportLogs);
        document.getElementById('clear-logs-btn').addEventListener('click', this.clearLogs);
        
        // Initialize component dropdown (populated from actual logs)
        this.updateComponentDropdown();
        
        // Start periodic updates of component list
        setInterval(() => this.updateComponentDropdown(), 5000);
    }
    
    static updateComponentDropdown() {
        const componentSelect = document.getElementById('log-component-filter');
        if (!componentSelect) return;
        
        // Get unique components from log history
        const components = [...new Set(BleLogger.logHistory.map(log => log.component))];
        
        // Save current selection
        const currentSelection = componentSelect.value;
        
        // Keep the first option (ALL)
        const firstOption = componentSelect.options[0];
        componentSelect.innerHTML = '';
        componentSelect.appendChild(firstOption);
        
        // Add all components
        components.forEach(component => {
            if (!component) return;
            
            const option = document.createElement('option');
            option.value = component;
            option.textContent = component;
            componentSelect.appendChild(option);
        });
        
        // Restore selection if possible
        if (components.includes(currentSelection)) {
            componentSelect.value = currentSelection;
        }
    }
    
    static applyFilters() {
        const levelFilter = document.getElementById('log-level-filter').value;
        const componentFilter = document.getElementById('log-component-filter').value;
        
        // Apply filters to UI logs
        const logContainer = document.getElementById('ble-log-container');
        if (!logContainer) return;
        
        const logEntries = logContainer.querySelectorAll('.log-entry');
        logEntries.forEach(entry => {
            const entryLevel = entry.getAttribute('data-level') || 'INFO';
            const entryComponent = entry.getAttribute('data-component') || '';
            
            const levelMatch = levelFilter === 'ALL' || 
                              BleLogger.LOG_LEVELS[entryLevel] >= BleLogger.LOG_LEVELS[levelFilter];
            const componentMatch = componentFilter === 'ALL' || entryComponent === componentFilter;
            
            entry.style.display = levelMatch && componentMatch ? 'block' : 'none';
        });
    }
    
    static exportLogs() {
        const logs = BleLogger.exportLogs();
        const blob = new Blob([logs], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `ble-logs-${new Date().toISOString().replace(/:/g, '-')}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    static clearLogs() {
        BleLogger.clearHistory();
        const logContainer = document.getElementById('ble-log-container');
        if (logContainer) {
            logContainer.innerHTML = '';
        }
    }
}
import { BleLogger } from './ble-logger.js';
import { BlePerformanceMonitor } from './ble-performance-monitor.js';

export class BleDiagnostics {
    /**
     * Create a complete diagnostic snapshot
     * @param {Object} appState - Application state
     * @returns {Object} Diagnostic information
     */
    static createSnapshot(appState) {
        BleLogger.info('Diagnostics', 'snapshot', 'Creating system diagnostic snapshot');
        
        const snapshot = {
            timestamp: new Date().toISOString(),
            browser: {
                userAgent: navigator.userAgent,
                language: navigator.language,
                platform: navigator.platform,
                bluetooth: 'bluetooth' in navigator ? 'available' : 'unavailable'
            },
            state: {
                isScanning: appState.isScanning,
                connectedDevice: appState.connectedDevice,
                adapter: appState.adapter,
                subscribedCount: appState.subscribedCharacteristics?.size || 0
            },
            performance: BlePerformanceMonitor.getReport(),
            recentLogs: BleLogger.logHistory.slice(-50) // Last 50 logs
        };
        
        BleLogger.debug('Diagnostics', 'snapshot', 'Diagnostic snapshot created');
        
        return snapshot;
    }
    
    /**
     * Save diagnostic snapshot to file
     */
    static async saveSnapshot(appState) {
        const snapshot = this.createSnapshot(appState);
        const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `ble-diagnostic-${new Date().toISOString().replace(/:/g, '-')}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        BleLogger.info('Diagnostics', 'save', 'Diagnostic snapshot saved to file');
    }
    
    /**
     * Run active diagnostics
     */
    static async runActiveDiagnostics(appState) {
        BleLogger.info('Diagnostics', 'run', 'Running active diagnostics');
        
        const results = {
            timestamp: new Date().toISOString(),
            adapterCheck: false,
            scanCheck: false,
            webSocketCheck: false
        };
        
        // Check adapter
        try {
            const adapterInfo = await appState.adapter.getAdapterInfo();
            results.adapterCheck = true;
            results.adapterInfo = adapterInfo;
        } catch (error) {
            BleLogger.error('Diagnostics', 'adapterCheck', 'Adapter check failed', {
                error: error.message
            });
            results.adapterError = error.message;
        }
        
        // Check WebSocket
        try {
            if (appState.bleWebSocket) {
                const wsState = appState.bleWebSocket.socket?.readyState;
                results.webSocketCheck = wsState === WebSocket.OPEN;
                results.webSocketState = wsState;
            }
        } catch (error) {
            BleLogger.error('Diagnostics', 'websocketCheck', 'WebSocket check failed', {
                error: error.message
            });
            results.webSocketError = error.message;
        }
        
        BleLogger.info('Diagnostics', 'complete', 'Active diagnostics complete', {
            results: results
        });
        
        return results;
    }
}
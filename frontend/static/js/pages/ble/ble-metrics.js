import { BleUI } from './ble-ui.js';
import { BleEvents } from './ble-events.js';

/**
 * BLE Metrics module for tracking and displaying performance metrics
 */
export class BleMetrics {
    constructor(state = {}) {
        this.state = state;
        
        // Performance metrics
        this.metrics = {
            connectionAttempts: 0,
            connectionSuccesses: 0,
            connectionFailures: 0,
            connectionTimes: [],
            totalDevices: 0,
            notifications: {
                total: 0,
                byCharacteristic: {}
            },
            operations: {
                read: { total: 0, success: 0, failure: 0 },
                write: { total: 0, success: 0, failure: 0 },
                scan: { total: 0, success: 0, failure: 0 }
            },
            scanResults: [],
            lastUpdate: Date.now()
        };
        
        // UI elements
        this.uiElements = {
            connectionSuccessRate: null,
            avgConnectionTime: null,
            deviceCount: null,
            notificationRate: null,
            refreshMetricsBtn: null
        };
    }

    /**
     * Initialize the metrics module
     */
    async initialize() {
        console.log('Initializing BLE Metrics module');
        
        // Get UI elements
        this.uiElements.connectionSuccessRate = document.getElementById('connection-success-rate');
        this.uiElements.avgConnectionTime = document.getElementById('avg-connection-time');
        this.uiElements.deviceCount = document.getElementById('device-count');
        this.uiElements.notificationRate = document.getElementById('notification-rate');
        this.uiElements.refreshMetricsBtn = document.getElementById('refresh-metrics-btn');
        
        // Add event listeners
        if (this.uiElements.refreshMetricsBtn) {
            this.uiElements.refreshMetricsBtn.addEventListener('click', () => this.refreshMetrics());
        }
        
        // Register event handlers
        BleEvents.on('DEVICE_CONNECTED', (data) => this.recordConnectionSuccess(data.deviceId));
        BleEvents.on('CHARACTERISTIC_NOTIFICATION', (data) => this.recordNotification(data.uuid));
        BleEvents.on('SCAN_COMPLETED', (data) => this.recordScanCompletion(data.devices?.length || 0));
        
        // Update UI initially
        this.updateUI();
        
        // Set up auto-refresh
        setInterval(() => this.updateUI(), 30000); // Refresh every 30 seconds
    }

    /**
     * Record a connection attempt
     * @param {string} deviceId - Device identifier
     */
    recordConnectionAttempt(deviceId) {
        this.metrics.connectionAttempts++;
        
        // Track start time to calculate connection duration
        this.metrics.connectionStartTime = Date.now();
    }

    /**
     * Record a successful connection
     * @param {string} deviceId - Device identifier
     */
    recordConnectionSuccess(deviceId) {
        this.metrics.connectionSuccesses++;
        
        // Calculate and record connection time
        if (this.metrics.connectionStartTime) {
            const connectionTime = Date.now() - this.metrics.connectionStartTime;
            this.metrics.connectionTimes.push(connectionTime);
            
            // Keep only the last 10 connection times
            if (this.metrics.connectionTimes.length > 10) {
                this.metrics.connectionTimes.shift();
            }
        }
        
        // Update UI
        this.updateUI();
    }

    /**
     * Record a connection failure
     * @param {string} deviceId - Device identifier
     * @param {string} reason - Failure reason
     */
    recordConnectionFailure(deviceId, reason) {
        this.metrics.connectionFailures++;
        
        // Update UI
        this.updateUI();
    }

    /**
     * Record a characteristic notification
     * @param {string} characteristicUuid - Characteristic UUID
     */
    recordNotification(characteristicUuid) {
        this.metrics.notifications.total++;
        
        // Track by characteristic
        if (!this.metrics.notifications.byCharacteristic[characteristicUuid]) {
            this.metrics.notifications.byCharacteristic[characteristicUuid] = 0;
        }
        this.metrics.notifications.byCharacteristic[characteristicUuid]++;
        
        // Update UI if we've received several notifications
        if (this.metrics.notifications.total % 5 === 0) {
            this.updateUI();
        }
    }

    /**
     * Record a scan completion
     * @param {number} deviceCount - Number of devices found
     */
    recordScanCompletion(deviceCount) {
        this.metrics.operations.scan.total++;
        this.metrics.operations.scan.success++;
        
        // Update total unique devices
        if (deviceCount > this.metrics.totalDevices) {
            this.metrics.totalDevices = deviceCount;
        }
        
        // Update UI
        this.updateUI();
    }

    /**
     * Calculate performance metrics
     * @returns {Object} - Calculated metrics
     */
    calculateMetrics() {
        // Connection success rate
        const successRate = this.metrics.connectionAttempts > 0 
            ? (this.metrics.connectionSuccesses / this.metrics.connectionAttempts * 100).toFixed(1) 
            : 'N/A';
        
        // Average connection time
        const avgConnectionTime = this.metrics.connectionTimes.length > 0
            ? (this.metrics.connectionTimes.reduce((a, b) => a + b, 0) / this.metrics.connectionTimes.length).toFixed(0)
            : 'N/A';
        
        // Notification rate (per minute)
        let notificationRate = 'N/A';
        const elapsedMinutes = (Date.now() - this.metrics.lastUpdate) / 60000;
        if (elapsedMinutes > 0 && this.metrics.notifications.total > 0) {
            notificationRate = (this.metrics.notifications.total / elapsedMinutes).toFixed(1);
        }
        
        return {
            successRate: successRate === 'N/A' ? successRate : `${successRate}%`,
            avgConnectionTime: avgConnectionTime === 'N/A' ? avgConnectionTime : `${avgConnectionTime}ms`,
            deviceCount: this.metrics.totalDevices,
            notificationRate: notificationRate === 'N/A' ? notificationRate : `${notificationRate}/min`
        };
    }

    /**
     * Update metrics UI
     */
    updateUI() {
        const metrics = this.calculateMetrics();
        
        // Update UI elements
        if (this.uiElements.connectionSuccessRate) {
            this.uiElements.connectionSuccessRate.textContent = metrics.successRate;
        }
        
        if (this.uiElements.avgConnectionTime) {
            this.uiElements.avgConnectionTime.textContent = metrics.avgConnectionTime;
        }
        
        if (this.uiElements.deviceCount) {
            this.uiElements.deviceCount.textContent = metrics.deviceCount;
        }
        
        if (this.uiElements.notificationRate) {
            this.uiElements.notificationRate.textContent = metrics.notificationRate;
        }
    }

    /**
     * Refresh metrics display
     */
    refreshMetrics() {
        // Get metrics via API
        fetch('/api/ble/metrics')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch metrics');
                }
                return response.json();
            })
            .then(data => {
                // Update metrics with data from server
                this.metrics = { ...this.metrics, ...data };
                this.updateUI();
                BleUI.showToast('Metrics refreshed', 'success');
            })
            .catch(error => {
                console.error('Error refreshing metrics:', error);
                BleUI.showToast(`Failed to refresh metrics: ${error.message}`, 'error');
            });
    }

    /**
     * Reset all metrics
     */
    resetMetrics() {
        // Reset local metrics
        this.metrics = {
            connectionAttempts: 0,
            connectionSuccesses: 0,
            connectionFailures: 0,
            connectionTimes: [],
            totalDevices: 0,
            notifications: {
                total: 0,
                byCharacteristic: {}
            },
            operations: {
                read: { total: 0, success: 0, failure: 0 },
                write: { total: 0, success: 0, failure: 0 },
                scan: { total: 0, success: 0, failure: 0 }
            },
            scanResults: [],
            lastUpdate: Date.now()
        };
        
        // Update UI
        this.updateUI();
        
        // Attempt to reset server metrics
        fetch('/api/ble/metrics/reset', { method: 'POST' })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to reset metrics on server');
                }
                return response.json();
            })
            .then(data => {
                BleUI.showToast('Metrics reset successfully', 'success');
            })
            .catch(error => {
                console.error('Error resetting metrics:', error);
                // We've already reset local metrics, so just show a warning
                BleUI.showToast(`Server metrics reset failed: ${error.message}`, 'warning');
            });
    }
}
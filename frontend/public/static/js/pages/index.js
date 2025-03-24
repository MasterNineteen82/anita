import API from '../core/api.js';
import ReaderManager from '../components/readers.js';
import logger from '../core/logger.js';
import UI from '../utils/ui.js';
import { getElement } from '../utils/dom.js';
import { loadFromStorage, formatDate } from '../base/utils.js';

/**
 * Dashboard controller for the index page
 */
class DashboardController {
    constructor() {
        this.api = new API();
        this.readerManager = new ReaderManager(this.api);
        this.recentOperations = [];
        this.maxRecentOperations = 5;
        this.refreshInterval = null;

        // Element references
        this.readersContainer = getElement('readers-status');
        this.systemStatusContainer = getElement('system-status');
        this.recentActivityContainer = getElement('recent-activity');
        this.quickLinksContainer = getElement('quick-links');

        // Initialization
        this.initialize();
    }

    async initialize() {
        logger.info('Initializing dashboard controller');
        
        try {
            // Initialize reader manager
            await this.readerManager.initialize();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Load dashboard components
            this.loadDashboardComponents();
            
            // Start automatic refresh
            this.startAutoRefresh();
            
            // Signal success
            UI.showToast('Dashboard initialized successfully', 'success');
        } catch (error) {
            logger.error('Error initializing dashboard', { error });
            UI.showToast('Error initializing dashboard', 'error');
        }
    }

    setupEventListeners() {
        // Listen for reader changes
        this.readerManager.on('readersUpdated', (readers) => this.updateReadersStatus(readers));
        this.readerManager.on('cardStatusChanged', (present, data) => this.handleCardStatusChanged(present, data));
        
        // Setup refresh button
        const refreshBtn = getElement('refresh-dashboard');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshDashboard());
        }
        
        // Setup quick action buttons
        this.setupQuickActionButtons();
    }

    setupQuickActionButtons() {
        // Example quick action setup
        const scanBtn = getElement('quick-scan');
        if (scanBtn) {
            scanBtn.addEventListener('click', () => this.performQuickScan());
        }
    }

    loadDashboardComponents() {
        this.updateSystemStatus();
        this.loadRecentOperations();
        this.populateQuickLinks();
    }

    async updateReadersStatus(readers) {
        if (!this.readersContainer) return;
        
        if (!readers || readers.length === 0) {
            this.readersContainer.innerHTML = '<div class="alert alert-warning">No readers detected</div>';
            return;
        }
        
        let html = '<div class="readers-list">';
        readers.forEach(reader => {
            const statusClass = reader.connected ? 'success' : 'danger';
            const statusText = reader.connected ? 'Connected' : 'Disconnected';
            
            html += `
                <div class="reader-item">
                    <span class="reader-name">${reader.name}</span>
                    <span class="reader-type">${reader.type || 'Unknown'}</span>
                    <span class="reader-status ${statusClass}">${statusText}</span>
                    <button class="btn btn-sm btn-primary select-reader" data-reader="${reader.name}">Select</button>
                </div>
            `;
        });
        html += '</div>';
        
        this.readersContainer.innerHTML = html;
        
        // Add event listeners to select buttons
        document.querySelectorAll('.select-reader').forEach(btn => {
            btn.addEventListener('click', () => this.selectReader(btn.dataset.reader));
        });
    }

    async updateSystemStatus() {
        if (!this.systemStatusContainer) return;
        
        try {
            const response = await this.api.get('/system/status');
            if (response.status === 'success') {
                const { version, uptime, memoryUsage, activeOperations } = response.data;
                
                this.systemStatusContainer.innerHTML = `
                    <div class="status-item">
                        <span class="status-label">Version:</span>
                        <span class="status-value">${version}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Uptime:</span>
                        <span class="status-value">${uptime}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Memory:</span>
                        <span class="status-value">${memoryUsage}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Active operations:</span>
                        <span class="status-value">${activeOperations}</span>
                    </div>
                `;
            } else {
                this.systemStatusContainer.innerHTML = '<div class="alert alert-warning">Unable to load system status</div>';
            }
        } catch (error) {
            logger.error('Error fetching system status', { error });
            this.systemStatusContainer.innerHTML = '<div class="alert alert-danger">Error loading system status</div>';
        }
    }

    loadRecentOperations() {
        if (!this.recentActivityContainer) return;
        
        // Try to load recent operations from storage
        const savedOperations = loadFromStorage('recent-operations', []);
        this.recentOperations = savedOperations;
        
        this.updateRecentOperationsUI();
    }

    updateRecentOperationsUI() {
        if (!this.recentActivityContainer || !this.recentOperations.length) {
            this.recentActivityContainer.innerHTML = '<div class="text-muted">No recent activity recorded</div>';
            return;
        }
        
        let html = '<div class="recent-operations">';
        this.recentOperations.slice(0, this.maxRecentOperations).forEach(op => {
            const statusClass = op.success ? 'success' : 'danger';
            
            html += `
                <div class="operation-item">
                    <div class="operation-time">${formatDate(op.timestamp)}</div>
                    <div class="operation-type">${op.type}</div>
                    <div class="operation-status ${statusClass}">${op.success ? 'Success' : 'Failed'}</div>
                </div>
            `;
        });
        html += '</div>';
        
        this.recentActivityContainer.innerHTML = html;
    }

    populateQuickLinks() {
        if (!this.quickLinksContainer) return;
        
        // Example quick links based on common operations
        const quickLinks = [
            { name: 'Scan Card', icon: '🔎', action: 'scan', color: 'primary' },
            { name: 'Read NFC Tag', icon: '📱', action: 'read-nfc', color: 'info' },
            { name: 'MIFARE Auth', icon: '🔑', action: 'mifare-auth', color: 'warning' },
            { name: 'Settings', icon: '⚙️', action: 'settings', color: 'secondary' }
        ];
        
        let html = '<div class="quick-links-grid">';
        quickLinks.forEach(link => {
            html += `
                <div class="quick-link-item ${link.color}" data-action="${link.action}">
                    <div class="quick-link-icon">${link.icon}</div>
                    <div class="quick-link-name">${link.name}</div>
                </div>
            `;
        });
        html += '</div>';
        
        this.quickLinksContainer.innerHTML = html;
        
        // Add event listeners
        document.querySelectorAll('.quick-link-item').forEach(item => {
            item.addEventListener('click', () => this.handleQuickLink(item.dataset.action));
        });
    }

    async selectReader(readerName) {
        try {
            await this.readerManager.selectReader(readerName);
            UI.showToast(`Reader "${readerName}" selected`, 'success');
        } catch (error) {
            logger.error('Error selecting reader', { error, reader: readerName });
            UI.showToast(`Failed to select reader: ${error.message}`, 'error');
        }
    }

    handleCardStatusChanged(present, data) {
        if (present) {
            UI.showToast('Card detected', 'info');
            this.addRecentOperation({
                type: 'Card Detection',
                success: true,
                timestamp: new Date(),
                details: data
            });
        }
    }

    addRecentOperation(operation) {
        this.recentOperations.unshift(operation);
        
        // Trim to max length
        if (this.recentOperations.length > this.maxRecentOperations) {
            this.recentOperations = this.recentOperations.slice(0, this.maxRecentOperations);
        }
        
        // Save to storage
        localStorage.setItem('recent-operations', JSON.stringify(this.recentOperations));
        
        // Update UI
        this.updateRecentOperationsUI();
    }

    handleQuickLink(action) {
        switch (action) {
            case 'scan':
                this.performQuickScan();
                break;
            case 'read-nfc':
                window.location.href = '/nfc';
                break;
            case 'mifare-auth':
                window.location.href = '/mifare';
                break;
            case 'settings':
                window.location.href = '/settings';
                break;
            default:
                logger.warn('Unknown quick link action', { action });
        }
    }

    async performQuickScan() {
        const reader = this.readerManager.getSelectedReader();
        if (!reader) {
            UI.showToast('Please select a reader first', 'warning');
            return;
        }
        
        try {
            UI.showToast('Scanning card...', 'info');
            const response = await this.api.get(`/smartcard/scan?reader=${encodeURIComponent(reader)}`);
            
            if (response.status === 'success') {
                UI.showToast('Card scan complete', 'success');
                
                // Show results in modal
                UI.showModal('Card Scan Results', `<pre>${JSON.stringify(response.data, null, 2)}</pre>`, {
                    confirm: () => console.log('Modal closed')
                }, {
                    confirmText: 'Close',
                    showCancel: false
                });
                
                this.addRecentOperation({
                    type: 'Quick Scan',
                    success: true,
                    timestamp: new Date(),
                    details: response.data
                });
            } else {
                UI.showToast(`Scan failed: ${response.message}`, 'error');
            }
        } catch (error) {
            logger.error('Error performing quick scan', { error });
            UI.showToast(`Scan error: ${error.message}`, 'error');
        }
    }

    refreshDashboard() {
        UI.showToast('Refreshing dashboard...', 'info');
        this.readerManager.fetchReaders();
        this.updateSystemStatus();
    }

    startAutoRefresh() {
        // Refresh dashboard every 30 seconds
        this.refreshInterval = setInterval(() => {
            if (!document.hidden) {
                this.refreshDashboard();
            }
        }, 30000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    dispose() {
        this.stopAutoRefresh();
        if (this.readerManager) {
            this.readerManager.dispose();
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    logger.info('Index page loaded');
    
    // Create dashboard controller
    const dashboard = new DashboardController();
    
    // Save instance for debugging
    window.dashboard = dashboard;
    
    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        dashboard.dispose();
    });
});
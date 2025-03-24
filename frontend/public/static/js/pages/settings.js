import API from '../core/api.js';
import UI from '../utils/ui.js';

/**
 * Settings page functionality with proper error handling
 */
class SettingsPage {
    constructor() {
        this.elements = {};
        this.settings = {};
        this.initialized = false;
    }
    
    /**
     * Initialize the settings page with proper error handling
     */
    async initialize() {
        try {
            // Safely cache DOM elements
            this._cacheElements();
            
            // Load initial settings
            await this._loadSettings();
            
            // Set up event listeners
            this._setupEventListeners();
            
            // Start uptime timer
            this._setupUptimeTimer();
            
            this.initialized = true;
            console.log('Settings page initialized');
        } catch (error) {
            console.error('Failed to initialize settings page:', error);
            UI.showToast('Error loading settings page. Please try again.', 'error');
        }
    }
    
    /**
     * Safely get and cache DOM elements
     * @private
     */
    _cacheElements() {
        const elementIds = [
            'theme-setting', 
            'logging-setting', 
            'auto-refresh-setting',
            'refresh-interval', 
            'simulation-mode',
            'save-settings', 
            'refresh-system-info',
            'uptime'
        ];
        
        elementIds.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                this.elements[id] = element;
            } else {
                console.warn(`Element not found: ${id}`);
            }
        });
        
        // Check if we have the minimum required elements
        if (!this.elements['save-settings']) {
            throw new Error('Required elements missing from page');
        }
    }
    
    /**
     * Load settings from API with fallback
     * @private
     */
    async _loadSettings() {
        // First try to load from localStorage as fallback
        const storedSettings = localStorage.getItem('user-settings');
        if (storedSettings) {
            try {
                this.settings = JSON.parse(storedSettings);
            } catch (e) {
                console.warn('Error parsing stored settings', e);
            }
        }
        
        // Then try to get from API
        try {
            const response = await fetch('/api/settings');
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success') {
                    this.settings = {...this.settings, ...data.data};
                    this._applySettingsToForm();
                }
            }
        } catch (e) {
            console.warn('Could not load settings from server', e);
            // Continue with localStorage settings
        }
    }
    
    /**
     * Apply loaded settings to form elements
     * @private
     */
    _applySettingsToForm() {
        // Safely set form values
        if (this.elements['theme-setting'] && typeof this.settings.theme === 'string') {
            this.elements['theme-setting'].checked = this.settings.theme === 'dark';
        }
        
        if (this.elements['logging-setting'] && typeof this.settings.logging_enabled === 'boolean') {
            this.elements['logging-setting'].checked = this.settings.logging_enabled;
        }
        
        if (this.elements['auto-refresh-setting'] && typeof this.settings.auto_refresh === 'boolean') {
            this.elements['auto-refresh-setting'].checked = this.settings.auto_refresh;
        }
        
        if (this.elements['refresh-interval'] && typeof this.settings.refresh_interval === 'number') {
            this.elements['refresh-interval'].value = this.settings.refresh_interval;
        }
        
        if (this.elements['simulation-mode'] && typeof this.settings.simulation_mode === 'boolean') {
            this.elements['simulation-mode'].checked = this.settings.simulation_mode;
        }
    }
    
    /**
     * Set up form event listeners
     * @private
     */
    _setupEventListeners() {
        // Save settings button
        if (this.elements['save-settings']) {
            this.elements['save-settings'].addEventListener('click', () => this._saveSettings());
        }
        
        // Refresh system info button
        if (this.elements['refresh-system-info']) {
            this.elements['refresh-system-info'].addEventListener('click', () => this._refreshSystemInfo());
        }
        
        // Theme setting preview
        if (this.elements['theme-setting']) {
            this.elements['theme-setting'].addEventListener('change', (e) => {
                document.body.classList.toggle('dark-theme', e.target.checked);
                document.body.classList.toggle('light-theme', !e.target.checked);
            });
        }
    }
    
    /**
     * Set up uptime timer
     * @private
     */
    _setupUptimeTimer() {
        if (!this.elements['uptime']) return;
        
        // Find start time from data attribute
        const startTimeElements = document.querySelectorAll('[data-start-time]');
        let startTime = 0;
        
        if (startTimeElements.length > 0) {
            const timeValue = startTimeElements[0].getAttribute('data-start-time');
            startTime = parseInt(timeValue || '0');
        }
        
        // If no start time found, use a reasonable fallback
        if (!startTime) {
            startTime = Math.floor(Date.now() / 1000) - 300; // 5 minutes ago
        }
        
        // Store for uptime calculation
        this.elements['uptime'].dataset.startTime = startTime;
        
        // Start update timer
        this._updateUptime();
        setInterval(() => this._updateUptime(), 1000);
    }
    
    /**
     * Update the uptime display
     * @private
     */
    _updateUptime() {
        if (!this.elements['uptime']) return;
        
        const startTimeStr = this.elements['uptime'].dataset.startTime;
        if (!startTimeStr) return;
        
        const startTime = parseInt(startTimeStr);
        if (isNaN(startTime)) return;
        
        const now = Math.floor(Date.now() / 1000);
        const uptime = now - startTime;
        
        const days = Math.floor(uptime / 86400);
        const hours = Math.floor((uptime % 86400) / 3600);
        const minutes = Math.floor((uptime % 3600) / 60);
        const seconds = uptime % 60;
        
        let uptimeStr = '';
        if (days > 0) uptimeStr += `${days}d `;
        uptimeStr += `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        this.elements['uptime'].textContent = uptimeStr;
    }
    
    /**
     * Save settings to server and localStorage
     * @private
     */
    async _saveSettings() {
        if (!this.elements['save-settings']) return;
        
        try {
            // Show saving state
            const originalText = this.elements['save-settings'].innerHTML;
            this.elements['save-settings'].innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
            this.elements['save-settings'].disabled = true;
            
            // Get values safely
            const settings = {
                theme: this.elements['theme-setting']?.checked ? 'dark' : 'light',
                logging_enabled: this.elements['logging-setting']?.checked || false,
                auto_refresh: this.elements['auto-refresh-setting']?.checked || false,
                refresh_interval: parseInt(this.elements['refresh-interval']?.value || '5000'),
                simulation_mode: this.elements['simulation-mode']?.checked || false
            };
            
            // Validate
            if (isNaN(settings.refresh_interval) || settings.refresh_interval < 1000) {
                UI.showToast('Refresh interval must be at least 1000ms', 'error');
                return;
            }
            
            // Save to localStorage for immediate use
            localStorage.setItem('user-settings', JSON.stringify(settings));
            
            // Send to server
            try {
                const response = await fetch('/api/settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(settings)
                });
                
                if (response.ok) {
                    UI.showToast('Settings saved successfully');
                } else {
                    const data = await response.json();
                    UI.showToast(`Error: ${data.message || 'Failed to save settings'}`, 'error');
                }
            } catch (error) {
                console.error('API error:', error);
                UI.showToast('Settings saved locally but server update failed', 'warning');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            UI.showToast('Error saving settings', 'error');
        } finally {
            // Restore button state
            if (this.elements['save-settings']) {
                this.elements['save-settings'].innerHTML = '<i class="fas fa-save"></i> Save Settings';
                this.elements['save-settings'].disabled = false;
            }
        }
    }
    
    /**
     * Refresh system information
     * @private
     */
    async _refreshSystemInfo() {
        if (!this.elements['refresh-system-info']) return;
        
        try {
            // Show loading state
            const button = this.elements['refresh-system-info'];
            button.classList.add('spinning');
            
            try {
                const response = await fetch('/api/system/info');
                if (response.ok) {
                    const data = await response.json();
                    
                    // Update data attributes with latest info
                    document.querySelectorAll('[data-info]').forEach(el => {
                        const key = el.dataset.info;
                        if (data[key]) {
                            el.textContent = data[key];
                        }
                    });
                    
                    UI.showToast('System information updated');
                } else {
                    UI.showToast('Failed to refresh system information', 'error');
                }
            } catch (error) {
                console.error('API error:', error);
                UI.showToast('Failed to connect to server', 'error');
            }
        } catch (error) {
            console.error('Error refreshing system info:', error);
        } finally {
            // Reset button state
            if (this.elements['refresh-system-info']) {
                this.elements['refresh-system-info'].classList.remove('spinning');
            }
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const settingsPage = new SettingsPage();
    settingsPage.initialize().catch(err => {
        console.error('Settings initialization error:', err);
    });
});

export default new SettingsPage();
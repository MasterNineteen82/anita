/**
 * Reader management functionality
 */
class ReaderManager {
    constructor(api) {
        this.api = api;
        this.readerSelect = this.safeGetElement('reader-select');
        this.autodetectCheckbox = this.safeGetElement('autodetect-reader');
        this.refreshButton = this.safeGetElement('refresh-readers');
        this.statusIndicator = this.safeGetElement('reader-status-indicator', false);
        
        this.selectedReader = null;
        this.autodetectEnabled = false;
        this.autodetectInterval = null;
        this.checkInterval = 1000; // Configurable interval (1 second default)
        this.eventListeners = {
            readerChanged: [],
            cardStatusChanged: [],
            readersUpdated: []
        };
        this.lastCardStatus = null;
        this.consecutiveErrors = 0;
        
        this.initialize();
    }
    
    /**
     * Safe wrapper for getElement that handles missing elements gracefully
     */
    safeGetElement(id, required = true) {
        try {
            return getElement(id);
        } catch (error) {
            if (required) {
                logger.warn(`Required element #${id} not found`, { error });
            }
            return null;
        }
    }
    
    initialize() {
        // Load saved preferences
        this.loadPreferences();
        
        // Set up event listeners if elements exist
        if (this.refreshButton) {
            this.refreshButton.addEventListener('click', () => this.fetchReaders());
        }
        
        if (this.autodetectCheckbox) {
            this.autodetectCheckbox.addEventListener('change', () => this.toggleAutodetect());
        }
        
        if (this.readerSelect) {
            this.readerSelect.addEventListener('change', () => this.handleReaderChange());
        }
        
        // Start autodetection if enabled
        if (this.autodetectEnabled) {
            this.startAutodetection();
        }
        
        // Fetch readers initially
        this.fetchReaders();
        
        // Set up periodic reader refresh (every 30 seconds)
        setInterval(() => {
            if (!document.hidden) {
                this.fetchReaders(false); // Silent refresh
            }
        }, 30000);
    }
    
    /**
     * Load user preferences from storage
     */
    loadPreferences() {
        // Load autodetect preference
        const autodetectState = loadFromStorage('autodetect', false);
        if (this.autodetectCheckbox) {
            this.autodetectCheckbox.checked = autodetectState;
        }
        this.autodetectEnabled = autodetectState;
        
        // Load selected reader preference
        this.selectedReader = loadFromStorage('selected_reader', null);
        
        // Load check interval preference
        const savedInterval = loadFromStorage('reader_check_interval', this.checkInterval);
        this.checkInterval = savedInterval;
    }
    
    /**
     * Save user preferences to storage
     */
    savePreferences() {
        saveToStorage('autodetect', this.autodetectEnabled);
        if (this.selectedReader) {
            saveToStorage('selected_reader', this.selectedReader);
        }
        saveToStorage('reader_check_interval', this.checkInterval);
    }
    
    /**
     * Fetch available readers from the API
     * @param {boolean} showLoadingState - Whether to show a loading state
     */
    async fetchReaders(showLoadingState = true) {
        if (showLoadingState && this.readerSelect) {
            this.setLoadingState(true);
        }
        
        try {
            const response = await this.api.get('/readers');
            
            if (response.status === 'success') {
                const readers = response.readers || [];
                this.updateReaderSelect(readers);
                
                // Select previously selected reader if it exists in the list
                const previousReader = this.selectedReader;
                
                if (response.selected_reader) {
                    this.selectedReader = response.selected_reader;
                } else if (previousReader && readers.some(r => r.name === previousReader)) {
                    this.selectedReader = previousReader;
                } else if (readers.length > 0) {
                    this.selectedReader = readers[0].name;
                } else {
                    this.selectedReader = null;
                }
                
                // Update select element if it exists
                if (this.readerSelect && this.selectedReader) {
                    this.readerSelect.value = this.selectedReader;
                }
                
                // Notify listeners
                this.notifyListeners('readersUpdated', readers);
                
                // Reset error counter on success
                this.consecutiveErrors = 0;
            } else {
                logger.error('Error fetching readers', { message: response.message });
                this.consecutiveErrors++;
            }
        } catch (error) {
            logger.error('Error fetching readers', { error });
            this.consecutiveErrors++;
            
            // If multiple consecutive errors, slow down polling
            if (this.consecutiveErrors > 3 && this.autodetectInterval) {
                this.adjustCheckInterval(this.checkInterval * 2);
            }
        } finally {
            if (showLoadingState && this.readerSelect) {
                this.setLoadingState(false);
            }
        }
    }
    
    /**
     * Set loading state for the reader select
     * @param {boolean} isLoading - Whether the component is in loading state
     */
    setLoadingState(isLoading) {
        if (this.readerSelect) {
            this.readerSelect.classList.toggle('loading', isLoading);
        }
        
        if (this.statusIndicator) {
            this.statusIndicator.classList.toggle('loading', isLoading);
            this.statusIndicator.textContent = isLoading ? 'Loading readers...' : '';
        }
    }
    
    /**
     * Update reader select dropdown with available readers
     * @param {Array} readers - List of available readers
     */
    updateReaderSelect(readers) {
        if (!this.readerSelect) return;
        
        // Save current selection to restore if possible
        const currentSelection = this.readerSelect.value;
        
        // Clear existing options
        this.readerSelect.innerHTML = '';
        
        if (readers.length > 0) {
            // Sort readers by name for consistent display
            const sortedReaders = [...readers].sort((a, b) => a.name.localeCompare(b.name));
            
            // Add reader options
            sortedReaders.forEach(reader => {
                const option = document.createElement('option');
                option.value = reader.name;
                option.textContent = `${reader.name} (${reader.type || 'Unknown'})`;
                
                // Add data attributes for additional reader properties
                if (reader.isContactless) option.dataset.contactless = 'true';
                if (reader.isContact) option.dataset.contact = 'true';
                
                this.readerSelect.appendChild(option);
            });
            
            // Enable select
            this.readerSelect.disabled = false;
            
            // Restore previous selection if it exists
            if (currentSelection && sortedReaders.some(r => r.name === currentSelection)) {
                this.readerSelect.value = currentSelection;
            }
        } else {
            // No readers found
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No readers found';
            option.disabled = true;
            this.readerSelect.appendChild(option);
            this.readerSelect.disabled = true;
        }
    }
    
    /**
     * Handle reader selection change
     */
    async handleReaderChange() {
        if (!this.readerSelect) return;
        
        const readerName = this.readerSelect.value;
        if (!readerName) return;
        
        this.setLoadingState(true);
        
        try {
            const response = await this.api.post('/smartcard/select', { reader: readerName });
            if (response.status === 'success') {
                this.selectedReader = readerName;
                this.savePreferences();
                logger.info('Reader selected', { reader: readerName });
                
                // Notify listeners of reader change
                this.notifyListeners('readerChanged', readerName);
                
                // Check card status immediately after reader change
                this.checkCardStatus();
            } else {
                logger.error('Error selecting reader', { message: response.message });
                // Revert to previous selection
                if (this.selectedReader && this.selectedReader !== readerName) {
                    this.readerSelect.value = this.selectedReader;
                }
            }
        } catch (error) {
            logger.error('Error selecting reader', { error });
            // Revert to previous selection
            if (this.selectedReader && this.selectedReader !== readerName) {
                this.readerSelect.value = this.selectedReader;
            }
        } finally {
            this.setLoadingState(false);
        }
    }
    
    /**
     * Toggle autodetection on/off
     */
    toggleAutodetect() {
        if (!this.autodetectCheckbox) return;
        
        this.autodetectEnabled = this.autodetectCheckbox.checked;
        this.savePreferences();
        
        if (this.autodetectEnabled) {
            this.startAutodetection();
        } else {
            this.stopAutodetection();
        }
    }
    
    /**
     * Adjust check interval for card status checks
     * @param {number} newInterval - New interval in milliseconds
     */
    adjustCheckInterval(newInterval) {
        // Ensure interval is between 500ms and 10s
        this.checkInterval = Math.max(500, Math.min(10000, newInterval));
        this.savePreferences();
        
        // Restart autodetection with new interval if enabled
        if (this.autodetectEnabled) {
            this.startAutodetection();
        }
    }
    
    /**
     * Start autodetection of card status
     */
    startAutodetection() {
        logger.info('Autodetection started', { interval: this.checkInterval });
        this.stopAutodetection(); // Clear any existing interval
        
        // Check for card presence at configured interval
        this.autodetectInterval = setInterval(() => this.checkCardStatus(), this.checkInterval);
        
        // Run once immediately
        this.checkCardStatus();
    }
    
    /**
     * Stop autodetection of card status
     */
    stopAutodetection() {
        if (this.autodetectInterval) {
            clearInterval(this.autodetectInterval);
            this.autodetectInterval = null;
            logger.info('Autodetection stopped');
        }
    }
    
    /**
     * Check card status in the selected reader
     */
    async checkCardStatus() {
        if (!this.selectedReader) return;
        
        try {
            const response = await this.api.get(`/smartcard/status?reader=${encodeURIComponent(this.selectedReader)}`);
            
            if (response.status === 'success') {
                const cardStatus = response.data || {};
                const cardPresent = cardStatus.present || false;
                
                // Determine if the status actually changed
                const statusChanged = this.lastCardStatus === null || 
                                     cardPresent !== this.lastCardStatus.present ||
                                     (cardPresent && 
                                      cardStatus.atr !== this.lastCardStatus.atr);
                
                // Update the last known status
                this.lastCardStatus = { ...cardStatus };
                
                // Add wasChanged flag to the status data
                cardStatus.wasChanged = statusChanged;
                
                // Only notify if status actually changed
                if (statusChanged) {
                    // Reset errors on successful status change
                    this.consecutiveErrors = 0;
                    
                    // Notify listeners of card status change
                    this.notifyListeners('cardStatusChanged', cardPresent, cardStatus);
                }
            } else {
                logger.error('Error checking card status', { message: response.message });
                this.consecutiveErrors++;
            }
        } catch (error) {
            logger.error('Error checking card status', { error });
            this.consecutiveErrors++;
            
            // If multiple consecutive errors, slow down polling
            if (this.consecutiveErrors > 3) {
                this.adjustCheckInterval(this.checkInterval * 2);
            }
        }
    }
    
    /**
     * Force a card status check immediately
     * @returns {Promise<Object>} Card status
     */
    async forceCardStatusCheck() {
        if (!this.selectedReader) return null;
        
        try {
            const response = await this.api.get(`/smartcard/status?reader=${encodeURIComponent(this.selectedReader)}&force=true`);
            
            if (response.status === 'success') {
                const cardStatus = response.data || {};
                const cardPresent = cardStatus.present || false;
                
                // Update the last known status
                this.lastCardStatus = { ...cardStatus };
                
                // Notify listeners of card status
                this.notifyListeners('cardStatusChanged', cardPresent, cardStatus);
                
                return cardStatus;
            } else {
                logger.error('Error forcing card status check', { message: response.message });
                return null;
            }
        } catch (error) {
            logger.error('Error forcing card status check', { error });
            return null;
        }
    }
    
    /**
     * Register event listeners
     * @param {string} event - Event name ('readerChanged', 'cardStatusChanged', 'readersUpdated')
     * @param {Function} callback - Event callback function
     * @returns {Function} Unsubscribe function
     */
    on(event, callback) {
        if (!this.eventListeners[event]) {
            this.eventListeners[event] = [];
        }
        
        this.eventListeners[event].push(callback);
        
        // Return unsubscribe function
        return () => this.off(event, callback);
    }
    
    /**
     * Unregister event listener
     * @param {string} event - Event name
     * @param {Function} callback - Event callback function to remove
     * @returns {boolean} Whether the listener was found and removed
     */
    off(event, callback) {
        if (!this.eventListeners[event]) return false;
        
        const index = this.eventListeners[event].indexOf(callback);
        if (index !== -1) {
            this.eventListeners[event].splice(index, 1);
            return true;
        }
        return false;
    }
    
    /**
     * Notify listeners of an event
     * @param {string} event - Event name
     * @param {...any} args - Arguments to pass to listeners
     */
    notifyListeners(event, ...args) {
        if (!this.eventListeners[event]) return;
        
        for (const listener of this.eventListeners[event]) {
            try {
                listener(...args);
            } catch (error) {
                logger.error(`Error in ${event} listener`, { error });
            }
        }
    }
    
    /**
     * Register for reader and card events (legacy method)
     * @param {Function} onReaderChanged - Callback for reader change events
     * @param {Function} onCardStatusChanged - Callback for card status change events
     */
    registerEvents(onReaderChanged, onCardStatusChanged) {
        if (onReaderChanged) this.on('readerChanged', onReaderChanged);
        if (onCardStatusChanged) this.on('cardStatusChanged', onCardStatusChanged);
    }
    
    /**
     * Get the currently selected reader
     * @returns {string|null} Selected reader name or null
     */
    getSelectedReader() {
        return this.selectedReader;
    }
    
    /**
     * Get the list of available readers
     * @returns {Promise<Array>} List of reader objects
     */
    async getReaders() {
        try {
            const response = await this.api.get('/readers');
            return response.status === 'success' ? (response.readers || []) : [];
        } catch (error) {
            logger.error('Error getting readers', { error });
            return [];
        }
    }
    
    /**
     * Filter readers by type
     * @param {string} type - Reader type to filter by
     * @returns {Promise<Array>} Filtered list of readers
     */
    async getReadersByType(type) {
        const readers = await this.getReaders();
        return readers.filter(reader => reader.type === type);
    }
    
    /**
     * Check if a reader is available
     * @param {string} readerName - Reader name to check
     * @returns {Promise<boolean>} Whether the reader is available
     */
    async isReaderAvailable(readerName) {
        const readers = await this.getReaders();
        return readers.some(reader => reader.name === readerName);
    }
    
    /**
     * Dispose of resources and stop all operations
     */
    dispose() {
        this.stopAutodetection();
        
        // Clear all event listeners
        Object.keys(this.eventListeners).forEach(event => {
            this.eventListeners[event] = [];
        });
    }
}

// Export the component
export default ReaderManager;

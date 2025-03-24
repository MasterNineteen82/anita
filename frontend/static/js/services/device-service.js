/**
 * Service for card reader device operations
 */
class DeviceService {
    /**
     * List all available card readers
     * @param {boolean} forceRefresh - Whether to force a fresh device discovery
     * @returns {Promise} Promise with reader information
     */
    static async listReaders(forceRefresh = false) {
        try {
            const response = await fetch(`/api/devices/readers?force_refresh=${forceRefresh}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to list readers');
            }
            return await response.json();
        } catch (error) {
            console.error('Error listing readers:', error);
            throw error;
        }
    }
    
    /**
     * Select a reader for operations
     * @param {string} readerName - Name of the reader to select
     * @returns {Promise} Promise with selection result
     */
    static async selectReader(readerName) {
        try {
            const response = await fetch(`/api/devices/readers/${encodeURIComponent(readerName)}/select`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to select reader');
            }
            return await response.json();
        } catch (error) {
            console.error('Error selecting reader:', error);
            throw error;
        }
    }
    
    /**
     * Check health of a reader
     * @param {string} readerName - Name of the reader to check
     * @returns {Promise} Promise with health status
     */
    static async checkReaderHealth(readerName) {
        try {
            const response = await fetch(`/api/devices/readers/${encodeURIComponent(readerName)}/health`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to check reader health');
            }
            return await response.json();
        } catch (error) {
            console.error('Error checking reader health:', error);
            throw error;
        }
    }
    
    /**
     * Set simulation mode
     * @param {boolean} enabled - Whether to enable simulation
     * @returns {Promise} Promise with operation result
     */
    static async setSimulationMode(enabled) {
        try {
            const response = await fetch(`/api/devices/simulation?enabled=${enabled}`, {
                method: 'POST'
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to set simulation mode');
            }
            return await response.json();
        } catch (error) {
            console.error('Error setting simulation mode:', error);
            throw error;
        }
    }

    /**
     * Read data from a card
     * @param {string} readerName - Name of the reader to use
     * @param {Object} options - Optional settings for the read operation
     * @returns {Promise} Promise with card data
     */
    static async readCard(readerName, options = {}) {
        try {
            const response = await fetch(`/api/devices/readers/${encodeURIComponent(readerName)}/read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(options)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to read card');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error reading card:', error);
            throw error;
        }
    }
}

export { DeviceService };
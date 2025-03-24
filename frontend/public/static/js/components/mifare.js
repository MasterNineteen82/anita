/**
 * MIFARE card operations component
 */
import { getElement } from '../utils/dom.js';
import logger from '../core/logger.js';
import UI from '../utils/ui.js';

class MifareManager {
    constructor(api, readerManager) {
        this.api = api;
        this.readerManager = readerManager;
        
        // Get required DOM elements
        this.keyTypeSelect = getElement('key-type');
        this.keyValueInput = getElement('key-value');
        this.blockNumberInput = getElement('block-number');
        this.authButton = getElement('auth-btn');
        this.authStatus = getElement('auth-status');
        
        this.rwBlockNumberInput = getElement('rw-block-number');
        this.readBlockButton = getElement('read-block-btn');
        this.readValueButton = getElement('read-value-btn');
        this.writeDataInput = getElement('write-data');
        this.writeBlockButton = getElement('write-block-btn');
        this.writeValueButton = getElement('write-value-btn');
        this.rwResult = getElement('rw-result').querySelector('pre');
        
        this.valueBlockNumberInput = getElement('value-block-number');
        this.valueAmountInput = getElement('value-amount');
        this.initValueButton = getElement('init-value-btn');
        this.incrementButton = getElement('increment-btn');
        this.decrementButton = getElement('decrement-btn');
        this.valueResult = getElement('value-result').querySelector('pre');
        
        this.authenticated = false;
        this.lastKeyType = null;
        this.lastKeyValue = null;
        this.lastBlockNumber = null;
        
        this.initialize();
    }
    
    initialize() {
        // Add event listeners
        this.authButton.addEventListener('click', () => this.authenticate());
        this.readBlockButton.addEventListener('click', () => this.readBlock());
        this.readValueButton.addEventListener('click', () => this.readValue());
        this.writeBlockButton.addEventListener('click', () => this.writeBlock());
        this.writeValueButton.addEventListener('click', () => this.writeValue());
        this.initValueButton.addEventListener('click', () => this.initializeValue());
        this.incrementButton.addEventListener('click', () => this.incrementValue());
        this.decrementButton.addEventListener('click', () => this.decrementValue());
        
        // Listen for card status changes
        if (this.readerManager) {
            this.readerManager.onCardStatusChanged = (status) => {
                if (!status.present) {
                    // Card removed, reset authenticated state
                    this.resetAuth();
                }
            };
        }
        
        // Load saved values from storage
        this.loadSavedValues();
    }
    
    loadSavedValues() {
        const keyType = localStorage.getItem('mifare-key-type') || 'A';
        const keyValue = localStorage.getItem('mifare-key-value') || 'FF FF FF FF FF FF';
        
        this.keyTypeSelect.value = keyType;
        this.keyValueInput.value = keyValue;
    }
    
    saveValues() {
        localStorage.setItem('mifare-key-type', this.keyTypeSelect.value);
        localStorage.setItem('mifare-key-value', this.keyValueInput.value);
    }
    
    resetAuth() {
        this.authenticated = false;
        this.lastKeyType = null;
        this.lastKeyValue = null;
        this.lastBlockNumber = null;
        this.authStatus.textContent = 'Authentication required';
        this.authStatus.className = 'status-message';
    }
    
    async authenticate() {
        // Get reader
        const reader = this.readerManager.getSelectedReader();
        if (!reader) {
            UI.showToast('Please select a reader first', 'error');
            return;
        }
        
        // Get key parameters
        const keyType = this.keyTypeSelect.value;
        const keyValue = this.keyValueInput.value.trim();
        const blockNumber = parseInt(this.blockNumberInput.value);
        
        // Validate key
        if (!this.validateKey(keyValue)) {
            UI.showToast('Invalid key format. Must be 12 hex characters (6 bytes)', 'error');
            return;
        }
        
        try {
            this.authStatus.textContent = 'Authenticating...';
            this.authStatus.className = 'status-message info';
            
            const response = await this.api.post('/mifare/auth', {
                reader: reader,
                key_type: keyType,
                key: keyValue.replace(/\s+/g, ''),
                block: blockNumber
            });
            
            if (response.status === 'success') {
                this.authenticated = true;
                this.lastKeyType = keyType;
                this.lastKeyValue = keyValue;
                this.lastBlockNumber = blockNumber;
                
                this.authStatus.textContent = 'Authentication successful';
                this.authStatus.className = 'status-message success';
                
                // Save values for next time
                this.saveValues();
            } else {
                this.resetAuth();
                this.authStatus.textContent = `Authentication failed: ${response.message}`;
                this.authStatus.className = 'status-message error';
            }
        } catch (error) {
            this.resetAuth();
            this.authStatus.textContent = `Error: ${error.message}`;
            this.authStatus.className = 'status-message error';
            logger.error('MIFARE authentication error', { error });
        }
    }
    
    validateKey(key) {
        // Remove spaces
        const cleanKey = key.replace(/\s+/g, '');
        // Check if it's 12 hex characters (6 bytes)
        return /^[0-9A-Fa-f]{12}$/.test(cleanKey);
    }
    
    async performOperation(operationName, endpoint, params, resultElement) {
        if (!this.ensureAuthenticated()) {
            return null;
        }
        
        try {
            resultElement.textContent = `${operationName}...`;
            
            const response = await this.api.post(endpoint, params);
            
            if (response.status === 'success') {
                return response;
            } else {
                resultElement.textContent = `Error: ${response.message}`;
                return null;
            }
        } catch (error) {
            resultElement.textContent = `Error: ${error.message}`;
            logger.error(`MIFARE ${operationName.toLowerCase()} error`, { 
                error, 
                ...params 
            });
            return null;
        }
    }

    async readBlock() {
        const blockNumber = parseInt(this.rwBlockNumberInput.value);
        const reader = this.readerManager.getSelectedReader();
        
        const response = await this.performOperation(
            'Reading block', 
            '/mifare/read_block',
            { reader, block: blockNumber },
            this.rwResult
        );
        
        if (response) {
            this.rwResult.textContent = response.data;
        }
    }
    
    async readValue() {
        // Check if authenticated
        if (!this.ensureAuthenticated()) {
            return;
        }
        
        const blockNumber = parseInt(this.rwBlockNumberInput.value);
        const reader = this.readerManager.getSelectedReader();
        
        try {
            this.rwResult.textContent = 'Reading value...';
            
            const response = await this.api.post('/mifare/read_value', {
                reader: reader,
                block: blockNumber
            });
            
            if (response.status === 'success') {
                this.rwResult.textContent = `Value: ${response.value}`;
            } else {
                this.rwResult.textContent = `Error: ${response.message}`;
            }
        } catch (error) {
            this.rwResult.textContent = `Error: ${error.message}`;
            logger.error('MIFARE read value error', { error, block: blockNumber });
        }
    }
    
    async writeBlock() {
        // Check if authenticated
        if (!this.ensureAuthenticated()) {
            return;
        }
        
        const blockNumber = parseInt(this.rwBlockNumberInput.value);
        const data = this.writeDataInput.value.trim();
        const reader = this.readerManager.getSelectedReader();
        
        if (!data || data.length !== 32) {
            UI.showToast('Data must be 32 hex characters (16 bytes)', 'error');
            return;
        }
        
        try {
            this.rwResult.textContent = 'Writing block...';
            
            const response = await this.api.post('/mifare/write_block', {
                reader: reader,
                block: blockNumber,
                data: data
            });
            
            if (response.status === 'success') {
                this.rwResult.textContent = 'Write successful';
            } else {
                this.rwResult.textContent = `Error: ${response.message}`;
            }
        } catch (error) {
            this.rwResult.textContent = `Error: ${error.message}`;
            logger.error('MIFARE write block error', { error, block: blockNumber });
        }
    }
    
    async writeValue() {
        // Check if authenticated
        if (!this.ensureAuthenticated()) {
            return;
        }
        
        const blockNumber = parseInt(this.rwBlockNumberInput.value);
        const value = parseInt(this.writeDataInput.value);
        const reader = this.readerManager.getSelectedReader();
        
        if (isNaN(value)) {
            UI.showToast('Invalid value', 'error');
            return;
        }
        
        try {
            this.rwResult.textContent = 'Writing value...';
            
            const response = await this.api.post('/mifare/write_value', {
                reader: reader,
                block: blockNumber,
                value: value
            });
            
            if (response.status === 'success') {
                this.rwResult.textContent = 'Write successful';
            } else {
                this.rwResult.textContent = `Error: ${response.message}`;
            }
        } catch (error) {
            this.rwResult.textContent = `Error: ${error.message}`;
            logger.error('MIFARE write value error', { error, block: blockNumber });
        }
    }
    
    async initializeValue() {
        // Check if authenticated
        if (!this.ensureAuthenticated()) {
            return;
        }
        
        const blockNumber = parseInt(this.valueBlockNumberInput.value);
        const value = parseInt(this.valueAmountInput.value);
        const reader = this.readerManager.getSelectedReader();
        
        if (isNaN(value)) {
            UI.showToast('Invalid value', 'error');
            return;
        }
        
        try {
            this.valueResult.textContent = 'Initializing value...';
            
            const response = await this.api.post('/mifare/init_value', {
                reader: reader,
                block: blockNumber,
                value: value
            });
            
            if (response.status === 'success') {
                this.valueResult.textContent = 'Initialization successful';
            } else {
                this.valueResult.textContent = `Error: ${response.message}`;
            }
        } catch (error) {
            this.valueResult.textContent = `Error: ${error.message}`;
            logger.error('MIFARE initialize value error', { error, block: blockNumber });
        }
    }
    
    async incrementValue() {
        // Check if authenticated
        if (!this.ensureAuthenticated()) {
            return;
        }
        
        const blockNumber = parseInt(this.valueBlockNumberInput.value);
        const value = parseInt(this.valueAmountInput.value);
        const reader = this.readerManager.getSelectedReader();
        
        if (isNaN(value)) {
            UI.showToast('Invalid value', 'error');
            return;
        }
        
        try {
            this.valueResult.textContent = 'Incrementing value...';
            
            const response = await this.api.post('/mifare/increment', {
                reader: reader,
                block: blockNumber,
                value: value
            });
            
            if (response.status === 'success') {
                this.valueResult.textContent = 'Increment successful';
            } else {
                this.valueResult.textContent = `Error: ${response.message}`;
            }
        } catch (error) {
            this.valueResult.textContent = `Error: ${error.message}`;
            logger.error('MIFARE increment value error', { error, block: blockNumber });
        }
    }
    
    async decrementValue() {
        // Check if authenticated
        if (!this.ensureAuthenticated()) {
            return;
        }
        
        const blockNumber = parseInt(this.valueBlockNumberInput.value);
        const value = parseInt(this.valueAmountInput.value);
        const reader = this.readerManager.getSelectedReader();
        
        if (isNaN(value)) {
            UI.showToast('Invalid value', 'error');
            return;
        }
        
        try {
            this.valueResult.textContent = 'Decrementing value...';
            
            const response = await this.api.post('/mifare/decrement', {
                reader: reader,
                block: blockNumber,
                value: value
            });
            
            if (response.status === 'success') {
                this.valueResult.textContent = 'Decrement successful';
            } else {
                this.valueResult.textContent = `Error: ${response.message}`;
            }
        } catch (error) {
            this.valueResult.textContent = `Error: ${error.message}`;
            logger.error('MIFARE decrement value error', { error, block: blockNumber });
        }
    }
    
    ensureAuthenticated() {
        if (!this.authenticated) {
            UI.showToast('Please authenticate first', 'error');
            return false;
        }
        return true;
    }
}

export default MifareManager;
/**
 * NFC tag operations component
 */
import { getElement } from '../utils/dom.js';
import { createElement } from '../utils/dom.js';
import logger from '../core/logger.js';
import UI from '../core/ui.js';

class NFCManager {
    constructor(api, readerManager) {
        this.api = api;
        this.readerManager = readerManager;
        
        // Operation states
        this.isOperationInProgress = false;
        this.currentOperation = null;
        this.abortController = null;
        
        // Get DOM elements
        this.discoverButton = getElement('nfc-discover-btn');
        this.readButton = getElement('nfc-read-btn');
        this.clearButton = getElement('nfc-clear-btn');
        this.nfcResult = getElement('nfc-result')?.querySelector('pre');
        this.statusIndicator = getElement('nfc-status-indicator');
        
        // Text record elements
        this.writeTextButton = getElement('write-text-btn');
        this.textInput = getElement('text-input');
        
        // URI record elements
        this.writeUriButton = getElement('write-uri-btn');
        this.uriInput = getElement('uri-input');
        
        // vCard record elements
        this.writeVcardButton = getElement('write-vcard-btn');
        this.nameInput = getElement('name-input');
        this.emailInput = getElement('email-input');
        this.phoneInput = getElement('phone-input');
        
        // Raw message elements
        this.writeRawButton = getElement('write-raw-btn');
        this.rawTypeInput = getElement('raw-type-input');
        this.rawDataInput = getElement('raw-data-input');
        
        // History tracking
        this.operationHistory = [];
        this.historyLimit = 10;
        this.historyContainer = getElement('nfc-history');
        
        this.initialize();
        this.loadHistory();
    }
    
    initialize() {
        // Add event listeners if the elements exist
        this.discoverButton?.addEventListener('click', () => this.discoverTag());
        this.readButton?.addEventListener('click', () => this.readTag());
        this.clearButton?.addEventListener('click', () => this.clearTag());
        this.writeTextButton?.addEventListener('click', () => this.writeText());
        this.writeUriButton?.addEventListener('click', () => this.writeUri());
        this.writeVcardButton?.addEventListener('click', () => this.writeVcard());
        this.writeRawButton?.addEventListener('click', () => this.writeRaw());
        
        // Add cancel operation button
        this.setupCancelButton();
        
        // Initialize status indicator
        this.updateStatus('ready');
    }
    
    setupCancelButton() {
        const container = this.nfcResult?.parentElement;
        if (!container) return;
        
        const cancelBtn = createElement('button', {
            className: 'btn btn-sm btn-danger cancel-operation',
            style: { display: 'none' },
            onClick: () => this.cancelOperation()
        }, ['Cancel Operation']);
        
        container.appendChild(cancelBtn);
        this.cancelButton = cancelBtn;
    }
    
    updateStatus(status, message = '') {
        if (!this.statusIndicator) return;
        
        this.statusIndicator.className = `status-indicator ${status}`;
        this.statusIndicator.textContent = message || this.getStatusText(status);
        
        // Update operation buttons state
        this.updateButtonsState(status === 'busy');
        
        // Show/hide cancel button
        if (this.cancelButton) {
            this.cancelButton.style.display = status === 'busy' ? 'inline-block' : 'none';
        }
    }
    
    getStatusText(status) {
        switch (status) {
            case 'ready': return 'Ready';
            case 'busy': return 'Operation in progress...';
            case 'success': return 'Operation successful';
            case 'error': return 'Error occurred';
            default: return '';
        }
    }
    
    updateButtonsState(disabled) {
        const buttons = [
            this.discoverButton, 
            this.readButton, 
            this.clearButton,
            this.writeTextButton, 
            this.writeUriButton, 
            this.writeVcardButton, 
            this.writeRawButton
        ];
        
        buttons.forEach(btn => {
            if (btn) btn.disabled = disabled;
        });
    }
    
    cancelOperation() {
        if (this.abortController) {
            this.abortController.abort();
            this.abortController = null;
        }
        
        this.isOperationInProgress = false;
        this.currentOperation = null;
        this.updateStatus('ready');
        
        if (this.nfcResult) {
            this.nfcResult.textContent = 'Operation cancelled by user.';
        }
        
        UI.showToast('Operation cancelled', 'info');
    }
    
    async startOperation(operationType, callback) {
        if (this.isOperationInProgress) {
            UI.showToast('Another operation is in progress', 'warning');
            return false;
        }
        
        const reader = this.readerManager.getSelectedReader();
        if (!reader) {
            UI.showToast('Please select a reader first', 'error');
            return false;
        }
        
        this.isOperationInProgress = true;
        this.currentOperation = operationType;
        this.abortController = new AbortController();
        this.updateStatus('busy', `${operationType} in progress...`);
        
        try {
            const result = await callback(reader);
            this.isOperationInProgress = false;
            
            if (result?.status === 'success') {
                this.updateStatus('success');
                this.addToHistory(operationType, result);
                setTimeout(() => this.updateStatus('ready'), 3000);
            } else {
                this.updateStatus('error');
                setTimeout(() => this.updateStatus('ready'), 3000);
            }
            
            return result;
        } catch (error) {
            // Don't update status if operation was cancelled
            if (error.name !== 'AbortError') {
                this.isOperationInProgress = false;
                this.updateStatus('error');
                setTimeout(() => this.updateStatus('ready'), 3000);
            }
            throw error;
        }
    }
    
    validateUri(uri) {
        try {
            new URL(uri);
            return true;
        } catch (e) {
            return false;
        }
    }
    
    validateEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }
    
    addToHistory(operationType, result) {
        const timestamp = new Date().toLocaleTimeString();
        const historyItem = {
            type: operationType,
            timestamp,
            result,
            success: result?.status === 'success'
        };
        
        this.operationHistory.unshift(historyItem);
        
        // Trim history to limit
        if (this.operationHistory.length > this.historyLimit) {
            this.operationHistory.pop();
        }
        
        // Save to local storage
        this.saveHistory();
        
        // Update UI
        this.updateHistoryUI();
    }
    
    updateHistoryUI() {
        if (!this.historyContainer) return;
        
        this.historyContainer.innerHTML = '';
        
        this.operationHistory.forEach(item => {
            const historyElement = createElement('li', {
                className: `history-item ${item.success ? 'success' : 'error'}`,
                onClick: () => this.showHistoryDetails(item)
            }, [
                `${item.timestamp} - ${item.type} (${item.success ? 'Success' : 'Failed'})`
            ]);
            
            this.historyContainer.appendChild(historyElement);
        });
    }
    
    showHistoryDetails(item) {
        if (this.nfcResult) {
            this.nfcResult.textContent = JSON.stringify(item.result, null, 2);
        }
    }
    
    saveHistory() {
        localStorage.setItem('nfc-operation-history', JSON.stringify(this.operationHistory));
    }
    
    loadHistory() {
        try {
            const savedHistory = localStorage.getItem('nfc-operation-history');
            if (savedHistory) {
                this.operationHistory = JSON.parse(savedHistory);
                this.updateHistoryUI();
            }
        } catch (error) {
            logger.error('Failed to load NFC operation history', { error });
        }
    }
    
    async discoverTag() {
        return this.startOperation('Discover Tag', async (reader) => {
            if (this.nfcResult) this.nfcResult.textContent = 'Discovering NFC tag...';
            
            const response = await this.api.post('/nfc/discover', {
                reader: reader
            }, { signal: this.abortController.signal });
            
            if (this.nfcResult) {
                if (response.status === 'success') {
                    this.nfcResult.textContent = JSON.stringify(response.data, null, 2);
                } else {
                    this.nfcResult.textContent = `Error: ${response.message}`;
                }
            }
            
            return response;
        }).catch(error => {
            if (error.name !== 'AbortError') {
                if (this.nfcResult) this.nfcResult.textContent = `Error: ${error.message}`;
                logger.error('NFC discover error', { error });
            }
        });
    }
    
    async readTag() {
        return this.startOperation('Read Tag', async (reader) => {
            if (this.nfcResult) this.nfcResult.textContent = 'Reading NFC tag...';
            
            const response = await this.api.post('/nfc/read', {
                reader: reader
            }, { signal: this.abortController.signal });
            
            if (this.nfcResult) {
                if (response.status === 'success') {
                    this.nfcResult.textContent = JSON.stringify(response.data, null, 2);
                } else {
                    this.nfcResult.textContent = `Error: ${response.message}`;
                }
            }
            
            return response;
        }).catch(error => {
            if (error.name !== 'AbortError') {
                if (this.nfcResult) this.nfcResult.textContent = `Error: ${error.message}`;
                logger.error('NFC read error', { error });
            }
        });
    }
    
    async clearTag() {
        const confirmed = await UI.confirm('Are you sure you want to clear this NFC tag? This will remove all data stored on it.');
        if (!confirmed) return;
        
        return this.startOperation('Clear Tag', async (reader) => {
            if (this.nfcResult) this.nfcResult.textContent = 'Clearing NFC tag...';
            
            const response = await this.api.post('/nfc/clear', {
                reader: reader
            }, { signal: this.abortController.signal });
            
            if (this.nfcResult) {
                if (response.status === 'success') {
                    this.nfcResult.textContent = 'Tag cleared successfully';
                } else {
                    this.nfcResult.textContent = `Error: ${response.message}`;
                }
            }
            
            return response;
        }).catch(error => {
            if (error.name !== 'AbortError') {
                if (this.nfcResult) this.nfcResult.textContent = `Error: ${error.message}`;
                logger.error('NFC clear error', { error });
            }
        });
    }
    
    async writeText() {
        const text = this.textInput?.value.trim();
        if (!text) {
            UI.showToast('Please enter text to write', 'error');
            return;
        }
        
        const reader = this.readerManager.getSelectedReader();
        if (!reader) {
            UI.showToast('Please select a reader first', 'error');
            return;
        }
        
        try {
            if (this.nfcResult) this.nfcResult.textContent = 'Writing text to tag...';
            
            const response = await this.api.post('/nfc/write_text', {
                reader: reader,
                text: text
            });
            
            if (this.nfcResult) {
                if (response.status === 'success') {
                    this.nfcResult.textContent = 'Text written successfully';
                    UI.showToast('Text written to tag', 'success');
                } else {
                    this.nfcResult.textContent = `Error: ${response.message}`;
                    UI.showToast(response.message, 'error');
                }
            }
        } catch (error) {
            if (this.nfcResult) this.nfcResult.textContent = `Error: ${error.message}`;
            logger.error('NFC write text error', { error });
            UI.showToast('Failed to write text to tag', 'error');
        }
    }
    
    async writeUri() {
        const uri = this.uriInput?.value.trim();
        if (!uri) {
            UI.showToast('Please enter a URI to write', 'error');
            return;
        }
        
        if (!this.validateUri(uri)) {
            UI.showToast('Please enter a valid URI', 'error');
            return;
        }
        
        return this.startOperation('Write URI', async (reader) => {
            if (this.nfcResult) this.nfcResult.textContent = 'Writing URI to NFC tag...';
            
            const response = await this.api.post('/nfc/write_uri', {
                reader: reader,
                uri: uri
            }, { signal: this.abortController.signal });
            
            if (this.nfcResult) {
                if (response.status === 'success') {
                    this.nfcResult.textContent = 'URI written successfully';
                    this.addToHistory('Write URI', uri);
                } else {
                    this.nfcResult.textContent = `Error: ${response.message}`;
                }
            }
            
            return response;
        }).catch(error => {
            if (error.name !== 'AbortError') {
                if (this.nfcResult) this.nfcResult.textContent = `Error: ${error.message}`;
                logger.error('NFC write URI error', { error });
            }
        });
    }
    
    async writeVcard() {
        const name = this.nameInput?.value.trim();
        const email = this.emailInput?.value.trim();
        const phone = this.phoneInput?.value.trim();
        
        if (!name && !email && !phone) {
            UI.showToast('Please enter at least one contact detail', 'error');
            return;
        }
        
        if (email && !this.validateEmail(email)) {
            UI.showToast('Please enter a valid email address', 'error');
            return;
        }
        
        return this.startOperation('Write vCard', async (reader) => {
            if (this.nfcResult) this.nfcResult.textContent = 'Writing vCard to NFC tag...';
            
            const response = await this.api.post('/nfc/write_vcard', {
                reader: reader,
                name: name,
                email: email,
                phone: phone
            }, { signal: this.abortController.signal });
            
            if (this.nfcResult) {
                if (response.status === 'success') {
                    this.nfcResult.textContent = 'vCard written successfully';
                    this.addToHistory('Write vCard', `${name} ${email} ${phone}`);
                } else {
                    this.nfcResult.textContent = `Error: ${response.message}`;
                }
            }
            
            return response;
        }).catch(error => {
            if (error.name !== 'AbortError') {
                if (this.nfcResult) this.nfcResult.textContent = `Error: ${error.message}`;
                logger.error('NFC write vCard error', { error });
            }
        });
    }
    
    async writeRaw() {
        const type = this.rawTypeInput?.value.trim();
        const data = this.rawDataInput?.value.trim();
        
        if (!type || !data) {
            UI.showToast('Please enter both record type and data', 'error');
            return;
        }
        
        return this.startOperation('Write Raw', async (reader) => {
            if (this.nfcResult) this.nfcResult.textContent = 'Writing raw record to NFC tag...';
            
            const response = await this.api.post('/nfc/write_raw', {
                reader: reader,
                type: type,
                data: data
            }, { signal: this.abortController.signal });
            
            if (this.nfcResult) {
                if (response.status === 'success') {
                    this.nfcResult.textContent = 'Raw record written successfully';
                    this.addToHistory('Write Raw Record', `${type}: ${data.substring(0, 20)}...`);
                } else {
                    this.nfcResult.textContent = `Error: ${response.message}`;
                }
            }
            
            return response;
        }).catch(error => {
            if (error.name !== 'AbortError') {
                if (this.nfcResult) this.nfcResult.textContent = `Error: ${error.message}`;
                logger.error('NFC write raw record error', { error });
            }
        });
    }
    
    // Helper method to interpret NFC errors and provide user-friendly messages
    getErrorMessage(error) {
        // Specific NFC error codes and messages
        const errorCodes = {
            'TAG_NOT_PRESENT': 'No NFC tag detected. Please place a tag on the reader.',
            'TAG_READ_ONLY': 'This tag is read-only and cannot be written to.',
            'TAG_INVALID_FORMAT': 'The tag format is not supported.',
            'TAG_CAPACITY_EXCEEDED': 'The data is too large for this tag.',
            'TAG_ACCESS_DENIED': 'Access denied. The tag may be password protected.',
        };
        
        if (error.code && errorCodes[error.code]) {
            return errorCodes[error.code];
        }
        
        return error.message || 'An unknown error occurred';
    }
}

export default NFCManager;
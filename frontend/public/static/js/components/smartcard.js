import { getElement, escapeHtml } from '../utils/dom.js';
import { saveToStorage, loadFromStorage } from '../utils/storage.js';
import logger from '../core/logger.js';
import UI from '../core/ui.js';

/**
 * Smart Card operations component
 */
class SmartCardManager {
    constructor(api, readerManager) {
        this.api = api;
        this.readerManager = readerManager;
        
        // Elements
        this.resultElement = getElement('smartcard-result');
        this.atrElement = getElement('card-atr');
        this.uidElement = getElement('card-uid');
        this.cardTypeElement = getElement('card-type');
        this.apduCommandInput = getElement('apdu-command');
        this.cardStatusDisplay = getElement('card-status-display');
        
        // Initialize
        this.initialize();
    }
    
    initialize() {
        // Register for reader events
        this.readerManager.registerEvents(
            this.handleReaderChanged.bind(this),
            this.handleCardStatusChanged.bind(this)
        );
        
        // Set up button click handlers
        getElement('test-reader')?.addEventListener('click', () => this.testReader());
        getElement('get-atr')?.addEventListener('click', () => this.getATR());
        getElement('get-uid')?.addEventListener('click', () => this.getUID());
        getElement('send-apdu')?.addEventListener('click', () => this.sendAPDU());
        
        // Result controls
        getElement('copy-result')?.addEventListener('click', () => this.copyResult());
        getElement('clear-result')?.addEventListener('click', () => this.clearResult());
        
        // Tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });
        
        // Command history
        getElement('clear-history')?.addEventListener('click', () => this.clearHistory());
        
        // Load command history
        this.loadHistory();
    }
    
    async handleReaderChanged(readerName) {
        logger.info(`Reader changed to: ${readerName}`);
        // Reset card status display
        this.updateCardStatus(false);
    }
    
    handleCardStatusChanged(present, data) {
        this.updateCardStatus(present);
        
        // If a card was just inserted, get its info
        if (present && data?.wasChanged) {
            this.getCardInfo();
        }
    }
    
    updateCardStatus(present) {
        if (present) {
            this.cardStatusDisplay.innerHTML = '<span style="color: var(--success-color);">Card Present</span>';
        } else {
            this.cardStatusDisplay.innerHTML = '<span style="color: var(--warning-color);">No Card Present</span>';
            
            // Clear card info when card is removed
            this.atrElement.textContent = 'Not read';
            this.uidElement.textContent = 'Not read';
            this.cardTypeElement.textContent = 'Unknown';
        }
    }
    
    switchTab(tabId) {
        // Update active tab button
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });
        
        // Update active tab pane
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane.id === `${tabId}-tab`);
        });
    }
    
    async testReader() {
        const reader = this.readerManager.getSelectedReader();
        if (!reader) {
            this.displayResult({ status: 'error', message: 'No reader selected' });
            return;
        }
        
        try {
            const response = await this.api.get(`/smartcard/test?reader=${encodeURIComponent(reader)}`);
            this.displayResult(response);
        } catch (error) {
            this.displayResult({ status: 'error', message: error.message });
        }
    }
    
    async getATR() {
        const reader = this.readerManager.getSelectedReader();
        if (!reader) {
            this.displayResult({ status: 'error', message: 'No reader selected' });
            return;
        }
        
        try {
            const response = await this.api.get(`/smartcard/atr?reader=${encodeURIComponent(reader)}`);
            this.displayResult(response);
            
            if (response.status === 'success' && response.data?.atr) {
                this.atrElement.textContent = response.data.atr;
            }
        } catch (error) {
            this.displayResult({ status: 'error', message: error.message });
        }
    }
    
    async getUID() {
        const reader = this.readerManager.getSelectedReader();
        if (!reader) {
            this.displayResult({ status: 'error', message: 'No reader selected' });
            return;
        }
        
        try {
            const response = await this.api.get(`/smartcard/uid?reader=${encodeURIComponent(reader)}`);
            this.displayResult(response);
            
            if (response.status === 'success' && response.data?.uid) {
                this.uidElement.textContent = response.data.uid;
            }
        } catch (error) {
            this.displayResult({ status: 'error', message: error.message });
        }
    }
    
    async getCardInfo() {
        await this.getATR();
        await this.getUID();
        
        // Determine card type based on ATR (simplified)
        const atr = this.atrElement.textContent;
        if (atr.includes('3B 8F 80')) {
            this.cardTypeElement.textContent = 'MIFARE DESFire';
        } else if (atr.includes('3B 8C 80')) {
            this.cardTypeElement.textContent = 'MIFARE Classic';
        } else if (atr.includes('3B 89')) {
            this.cardTypeElement.textContent = 'ISO 14443 Type A';
        } else if (atr.includes('3B 8A')) {
            this.cardTypeElement.textContent = 'ISO 14443 Type B';
        } else {
            this.cardTypeElement.textContent = 'Unknown';
        }
    }
    
    async sendAPDU() {
        const reader = this.readerManager.getSelectedReader();
        if (!reader) {
            this.displayResult({ status: 'error', message: 'No reader selected' });
            return;
        }
        
        const command = this.apduCommandInput.value.trim();
        if (!command) {
            this.displayResult({ status: 'error', message: 'Please enter an APDU command' });
            return;
        }
        
        try {
            const response = await this.api.post('/smartcard/transmit', {
                reader: reader,
                command: command
            });
            
            this.displayResult(response);
            
            // Add to history
            if (response.status === 'success') {
                this.addToHistory(command);
            }
        } catch (error) {
            this.displayResult({ status: 'error', message: error.message });
        }
    }
    
    displayResult(data) {
        this.resultElement.classList.remove('fade-in');
        
        setTimeout(() => {
            if (data.status === 'error') {
                this.resultElement.innerHTML = `<span style="color: var(--danger-color);">${escapeHtml(data.message)}</span>`;
            } else {
                this.resultElement.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            }
            
            this.resultElement.classList.add('fade-in');
        }, 50);
    }
    
    copyResult() {
        const text = this.resultElement.innerText;
        navigator.clipboard.writeText(text)
            .then(() => UI.showToast('Copied to clipboard', 'success'))
            .catch(err => logger.error('Failed to copy text', { error: err }));
    }
    
    clearResult() {
        this.resultElement.innerHTML = 'Results will appear here...';
    }
    
    addToHistory(command) {
        const list = getElement('sc-command-history');
        const item = document.createElement('li');
        item.className = 'command-item';
        item.textContent = command;
        item.addEventListener('click', () => this.apduCommandInput.value = command);
        
        list.insertBefore(item, list.firstChild);
        
        // Keep history manageable
        while (list.children.length > 10) {
            list.removeChild(list.lastChild);
        }
        
        this.saveHistory();
    }
    
    saveHistory() {
        const list = getElement('sc-command-history');
        const commands = Array.from(list.children).map(item => item.textContent);
        saveToStorage('apdu-command-history', commands);
    }
    
    loadHistory() {
        const commands = loadFromStorage('apdu-command-history', []);
        const list = getElement('sc-command-history');
        
        list.innerHTML = '';
        commands.forEach(command => this.addToHistory(command));
    }
    
    clearHistory() {
        const list = getElement('sc-command-history');
        list.innerHTML = '';
        this.saveHistory();
    }
}

export default SmartCardManager;
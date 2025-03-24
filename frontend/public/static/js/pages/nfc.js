import NFCManager from '../components/nfc.js';
import API from '../core/api.js';
import ReaderManager from '../components/readers.js';
import logger from '../core/logger.js';
import UI from '../utils/ui.js';
import { getElement } from '../utils/dom.js';
import BankCard from '../components/bank-card.js';

/**
 * NFC Page Logic
 */
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const api = new API();
        const readerManager = new ReaderManager(api);
        await readerManager.initialize();

        const nfcManager = new NFCManager(api, readerManager);

        // Expose NFCManager instance for debugging
        window.nfcManager = nfcManager;

        // Enhanced error handling and UI feedback
        readerManager.on('readersUpdated', (readers) => {
            if (readers && readers.length > 0) {
                UI.showToast('NFC readers updated.', 'success');
            } else {
                UI.showToast('No NFC readers found.', 'warning');
            }
        });

        readerManager.on('cardStatusChanged', (present, cardData) => {
            if (present) {
                UI.showToast('NFC card detected.', 'info');
                logger.info('NFC Card Data:', cardData);
            } else {
                UI.showToast('NFC card removed.', 'info');
            }
        });

        // Global error listener
        window.addEventListener('error', (event) => {
            logger.error('Unhandled error:', event.error || event.message, event);
            UI.showToast(`An unexpected error occurred: ${event.error ? event.error.message : event.message}`, 'error');
        });

        // Global unhandled rejection listener
        window.addEventListener('unhandledrejection', (event) => {
            logger.error('Unhandled promise rejection:', event.reason, event);
            UI.showToast(`An unexpected promise rejection occurred: ${event.reason}`, 'error');
        });

        // Implement a more robust error handling mechanism
        // that displays errors to the user in a user-friendly way.
        nfcManager.readerManager.on('readerChanged', (readerName) => {
            UI.showToast(`Reader changed to ${readerName}`, 'info');
        });

        // Example of using UI.showModal for confirmations or data input
        const confirmWrite = async (data) => {
            return new Promise((resolve) => {
                UI.showModal(
                    'Confirm Write',
                    `Are you sure you want to write this data to the NFC tag?\n\n${JSON.stringify(data, null, 2)}`,
                    {
                        confirm: () => resolve(true),
                        cancel: () => resolve(false)
                    },
                    {
                        confirmText: 'Write',
                        cancelText: 'Cancel',
                        size: 'md',
                        centered: true
                    }
                );
            });
        };

        // Example usage (assuming nfcManager has a writeText function)
        const writeData = async (text) => {
            const confirmed = await confirmWrite({ type: 'text', content: text });
            if (confirmed) {
                try {
                    const result = await nfcManager.writeText(text);
                    UI.showToast(`Write operation result: ${result.status}`, result.status === 'success' ? 'success' : 'error');
                } catch (writeError) {
                    logger.error('Error during write operation:', writeError);
                    UI.showToast(`Write operation failed: ${writeError.message}`, 'error');
                }
            } else {
                UI.showToast('Write operation cancelled.', 'info');
            }
        };

        // Attach writeData to a button (example)
        const writeButton = getElement('write-text-btn');
        if (writeButton) {
            writeButton.addEventListener('click', () => {
                const textInput = getElement('text-input');
                if (textInput) {
                    writeData(textInput.value);
                } else {
                    UI.showToast('Text input element not found.', 'error');
                }
            });
        }

        // Initialize the page
        const nfcCardContainer = getElement('nfc-card-container');
        
        if (nfcCardContainer) {
            const bankCard = new BankCard({
                cardNumber: '6475 9281 3821 7463',
                name: 'NFC TAG DEMO',
                validThru: '01/27',
                container: nfcCardContainer
            });
            
            // Optionally store the bank card instance for later use
            window.nfcBankCard = bankCard;
            
            // Example: Update card status based on NFC operations
            const nfcManager = window.app?.nfcManager;
            if (nfcManager) {
                // Listen for operation start
                nfcManager.onOperationStart = (operation) => {
                    bankCard.setStatus('processing');
                    logger.debug('NFC operation started', { operation });
                };
                
                // Listen for operation completion
                nfcManager.onOperationComplete = (operation, success) => {
                    bankCard.setStatus(success ? 'verified' : 'error');
                    setTimeout(() => bankCard.setStatus('default'), 3000);
                    logger.debug('NFC operation completed', { operation, success });
                };
            }
        }

    } catch (error) {
        logger.error('Error initializing NFC page:', error);
        UI.showToast('Failed to initialize NFC page.', 'error');
    }
});
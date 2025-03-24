import BankCard from '../components/bank-card.js';
import logger from '../core/logger.js';
import { getElement } from '../utils/dom.js';
import { apiRequest } from '../services/api.js';

document.addEventListener('DOMContentLoaded', () => {
    const mifareContainer = getElement('mifare-card-container');
    const statusElement = getElement('mifare-status');
    const readButton = getElement('mifare-read-btn');
    const writeButton = getElement('mifare-write-btn');
    
    if (!mifareContainer) {
        logger.error('MIFARE card container not found');
        return;
    }
    
    try {
        const bankCard = new BankCard({
            cardNumber: '5412 7534 9021 4567',
            name: 'MIFARE CLASSIC',
            validThru: '06/26',
            container: mifareContainer
        });
        
        window.mifareBankCard = bankCard;
        
        // MIFARE operation handlers
        const handleReadCard = async () => {
            try {
                updateStatus('Reading card data...');
                const response = await apiRequest('/api/mifare/read');
                if (response.success) {
                    updateStatus('Card read successfully');
                    bankCard.updateCardData(response.data);
                } else {
                    throw new Error(response.message || 'Failed to read card');
                }
            } catch (error) {
                logger.error('MIFARE read error:', error);
                updateStatus('Failed to read card: ' + error.message);
            }
        };
        
        const handleWriteCard = async () => {
            try {
                updateStatus('Writing to card...');
                const cardData = bankCard.getCardData();
                const response = await apiRequest('/api/mifare/write', {
                    method: 'POST',
                    body: JSON.stringify(cardData)
                });
                updateStatus(response.success ? 'Card written successfully' : 'Write failed');
            } catch (error) {
                logger.error('MIFARE write error:', error);
                updateStatus('Failed to write to card: ' + error.message);
            }
        };
        
        // Helper function to update status
        const updateStatus = (message) => {
            if (statusElement) {
                statusElement.textContent = message;
            }
            logger.info('MIFARE status:', message);
        };
        
        // Add event listeners
        if (readButton) readButton.addEventListener('click', handleReadCard);
        if (writeButton) writeButton.addEventListener('click', handleWriteCard);
        
    } catch (error) {
        logger.error('Error initializing MIFARE card:', error);
    }
});
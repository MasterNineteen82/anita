import BankCard from '../components/bank-card.js';
import logger from '../core/logger.js';
import { getElement } from '../utils/dom.js';
import { fetchSmartCardData } from '../services/api.js';

document.addEventListener('DOMContentLoaded', async () => {
    const smartcardContainer = getElement('smartcard-card-container');
    const loadingIndicator = getElement('smartcard-loading') || createLoadingIndicator();
    
    if (!smartcardContainer) {
        logger.error('Smartcard container not found');
        return;
    }
    
    try {
        showLoading(loadingIndicator, smartcardContainer);
        
        // Fetch card data from API instead of hardcoding
        const cardData = await fetchSmartCardData();
        
        const bankCard = new BankCard({
            cardNumber: cardData.number || '•••• •••• •••• ••••',
            name: cardData.holderName || 'SMARTCARD USER',
            validThru: cardData.expiryDate || '--/--',
            container: smartcardContainer
        });
        
        window.smartcardBankCard = bankCard;
        
        // Implement SmartCard operation listeners
        setupEventListeners(bankCard);
        
    } catch (error) {
        logger.error('Failed to initialize smartcard:', error);
        showErrorMessage(smartcardContainer, 'Unable to load card information');
    } finally {
        hideLoading(loadingIndicator);
    }
});

function setupEventListeners(bankCard) {
    const reloadBtn = getElement('smartcard-reload');
    const activateBtn = getElement('smartcard-activate');
    
    if (reloadBtn) {
        reloadBtn.addEventListener('click', async () => {
            try {
                await bankCard.reload();
                logger.info('Card reloaded successfully');
            } catch (error) {
                logger.error('Reload failed:', error);
            }
        });
    }
    
    if (activateBtn) {
        activateBtn.addEventListener('click', async () => {
            try {
                await bankCard.activate();
                logger.info('Card activated successfully');
            } catch (error) {
                logger.error('Activation failed:', error);
            }
        });
    }
}

function createLoadingIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'smartcard-loading';
    indicator.className = 'loading-spinner';
    indicator.style.display = 'none';
    document.body.appendChild(indicator);
    return indicator;
}

function showLoading(indicator, container) {
    if (indicator && container) {
        indicator.style.display = 'block';
        container.classList.add('loading');
    }
}

function hideLoading(indicator) {
    if (indicator) {
        indicator.style.display = 'none';
    }
    const container = getElement('smartcard-card-container');
    if (container) {
        container.classList.remove('loading');
    }
}

function showErrorMessage(container, message) {
    if (container) {
        const errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        errorElement.textContent = message;
        container.appendChild(errorElement);
    }
}
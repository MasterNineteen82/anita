/**
 * Main application entry point
 */
import API from './core/api.js';
import CONFIG from './core/config.js';
import WebSocketService from './services/websocket.js';
import ReaderManager from './components/readers.js';
import SmartCardManager from './components/smartcard.js';
import MifareManager from './components/mifare.js';
import NFCManager from './components/nfc.js';
import logger from './core/logger.js';
import CardGridManager from './components/card-grid.js';

class App {
    constructor() {
        logger.info('Initializing application');

        this.api = new API(CONFIG.apiBaseUrl);
        this.ws = new WebSocketService(CONFIG);
        this.components = {}; // Centralized component registry

        this.setupWebSocketHandlers();
    }

    registerComponent(name, component) {
        this.components[name] = component;
    }

    async initialize() {
        try {
            await this.initializeComponents();
            logger.info('Application initialized');
        } catch (error) {
            logger.error('Error initializing application:', error);
        }
    }

    setupWebSocketHandlers() {
        this.ws.on('card_inserted', (data) => {
            logger.info('Card inserted event', data);
            try {
                if (this.components.readerManager) {
                    this.components.readerManager.handleCardEvent(data);
                }
            } catch (error) {
                logger.error('Error handling card_inserted event:', error);
            }
        });

        this.ws.on('card_removed', (data) => {
            logger.info('Card removed event', data);
            try {
                if (this.components.readerManager) {
                    this.components.readerManager.handleCardRemoved(data);
                }
            } catch (error) {
                logger.error('Error handling card_removed event:', error);
            }
        });

        this.ws.on('reader_connected', (data) => {
            logger.info('Reader connected event', data);
            try {
                if (this.components.readerManager) {
                    this.components.readerManager.fetchReaders();
                }
            } catch (error) {
                logger.error('Error handling reader_connected event:', error);
            }
        });

        this.ws.on('reader_disconnected', (data) => {
            logger.info('Reader disconnected event', data);
            try {
                if (this.components.readerManager) {
                    this.components.readerManager.fetchReaders();
                }
            } catch (error) {
                logger.error('Error handling reader_disconnected event:', error);
            }
        });
    }

    async initializeComponents() {
        // Initialize ReaderManager
        if (document.getElementById('reader-select')) {
            const readerManager = new ReaderManager(this.api);
            this.registerComponent('readerManager', readerManager);
            await readerManager.initialize(); // Assuming initialize is async
        }

        // Initialize page-specific components
        if (document.getElementById('smartcard-container')) {
            const smartCardManager = new SmartCardManager(this.api, this.components.readerManager);
            this.registerComponent('smartCardManager', smartCardManager);
            await smartCardManager.initialize(); // Assuming initialize is async
        }

        if (document.getElementById('mifare-container')) {
            const mifareManager = new MifareManager(this.api, this.components.readerManager);
            this.registerComponent('mifareManager', mifareManager);
            await mifareManager.initialize(); // Assuming initialize is async
        }

        if (document.getElementById('nfc-container')) {
            const nfcManager = new NFCManager(this.api, this.components.readerManager);
            this.registerComponent('nfcManager', nfcManager);
            await nfcManager.initialize(); // Assuming initialize is async
        }
    }

    dispose() {
        logger.info('Disposing application resources');

        // Dispose of components
        for (const componentName in this.components) {
            if (this.components[componentName] && typeof this.components[componentName].dispose === 'function') {
                try {
                    this.components[componentName].dispose();
                } catch (error) {
                    logger.error(`Error disposing of component ${componentName}:`, error);
                }
            }
        }

        // Disconnect WebSocket
        try {
            this.ws.disconnect();
        } catch (error) {
            logger.error('Error disconnecting WebSocket:', error);
        }

        logger.info('Application resources disposed');
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    try {
        window.app = new App();
        await window.app.initialize();

        // Initialize card grid for drag-and-drop functionality
        const cardGrid = new CardGridManager();
        window.cardGrid = cardGrid; // Make it available globally if needed
    } catch (error) {
        console.error('Error initializing application:', error);
    }
});

// Dispose of resources on page unload
window.addEventListener('beforeunload', () => {
    if (window.app) {
        window.app.dispose();
    }
});
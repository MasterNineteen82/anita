import CONFIG from './core/config.js';
import App from './app.js';

// Single entry point for the entire application
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Create and initialize the application
        window.app = new App({
            apiBaseUrl: CONFIG.apiBaseUrl,
            debug: CONFIG.features.debugMode
        });
        
        await window.app.initialize();
        
        // Register current page handler
        const currentPage = document.body.dataset.page;
        if (currentPage && window.app.pageHandlers[currentPage]) {
            await window.app.pageHandlers[currentPage].initialize();
        }
    } catch (error) {
        console.error('Application initialization failed:', error);
    }
});
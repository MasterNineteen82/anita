// Main entry point for all page-specific JavaScript

// Import modules based on the current page
document.addEventListener('DOMContentLoaded', () => {
    const currentPath = window.location.pathname;
    if (currentPath.includes('/ble')) {
        import('./ble/ble.js').catch(err => {
            console.error('Error loading BLE module:', err);
            const mainContent = document.getElementById('main-content');
            if (mainContent) {
                mainContent.innerHTML = `
                    <div class="p-4 bg-red-100 text-red-800 rounded">
                        <h3 class="font-bold">Module Load Error</h3>
                        <p>Failed to load BLE functionality: ${err.message}</p>
                    </div>
                `;
            }
        });
    }
});
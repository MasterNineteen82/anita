/**
 * Frontend configuration
 */
const CONFIG = {
    // API settings
    apiBaseUrl: process.env.NODE_ENV === 'production' ? 'https://api.example.com' : '/api',
    wsUrl: `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/events`,
    
    // Feature flags
    features: {
        enableLogging: true,
        enableAutodetection: true,
        enableAnimation: true,
        debugMode: process.env.NODE_ENV !== 'production',
        enableNotifications: true,
        enableDarkMode: true
    },
    
    // Card detection settings
    cardDetection: {
        pollInterval: 1000,
        retryCount: 3
    },
    
    // UI settings
    ui: {
        theme: 'dark', // or 'light'
        language: 'en' // default language
    }
};

export default CONFIG;
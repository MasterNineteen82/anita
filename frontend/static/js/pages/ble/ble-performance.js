import { BleAdapter } from "./ble-adapter.js";

export class BlePerformance {
    static measurements = {};
    
    static startMeasure(label) {
        performance.mark(`${label}-start`);
    }
    
    static endMeasure(label) {
        performance.mark(`${label}-end`);
        performance.measure(label, `${label}-start`, `${label}-end`);
        
        const measure = performance.getEntriesByName(label)[0];
        this.measurements[label] = measure.duration;
        
        console.log(`Performance: ${label} took ${measure.duration.toFixed(2)}ms`);
        return measure.duration;
    }
    
    static getStats() {
        return this.measurements;
    }
}

export class BlePerformanceUI {
    static init() {
        const statsContainer = document.createElement('div');
        statsContainer.id = 'ble-performance-stats';
        statsContainer.style.position = 'fixed';
        statsContainer.style.top = '10px';
        statsContainer.style.right = '10px';
        statsContainer.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
        statsContainer.style.padding = '10px';
        statsContainer.style.borderRadius = '5px';
        statsContainer.style.zIndex = '1000';
        
        document.body.appendChild(statsContainer);
    }
    
    static updateStats() {
        const statsContainer = document.getElementById('ble-performance-stats');
        const stats = BlePerformance.getStats();
        
        statsContainer.innerHTML = '<h4>BLE Performance Stats</h4>';
        
        for (const [label, duration] of Object.entries(stats)) {
            const statItem = document.createElement('div');
            statItem.textContent = `${label}: ${duration.toFixed(2)}ms`;
                    statsContainer.appendChild(statItem);
        }
    }
}

export class BleMetrics {
    constructor() {
        this.measurements = {};
    }
    
    start(label) {
        performance.mark(`${label}-start`);
    }
    
    end(label) {
        performance.mark(`${label}-end`);
        performance.measure(label, `${label}-start`, `${label}-end`);
        
        const measure = performance.getEntriesByName(label)[0];
        this.measurements[label] = measure.duration;
        
        console.log(`Performance: ${label} took ${measure.duration.toFixed(2)}ms`);
        return measure.duration;
    }
    
    getStats() {
        return this.measurements;
    }
}

// BleAdapter is already imported at the top, so no need to export it again
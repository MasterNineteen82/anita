/**
 * Performs health checks on critical backend services
 * and updates UI accordingly
 */
class ServiceHealthChecker {
    constructor(services = {}, healthCheckInterval = 30000) {
        this.services = services;
        this.healthStatus = {};
        this.interval = healthCheckInterval;
        this.intervalId = null;
    }

    /**
     * Start running periodic health checks
     */
    start() {
        this.checkAllServices();
        this.intervalId = setInterval(() => this.checkAllServices(), this.interval);
    }

    /**
     * Check all registered services
     */
    async checkAllServices() {
        for (const [name, endpoint] of Object.entries(this.services)) {
            try {
                const isHealthy = await this.checkService(endpoint);
                this.updateServiceStatus(name, isHealthy);
            } catch (error) {
                this.updateServiceStatus(name, false);
            }
        }
        this.updateUI();
    }

    /**
     * Check an individual service
     */
    async checkService(endpoint) {
        try {
            const response = await fetch(endpoint, { 
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });
            return response.ok;
        } catch (error) {
            console.error(`Health check failed for ${endpoint}:`, error);
            return false;
        }
    }

    /**
     * Update the status of a service
     */
    updateServiceStatus(name, isHealthy) {
        this.healthStatus[name] = isHealthy;
        document.dispatchEvent(new CustomEvent('service-status-change', {
            detail: { service: name, healthy: isHealthy }
        }));
    }

    /**
     * Update the UI to reflect service health
     */
    updateUI() {
        const statusContainer = document.getElementById('service-status-container');
        if (!statusContainer) return;

        statusContainer.innerHTML = '';
        
        for (const [name, isHealthy] of Object.entries(this.healthStatus)) {
            const statusEl = document.createElement('div');
            statusEl.className = `service-status ${isHealthy ? 'healthy' : 'unhealthy'}`;
            statusEl.innerHTML = `
                <span class="status-indicator ${isHealthy ? 'bg-green-500' : 'bg-red-500'}"></span>
                <span class="service-name">${name}</span>
            `;
            statusContainer.appendChild(statusEl);
        }
    }

    /**
     * Stop health checks
     */
    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
}
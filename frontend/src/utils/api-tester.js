// Utility to test all API endpoints and verify they're working

import apiClient from '../api/client';
import API_ROUTES from '../config/api-routes';

class ApiTester {
  async testAllEndpoints() {
    const results = {
      succeeded: [],
      failed: [],
    };

    // Test System endpoints
    await this.testEndpoint(API_ROUTES.SYSTEM.STATUS, 'GET', null, results);
    
    // Test SmartCard endpoints
    await this.testEndpoint(API_ROUTES.SMARTCARD.READERS, 'GET', null, results);
    await this.testEndpoint(API_ROUTES.SMARTCARD.STATUS, 'GET', null, results);
    
    // Test NFC endpoints
    await this.testEndpoint(API_ROUTES.NFC.STATUS, 'GET', null, results);
    await this.testEndpoint(API_ROUTES.NFC.DEVICES, 'GET', null, results);
    await this.testEndpoint(API_ROUTES.NFC.DISCOVER, 'GET', null, results);
    
    // Additional endpoints can be tested here
    
    return results;
  }

  async testEndpoint(endpoint, method = 'GET', body = null, results) {
    try {
      const options = {
        method,
      };
      
      if (body) {
        options.body = JSON.stringify(body);
      }
      
      await apiClient.request(endpoint, options);
      results.succeeded.push(endpoint);
      console.log(`✅ Endpoint ${endpoint} is working`);
    } catch (error) {
      results.failed.push({ endpoint, error: error.message });
      console.error(`❌ Endpoint ${endpoint} failed:`, error);
    }
  }

  // No changes needed if using proxy configuration correctly

  // If you need to test the full setup including proxy:
  async testProxyAndBackend() {
    const results = {
      proxy: 'unknown',
      backend: 'unknown',
      apiEndpoints: []
    };

    // Test if proxy is working
    try {
      await fetch('/api/status');
      results.proxy = 'working';
    } catch (e) {
      results.proxy = 'failed';
    }

    // Test if direct backend connection works (bypassing proxy)
    try {
      await fetch('http://localhost:8000/api/status');
      results.backend = 'working';
    } catch (e) {
      results.backend = 'failed';
    }

    // Test all API endpoints through proxy
    results.apiEndpoints = await this.testAllEndpoints();
    
    return results;
  }
}

export default new ApiTester();
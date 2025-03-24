import API_ROUTES from '../config/api-routes';

class ApiClient {
  constructor(baseUrl = '/api') {
    this.baseUrl = baseUrl;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `API Error: ${response.status}`);
      }

      const data = await response.json();
      
      // Check for standardized error response
      if (data.status === 'error') {
        throw new Error(data.message || 'API Error');
      }
      
      return data;
    } catch (error) {
      console.error(`API Error (${endpoint}):`, error);
      throw error;
    }
  }

  // System APIs
  async getStatus() {
    return this.request(API_ROUTES.SYSTEM.STATUS);
  }

  // Smartcard APIs
  async getSmartcardReaders() {
    return this.request(API_ROUTES.SMARTCARD.READERS);
  }
  
  async transmitAPDU(reader, apdu) {
    return this.request(API_ROUTES.SMARTCARD.TRANSMIT, {
      method: 'POST',
      body: JSON.stringify({ reader, apdu })
    });
  }

  // NFC APIs  
  async getNFCStatus() {
    return this.request(API_ROUTES.NFC.STATUS);
  }

  async discoverNFCTags() {
    return this.request(API_ROUTES.NFC.DISCOVER);
  }
}

export default new ApiClient();
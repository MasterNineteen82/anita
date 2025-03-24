import API_ROUTES from '../config/api-routes';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.callbacks = {
      onSmartcardUpdate: null,
      onConnectionChange: null
    };
    this.reconnectInterval = null;
    this.isConnected = false;
  }

  connectToSmartcardWS() {
    if (this.socket) this.disconnect();
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}${API_ROUTES.WEBSOCKETS.SMARTCARD}`;
    
    this.socket = new WebSocket(wsUrl);
    
    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.isConnected = true;
      if (this.callbacks.onConnectionChange) {
        this.callbacks.onConnectionChange(true);
      }
      
      // Clear reconnect interval if it was set
      if (this.reconnectInterval) {
        clearInterval(this.reconnectInterval);
        this.reconnectInterval = null;
      }
    };
    
    this.socket.onclose = () => {
      console.log('WebSocket disconnected');
      this.isConnected = false;
      if (this.callbacks.onConnectionChange) {
        this.callbacks.onConnectionChange(false);
      }
      
      // Set up reconnection
      if (!this.reconnectInterval) {
        this.reconnectInterval = setInterval(() => {
          if (!this.isConnected) this.connectToSmartcardWS();
        }, 5000);
      }
    };
    
    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle different message types
        if (data.type === 'reader_status' && this.callbacks.onSmartcardUpdate) {
          this.callbacks.onSmartcardUpdate(data.data);
        }
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
      }
    };
    
    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    
    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval);
      this.reconnectInterval = null;
    }
  }
  
  registerCallbacks(callbacks) {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }
}

export default new WebSocketService();
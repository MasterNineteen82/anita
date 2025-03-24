// Maps to our refactored backend routes

const API_ROUTES = {
  SYSTEM: {
    STATUS: '/status',
    LOG: '/log'
  },
  SMARTCARD: {
    READERS: '/smartcard/readers',
    STATUS: '/smartcard/status', 
    ATR: '/smartcard/atr',
    TRANSMIT: '/smartcard/transmit'
  },
  NFC: {
    STATUS: '/nfc/status',
    DEVICES: '/nfc/devices',
    DISCOVER: '/nfc/discover'
  },
  WEBSOCKETS: {
    SMARTCARD: '/ws/smartcard'
  }
};

export default API_ROUTES;
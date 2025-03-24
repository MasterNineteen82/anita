// logger.js: Unified logging utility for ANITA application

export default class Logger {
  
  static log(level, message, details = {}) {
    const timestamp = new Date().toISOString();
    const formattedMessage = `[${timestamp}] [${level.toUpperCase()}]: ${message}`;

    switch(level) {
      case 'info':
        console.info(formattedMessage, details);
        break;
      case 'warn':
        console.warn(formattedMessage, details);
        break;
      case 'error':
        console.error(formattedMessage, details);
        break;
      default:
        console.log(formattedMessage, details);
        break;
    }

    // Optionally extend here to log to a backend endpoint
    // Logger.sendToServer(level, message, details);
  }

  static info(message, details = {}) {
    Logger.log('info', message, details);
  }

  static warn(message, details = {}) {
    Logger.log('warn', message, details);
  }

  static error(message, details = {}) {
    Logger.log('error', message, details);
  }

  // Extendable method for future backend integration
  static async sendToServer(level, message, details) {
    try {
      await fetch('/api/logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level, message, details, timestamp: new Date().toISOString() })
      });
    } catch (e) {
      console.error('Logging to server failed:', e);
    }
  }
}

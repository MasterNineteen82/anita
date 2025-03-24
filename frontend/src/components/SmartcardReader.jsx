// Example of updating a component to work with our new API structure

import React, { useEffect, useState } from 'react';
import apiClient from '../api/client';
import websocketService from '../services/websocket-service';

function SmartcardReader() {
  const [readers, setReaders] = useState([]);
  const [selectedReader, setSelectedReader] = useState(0);
  const [readerStatus, setReaderStatus] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  
  // Fetch readers on component mount
  useEffect(() => {
    const fetchReaders = async () => {
      try {
        const response = await apiClient.getSmartcardReaders();
        if (response.status === 'success' && response.data.readers) {
          setReaders(response.data.readers);
        }
      } catch (error) {
        console.error('Error fetching smartcard readers:', error);
      }
    };
    
    fetchReaders();
    
    // Set up WebSocket
    websocketService.registerCallbacks({
      onSmartcardUpdate: (data) => setReaderStatus(data),
      onConnectionChange: (connected) => setIsConnected(connected)
    });
    
    websocketService.connectSmartcardMonitor();
    
    // Clean up
    return () => {
      websocketService.disconnectSmartcardMonitor();
    };
  }, []);
  
  // Component rendering
  return (
    <div className="smartcard-reader-container">
      <h2>Smartcard Reader</h2>
      
      {/* Connection status indicator */}
      <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
        {isConnected ? 'Connected' : 'Disconnected'}
      </div>
      
      {/* Reader selection */}
      {readers.length > 0 && (
        <div className="reader-selector">
          <label htmlFor="reader-select">Select Reader:</label>
          <select 
            id="reader-select"
            value={selectedReader}
            onChange={(e) => setSelectedReader(Number(e.target.value))}
          >
            {readers.map((reader, index) => (
              <option key={index} value={index}>
                {reader}
              </option>
            ))}
          </select>
        </div>
      )}
      
      {/* Reader status */}
      {readerStatus && (
        <div className="reader-status">
          <h3>Status</h3>
          <ul>
            {readerStatus.readers.map((reader, index) => (
              <li key={index}>
                <strong>{reader.name}</strong>: 
                {reader.has_card ? (
                  <span className="card-present">Card Present ({reader.card_type || 'Unknown'})</span>
                ) : (
                  <span className="no-card">No Card</span>
                )}
              </li>
            ))}
          </ul>
          <p className="timestamp">Last updated: {new Date(readerStatus.timestamp).toLocaleTimeString()}</p>
        </div>
      )}
    </div>
  );
}

export default SmartcardReader;
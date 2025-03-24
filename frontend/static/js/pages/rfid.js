import UI from '/static/js/utils/ui.js';
import Logger from '/static/js/utils/logger.js';

document.addEventListener('DOMContentLoaded', () => {
  const rfidStatus = document.getElementById('rfid-status');
  const tagId = document.getElementById('tag-id');
  const startReadingBtn = document.getElementById('start-reading-btn');
  const stopReadingBtn = document.getElementById('stop-reading-btn');
  const clearDataBtn = document.getElementById('clear-data-btn');
  const logContainer = document.getElementById('log-container');

  let readingActive = false;

  // Function to add a log entry
  function addLogEntry(message, type = 'info') {
    const logEntry = document.createElement('div');
    logEntry.className = `text-xs font-mono border-l-2 pl-2 py-1 mb-1`;
    if (type === 'error') {
      logEntry.classList.add('border-red-500', 'text-red-400');
    } else if (type === 'success') {
      logEntry.classList.add('border-green-500', 'text-green-400');
    } else {
      logEntry.classList.add('border-gray-500', 'text-gray-400');
    }
    logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
  }

  // Function to update the RFID status
  function updateStatus(status, tag = null) {
    rfidStatus.textContent = status;
    tagId.textContent = tag || 'N/A';
  }

  // Function to start reading RFID tags
  async function startReading() {
    readingActive = true;
    UI.setLoading('start-reading-btn', true);
    updateStatus('Starting...');

    try {
      const response = await fetch('/api/rfid/start', { method: 'POST' });
      const data = await response.json();

      if (data.success) {
        updateStatus('Reading...');
        addLogEntry('RFID reading started', 'success');
        startPolling(); // Start polling for tag data
      } else {
        updateStatus('Error');
        addLogEntry(`Failed to start reading: ${data.error}`, 'error');
        UI.toast(`Failed to start reading: ${data.error}`, 'error');
      }
    } catch (error) {
      console.error('Error starting RFID reading:', error);
      updateStatus('Error');
      addLogEntry(`Failed to start reading: ${error.message}`, 'error');
      UI.toast('Failed to start reading. Check console.', 'error');
    } finally {
      UI.setLoading('start-reading-btn', false);
    }
  }

  // Function to stop reading RFID tags
  async function stopReading() {
    readingActive = false;
    UI.setLoading('stop-reading-btn', true);
    updateStatus('Stopping...');

    try {
      const response = await fetch('/api/rfid/stop', { method: 'POST' });
      const data = await response.json();

      if (data.success) {
        updateStatus('Stopped');
        addLogEntry('RFID reading stopped', 'success');
      } else {
        updateStatus('Error');
        addLogEntry(`Failed to stop reading: ${data.error}`, 'error');
        UI.toast(`Failed to stop reading: ${data.error}`, 'error');
      }
    } catch (error) {
      console.error('Error stopping RFID reading:', error);
      updateStatus('Error');
      addLogEntry(`Failed to stop reading: ${error.message}`, 'error');
      UI.toast('Failed to stop reading. Check console.', 'error');
    } finally {
      UI.setLoading('stop-reading-btn', false);
    }
  }

  // Function to poll for RFID tag data
  async function startPolling() {
    while (readingActive) {
      try {
        const response = await fetch('/api/rfid/tag');
        const data = await response.json();

        if (data.success && data.tag_id) {
          updateStatus('Tag Detected', data.tag_id);
          addLogEntry(`Tag detected: ${data.tag_id}`, 'info');
        } else if (data.success) {
          updateStatus('Reading...'); // No tag detected
        } else {
          addLogEntry(`Error reading tag: ${data.error}`, 'error');
        }
      } catch (error) {
        console.error('Error polling for RFID tag:', error);
        addLogEntry(`Error polling for tag: ${error.message}`, 'error');
      }
      await new Promise(resolve => setTimeout(resolve, 1000)); // Poll every 1 second
    }
  }

  // Event listeners
  startReadingBtn.addEventListener('click', startReading);
  stopReadingBtn.addEventListener('click', stopReading);
  clearDataBtn.addEventListener('click', () => {
    logContainer.innerHTML = ''; // Clear the log
    updateStatus('Stopped'); // Reset the status
  });
});
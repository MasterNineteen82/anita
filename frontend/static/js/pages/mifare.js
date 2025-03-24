// mifare.js: Handles MIFARE page interactions and card operations
import UI from '/static/js/utils/ui.js';
import Logger from '/static/js/utils/logger.js';

document.addEventListener('DOMContentLoaded', () => {
  const readerSelect = document.getElementById('reader-select');
  const sectorInput = document.getElementById('sector-input');
  const blockInput = document.getElementById('block-input');
  const dataInput = document.getElementById('data-input');
  const keyInput = document.getElementById('key-input');
  const readBtn = document.getElementById('read-btn');
  const writeBtn = document.getElementById('write-btn');
  const logContainer = document.getElementById('log-container');
  const refreshReadersBtn = document.getElementById('refresh-readers-btn');

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

  // Function to load available readers
  async function loadReaders() {
    UI.setLoading('refresh-readers-btn', true);
    try {
      const response = await fetch('/api/mifare/readers');
      const data = await response.json();

      if (data.success && data.readers) {
        readerSelect.innerHTML = data.readers.map(reader => `<option value="${reader}">${reader}</option>`).join('');
        addLogEntry('Readers loaded successfully.', 'success');
      } else {
        readerSelect.innerHTML = '<option>No readers found</option>';
        addLogEntry(`Failed to load readers: ${data.error}`, 'warn');
        UI.toast(`Failed to load readers: ${data.error}`, 'warn');
      }
    } catch (error) {
      console.error('Error loading readers:', error);
      addLogEntry(`Error loading readers: ${error.message}`, 'error');
      UI.toast('Error loading readers. Check console.', 'error');
    } finally {
      UI.setLoading('refresh-readers-btn', false);
    }
  }

  // Function to read data from a Mifare card
  async function readData() {
    const reader = readerSelect.value;
    const sector = parseInt(sectorInput.value);
    const block = parseInt(blockInput.value);
    const key = keyInput.value.trim();

    if (!reader || isNaN(sector) || isNaN(block) || !key) {
      UI.toast('Please fill in all the required fields.', 'warn');
      return;
    }

    UI.setLoading('read-btn', true);
    try {
      const response = await fetch('/api/mifare/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reader, sector, block, key }),
      });

      const data = await response.json();

      if (data.success && data.data) {
        dataInput.value = data.data;
        addLogEntry(`Data read successfully from Sector ${sector}, Block ${block}: ${data.data}`, 'success');
      } else {
        addLogEntry(`Failed to read data: ${data.error}`, 'error');
        UI.toast(`Failed to read data: ${data.error}`, 'error');
      }
    } catch (error) {
      console.error('Error reading data:', error);
      addLogEntry(`Error reading data: ${error.message}`, 'error');
      UI.toast('Error reading data. Check console.', 'error');
    } finally {
      UI.setLoading('read-btn', false);
    }
  }

  // Function to write data to a Mifare card
  async function writeData() {
    const reader = readerSelect.value;
    const sector = parseInt(sectorInput.value);
    const block = parseInt(blockInput.value);
    const data = dataInput.value.trim();
    const key = keyInput.value.trim();

    if (!reader || isNaN(sector) || isNaN(block) || !data || !key) {
      UI.toast('Please fill in all the required fields.', 'warn');
      return;
    }

    UI.setLoading('write-btn', true);
    try {
      const response = await fetch('/api/mifare/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reader, sector, block, data, key }),
      });

      const data = await response.json();

      if (data.success) {
        addLogEntry(`Data written successfully to Sector ${sector}, Block ${block}`, 'success');
        UI.toast('Data written successfully.', 'success');
      } else {
        addLogEntry(`Failed to write data: ${data.error}`, 'error');
        UI.toast(`Failed to write data: ${data.error}`, 'error');
      }
    } catch (error) {
      console.error('Error writing data:', error);
      addLogEntry(`Error writing data: ${error.message}`, 'error');
      UI.toast('Error writing data. Check console.', 'error');
    } finally {
      UI.setLoading('write-btn', false);
    }
  }

  // Event listeners
  readBtn.addEventListener('click', readData);
  writeBtn.addEventListener('click', writeData);
  refreshReadersBtn.addEventListener('click', loadReaders);

  // Load readers on page load
  loadReaders();
});

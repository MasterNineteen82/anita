// smartcard.js: Handles Smartcard page interactions clearly and consistently
import UI from '/static/js/utils/ui.js';
import Logger from '/static/js/utils/logger.js';

document.addEventListener('DOMContentLoaded', () => {
  // Add your Smartcard-specific JavaScript code here
  console.log('Smartcard page loaded.');
  
  const readerSelect = document.getElementById('reader-select');
  const refreshBtn = document.getElementById('reader-refresh-btn');
  const sendApduBtn = document.getElementById('send-apdu');
  const apduCommandInput = document.getElementById('apdu-command');
  const apduResponseOutput = document.getElementById('apdu-response');

  // Load Readers
  async function loadReaders() {
    UI.setLoading('reader-refresh-btn', true);
    try {
      const response = await fetch('/api/smartcard/readers');
      const readers = await response.json();

      readerSelect.innerHTML = readers.length
        ? readers.map(r => `<option>${r}</option>`).join('')
        : `<option>No readers found</option>`;

      Logger.info('Readers loaded', { count: readers.length });
    } catch (err) {
      Logger.error('Failed to load readers', err);
      UI.toast('Error loading readers', 'error');
    } finally {
      UI.setLoading('reader-refresh-btn', false);
    }
  }

  // Send APDU command
  async function sendAPDU() {
    const reader = readerSelect.value;
    const command = apduCommandInput.value.trim();

    if (!reader || !command) {
      UI.toast('Please select a reader and enter a command.', 'warn');
      return;
    }

    UI.setLoading('send-apdu', true);
    try {
      const response = await fetch('/api/smartcard/apdu', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reader, command })
      });

      const data = await response.json();
      apduResponseOutput.value = data.response;
      Logger.info('APDU sent successfully', { reader, command });
    } catch (err) {
      Logger.error('Failed to send APDU command', err);
      UI.toast('Error sending APDU', 'error');
    } finally {
      UI.setLoading('send-apdu', false);
    }
  }

  // Event listeners
  refreshBtn.addEventListener('click', loadReaders);
  sendApduBtn.addEventListener('click', sendAPDU);

  // Initial load
  loadReaders();
});

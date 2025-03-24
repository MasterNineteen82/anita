// nfc.js: Handles NFC page interactions and tag operations
import UI from '/static/js/utils/ui.js';
import Logger from '/static/js/utils/logger.js';

document.addEventListener('DOMContentLoaded', () => {
  const readerSelect = document.getElementById('reader-select');
  const refreshBtn = document.getElementById('reader-refresh-btn');

  const modals = {
    writeText: 'write-text-modal',
    writeUrl: 'write-url-modal',
  };

  // NFC operations
  async function performNfcOperation(endpoint, payload = {}) {
    UI.toast('Performing NFC operation...');
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      Logger.info('NFC operation successful', data);
      UI.toast(data.message || 'Operation successful');
    } catch (err) {
      Logger.error('NFC operation failed', err);
      UI.toast('Operation failed', 'error');
    }
  }

  // Event handlers
  document.getElementById('read-tag-info-btn').addEventListener('click', () => {
    performNfcOperation('/api/nfc/read-tag-info', { reader: readerSelect.value });
  });

  document.getElementById('read-ndef-btn').addEventListener('click', () => {
    performNfcOperation('/api/nfc/read-ndef', { reader: readerSelect.value });
  });

  document.getElementById('write-text-btn').addEventListener('click', () => {
    UI.showModal(modals.writeText);
  });

  document.getElementById('write-url-btn').addEventListener('click', () => {
    UI.showModal(modals.writeUrl);
  });

  document.getElementById('erase-tag-btn').addEventListener('click', () => {
    performNfcOperation('/api/nfc/erase-tag', { reader: readerSelect.value });
  });

  // Modal interactions (Write Text)
  document.getElementById('confirm-write-text').addEventListener('click', () => {
    const text = document.getElementById('text-input').value;
    const lang = document.getElementById('text-lang').value;
    performNfcOperation('/api/nfc/write-text', { reader: readerSelect.value, text, lang });
    UI.hideModal(modals.writeText);
  });

  document.getElementById('cancel-write-text').addEventListener('click', () => {
    UI.hideModal(modals.writeText);
  });

  // Modal interactions (Write URL)
  document.getElementById('confirm-write-url').addEventListener('click', () => {
    const url = document.getElementById('url-input').value;
    performNfcOperation('/api/nfc/write-url', { reader: readerSelect.value, url });
    UI.hideModal(modals.writeUrl);
  });

  document.getElementById('cancel-write-url').addEventListener('click', () => {
    UI.hideModal(modals.writeUrl);
  });

  // Load NFC readers initially
  async function loadReaders() {
    UI.setLoading('reader-refresh-btn', true);
    try {
      const readers = await (await fetch('/api/nfc/readers')).json();
      readerSelect.innerHTML = readers.length
        ? readers.map(r => `<option>${r}</option>`).join('')
        : `<option>No readers found</option>`;
      Logger.info('NFC readers loaded', { readers });
    } catch (err) {
      Logger.error('Failed to load NFC readers', err);
      UI.toast('Could not load NFC readers', 'error');
    } finally {
      UI.setLoading('reader-refresh-btn', false);
    }
  }

  refreshBtn.addEventListener('click', loadReaders);
  loadReaders();
});

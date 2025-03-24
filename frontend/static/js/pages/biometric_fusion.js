import UI from '/static/js/utils/ui.js';
import Logger from '/static/js/utils/logger.js';

document.addEventListener('DOMContentLoaded', () => {
  const userIdInput = document.getElementById('user-id');
  const faceCheckbox = document.getElementById('face-checkbox');
  const fingerprintCheckbox = document.getElementById('fingerprint-checkbox');
  const irisCheckbox = document.getElementById('iris-checkbox');
  const authenticateBtn = document.getElementById('authenticate-btn');
  const logContainer = document.getElementById('log-container');
  const statusDisplay = document.getElementById('status-display');

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

  // Function to set the status display
  function setStatus(message, type = 'info') {
    statusDisplay.textContent = message;
    statusDisplay.className = `font-medium`; // Reset classes
    if (type === 'error') {
      statusDisplay.classList.add('text-red-400');
    } else if (type === 'success') {
      statusDisplay.classList.add('text-green-400');
    } else {
      statusDisplay.classList.add('text-yellow-400');
    }
  }

  // Function to handle biometric authentication
  async function authenticate() {
    const userId = userIdInput.value.trim();
    if (!userId) {
      UI.toast('Please enter a User ID.', 'warn');
      return;
    }

    const selectedBiometrics = [];
    if (faceCheckbox.checked) selectedBiometrics.push('face');
    if (fingerprintCheckbox.checked) selectedBiometrics.push('fingerprint');
    if (irisCheckbox.checked) selectedBiometrics.push('iris');

    if (selectedBiometrics.length === 0) {
      UI.toast('Please select at least one biometric method.', 'warn');
      return;
    }

    UI.setLoading('authenticate-btn', true);
    setStatus('Authenticating...', 'info');

    try {
      const response = await fetch('/api/biometric/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          biometrics: selectedBiometrics,
        }),
      });
      const data = await response.json();

      if (data.success && data.authenticated) {
        setStatus('Authenticated successfully.', 'success');
        addLogEntry(`User ${userId} authenticated using ${selectedBiometrics.join(', ')}`, 'success');
        UI.toast('Authenticated successfully!', 'success');
      } else {
        setStatus('Authentication failed.', 'error');
        addLogEntry(`Authentication failed for User ${userId} using ${selectedBiometrics.join(', ')}`, 'warn');
        UI.toast('Authentication failed.', 'warn');
      }
    } catch (error) {
      console.error('Biometric authentication error:', error);
      setStatus('Authentication failed. Check console.', 'error');
      addLogEntry(`Authentication failed: ${error.message}`, 'error');
      UI.toast('Authentication failed. Check console.', 'error');
    } finally {
      UI.setLoading('authenticate-btn', false);
    }
  }

  // Event listener
  authenticateBtn.addEventListener('click', authenticate);
});
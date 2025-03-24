import UI from '/static/js/utils/ui.js';
import Logger from '/static/js/utils/logger.js';

document.addEventListener('DOMContentLoaded', () => {
  const captureBtn = document.getElementById('capture-btn');
  const verifyBtn = document.getElementById('verify-btn');
  const enrollBtn = document.getElementById('enroll-btn');
  const fingerprintImage = document.getElementById('fingerprint-image');
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

  // Function to handle fingerprint capture
  async function captureFingerprint() {
    UI.setLoading('capture-btn', true);
    setStatus('Capturing...', 'info');

    try {
      const response = await fetch('/api/fingerprint/capture', { method: 'POST' });
      const data = await response.json();

      if (data.success && data.image) {
        fingerprintImage.src = `data:image/png;base64,${data.image}`;
        setStatus('Fingerprint captured.', 'success');
        addLogEntry('Fingerprint captured successfully.', 'success');
      } else {
        setStatus(`Capture failed: ${data.error}`, 'error');
        addLogEntry(`Capture failed: ${data.error}`, 'error');
        UI.toast(`Capture failed: ${data.error}`, 'error');
      }
    } catch (error) {
      console.error('Fingerprint capture error:', error);
      setStatus('Capture failed. Check console.', 'error');
      addLogEntry(`Capture failed: ${error.message}`, 'error');
      UI.toast('Capture failed. Check console.', 'error');
    } finally {
      UI.setLoading('capture-btn', false);
    }
  }

  // Function to handle fingerprint verification
  async function verifyFingerprint() {
    UI.setLoading('verify-btn', true);
    setStatus('Verifying...', 'info');

    try {
      const response = await fetch('/api/fingerprint/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: fingerprintImage.src.split(',')[1] }), // Send base64 image data
      });
      const data = await response.json();

      if (data.success && data.match) {
        setStatus('Fingerprint verified.', 'success');
        addLogEntry('Fingerprint verified successfully.', 'success');
        UI.toast('Fingerprint verified!', 'success');
      } else {
        setStatus('Fingerprint not matched.', 'error');
        addLogEntry('Fingerprint not matched.', 'warn');
        UI.toast('Fingerprint not matched.', 'warn');
      }
    } catch (error) {
      console.error('Fingerprint verification error:', error);
      setStatus('Verification failed. Check console.', 'error');
      addLogEntry(`Verification failed: ${error.message}`, 'error');
      UI.toast('Verification failed. Check console.', 'error');
    } finally {
      UI.setLoading('verify-btn', false);
    }
  }

  // Function to handle fingerprint enrollment
  async function enrollFingerprint() {
    UI.setLoading('enroll-btn', true);
    setStatus('Enrolling...', 'info');

    try {
      const response = await fetch('/api/fingerprint/enroll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: fingerprintImage.src.split(',')[1] }), // Send base64 image data
      });
      const data = await response.json();

      if (data.success) {
        setStatus('Fingerprint enrolled.', 'success');
        addLogEntry('Fingerprint enrolled successfully.', 'success');
        UI.toast('Fingerprint enrolled!', 'success');
      } else {
        setStatus(`Enrollment failed: ${data.error}`, 'error');
        addLogEntry(`Enrollment failed: ${data.error}`, 'error');
        UI.toast(`Enrollment failed: ${data.error}`, 'error');
      }
    } catch (error) {
      console.error('Fingerprint enrollment error:', error);
      setStatus('Enrollment failed. Check console.', 'error');
      addLogEntry(`Enrollment failed: ${error.message}`, 'error');
      UI.toast('Enrollment failed. Check console.', 'error');
    } finally {
      UI.setLoading('enroll-btn', false);
    }
  }

  // Event listeners
  captureBtn.addEventListener('click', captureFingerprint);
  verifyBtn.addEventListener('click', verifyFingerprint);
  enrollBtn.addEventListener('click', enrollFingerprint);
});
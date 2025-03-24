import UI from '/static/js/utils/ui.js';
import Logger from '/static/js/utils/logger.js';

document.addEventListener('DOMContentLoaded', () => {
  const enrollFaceBtn = document.getElementById('enroll-face-btn');
  const enrollFingerprintBtn = document.getElementById('enroll-fingerprint-btn');
  const enrollIrisBtn = document.getElementById('enroll-iris-btn');
  const verifyFaceBtn = document.getElementById('verify-face-btn');
  const verifyFingerprintBtn = document.getElementById('verify-fingerprint-btn');
  const verifyIrisBtn = document.getElementById('verify-iris-btn');
  const userIdInput = document.getElementById('user-id');
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

  // Function to handle face enrollment
  async function enrollFace() {
    const userId = userIdInput.value.trim();
    if (!userId) {
      UI.toast('Please enter a User ID.', 'warn');
      return;
    }

    UI.setLoading('enroll-face-btn', true);
    setStatus('Enrolling Face...', 'info');

    try {
      const response = await fetch('/api/biometric/enroll/face', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      const data = await response.json();

      if (data.success) {
        setStatus('Face enrolled successfully.', 'success');
        addLogEntry(`Face enrolled for User ID: ${userId}`, 'success');
        UI.toast('Face enrolled successfully!', 'success');
      } else {
        setStatus(`Face enrollment failed: ${data.error}`, 'error');
        addLogEntry(`Face enrollment failed: ${data.error}`, 'error');
        UI.toast(`Face enrollment failed: ${data.error}`, 'error');
      }
    } catch (error) {
      console.error('Face enrollment error:', error);
      setStatus('Face enrollment failed. Check console.', 'error');
      addLogEntry(`Face enrollment failed: ${error.message}`, 'error');
      UI.toast('Face enrollment failed. Check console.', 'error');
    } finally {
      UI.setLoading('enroll-face-btn', false);
    }
  }

  // Function to handle fingerprint enrollment
  async function enrollFingerprint() {
    const userId = userIdInput.value.trim();
    if (!userId) {
      UI.toast('Please enter a User ID.', 'warn');
      return;
    }

    UI.setLoading('enroll-fingerprint-btn', true);
    setStatus('Enrolling Fingerprint...', 'info');

    try {
      const response = await fetch('/api/biometric/enroll/fingerprint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      const data = await response.json();

      if (data.success) {
        setStatus('Fingerprint enrolled successfully.', 'success');
        addLogEntry(`Fingerprint enrolled for User ID: ${userId}`, 'success');
        UI.toast('Fingerprint enrolled successfully!', 'success');
      } else {
        setStatus(`Fingerprint enrollment failed: ${data.error}`, 'error');
        addLogEntry(`Fingerprint enrollment failed: ${data.error}`, 'error');
        UI.toast(`Fingerprint enrollment failed: ${data.error}`, 'error');
      }
    } catch (error) {
      console.error('Fingerprint enrollment error:', error);
      setStatus('Fingerprint enrollment failed. Check console.', 'error');
      addLogEntry(`Fingerprint enrollment failed: ${error.message}`, 'error');
      UI.toast('Fingerprint enrollment failed. Check console.', 'error');
    } finally {
      UI.setLoading('enroll-fingerprint-btn', false);
    }
  }

  // Function to handle iris enrollment
  async function enrollIris() {
    const userId = userIdInput.value.trim();
    if (!userId) {
      UI.toast('Please enter a User ID.', 'warn');
      return;
    }

    UI.setLoading('enroll-iris-btn', true);
    setStatus('Enrolling Iris...', 'info');

    try {
      const response = await fetch('/api/biometric/enroll/iris', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      const data = await response.json();

      if (data.success) {
        setStatus('Iris enrolled successfully.', 'success');
        addLogEntry(`Iris enrolled for User ID: ${userId}`, 'success');
        UI.toast('Iris enrolled successfully!', 'success');
      } else {
        setStatus(`Iris enrollment failed: ${data.error}`, 'error');
        addLogEntry(`Iris enrollment failed: ${data.error}`, 'error');
        UI.toast(`Iris enrollment failed: ${data.error}`, 'error');
      }
    } catch (error) {
      console.error('Iris enrollment error:', error);
      setStatus('Iris enrollment failed. Check console.', 'error');
      addLogEntry(`Iris enrollment failed: ${error.message}`, 'error');
      UI.toast('Iris enrollment failed. Check console.', 'error');
    } finally {
      UI.setLoading('enroll-iris-btn', false);
    }
  }

  // Function to handle face verification
  async function verifyFace() {
    const userId = userIdInput.value.trim();
    if (!userId) {
      UI.toast('Please enter a User ID.', 'warn');
      return;
    }

    UI.setLoading('verify-face-btn', true);
    setStatus('Verifying Face...', 'info');

    try {
      const response = await fetch('/api/biometric/verify/face', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      const data = await response.json();

      if (data.success && data.match) {
        setStatus('Face verified successfully.', 'success');
        addLogEntry(`Face verified for User ID: ${userId}`, 'success');
        UI.toast('Face verified successfully!', 'success');
      } else {
        setStatus('Face verification failed.', 'error');
        addLogEntry(`Face verification failed for User ID: ${userId}`, 'warn');
        UI.toast('Face verification failed.', 'warn');
      }
    } catch (error) {
      console.error('Face verification error:', error);
      setStatus('Face verification failed. Check console.', 'error');
      addLogEntry(`Face verification failed: ${error.message}`, 'error');
      UI.toast('Face verification failed. Check console.', 'error');
    } finally {
      UI.setLoading('verify-face-btn', false);
    }
  }

  // Function to handle fingerprint verification
  async function verifyFingerprint() {
    const userId = userIdInput.value.trim();
    if (!userId) {
      UI.toast('Please enter a User ID.', 'warn');
      return;
    }

    UI.setLoading('verify-fingerprint-btn', true);
    setStatus('Verifying Fingerprint...', 'info');

    try {
      const response = await fetch('/api/biometric/verify/fingerprint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      const data = await response.json();

      if (data.success && data.match) {
        setStatus('Fingerprint verified successfully.', 'success');
        addLogEntry(`Fingerprint verified for User ID: ${userId}`, 'success');
        UI.toast('Fingerprint verified successfully!', 'success');
      } else {
        setStatus('Fingerprint verification failed.', 'error');
        addLogEntry(`Fingerprint verification failed for User ID: ${userId}`, 'warn');
        UI.toast('Fingerprint verification failed.', 'warn');
      }
    } catch (error) {
      console.error('Fingerprint verification error:', error);
      setStatus('Fingerprint verification failed. Check console.', 'error');
      addLogEntry(`Fingerprint verification failed: ${error.message}`, 'error');
      UI.toast('Fingerprint verification failed. Check console.', 'error');
    } finally {
      UI.setLoading('verify-fingerprint-btn', false);
    }
  }

  // Function to handle iris verification
  async function verifyIris() {
    const userId = userIdInput.value.trim();
    if (!userId) {
      UI.toast('Please enter a User ID.', 'warn');
      return;
    }

    UI.setLoading('verify-iris-btn', true);
    setStatus('Verifying Iris...', 'info');

    try {
      const response = await fetch('/api/biometric/verify/iris', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      const data = await response.json();

      if (data.success && data.match) {
        setStatus('Iris verified successfully.', 'success');
        addLogEntry(`Iris verified for User ID: ${userId}`, 'success');
        UI.toast('Iris verified successfully!', 'success');
      } else {
        setStatus('Iris verification failed.', 'error');
        addLogEntry(`Iris verification failed for User ID: ${userId}`, 'warn');
        UI.toast('Iris verification failed.', 'warn');
      }
    } catch (error) {
      console.error('Iris verification error:', error);
      setStatus('Iris verification failed. Check console.', 'error');
      addLogEntry(`Iris verification failed: ${error.message}`, 'error');
      UI.toast('Iris verification failed. Check console.', 'error');
    } finally {
      UI.setLoading('verify-iris-btn', false);
    }
  }

  // Event listeners
  enrollFaceBtn.addEventListener('click', enrollFace);
  enrollFingerprintBtn.addEventListener('click', enrollFingerprint);
  enrollIrisBtn.addEventListener('click', enrollIris);
  verifyFaceBtn.addEventListener('click', verifyFace);
  verifyFingerprintBtn.addEventListener('click', verifyFingerprint);
  verifyIrisBtn.addEventListener('click', verifyIris);
});
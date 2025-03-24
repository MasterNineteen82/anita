// settings.js: Handles interactions for the Settings page
import UI from '/static/js/utils/ui.js';
import Logger from '/static/js/utils/logger.js';

document.addEventListener('DOMContentLoaded', () => {

  const saveBtn = document.querySelector('button:contains("Save All Settings")');
  const cancelBtn = document.querySelector('button:contains("Cancel Changes")');
  const refreshInfoBtn = document.querySelector('button:contains("Refresh Info")');

  // Save settings handler
  async function saveSettings() {
    UI.setLoading(saveBtn.id, true);
    try {
      const settings = gatherSettings();
      const res = await fetch('/api/settings/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });

      const data = await res.json();
      if (data.success) {
        UI.toast('Settings saved successfully');
        Logger.info('Settings saved', settings);
      } else {
        UI.toast('Failed to save settings', 'error');
        Logger.warn('Settings save failed', data);
      }
    } catch (err) {
      Logger.error('Error saving settings', err);
      UI.toast('Could not save settings', 'error');
    } finally {
      UI.setLoading(saveBtn.id, false);
    }
  }

  // Gather settings data from the page
  function gatherSettings() {
    return {
      darkTheme: document.getElementById('dark-theme').checked,
      autoRefresh: document.getElementById('auto-refresh').checked,
      refreshInterval: document.querySelector('input[type="number"]').value,
      enableLogging: document.getElementById('enable-logging').checked,
      simulationMode: document.getElementById('simulation-mode').checked,
      apiBaseUrl: document.querySelector('input[placeholder="https://api.example.com"]').value,
      websocketUrl: document.querySelector('input[placeholder="wss://socket.example.com"]').value,
      mifareKey: document.querySelector('input[value="FFFFFFFFFFFF"]').value,
      mifareKeyType: document.querySelector('select').value,
      pluginDirectory: document.querySelector('input[placeholder="/plugins"]').value,
      examplePluginEnabled: document.getElementById('plugin-example').checked,
    };
  }

  // Cancel changes handler
  function cancelChanges() {
    window.location.reload();
  }

  // Refresh system info handler
  async function refreshSystemInfo() {
    UI.setLoading(refreshInfoBtn.id, true);
    try {
      const res = await fetch('/api/settings/system-info');
      const data = await res.json();

      document.getElementById('uptime').textContent = data.uptime || '--';
      UI.toast('System info refreshed');
      Logger.info('System info refreshed', data);
    } catch (err) {
      Logger.error('Failed to refresh system info', err);
      UI.toast('Could not refresh info', 'error');
    } finally {
      UI.setLoading(refreshInfoBtn.id, false);
    }
  }

  // Event listeners
  saveBtn.addEventListener('click', saveSettings);
  cancelBtn.addEventListener('click', cancelChanges);
  refreshInfoBtn.addEventListener('click', refreshSystemInfo);

  // Initial load of system info
  refreshSystemInfo();
});

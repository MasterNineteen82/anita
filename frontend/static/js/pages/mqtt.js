document.addEventListener('DOMContentLoaded', () => {
  const brokerAddressInput = document.getElementById('broker-address');
  const brokerPortInput = document.getElementById('broker-port');
  const clientIdInput = document.getElementById('client-id');
  const usernameInput = document.getElementById('username');
  const passwordInput = document.getElementById('password');
  const useSslCheckbox = document.getElementById('use-ssl');
  const connectBtn = document.getElementById('connect-btn');
  const disconnectBtn = document.getElementById('disconnect-btn');
  const connectionStatusSpan = document.getElementById('connection-status');

  const pubTopicInput = document.getElementById('pub-topic');
  const pubMessageTextarea = document.getElementById('pub-message');
  const pubQosSelect = document.getElementById('pub-qos');
  const pubRetainCheckbox = document.getElementById('pub-retain');
  const publishBtn = document.getElementById('publish-btn');
  const clearPubBtn = document.getElementById('clear-pub-btn');

  const subTopicInput = document.getElementById('sub-topic');
  const subQosSelect = document.getElementById('sub-qos');
  const subscribeBtn = document.getElementById('subscribe-btn');
  const unsubscribeBtn = document.getElementById('unsubscribe-btn');
  const subscriptionsListDiv = document.getElementById('subscriptions-list');

  const filterLogInput = document.getElementById('filter-log');
  const filterTypeSelect = document.getElementById('filter-type');
  const messageLogContainerDiv = document.getElementById('message-log-container');
  const clearLogBtn = document.getElementById('clear-log-btn');
  const exportLogBtn = document.getElementById('export-log-btn');

  const refreshDashBtn = document.getElementById('refresh-dash-btn');
  const saveDashBtn = document.getElementById('save-dash-btn');

  let mqttClient = null;

  const updateConnectionStatus = (status) => {
    connectionStatusSpan.textContent = status;
    if (status === 'Connected') {
      connectionStatusSpan.classList.remove('text-yellow-400');
      connectionStatusSpan.classList.add('text-green-400');
    } else {
      connectionStatusSpan.classList.remove('text-green-400');
      connectionStatusSpan.classList.add('text-yellow-400');
    }
  };

  connectBtn.addEventListener('click', () => {
    const broker = brokerAddressInput.value;
    const port = parseInt(brokerPortInput.value);
    const clientId = clientIdInput.value;
    const username = usernameInput.value;
    const password = passwordInput.value;
    const useSSL = useSslCheckbox.checked;

    // Placeholder: Implement MQTT connection logic here
    updateConnectionStatus('Connecting...');
    setTimeout(() => {
      updateConnectionStatus('Connected');
    }, 2000);
  });

  disconnectBtn.addEventListener('click', () => {
    // Placeholder: Implement MQTT disconnection logic here
    updateConnectionStatus('Disconnecting...');
    setTimeout(() => {
      updateConnectionStatus('Disconnected');
    }, 2000);
  });

  publishBtn.addEventListener('click', () => {
    const topic = pubTopicInput.value;
    const message = pubMessageTextarea.value;
    const qos = parseInt(pubQosSelect.value);
    const retain = pubRetainCheckbox.checked;

    // Placeholder: Implement MQTT publish logic here
    console.log(`Publishing to ${topic} with message: ${message}, QoS: ${qos}, Retain: ${retain}`);
  });

  clearPubBtn.addEventListener('click', () => {
    pubMessageTextarea.value = '';
  });

  subscribeBtn.addEventListener('click', () => {
    const topic = subTopicInput.value;
    const qos = parseInt(subQosSelect.value);

    // Placeholder: Implement MQTT subscribe logic here
    console.log(`Subscribing to ${topic} with QoS: ${qos}`);
  });

  unsubscribeBtn.addEventListener('click', () => {
    const topic = subTopicInput.value;

    // Placeholder: Implement MQTT unsubscribe logic here
    console.log(`Unsubscribing from ${topic}`);
  });

  clearLogBtn.addEventListener('click', () => {
    messageLogContainerDiv.innerHTML = '';
  });

  exportLogBtn.addEventListener('click', () => {
    // Placeholder: Implement log export logic here
    console.log('Exporting message log');
  });

  refreshDashBtn.addEventListener('click', () => {
    // Placeholder: Implement dashboard refresh logic here
    console.log('Refreshing dashboard');
  });

  saveDashBtn.addEventListener('click', () => {
    // Placeholder: Implement dashboard layout save logic here
    console.log('Saving dashboard layout');
  });
});
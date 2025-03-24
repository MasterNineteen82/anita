import UI from '/static/js/utils/ui.js';
import Logger from '/static/js/utils/logger.js';

// WebSocket connection
let socket;
let isConnected = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

// Store for active UWB devices
let activeDevices = [];

// Map visualization context
let mapContext = {
    canvas: null,
    ctx: null,
    width: 0,
    height: 0,
    scale: 10, // pixels per meter
    offsetX: 0,
    offsetY: 0,
    deviceColors: {},
    devicePositions: {}
};

document.addEventListener('DOMContentLoaded', () => {
  const deviceIdInput = document.getElementById('device-id');
  const locXInput = document.getElementById('loc-x');
  const locYInput = document.getElementById('loc-y');
  const locZInput = document.getElementById('loc-z');
  const registerDeviceBtn = document.getElementById('register-device-btn');
  const activeDevicesContainer = document.getElementById('active-devices');
  const refreshDevicesBtn = document.getElementById('refresh-devices-btn');
  const selectDeviceSelect = document.getElementById('select-device');
  const coordXDiv = document.getElementById('coord-x');
  const coordYDiv = document.getElementById('coord-y');
  const coordZDiv = document.getElementById('coord-z');
  const locateDeviceBtn = document.getElementById('locate-device-btn');
  const mapContainerDiv = document.getElementById('map-container');
  const autoUpdateMapCheckbox = document.getElementById('auto-update-map');
  const centerMapBtn = document.getElementById('center-map-btn');
  const historyDeviceSelect = document.getElementById('history-device');
  const clearHistoryBtn = document.getElementById('clear-history-btn');
  const exportHistoryBtn = document.getElementById('export-history-btn');
  const logContainerDiv = document.getElementById('log-container');

  // Initialize UI components
  initializeUI();
  
  // Connect to WebSocket
  connectWebSocket();
  
  // Set up event listeners
  setupEventListeners();

  // Initial device list load
  sendMessage('get_active_devices', {});
});

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    socket = new WebSocket(`${protocol}//${window.location.host}/ws/uwb`);
    
    socket.onopen = () => {
        console.log('WebSocket connection established');
        isConnected = true;
        reconnectAttempts = 0;
        
        // Request initial data
        sendMessage('get_active_devices', {});
        
        // Show connected status
        updateConnectionStatus('connected');
    };
    
    socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };
    
    socket.onclose = () => {
        isConnected = false;
        console.log('WebSocket connection closed');
        
        // Show disconnected status
        updateConnectionStatus('disconnected');
        
        // Attempt to reconnect
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            setTimeout(connectWebSocket, 2000 * reconnectAttempts);
        } else {
            showError('Connection lost. Please refresh the page to reconnect.');
        }
    };
    
    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

function sendMessage(type, payload) {
    if (!isConnected) {
        showError('Not connected to server');
        return;
    }
    
    const message = {
        type: type,
        payload: payload
    };
    
    socket.send(JSON.stringify(message));
}

function handleWebSocketMessage(message) {
    const { type, payload } = message;
    
    switch (type) {
        case 'uwb.device_list':
            handleDeviceList(payload);
            break;
            
        case 'uwb.device_registered':
            handleDeviceRegistered(payload);
            break;
            
        case 'uwb.location':
            handleDeviceLocation(payload);
            break;
            
        case 'uwb.position_update':
            handlePositionUpdate(payload);
            break;
            
        case 'uwb.tracking_started':
            handleTrackingStarted(payload);
            break;
            
        case 'uwb.tracking_stopped':
            handleTrackingStopped();
            break;
            
        case 'uwb.location_history':
            handleLocationHistory(payload);
            break;
            
        case 'device.status':
            handleDeviceStatus(payload);
            break;
            
        case 'error':
            handleError(payload);
            break;
            
        default:
            console.warn('Unknown message type:', type);
    }
}

// Message Handlers

function handleDeviceList(payload) {
    const { devices } = payload;
    activeDevices = devices;
    
    updateDeviceList(devices);
    updateDeviceSelectors(devices);
    
    // Initialize device colors for map
    devices.forEach(device => {
        if (!mapContext.deviceColors[device.id]) {
            mapContext.deviceColors[device.id] = getRandomColor();
        }
        
        // Initialize position if available
        if (device.location) {
            mapContext.devicePositions[device.id] = device.location;
        }
    });
    
    // Update map with initial positions
    drawMap();
}

function handleDeviceRegistered(payload) {
    const { device_id } = payload;
    showSuccess(`Device ${device_id} registered successfully`);
    
    // Refresh device list
    sendMessage('get_active_devices', {});
}

function handleDeviceLocation(payload) {
    const { device_id, location } = payload;
    
    // Update position on map
    mapContext.devicePositions[device_id] = location;
    drawMap();
    
    // Update location display
    updateLocationDisplay(device_id, location);
}

function handlePositionUpdate(payload) {
    const { positions } = payload;
    
    // Update positions in our local store
    Object.keys(positions).forEach(deviceId => {
        mapContext.devicePositions[deviceId] = positions[deviceId];
    });
    
    // Redraw map
    drawMap();
}

function handleTrackingStarted(payload) {
    const { device_ids, update_frequency } = payload;
    
    // Update UI to show tracking state
    updateTrackingStatus(`Tracking ${device_ids.length} devices at ${update_frequency.toFixed(1)}Hz`);
    
    // Enable auto-update checkbox if it exists
    const autoUpdateCheckbox = document.getElementById('auto-update-map');
    if (autoUpdateCheckbox) {
        autoUpdateCheckbox.checked = true;
    }
}

function handleTrackingStopped() {
    // Update UI to show tracking stopped
    updateTrackingStatus('Tracking stopped');
    
    // Disable auto-update checkbox if it exists
    const autoUpdateCheckbox = document.getElementById('auto-update-map');
    if (autoUpdateCheckbox) {
        autoUpdateCheckbox.checked = false;
    }
}

function handleLocationHistory(payload) {
    const { device_id, history } = payload;
    
    // Update history table
    updateHistoryTable(device_id, history);
    
    // Draw history path on map if requested
    const showHistoryOnMap = document.getElementById('show-history-on-map')?.checked;
    if (showHistoryOnMap) {
        drawHistoryPath(device_id, history);
    }
}

function handleDeviceStatus(payload) {
    const { device_id, status } = payload;
    
    // Update device status in the UI
    updateDeviceStatus(device_id, status);
    
    // Show notification
    if (status === 'connected') {
        showNotification(`Device ${device_id} is now online`);
    } else if (status === 'disconnected') {
        showNotification(`Device ${device_id} is now offline`);
    }
    
    // Refresh device list if needed
    sendMessage('get_active_devices', {});
}

function handleError(payload) {
    const { message } = payload;
    showError(message);
}

// UI Functions

function initializeUI() {
    // Initialize map canvas
    mapContext.canvas = document.getElementById('location-map');
    if (mapContext.canvas) {
        mapContext.ctx = mapContext.canvas.getContext('2d');
        mapContext.width = mapContext.canvas.width;
        mapContext.height = mapContext.canvas.height;
        
        // Set initial offset to center of canvas
        mapContext.offsetX = mapContext.width / 2;
        mapContext.offsetY = mapContext.height / 2;
        
        // Draw empty map
        drawMap();
    }
    
    // Initialize connection status indicator
    updateConnectionStatus('connecting');
}

function setupEventListeners() {
    // Register device button
    const registerDeviceBtn = document.getElementById('register-device-btn');
    if (registerDeviceBtn) {
        registerDeviceBtn.addEventListener('click', () => {
            const deviceId = document.getElementById('device-id')?.value;
            const locX = parseFloat(document.getElementById('loc-x')?.value || 0);
            const locY = parseFloat(document.getElementById('loc-y')?.value || 0);
            const locZ = parseFloat(document.getElementById('loc-z')?.value || 0);
            
            if (!deviceId) {
                showError('Please enter a device ID');
                return;
            }
            
            sendMessage('register_device', {
                device_id: deviceId,
                initial_location: { x: locX, y: locY, z: locZ }
            });
        });
    }
    
    // Refresh devices button
    const refreshDevicesBtn = document.getElementById('refresh-devices-btn');
    if (refreshDevicesBtn) {
        refreshDevicesBtn.addEventListener('click', () => {
            sendMessage('get_active_devices', {});
        });
    }
    
    // Auto-update map checkbox
    const autoUpdateMapCheckbox = document.getElementById('auto-update-map');
    if (autoUpdateMapCheckbox) {
        autoUpdateMapCheckbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                startPositionTracking();
            } else {
                stopPositionTracking();
            }
        });
    }
}

function startPositionTracking() {
    const selectedDevices = getSelectedDeviceIds();
    if (selectedDevices.length === 0) {
        showError('Please select at least one device to track');
        return;
    }
    
    sendMessage('start_position_tracking', {
        device_ids: selectedDevices,
        update_frequency: 0.5  // Update twice per second
    });
}

function stopPositionTracking() {
    sendMessage('stop_position_tracking', {});
}

function getSelectedDeviceIds() {
    // Get all selected devices from the UI
    const selectedDevices = [];
    const deviceCheckboxes = document.querySelectorAll('.device-checkbox:checked');
    deviceCheckboxes.forEach(checkbox => {
        selectedDevices.push(checkbox.value);
    });
    
    // If nothing explicitly selected, use the device from dropdown
    if (selectedDevices.length === 0) {
        const selectedDevice = document.getElementById('select-device')?.value;
        if (selectedDevice) {
            selectedDevices.push(selectedDevice);
        }
    }
    
    return selectedDevices;
}

function updateDeviceList(devices) {
    const container = document.querySelector('#active-devices .space-y-1');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (devices.length === 0) {
        container.innerHTML = '<div class="text-gray-400 text-center py-3">No active devices</div>';
        return;
    }
    
    devices.forEach(device => {
        const deviceEl = document.createElement('div');
        deviceEl.className = 'py-2 px-3 bg-gray-700 bg-opacity-50 rounded flex justify-between items-center';
        deviceEl.innerHTML = `
            <div>
                <div class="font-medium">${device.id}</div>
                <div class="text-xs text-gray-400">Last seen: ${device.last_seen || 'Just now'}</div>
            </div>
            <div class="flex space-x-2">
                <button class="text-blue-400 hover:text-blue-300" data-device-id="${device.id}"><i class="fas fa-edit"></i></button>
                <button class="text-red-400 hover:text-red-300" data-device-id="${device.id}"><i class="fas fa-trash"></i></button>
            </div>
        `;
        container.appendChild(deviceEl);
    });
}

function updateDeviceSelectors(devices) {
    const selectors = ['select-device', 'history-device'];
    
    selectors.forEach(selectorId => {
        const select = document.getElementById(selectorId);
        if (!select) return;
        
        // Save current selection
        const currentValue = select.value;
        
        // Clear and rebuild options
        select.innerHTML = '';
        
        // Add placeholder if needed
        if (selectorId === 'select-device') {
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = 'Select a device...';
            select.appendChild(placeholder);
        }
        
        // Add device options
        devices.forEach(device => {
            const option = document.createElement('option');
            option.value = device.id;
            option.textContent = device.id;
            select.appendChild(option);
        });
        
        // Restore selection if possible
        if (currentValue) {
            select.value = currentValue;
        }
    });
}

function updateConnectionStatus(status) {
    const statusEl = document.getElementById('connection-status');
    if (!statusEl) return;
    
    statusEl.className = 'flex items-center text-sm';
    
    switch(status) {
        case 'connected':
            statusEl.innerHTML = '<span class="w-2 h-2 bg-green-500 rounded-full mr-2"></span> Connected';
            statusEl.classList.add('text-green-400');
            break;
        case 'disconnected':
            statusEl.innerHTML = '<span class="w-2 h-2 bg-red-500 rounded-full mr-2"></span> Disconnected';
            statusEl.classList.add('text-red-400');
            break;
        case 'connecting':
            statusEl.innerHTML = '<span class="w-2 h-2 bg-yellow-500 rounded-full mr-2"></span> Connecting...';
            statusEl.classList.add('text-yellow-400');
            break;
        default:
            console.warn('Unknown connection status:', status);
            statusEl.innerHTML = '<span class="w-2 h-2 bg-gray-500 rounded-full mr-2"></span> Unknown';
            statusEl.classList.add('text-gray-400');
            break;
    }
}

function showError(message) {
    console.error(message);
    UI.toast(message, 'error');
    
    // Also log to console
    const logContainer = document.getElementById('log-container');
    if (logContainer) {
        const logEntry = document.createElement('div');
        logEntry.className = 'text-xs font-mono border-l-2 pl-2 py-1 mb-1 border-red-500 text-red-400';
        logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }
}

function showSuccess(message) {
    UI.toast(message, 'success');
}

function showNotification(message) {
    UI.toast(message);
}

function updateLocationDisplay(deviceId, location) {
    // Update coordinate display in the UI
    const coordXDiv = document.getElementById('coord-x');
    const coordYDiv = document.getElementById('coord-y');
    const coordZDiv = document.getElementById('coord-z');
    
    if (coordXDiv && coordYDiv && coordZDiv) {
        coordXDiv.textContent = location.x.toFixed(2);
        coordYDiv.textContent = location.y.toFixed(2);
        coordZDiv.textContent = location.z.toFixed(2);
    }
    
    // Log the update
    addLogEntry(`Location of ${deviceId}: [${location.x}, ${location.y}, ${location.z}]`, 'info');
}

function updateHistoryTable(deviceId, history) {
    const historyContainer = document.getElementById('location-history-container');
    if (!historyContainer) return;
    
    historyContainer.innerHTML = '';
    
    if (history.length === 0) {
        historyContainer.innerHTML = '<div class="text-gray-400 text-center py-3">No history available</div>';
        return;
    }
    
    // Create table
    const table = document.createElement('table');
    table.className = 'min-w-full divide-y divide-gray-600';
    
    // Add header
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th class="px-2 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Time</th>
            <th class="px-2 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">X</th>
            <th class="px-2 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Y</th>
            <th class="px-2 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Z</th>
        </tr>
    `;
    table.appendChild(thead);
    
    // Add body
    const tbody = document.createElement('tbody');
    tbody.className = 'divide-y divide-gray-600';
    
    history.forEach((entry, index) => {
        const row = document.createElement('tr');
        row.className = index % 2 === 0 ? 'bg-gray-800' : 'bg-gray-700';
        
        const time = new Date(entry.timestamp).toLocaleTimeString();
        
        row.innerHTML = `
            <td class="px-2 py-2 whitespace-nowrap text-sm text-gray-300">${time}</td>
            <td class="px-2 py-2 whitespace-nowrap text-sm text-gray-300">${entry.location.x.toFixed(2)}</td>
            <td class="px-2 py-2 whitespace-nowrap text-sm text-gray-300">${entry.location.y.toFixed(2)}</td>
            <td class="px-2 py-2 whitespace-nowrap text-sm text-gray-300">${entry.location.z.toFixed(2)}</td>
        `;
        
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    historyContainer.appendChild(table);
}

function updateDeviceStatus(deviceId, status) {
    // Find the device element in the list
    const deviceEls = document.querySelectorAll('#active-devices .space-y-1 > div');
    
    for (const el of deviceEls) {
        const nameEl = el.querySelector('.font-medium');
        if (nameEl && nameEl.textContent === deviceId) {
            // Update status indicator
            const statusIndicator = document.createElement('span');
            statusIndicator.className = 'ml-2 w-2 h-2 rounded-full';
            
            if (status === 'connected') {
                statusIndicator.classList.add('bg-green-500');
            } else if (status === 'disconnected') {
                statusIndicator.classList.add('bg-red-500');
            } else {
                statusIndicator.classList.add('bg-yellow-500');
            }
            
            // Add or replace status indicator
            const existingIndicator = nameEl.querySelector('.rounded-full');
            if (existingIndicator) {
                nameEl.replaceChild(statusIndicator, existingIndicator);
            } else {
                nameEl.appendChild(statusIndicator);
            }
            
            break;
        }
    }
}

function drawMap() {
    if (!mapContext.ctx || !mapContext.canvas) return;
    
    const { ctx, width, height, scale, offsetX, offsetY, devicePositions, deviceColors } = mapContext;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Draw grid
    ctx.strokeStyle = 'rgba(107, 114, 128, 0.2)';
    ctx.lineWidth = 1;
    
    // Vertical grid lines
    for (let x = offsetX % 50; x < width; x += 50) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }
    
    // Horizontal grid lines
    for (let y = offsetY % 50; y < height; y += 50) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }
    
    // Draw origin
    ctx.strokeStyle = 'rgba(107, 114, 128, 0.5)';
    ctx.lineWidth = 2;
    
    // X-axis
    ctx.beginPath();
    ctx.moveTo(0, offsetY);
    ctx.lineTo(width, offsetY);
    ctx.stroke();
    
    // Y-axis
    ctx.beginPath();
    ctx.moveTo(offsetX, 0);
    ctx.lineTo(offsetX, height);
    ctx.stroke();
    
    // Draw devices
    Object.keys(devicePositions).forEach(deviceId => {
        const pos = devicePositions[deviceId];
        const color = deviceColors[deviceId] || '#FFFFFF';
        
        // Convert coordinates
        const x = offsetX + pos.x * scale;
        const y = offsetY - pos.y * scale; // Invert Y for screen coordinates
        
        // Draw device point
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, Math.PI * 2);
        ctx.fill();
        
        // Draw device label
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '12px sans-serif';
        ctx.fillText(deviceId, x + 10, y + 5);
    });
}

function drawHistoryPath(deviceId, history) {
    if (!mapContext.ctx || !mapContext.canvas || history.length < 2) return;
    
    const { ctx, scale, offsetX, offsetY, deviceColors } = mapContext;
    const color = deviceColors[deviceId] || '#FFFFFF';
    
    // Draw path
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 3]); // Dashed line
    
    ctx.beginPath();
    
    // Start from the oldest position
    const firstPos = history[0].location;
    const startX = offsetX + firstPos.x * scale;
    const startY = offsetY - firstPos.y * scale;
    ctx.moveTo(startX, startY);
    
    // Draw line to each subsequent position
    for (let i = 1; i < history.length; i++) {
        const pos = history[i].location;
        const x = offsetX + pos.x * scale;
        const y = offsetY - pos.y * scale;
        ctx.lineTo(x, y);
    }
    
    ctx.stroke();
    ctx.setLineDash([]); // Reset to solid line
}

function getRandomColor() {
    // Generate a random color for device representation
    const hue = Math.floor(Math.random() * 360);
    return `hsl(${hue}, 70%, 60%)`;
}

function clearRegistrationForm() {
    const fields = ['device-id', 'loc-x', 'loc-y', 'loc-z'];
    fields.forEach(id => {
        const element = document.getElementById(id);
        if (element) element.value = '';
    });
}

function updateTrackingStatus(message) {
    const trackingStatus = document.getElementById('tracking-status');
    if (trackingStatus) {
        trackingStatus.textContent = message;
    } else {
        // Log if element doesn't exist
        console.warn('Tracking status element not found in DOM');
    }
}

function addLogEntry(message, type = 'info') {
    const logContainerDiv = document.getElementById('log-container');
    if (!logContainerDiv) return;
    
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
    logContainerDiv.appendChild(logEntry);
    logContainerDiv.scrollTop = logContainerDiv.scrollHeight;
}
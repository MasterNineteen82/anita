// frontend/static/js/pages/ble/ble-device-info.js
export async function getDeviceInformation(state, deviceId) {
    if (!state.connectedDevice) {
        return null;
    }
    
    // Device Information Service
    const deviceInfoServiceUuid = '0000180a-0000-1000-8000-00805f9b34fb';
    const characteristicUuids = {
        manufacturerName: '00002a29-0000-1000-8000-00805f9b34fb',
        modelNumber: '00002a24-0000-1000-8000-00805f9b34fb',
        serialNumber: '00002a25-0000-1000-8000-00805f9b34fb',
        hardwareRevision: '00002a27-0000-1000-8000-00805f9b34fb',
        firmwareRevision: '00002a26-0000-1000-8000-00805f9b34fb',
        softwareRevision: '00002a28-0000-1000-8000-00805f9b34fb'
    };
    
    const deviceInfo = {};
    
    // Try to read each characteristic
    for (const [key, uuid] of Object.entries(characteristicUuids)) {
        try {
            const response = await fetch(`/api/ble/characteristics/${uuid}/read?service=${deviceInfoServiceUuid}`);
            
            if (response.ok) {
                const data = await response.json();
                if (data && data.value) {
                    // Convert hex to ASCII for text fields
                    const hexValue = data.value.replace(/\s/g, '');
                    const textValue = hexToAscii(hexValue);
                    deviceInfo[key] = textValue;
                }
            }
        } catch (error) {
            // Just continue if a characteristic isn't available
            console.log(`Could not read ${key}: ${error.message}`);
        }
    }
    
    // Store device info
    if (Object.keys(deviceInfo).length > 0) {
        // Save to state
        state.deviceInfo = deviceInfo;
        
        // Update UI if elements exist
        displayDeviceInfo(state, deviceInfo);
        
        // Save to device history
        const deviceHistory = JSON.parse(localStorage.getItem('bleDeviceHistory') || '{}');
        deviceHistory[deviceId] = {
            ...deviceHistory[deviceId],
            info: deviceInfo,
            lastSeen: new Date().toISOString()
        };
        localStorage.setItem('bleDeviceHistory', JSON.stringify(deviceHistory));
    }
    
    return deviceInfo;
}

// Helper to convert hex to ASCII
function hexToAscii(hex) {
    let ascii = '';
    for (let i = 0; i < hex.length; i += 2) {
        const charCode = parseInt(hex.substr(i, 2), 16);
        if (charCode >= 32 && charCode <= 126) { // Printable ASCII only
            ascii += String.fromCharCode(charCode);
        }
    }
    return ascii;
}

// Display device info in UI
function displayDeviceInfo(state, deviceInfo) {
    const container = state.domElements.deviceInfoContainer;
    if (!container) return;
    
    container.innerHTML = '';
    
    // Create a table for device info
    const table = document.createElement('table');
    table.className = 'w-full text-sm';
    
    for (const [key, value] of Object.entries(deviceInfo)) {
        if (!value) continue;
        
        const row = table.insertRow();
        const keyCell = row.insertCell(0);
        const valueCell = row.insertCell(1);
        
        keyCell.className = 'text-gray-400 pr-2';
        valueCell.className = 'text-white';
        
        // Format key from camelCase to Title Case
        const formattedKey = key.replace(/([A-Z])/g, ' $1')
            .replace(/^./, str => str.toUpperCase());
        
        keyCell.textContent = formattedKey;
        valueCell.textContent = value;
    }
    
    container.appendChild(table);
}
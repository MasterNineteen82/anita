class BleDirectTest {
    constructor() {
        this.results = document.getElementById('ble-test-results');
        if (!this.results) {
            this.results = document.createElement('div');
            this.results.id = 'ble-test-results';
            this.results.style.cssText = 'position:fixed; top:20px; right:20px; width:400px; max-height:80vh; overflow:auto; background:#fff; border:1px solid #ccc; padding:15px; z-index:9999; border-radius:5px; box-shadow:0 0 10px rgba(0,0,0,0.2)';
            document.body.appendChild(this.results);
        }
        this.log('BLE Direct Test initialized');
    }
    
    log(message, type = 'info') {
        const entry = document.createElement('div');
        entry.className = `log-entry log-${type}`;
        entry.innerHTML = `<span class="time">${new Date().toLocaleTimeString()}</span> <span class="message">${message}</span>`;
        entry.style.cssText = `margin-bottom:5px; padding:5px; border-radius:3px; background:${type === 'error' ? '#ffebee' : type === 'success' ? '#e8f5e9' : '#e3f2fd'}`;
        this.results.appendChild(entry);
        this.results.scrollTop = this.results.scrollHeight;
        console.log(`[BLE Test] ${message}`);
    }
    
    async testRealOnly() {
        try {
            this.log('Starting REAL-ONLY scan test...');
            const response = await fetch('/api/ble/scan/real_only', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ scan_time: 15.0 })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}: ${await response.text()}`);
            }
            
            const data = await response.json();
            this.log(`Scan complete: Found ${data.devices.length} devices`, 'success');
            
            data.devices.forEach((device, i) => {
                this.log(`${i+1}. ${device.name} (${device.address}) - RSSI: ${device.rssi}dBm`, 'success');
            });
            
            if (data.devices.length === 0) {
                this.log('No devices found! Ensure Bluetooth is on and devices are nearby.', 'error');
            }
            
            return data;
        } catch (error) {
            this.log(`Error: ${error.message}`, 'error');
            return null;
        }
    }
    
    async testDirectBackend() {
        try {
            this.log('Testing direct backend scan...');
            const response = await fetch('/api/ble/scan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    scanTime: 15,
                    mock: false,
                    real_scan: true,
                    direct_test: true
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}: ${await response.text()}`);
            }
            
            const data = await response.json();
            const mockCount = data.devices.filter(d => d.isMock || d.name?.includes('Mock')).length;
            const realCount = data.devices.length - mockCount;
            
            this.log(`Scan complete: ${realCount} real devices, ${mockCount} mock devices`, 
                     realCount > 0 ? 'success' : 'info');
            
            data.devices.forEach((device, i) => {
                const isMock = device.isMock || device.name?.includes('Mock');
                this.log(`${i+1}. ${device.name} (${device.address}) - ${isMock ? 'MOCK' : 'REAL'}`, 
                         isMock ? 'info' : 'success');
            });
            
            return data;
        } catch (error) {
            this.log(`Error: ${error.message}`, 'error');
            return null;
        }
    }
    
    runAllTests() {
        this.log('Running all BLE tests sequentially');
        this.testRealOnly().then(() => {
            setTimeout(() => {
                this.testDirectBackend();
            }, 1000);
        });
    }
}

// Create global instance
window.bleTest = new BleDirectTest();
console.log('BLE Test utility loaded. Use window.bleTest.runAllTests() to run all tests');
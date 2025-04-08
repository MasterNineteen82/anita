import { BleLogger } from './ble-logger.js';

export class BleStateTracker {
    static previousState = null;
    
    /**
     * Track state changes
     * @param {Object} appState - Current application state
     */
    static trackState(appState) {
        // First call, just store the state
        if (!this.previousState) {
            this.previousState = this.cloneState(appState);
            return;
        }
        
        // Check for key state changes
        this.detectChanges(this.previousState, appState);
        
        // Update previous state
        this.previousState = this.cloneState(appState);
    }
    
    /**
     * Clone the state to avoid reference issues
     */
    static cloneState(state) {
        // Only clone what we need to track
        return {
            isScanning: state.isScanning,
            connectedDevice: state.connectedDevice ? {
                id: state.connectedDevice.id,
                name: state.connectedDevice.name,
                address: state.connectedDevice.address
            } : null,
            selectedService: state.selectedService,
            selectedCharacteristic: state.selectedCharacteristic,
            adapterInfo: state.adapter ? { 
                powered: state.adapter.powered,
                available: state.adapter.available
            } : null,
            subscribedCharacteristics: Array.from(state.subscribedCharacteristics || [])
        };
    }
    
    /**
     * Detect changes between states and log them
     */
    static detectChanges(oldState, newState) {
        // Check connection state
        if (!oldState.connectedDevice && newState.connectedDevice) {
            BleLogger.info('State', 'connection', 'Device connected', {
                device: newState.connectedDevice
            });
        } else if (oldState.connectedDevice && !newState.connectedDevice) {
            BleLogger.info('State', 'connection', 'Device disconnected', {
                previousDevice: oldState.connectedDevice
            });
        }
        
        // Check scanning state
        if (!oldState.isScanning && newState.isScanning) {
            BleLogger.info('State', 'scanning', 'Scanning started');
        } else if (oldState.isScanning && !newState.isScanning) {
            BleLogger.info('State', 'scanning', 'Scanning stopped');
        }
        
        // Check adapter changes
        if (oldState.adapterInfo?.powered !== newState.adapterInfo?.powered) {
            BleLogger.info('State', 'adapter', `Adapter power state changed to: ${newState.adapterInfo?.powered ? 'ON' : 'OFF'}`);
        }
        
        if (oldState.adapterInfo?.available !== newState.adapterInfo?.available) {
            BleLogger.info('State', 'adapter', `Adapter availability changed to: ${newState.adapterInfo?.available ? 'AVAILABLE' : 'UNAVAILABLE'}`);
        }
        
        // Check subscriptions
        const oldSubs = new Set(oldState.subscribedCharacteristics);
        const newSubs = new Set(newState.subscribedCharacteristics);
        
        // Check for new subscriptions
        for (const uuid of newSubs) {
            if (!oldSubs.has(uuid)) {
                BleLogger.info('State', 'subscription', `Subscribed to characteristic: ${uuid}`);
            }
        }
        
        // Check for removed subscriptions
        for (const uuid of oldSubs) {
            if (!newSubs.has(uuid)) {
                BleLogger.info('State', 'subscription', `Unsubscribed from characteristic: ${uuid}`);
            }
        }
    }
}
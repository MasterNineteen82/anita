/**
 * BLE bonding and device management module
 */

import { logMessage } from '../../utils/logger.js';

/**
 * List all bonded devices
 * @returns {Promise<Array>} List of bonded devices
 */
export async function listBondedDevices() {
    try {
        const response = await fetch('/api/ble/devices/bonded');
        if (!response.ok) {
            throw new Error(`Failed to get bonded devices: ${response.status} ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        logMessage(`Error listing bonded devices: ${error.message}`, 'error');
        return [];
    }
}

/**
 * Bond with a device
 * @param {string} address - Device address
 * @returns {Promise<boolean>} Success status
 */
export async function bondDevice(address) {
    try {
        const response = await fetch(`/api/ble/devices/${address}/bond`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`Bonding failed: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        logMessage(`Device bonded: ${result.message}`, 'info');
        return true;
    } catch (error) {
        logMessage(`Bonding error: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Remove bond with a device
 * @param {string} address - Device address
 * @returns {Promise<boolean>} Success status
 */
export async function unbondDevice(address) {
    try {
        const response = await fetch(`/api/ble/devices/${address}/bond`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`Unbonding failed: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        logMessage(`Device unbonded: ${result.message}`, 'info');
        return true;
    } catch (error) {
        logMessage(`Unbonding error: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Negotiate MTU with connected device
 * @param {number} size - Desired MTU size
 * @returns {Promise<number>} Negotiated MTU size
 */
export async function negotiateMTU(size = 217) {
    try {
        const response = await fetch('/api/ble/mtu', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ size })
        });
        
        if (!response.ok) {
            throw new Error(`MTU negotiation failed: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        logMessage(`MTU negotiated: ${result.mtu}`, 'info');
        return result.mtu;
    } catch (error) {
        logMessage(`MTU negotiation error: ${error.message}`, 'error');
        throw error;
    }
}

/**
 * Set connection parameters
 * @param {Object} params - Connection parameters
 * @param {number} params.minInterval - Minimum connection interval (ms)
 * @param {number} params.maxInterval - Maximum connection interval (ms)
 * @param {number} params.latency - Slave latency
 * @param {number} params.timeout - Supervision timeout (ms)
 * @returns {Promise<Object>} Updated connection parameters
 */
export async function setConnectionParameters(params) {
    try {
        const response = await fetch('/api/ble/connection-parameters', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        
        if (!response.ok) {
            throw new Error(`Setting connection parameters failed: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        logMessage(`Connection parameters updated`, 'info');
        return result;
    } catch (error) {
        logMessage(`Connection parameter error: ${error.message}`, 'error');
        throw error;
    }
}

/**
 * Get current connection parameters
 * @returns {Promise<Object>} Current connection parameters
 */
export async function getConnectionParameters() {
    try {
        const response = await fetch('/api/ble/connection-parameters');
        
        if (!response.ok) {
            throw new Error(`Getting connection parameters failed: ${response.status} ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        logMessage(`Connection parameter error: ${error.message}`, 'error');
        throw error;
    }
}
import { BLEEventEmitter } from './ble-events.js';

/**
 * Diagnostic tool for BLE system
 */
export function runDiagnostics() {
    console.group('BLE System Diagnostics');
    
    // Check event system
    console.log('Checking event system...');
    if (window.bleEvents) {
        console.log('✅ Event system exists', window.bleEvents);
        
        // Test event emission
        try {
            const testEvent = 'test.diagnostic.event';
            let eventReceived = false;
            
            window.bleEvents.on(testEvent, () => { 
                eventReceived = true;
                console.log('✅ Event listener fired successfully');
            });
            
            window.bleEvents.emit(testEvent, {diagnostics: true});
            
            console.log(eventReceived ? 
                '✅ Event system working properly' : 
                '❌ Event emission failed - listeners not called');
        } catch (e) {
            console.error('❌ Event system test failed', e);
        }
    } else {
        console.error('❌ Event system not initialized (window.bleEvents is undefined)');
    }
    
    // Check DOM references
    console.log('Checking DOM references...');
    const criticalElements = [
        'scanButton', 'deviceList', 'statusIndicatorContainer', 
        'logMessages', 'debugPanel', 'clearLogButton'
    ];
    
    if (window.state && window.state.domElements) {
        const missingElements = criticalElements.filter(id => !window.state.domElements[id]);
        if (missingElements.length === 0) {
            console.log('✅ All critical DOM elements found');
        } else {
            console.warn(`❌ Missing critical DOM elements: ${missingElements.join(', ')}`);
        }
    } else {
        console.error('❌ State or domElements not properly initialized');
    }
    
    // Add to page for user to see
    const diagnosticsDiv = document.createElement('div');
    diagnosticsDiv.id = 'ble-diagnostics';
    diagnosticsDiv.style.position = 'fixed';
    diagnosticsDiv.style.top = '10px';
    diagnosticsDiv.style.right = '10px';
    diagnosticsDiv.style.backgroundColor = '#333';
    diagnosticsDiv.style.color = '#fff';
    diagnosticsDiv.style.padding = '10px';
    diagnosticsDiv.style.borderRadius = '5px';
    diagnosticsDiv.style.zIndex = '9999';
    diagnosticsDiv.style.maxWidth = '400px';
    diagnosticsDiv.style.maxHeight = '300px';
    diagnosticsDiv.style.overflow = 'auto';
    
    diagnosticsDiv.innerHTML = `
        <h3 style="margin: 0 0 10px 0;">BLE Diagnostics</h3>
        <button id="fix-event-system" style="margin: 5px; padding: 5px; background: #007bff; border: none; color: white; border-radius: 3px;">
            Fix Event System
        </button>
        <button id="fix-dom-refs" style="margin: 5px; padding: 5px; background: #007bff; border: none; color: white; border-radius: 3px;">
            Fix DOM References
        </button>
        <button id="close-diagnostics" style="margin: 5px; padding: 5px; background: #dc3545; border: none; color: white; border-radius: 3px;">
            Close
        </button>
        <div id="diagnostic-results" style="margin-top: 10px;"></div>
    `;
    
    document.body.appendChild(diagnosticsDiv);
    
    // Add event listeners
    document.getElementById('fix-event-system').addEventListener('click', () => {
        try {
            // Re-initialize event system
            if (!window.bleEvents) {
                window.bleEvents = new BLEEventEmitter();
                document.getElementById('diagnostic-results').innerHTML += '<p>✅ Event system re-initialized</p>';
            } else {
                document.getElementById('diagnostic-results').innerHTML += '<p>Event system already exists</p>';
            }
        } catch (e) {
            document.getElementById('diagnostic-results').innerHTML += `<p>❌ Error: ${e.message}</p>`;
        }
    });
    
    document.getElementById('fix-dom-refs').addEventListener('click', () => {
        try {
            // Re-initialize DOM references
            if (window.initializeDomReferences) {
                window.initializeDomReferences();
                document.getElementById('diagnostic-results').innerHTML += '<p>✅ DOM references re-initialized</p>';
            } else {
                document.getElementById('diagnostic-results').innerHTML += '<p>❌ initializeDomReferences function not found</p>';
            }
        } catch (e) {
            document.getElementById('diagnostic-results').innerHTML += `<p>❌ Error: ${e.message}</p>`;
        }
    });
    
    document.getElementById('close-diagnostics').addEventListener('click', () => {
        document.body.removeChild(diagnosticsDiv);
    });
    
    console.groupEnd();
}

// Export BLEEventEmitter as backup
export { BLEEventEmitter };
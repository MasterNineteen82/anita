export class BleErrorBoundary {
    static wrapMethod(instance, methodName, context = '') {
        const originalMethod = instance[methodName];
        
        if (typeof originalMethod !== 'function') {
            console.error(`Method ${methodName} is not a function`);
            return;
        }
        
        instance[methodName] = function(...args) {
            try {
                return originalMethod.apply(this, args);
            } catch (error) {
                console.error(`Error in ${context || 'BLE'}.${methodName}:`, error);
                
                // Update UI to show error
                const statusElement = document.getElementById('ble-status-alert');
                if (statusElement) {
                    statusElement.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle mr-2"></i>
                            Error in ${context || 'BLE'}.${methodName}: ${error.message}
                        </div>
                    `;
                }
                
                // Rethrow for promise rejection if needed
                throw error;
            }
        };
    }
    
    static wrapAllMethods(instance, methodNames, context = '') {
        methodNames.forEach(methodName => {
            this.wrapMethod(instance, methodName, context);
        });
    }
}
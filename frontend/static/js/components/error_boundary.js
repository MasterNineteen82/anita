/**
 * Error boundary component to catch and handle errors
 * @param {Function} props.renderError - Function to render error UI
 * @param {Function} props.reportError - Function to report error
 * @param {String} props.componentName - Name of the component
 * @param {Node} props.children - Child components
 */
export class ErrorBoundary {
    constructor(props) {
        this.props = props;
        this.state = { hasError: false, error: null };
        this.containerElement = null;
    }

    /**
     * Attach error boundary to a DOM element
     * @param {HTMLElement} element - The DOM element to attach to
     */
    attach(element) {
        this.containerElement = element;
        this.render();
    }

    /**
     * Handle errors that occur in child components
     * @param {Error} error - The error that was thrown
     */
    handleError(error) {
        console.error(`Error in ${this.props.componentName || 'component'}:`, error);
        
        this.state.hasError = true;
        this.state.error = error;
        
        // Report error if function provided
        if (typeof this.props.reportError === 'function') {
            this.props.reportError(error, this.props.componentName);
        }
        
        this.render();
    }

    /**
     * Render the component
     */
    render() {
        if (!this.containerElement) return;
        
        if (this.state.hasError) {
            // Render error UI
            if (typeof this.props.renderError === 'function') {
                this.containerElement.innerHTML = '';
                const errorUI = this.props.renderError(this.state.error);
                if (typeof errorUI === 'string') {
                    this.containerElement.innerHTML = errorUI;
                } else if (errorUI instanceof HTMLElement) {
                    this.containerElement.appendChild(errorUI);
                }
            } else {
                // Default error UI
                this.containerElement.innerHTML = `
                    <div class="error-boundary p-4 bg-red-100 border border-red-400 text-red-700 rounded">
                        <h3 class="font-bold">Something went wrong</h3>
                        <p>The ${this.props.componentName || 'component'} encountered an error and could not be loaded.</p>
                        <button class="mt-2 bg-red-700 text-white px-3 py-1 rounded hover:bg-red-800" id="error-retry">Retry</button>
                    </div>
                `;
                
                // Add retry button functionality
                const retryBtn = this.containerElement.querySelector('#error-retry');
                if (retryBtn) {
                    retryBtn.addEventListener('click', () => {
                        this.state.hasError = false;
                        this.state.error = null;
                        if (typeof this.props.onRetry === 'function') {
                            this.props.onRetry();
                        }
                        this.render();
                    });
                }
            }
        } else {
            // Normal rendering handled by the parent
        }
    }

    /**
     * Reset the error state
     */
    reset() {
        this.state.hasError = false;
        this.state.error = null;
        this.render();
    }
}

// Factory function to create error boundaries
export function createErrorBoundary(componentName, renderErrorFn, reportErrorFn, onRetryFn) {
    return new ErrorBoundary({
        componentName, 
        renderError: renderErrorFn,
        reportError: reportErrorFn,
        onRetry: onRetryFn
    });
}
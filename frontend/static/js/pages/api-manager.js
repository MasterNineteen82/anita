document.addEventListener('DOMContentLoaded', () => {
    // Toast notification utility
    const UI = {
        toast: function(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `fixed bottom-4 right-4 px-4 py-2 rounded-md text-white text-sm z-50 ${
                type === 'success' ? 'bg-green-500' : 
                type === 'error' ? 'bg-red-500' : 
                'bg-blue-500'
            }`;
            toast.textContent = message;
            document.body.appendChild(toast);
            
            // Remove after 3 seconds
            setTimeout(() => {
                toast.classList.add('opacity-0', 'transition-opacity');
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
    };
    
    // Initialize variables
    let apiEndpoints = [];
    let currentCategory = 'all';
    let selectedEndpoint = null;
    let requestStats = {
        totalRequests: 0,
        successfulRequests: 0,
        totalResponseTime: 0,
        recentRequests: []
    };
    
    // DOM elements
    const endpointsList = document.getElementById('endpoints-list');
    const apiCategories = document.getElementById('api-categories');
    const endpointSearch = document.getElementById('endpoint-search');
    const testApiSection = document.getElementById('test-api-section');
    
    // Initialize the API manager
    initApiManager();
    
    // Event listeners
    document.getElementById('refresh-endpoints').addEventListener('click', loadApiEndpoints);
    endpointSearch.addEventListener('input', filterEndpoints);
    document.getElementById('params-accordion').addEventListener('click', toggleAccordion);
    document.getElementById('headers-accordion').addEventListener('click', toggleAccordion);
    document.getElementById('body-accordion').addEventListener('click', toggleAccordion);
    document.getElementById('send-request').addEventListener('click', sendApiRequest);
    document.getElementById('add-header').addEventListener('click', addHeaderField);
    document.getElementById('clear-recent').addEventListener('click', clearRecentRequests);
    
    // Initialize API manager
    async function initApiManager() {
        await loadApiEndpoints();
        updateApiStatus();
        setInterval(updateApiStatus, 30000); // Update status every 30 seconds
    }
    
    // Load API endpoints from the server
    async function loadApiEndpoints() {
        try {
            const response = await fetch('/api/docs.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            apiEndpoints = data.routes;
            
            // Update UI
            updateCategoryTabs(data.categorized_routes);
            displayEndpoints(apiEndpoints);
            updateConnectionStats(data.routes_count);
            
            // Show success notification
            UI.toast('API endpoints loaded successfully', 'success');
        } catch (error) {
            console.error('Error loading API endpoints:', error);
            UI.toast('Failed to load API endpoints', 'error');
        }
    }
    
    // Update category tabs
    function updateCategoryTabs(categorizedRoutes) {
        // Clear existing tabs except 'All'
        const allCategoryTab = apiCategories.querySelector('[data-category="all"]');
        apiCategories.innerHTML = '';
        apiCategories.appendChild(allCategoryTab);
        
        // Create category tabs
        for (const category in categorizedRoutes) {
            const li = document.createElement('li');
            li.className = 'mr-2';
            
            const button = document.createElement('button');
            button.className = 'category-tab text-sm py-2 px-4 rounded-t-md text-gray-400 hover:text-white';
            button.setAttribute('data-category', category);
            button.textContent = category;
            
            button.addEventListener('click', () => selectCategory(category));
            
            li.appendChild(button);
            apiCategories.appendChild(li);
        }
        
        // Set 'All' as active
        selectCategory('all');
    }
    
    // Select a category
    function selectCategory(category) {
        currentCategory = category;
        
        // Update tab styles
        document.querySelectorAll('.category-tab').forEach(tab => {
            if (tab.getAttribute('data-category') === category) {
                tab.classList.add('bg-gray-700', 'text-white');
                tab.classList.remove('text-gray-400');
            } else {
                tab.classList.remove('bg-gray-700', 'text-white');
                tab.classList.add('text-gray-400');
            }
        });
        
        // Filter endpoints by category
        filterEndpoints();
    }
    
    // Filter endpoints based on search input and selected category
    function filterEndpoints() {
        const searchTerm = endpointSearch.value.toLowerCase();
        
        let filteredEndpoints = apiEndpoints;
        
        // Filter by category
        if (currentCategory !== 'all') {
            filteredEndpoints = filteredEndpoints.filter(endpoint => 
                endpoint.tags && endpoint.tags.includes(currentCategory)
            );
        }
        
        // Filter by search term
        if (searchTerm) {
            filteredEndpoints = filteredEndpoints.filter(endpoint => 
                endpoint.path.toLowerCase().includes(searchTerm) || 
                endpoint.method.toLowerCase().includes(searchTerm) || 
                (endpoint.description && endpoint.description.toLowerCase().includes(searchTerm))
            );
        }
        
        // Display filtered endpoints
        displayEndpoints(filteredEndpoints);
    }
    
    // Display endpoints in the table
    function displayEndpoints(endpoints) {
        if (!endpoints || endpoints.length === 0) {
            endpointsList.innerHTML = `
                <tr>
                    <td colspan="4" class="px-4 py-4 text-center text-gray-400">No endpoints found</td>
                </tr>
            `;
            return;
        }
        
        // Sort endpoints by path
        endpoints.sort((a, b) => a.path.localeCompare(b.path));
        
        endpointsList.innerHTML = '';
        
        endpoints.forEach(endpoint => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-700';
            
            // Method column with color-coded badge
            const methodCell = document.createElement('td');
            methodCell.className = 'px-4 py-3 whitespace-nowrap';
            
            const methodBadge = document.createElement('span');
            methodBadge.className = 'px-2 py-1 text-xs font-medium rounded-md';
            
            // Color-code method
            switch (endpoint.method.toUpperCase()) {
                case 'GET':
                    methodBadge.classList.add('bg-blue-800', 'text-blue-200');
                    break;
                case 'POST':
                    methodBadge.classList.add('bg-green-800', 'text-green-200');
                    break;
                case 'PUT':
                    methodBadge.classList.add('bg-yellow-800', 'text-yellow-200');
                    break;
                case 'DELETE':
                    methodBadge.classList.add('bg-red-800', 'text-red-200');
                    break;
                case 'PATCH':
                    methodBadge.classList.add('bg-purple-800', 'text-purple-200');
                    break;
                default:
                    methodBadge.classList.add('bg-gray-600', 'text-gray-200');
            }
            
            methodBadge.textContent = endpoint.method.toUpperCase();
            methodCell.appendChild(methodBadge);
            
            // Path column
            const pathCell = document.createElement('td');
            pathCell.className = 'px-4 py-3 font-mono text-sm';
            pathCell.textContent = endpoint.path;
            
            // Description column
            const descriptionCell = document.createElement('td');
            descriptionCell.className = 'px-4 py-3 text-sm text-gray-300';
            descriptionCell.textContent = endpoint.description || 'No description';
            
            // Actions column
            const actionsCell = document.createElement('td');
            actionsCell.className = 'px-4 py-3 whitespace-nowrap text-sm';
            
            const testButton = document.createElement('button');
            testButton.className = 'text-blue-400 hover:text-blue-300 mr-3';
            testButton.innerHTML = '<i class="fas fa-play-circle mr-1"></i> Test';
            testButton.addEventListener('click', () => selectEndpointForTesting(endpoint));
            
            const docsButton = document.createElement('button');
            docsButton.className = 'text-gray-400 hover:text-gray-300';
            docsButton.innerHTML = '<i class="fas fa-book mr-1"></i> Docs';
            docsButton.addEventListener('click', () => viewEndpointDocs(endpoint));
            
            actionsCell.appendChild(testButton);
            actionsCell.appendChild(docsButton);
            
            // Add cells to row
            row.appendChild(methodCell);
            row.appendChild(pathCell);
            row.appendChild(descriptionCell);
            row.appendChild(actionsCell);
            
            endpointsList.appendChild(row);
        });
        
        // Update active routes count
        document.getElementById('active-routes').textContent = endpoints.length;
    }
    
    // Select an endpoint for testing
    function selectEndpointForTesting(endpoint) {
        selectedEndpoint = endpoint;
        
        // Show test section
        testApiSection.classList.remove('hidden');
        
        // Scroll to test section
        testApiSection.scrollIntoView({ behavior: 'smooth' });
        
        // Update endpoint details
        document.getElementById('test-method').textContent = endpoint.method.toUpperCase();
        document.getElementById('test-path').textContent = endpoint.path;
        document.getElementById('test-description').textContent = endpoint.description || 'No description';
        
        // Reset response section
        document.getElementById('response-container').classList.add('hidden');
        document.getElementById('response-error').classList.add('hidden');
        document.getElementById('response-waiting').classList.add('hidden');
        
        // Handle request body visibility based on method
        const bodySection = document.getElementById('body-section');
        if (['POST', 'PUT', 'PATCH'].includes(endpoint.method.toUpperCase())) {
            bodySection.classList.remove('hidden');
            document.getElementById('request-body').value = '{\n  \n}';
        } else {
            bodySection.classList.add('hidden');
        }
        
        // Parse URL parameters (if any)
        parseUrlParameters(endpoint.path);
    }
    
    // Parse URL parameters from the endpoint path
    function parseUrlParameters(path) {
        const paramContainer = document.getElementById('query-params-container');
        paramContainer.innerHTML = '';
        
        // Check for query parameters in path
        const pathParts = path.split('?');
        if (pathParts.length > 1) {
            const queryParams = pathParts[1].split('&');
            
            queryParams.forEach(param => {
                const [key, defaultValue] = param.split('=');
                
                const paramRow = document.createElement('div');
                paramRow.className = 'grid grid-cols-3 gap-2 mb-2';
                
                const keyInput = document.createElement('input');
                keyInput.type = 'text';
                keyInput.value = key;
                keyInput.className = 'bg-gray-700 rounded px-3 py-2 text-sm col-span-1';
                keyInput.readOnly = true;
                
                const valueInput = document.createElement('input');
                valueInput.type = 'text';
                valueInput.value = defaultValue || '';
                valueInput.placeholder = 'Value';
                valueInput.className = 'bg-gray-700 rounded px-3 py-2 text-sm col-span-2';
                valueInput.setAttribute('data-param', key);
                
                paramRow.appendChild(keyInput);
                paramRow.appendChild(valueInput);
                paramContainer.appendChild(paramRow);
            });
            
            // Show parameters section
            document.getElementById('params-content').classList.remove('hidden');
        } else {
            // Check for path parameters like {id}
            const pathParams = path.match(/{([^}]+)}/g);
            if (pathParams && pathParams.length > 0) {
                pathParams.forEach(param => {
                    const paramName = param.replace('{', '').replace('}', '');
                    
                    const paramRow = document.createElement('div');
                    paramRow.className = 'grid grid-cols-3 gap-2 mb-2';
                    
                    const keyInput = document.createElement('input');
                    keyInput.type = 'text';
                    keyInput.value = paramName;
                    keyInput.className = 'bg-gray-700 rounded px-3 py-2 text-sm col-span-1';
                    keyInput.readOnly = true;
                    
                    const valueInput = document.createElement('input');
                    valueInput.type = 'text';
                    valueInput.placeholder = 'Value';
                    valueInput.className = 'bg-gray-700 rounded px-3 py-2 text-sm col-span-2';
                    valueInput.setAttribute('data-param', paramName);
                    
                    paramRow.appendChild(keyInput);
                    paramRow.appendChild(valueInput);
                    paramContainer.appendChild(paramRow);
                });
                
                // Show parameters section
                document.getElementById('params-content').classList.remove('hidden');
            } else {
                // No parameters
                paramContainer.innerHTML = '<div class="text-sm text-gray-400 italic py-2">No parameters required</div>';
            }
        }
    }
    
    // View endpoint documentation
    function viewEndpointDocs(endpoint) {
        // Redirect to Swagger docs with the endpoint path highlighted
        window.open(`/docs#/${endpoint.tags[0]}/${endpoint.path.replace(/\//g, '_')}`, '_blank');
    }
    
    // Send API request
    async function sendApiRequest() {
        if (!selectedEndpoint) return;
        
        // Show waiting spinner
        document.getElementById('response-waiting').classList.remove('hidden');
        document.getElementById('response-container').classList.add('hidden');
        document.getElementById('response-error').classList.add('hidden');
        
        const startTime = performance.now();
        
        try {
            // Build request URL with parameters
            let url = selectedEndpoint.path;
            
            // Replace path parameters
            const pathParams = url.match(/{([^}]+)}/g);
            if (pathParams) {
                pathParams.forEach(param => {
                    const paramName = param.replace('{', '').replace('}', '');
                    const paramInput = document.querySelector(`input[data-param="${paramName}"]`);
                    
                    if (paramInput && paramInput.value) {
                        url = url.replace(param, paramInput.value);
                    } else {
                        throw new Error(`Path parameter ${paramName} is required`);
                    }
                });
            }
            
            // Build headers
            const headers = {};
            const headerInputs = document.querySelectorAll('#headers-container input');
            for (let i = 0; i < headerInputs.length; i += 2) {
                const key = headerInputs[i].value.trim();
                const value = headerInputs[i + 1].value.trim();
                
                if (key && value) {
                    headers[key] = value;
                }
            }
            
            // Add content type header if body is present
            if (['POST', 'PUT', 'PATCH'].includes(selectedEndpoint.method.toUpperCase())) {
                headers['Content-Type'] = 'application/json';
            }
            
            // Build request options
            const options = {
                method: selectedEndpoint.method.toUpperCase(),
                headers: headers
            };
            
            // Add body if needed
            if (['POST', 'PUT', 'PATCH'].includes(selectedEndpoint.method.toUpperCase())) {
                const bodyText = document.getElementById('request-body').value;
                if (bodyText.trim()) {
                    try {
                        // Validate JSON
                        const bodyJson = JSON.parse(bodyText);
                        options.body = JSON.stringify(bodyJson);
                    } catch (e) {
                        throw new Error(`Invalid JSON in request body: ${e.message}`);
                    }
                }
            }
            
            // Send the request
            const response = await fetch(url, options);
            
            // Get response time
            const endTime = performance.now();
            const responseTime = endTime - startTime;
            
            // Handle response
            let responseData;
            let contentType = response.headers.get('content-type') || '';
            
            if (contentType.includes('application/json')) {
                responseData = await response.json();
            } else {
                responseData = await response.text();
            }
            
            // Display response
            document.getElementById('response-waiting').classList.add('hidden');
            document.getElementById('response-container').classList.remove('hidden');
            
            // Update response status
            const statusEl = document.getElementById('response-status');
            statusEl.textContent = response.status;
            
            if (response.ok) {
                statusEl.className = 'text-green-400';
            } else {
                statusEl.className = 'text-red-400';
            }
            
            // Update response time
            document.getElementById('response-time').textContent = `${responseTime.toFixed(2)}ms`;
            
            // Update response body
            const responseBody = document.getElementById('response-body');
            
            if (typeof responseData === 'object') {
                responseBody.textContent = JSON.stringify(responseData, null, 2);
            } else {
                responseBody.textContent = responseData;
            }
            
            // Update stats
            updateRequestStats(response.status, responseTime, {
                method: selectedEndpoint.method,
                path: selectedEndpoint.path,
                status: response.status,
                time: responseTime,
                timestamp: new Date().toISOString()
            });
            
        } catch (error) {
            // Handle errors
            document.getElementById('response-waiting').classList.add('hidden');
            document.getElementById('response-error').classList.remove('hidden');
            
            document.getElementById('error-message').textContent = error.message;
            console.error('API request error:', error);
        }
    }
    
    // Add a new header field
    function addHeaderField() {
        const headerContainer = document.getElementById('headers-container');
        
        const headerRow = document.createElement('div');
        headerRow.className = 'grid grid-cols-3 gap-2 mb-2';
        
        const keyInput = document.createElement('input');
        keyInput.type = 'text';
        keyInput.placeholder = 'Header name';
        keyInput.className = 'bg-gray-700 rounded px-3 py-2 text-sm col-span-1';
        
        const valueInput = document.createElement('input');
        valueInput.type = 'text';
        valueInput.placeholder = 'Value';
        valueInput.className = 'bg-gray-700 rounded px-3 py-2 text-sm col-span-1';
        
        const removeButton = document.createElement('button');
        removeButton.className = 'bg-gray-700 hover:bg-gray-600 text-red-400 rounded px-3 py-2 text-sm';
        removeButton.innerHTML = '<i class="fas fa-times"></i>';
        removeButton.addEventListener('click', () => headerRow.remove());
        
        headerRow.appendChild(keyInput);
        headerRow.appendChild(valueInput);
        headerRow.appendChild(removeButton);
        
        headerContainer.appendChild(headerRow);
        
        // Show headers section
        document.getElementById('headers-content').classList.remove('hidden');
        
        // Focus on the new input
        keyInput.focus();
    }
    
    // Toggle accordion sections
    function toggleAccordion(event) {
        const accordionButton = event.currentTarget;
        const accordionContent = document.getElementById(accordionButton.getAttribute('aria-controls'));
        
        if (accordionContent) {
            const isExpanded = accordionButton.getAttribute('aria-expanded') === 'true';
            
            accordionButton.setAttribute('aria-expanded', String(!isExpanded));
            
            if (isExpanded) {
                accordionContent.classList.add('hidden');
            } else {
                accordionContent.classList.remove('hidden');
            }
        }
    }
    
    // Update request statistics
    function updateRequestStats(status, responseTime, requestInfo) {
        requestStats.totalRequests++;
        
        if (status >= 200 && status < 300) {
            requestStats.successfulRequests++;
        }
        
        requestStats.totalResponseTime += responseTime;
        
        // Add to recent requests (keep last 10)
        requestStats.recentRequests.unshift(requestInfo);
        if (requestStats.recentRequests.length > 10) {
            requestStats.recentRequests.pop();
        }
        
        // Update UI
        document.getElementById('total-requests').textContent = requestStats.totalRequests;
        document.getElementById('success-rate').textContent = requestStats.totalRequests 
            ? `${Math.round((requestStats.successfulRequests / requestStats.totalRequests) * 100)}%`
            : '0%';
        document.getElementById('avg-response-time').textContent = requestStats.totalRequests
            ? `${(requestStats.totalResponseTime / requestStats.totalRequests).toFixed(2)}ms`
            : '0ms';
            
        // Update recent requests table
        updateRecentRequestsTable();
    }
    
    // Update recent requests table
    function updateRecentRequestsTable() {
        const recentList = document.getElementById('recent-requests-list');
        
        if (!recentList) return;
        
        if (requestStats.recentRequests.length === 0) {
            recentList.innerHTML = `
                <tr>
                    <td colspan="4" class="px-4 py-4 text-center text-gray-400">No recent requests</td>
                </tr>
            `;
            return;
        }
        
        recentList.innerHTML = '';
        
        requestStats.recentRequests.forEach(request => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-700';
            
            // Method column
            const methodCell = document.createElement('td');
            methodCell.className = 'px-4 py-3 whitespace-nowrap';
            
            const methodBadge = document.createElement('span');
            methodBadge.className = 'px-2 py-1 text-xs font-medium rounded-md';
            
            // Color-code method
            switch (request.method.toUpperCase()) {
                case 'GET':
                    methodBadge.classList.add('bg-blue-800', 'text-blue-200');
                    break;
                case 'POST':
                    methodBadge.classList.add('bg-green-800', 'text-green-200');
                    break;
                case 'PUT':
                    methodBadge.classList.add('bg-yellow-800', 'text-yellow-200');
                    break;
                case 'DELETE':
                    methodBadge.classList.add('bg-red-800', 'text-red-200');
                    break;
                case 'PATCH':
                    methodBadge.classList.add('bg-purple-800', 'text-purple-200');
                    break;
                default:
                    methodBadge.classList.add('bg-gray-600', 'text-gray-200');
            }
            
            methodBadge.textContent = request.method.toUpperCase();
            methodCell.appendChild(methodBadge);
            
            // Path column
            const pathCell = document.createElement('td');
            pathCell.className = 'px-4 py-3 font-mono text-sm';
            pathCell.textContent = request.path;
            
            // Status column
            const statusCell = document.createElement('td');
            statusCell.className = 'px-4 py-3 whitespace-nowrap text-sm';
            
            const statusBadge = document.createElement('span');
            statusBadge.className = 'px-2 py-1 text-xs font-medium rounded-md';
            
            if (request.status >= 200 && request.status < 300) {
                statusBadge.classList.add('bg-green-800', 'text-green-200');
            } else if (request.status >= 400 && request.status < 500) {
                statusBadge.classList.add('bg-red-800', 'text-red-200');
            } else if (request.status >= 500) {
                statusBadge.classList.add('bg-orange-800', 'text-orange-200');
            } else {
                statusBadge.classList.add('bg-gray-600', 'text-gray-200');
            }
            
            statusBadge.textContent = request.status;
            statusCell.appendChild(statusBadge);
            
            // Time column
            const timeCell = document.createElement('td');
            timeCell.className = 'px-4 py-3 text-sm text-gray-300';
            timeCell.textContent = `${request.time.toFixed(2)}ms`;
            
            // Add cells to row
            row.appendChild(methodCell);
            row.appendChild(pathCell);
            row.appendChild(statusCell);
            row.appendChild(timeCell);
            
            recentList.appendChild(row);
        });
    }
    
    // Clear recent requests
    function clearRecentRequests() {
        requestStats.recentRequests = [];
        updateRecentRequestsTable();
    }
    
    // Update API status
    async function updateApiStatus() {
        try {
            const response = await fetch('/api/status');
            
            if (response.ok) {
                const data = await response.json();
                
                // Update UI with API status
                document.getElementById('api-status').innerHTML = 
                    `<span class="w-2 h-2 bg-green-500 rounded-full inline-block mr-2"></span> Online`;
                document.getElementById('api-status').className = 'text-green-400';
                
                // Update other status indicators
                if (data.uptime) {
                    document.getElementById('api-uptime').textContent = formatUptime(data.uptime);
                }
                
                if (data.memory) {
                    document.getElementById('api-memory').textContent = formatMemory(data.memory);
                }
                
                if (data.active_connections) {
                    document.getElementById('active-connections').textContent = data.active_connections;
                }
            } else {
                document.getElementById('api-status').innerHTML = 
                    `<span class="w-2 h-2 bg-red-500 rounded-full inline-block mr-2"></span> Offline`;
                document.getElementById('api-status').className = 'text-red-400';
            }
        } catch (error) {
            console.error('Error updating API status:', error);
            document.getElementById('api-status').innerHTML = 
                `<span class="w-2 h-2 bg-red-500 rounded-full inline-block mr-2"></span> Offline`;
            document.getElementById('api-status').className = 'text-red-400';
        }
    }
    
    // Update connection statistics
    function updateConnectionStats(routesCount) {
        document.getElementById('total-routes').textContent = routesCount || 0;
    }
    
    // Format uptime for display
    function formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) {
            return `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }
    
    // Format memory usage for display
    function formatMemory(bytes) {
        if (bytes < 1024) {
            return `${bytes} B`;
        } else if (bytes < 1024 * 1024) {
            return `${(bytes / 1024).toFixed(2)} KB`;
        } else if (bytes < 1024 * 1024 * 1024) {
            return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
        } else {
            return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
        }
    }
});
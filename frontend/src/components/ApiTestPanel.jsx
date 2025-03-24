import React, { useState } from 'react';
import ApiTester from '../utils/api-tester';

const ApiTestPanel = () => {
  const [testResults, setTestResults] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const runTests = async () => {
    setLoading(true);
    try {
      const results = await ApiTester.testProxyAndBackend();
      setTestResults(results);
    } catch (error) {
      console.error('Error running API tests:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="api-test-panel">
      <h2>API Connection Tester</h2>
      <button 
        onClick={runTests}
        disabled={loading}
      >
        {loading ? 'Running Tests...' : 'Test API Connections'}
      </button>
      
      {testResults && (
        <div className="test-results">
          <h3>Connection Status</h3>
          <div>Proxy: <span className={testResults.proxy === 'working' ? 'success' : 'error'}>{testResults.proxy}</span></div>
          <div>Backend: <span className={testResults.backend === 'working' ? 'success' : 'error'}>{testResults.backend}</span></div>
          
          <h3>API Endpoints</h3>
          <div>
            <h4>Succeeded</h4>
            <ul>
              {testResults.apiEndpoints.succeeded.map(endpoint => (
                <li key={endpoint}>{endpoint}</li>
              ))}
            </ul>
          </div>
          
          <div>
            <h4>Failed</h4>
            <ul>
              {testResults.apiEndpoints.failed.map((item, index) => (
                <li key={index}>
                  {item.endpoint}: {item.error}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default ApiTestPanel;
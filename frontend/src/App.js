import React from 'react';
import ApiTestPanel from './components/ApiTestPanel';

function App() {
  return (
    <div className="App">
      <header>
        <h1>ANITA API Test Panel</h1>
      </header>
      <main>
        <ApiTestPanel />
      </main>
      <footer>
        <p>This is a test panel for the ANITA API. The main application is available at <a href="http://localhost:8000">http://localhost:8000</a></p>
      </footer>
    </div>
  );
}

export default App;
# ANITA - Advanced NFC Integration & Testing Application

## Overview

ANITA is an advanced platform for NFC/RFID system integration, testing, and management. This repository contains a proof of concept (POC) implementation that demonstrates core functionality and validates the technical approach before full-scale development.

The system provides a comprehensive web interface for managing card readers, performing NFC operations, and configuring system parameters with real-time feedback through WebSockets.

## Features

### Core Functionality

- ✅ Device discovery and management
- ✅ Card operations (read/write)
- ✅ NFC operations support
- ✅ Real-time status updates via WebSockets
- ✅ API testing interface
- ✅ Simulation mode for hardware-free testing

### User Interface

- ✅ Modern, responsive web interface
- ✅ Dark/light theme support
- ✅ Real-time device status visualization
- ✅ Card presence detection
- ✅ Operation status reporting
- ✅ System health monitoring

### Configuration & Customization

- ✅ Multi-layered configuration system
- ✅ Environment variable support
- ✅ JSON-based configuration persistence
- ✅ MIFARE key management
- ✅ API endpoint configuration

## Technology Stack

- **Frontend**: HTML5, JavaScript, TailwindCSS
- **Backend**: Python, FastAPI, WebSockets
- **Documentation**: Jupyter Notebooks
- **Testing**: Unit testing, simulation mode

## Project Structure

anita-poc/
├── automation_scripts/     # Automation tools and utilities
├── backend/                # Backend Python code
│   └── ws/                 # WebSocket implementation
├── configuration_management/   # Configuration files and utilities
│   ├── api_configuration/
│   ├── card_configuration/
│   └── device_configuration/
├── diagnostics/            # Debugging and diagnostic tools
├── documentation/          # Comprehensive documentation
│   ├── apiguide.ipynb
│   ├── backendfuncCreation.ipynb
│   ├── frontenddevelopment.ipynb
│   ├── frontendUICreation.ipynb
│   └── globalconfiguration.ipynb
├── frontend/               # Web interface files
│   └── static/
│       ├── css/            # Stylesheets
│       ├── js/             # JavaScript modules
│       └── templates/      # HTML templates
├── main_application/       # Core application logic
└── testing/                # Test suites and utilities

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/anita-poc.git

# Navigate to the project directory
cd anita-poc

# Set up Python environment (requires Python 3.8+)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Start the backend server
python backend/app.py

# Open frontend in browser
# Navigate to http://localhost:8000
```

## Configuration

ANITA employs a hierarchical configuration system with several layers:

1. **Default Values**: Hardcoded defaults
2. **Environment Variables**: System-level configuration
    - `ANITA_ENV`: Application environment (development, testing, production)
    - `ANITA_LOG_LEVEL`: Logging verbosity
    - `ANITA_API_KEY`: Authentication key for external API access
    - `ANITA_HOST`/`ANITA_PORT`: Network binding configuration

3. **Configuration Files**: JSON-based persistent configuration
    - `config.json`: Primary configuration file
    - `.env`: Environment variable definitions

4. **UI Settings**: Runtime configuration via web interface

## Development

### Backend Development

For adding new backend functionality:

```bash
# Create new API endpoints
python -m backend.tools.create_endpoint --name your_feature

# Run backend tests
pytest backend/tests/

# Check for import issues
python debug_imports.py
```

Refer to [Backend Function Creation Guide](documentation/backendfuncCreation.ipynb) for detailed instructions.

### Frontend Development

The frontend uses vanilla JavaScript with TailwindCSS. See [Frontend Development Guide](documentation/frontenddevelopment.ipynb) for details.

## API Documentation

The API follows RESTful principles with the following endpoints:

- `/api/v1/readers` - Manage card readers
- `/api/v1/cards` - Card operations
- `/api/v1/nfc` - NFC operations
- `/api/v1/settings` - System configuration

All API requests require authentication. See [API Guide](documentation/apiguide.ipynb) for comprehensive documentation.

## Rate Limiting

The API is rate-limited to prevent abuse:

- 100 requests per minute per API key
- Status code 429 returned when exceeded
- Retry-After header indicates waiting time

## Testing

- Run simulation mode for hardware-free testing
- Unit tests cover core functionality
- API testing interface for endpoint validation

## Roadmap

- ⬜ Authentication system implementation
- ⬜ Database integration for persistent storage
- ⬜ Enhanced biometric integration
- ⬜ Comprehensive UWB positioning
- ⬜ Mobile application version
- ⬜ Plugin system for extensibility

## License

[MIT](LICENSE)

## Contributors

- ANITA Development Team

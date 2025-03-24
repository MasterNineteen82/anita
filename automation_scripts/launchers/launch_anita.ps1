#######################################################
# ANITA Application Launcher
# This script handles the proper startup of all ANITA components
#######################################################

# Add this at the beginning of your launch_anita.ps1 script
# Create virtual environment if it doesn't exist
$venvPath = Join-Path $ProjectRoot "venv"
if (-not (Test-Path $venvPath)) {
    Write-Log "Creating virtual environment..." -Level "INFO"
    & python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Failed to create virtual environment. Make sure Python is installed." -Level "ERROR"
        exit 1
    }
}

# Activate virtual environment
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    Write-Log "Activating virtual environment..." -Level "INFO"
    . $activateScript
    # Verify activation worked
    if (-not $env:VIRTUAL_ENV) {
        Write-Log "Failed to activate virtual environment" -Level "ERROR"
        exit 1
    }
} else {
    Write-Log "Virtual environment activation script not found" -Level "ERROR"
    exit 1
}

# Configuration
$ProjectRoot = "K:\anita\poc"
$LogDir = Join-Path $ProjectRoot "logs\active"
$LaunchLog = Join-Path $LogDir "app_launch_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Ensure log directory exists
if (-not (Test-Path $LogDir)) {
    New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
}

function Write-Log {
    param (
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$Level] $timestamp - $Message"
    
    # Write to console with color
    switch ($Level) {
        "INFO" { Write-Host $logMessage -ForegroundColor Cyan }
        "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        default { Write-Host $logMessage }
    }
    
    # Write to log file
    $logMessage | Out-File -FilePath $LaunchLog -Append
}

function Test-Command {
    param (
        [string]$Command
    )
    
    try {
        & $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Check if Python is available
if (-not (Test-Command "python --version")) {
    Write-Log "Python not found in PATH. Please install Python 3.8 or higher." -Level "ERROR"
    exit 1
}

# Check dependencies
Write-Log "Checking dependencies..."
python -c "import fastapi, uvicorn, alembic, pydantic" -ErrorAction SilentlyContinue
if ($LASTEXITCODE -ne 0) {
    Write-Log "Missing dependencies. Running dependency installation..." -Level "WARNING"
    python -m pip install -r "$ProjectRoot\requirements.txt"
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Failed to install dependencies. See error above." -Level "ERROR"
        exit 1
    }
}

# Run database migrations if needed
Write-Log "Checking database migrations..."
python "$ProjectRoot\backend\db\check_migrations.py"
if ($LASTEXITCODE -ne 0) {
    Write-Log "Database migration check failed." -Level "WARNING"
    $runMigrations = Read-Host "Run database migrations? (y/n)"
    if ($runMigrations -eq "y") {
        python "$ProjectRoot\backend\db\run_migrations.py"
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Migration failed. See error above." -Level "ERROR"
            exit 1
        }
    } else {
        Write-Log "Skipping migrations. Application may not work correctly." -Level "WARNING"
    }
}

# Start the application
Write-Log "Starting ANITA application..."
try {
    # Start background services first
    Start-Process -FilePath "python" -ArgumentList "$ProjectRoot\backend\services\smartcard_service.py" -NoNewWindow -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    
    # Launch main application
    Write-Log "Launching main application server..."
    python "$ProjectRoot\app.py"
} catch {
    Write-Log "Failed to start application: $_" -Level "ERROR"
    exit 1
}
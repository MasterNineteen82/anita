set PYTHONIOENCODING=utf-8
REM filepath: k:\anita\poc\automation_scripts\launch_anita.bat
@echo off
title ANITA Launcher
echo Starting ANITA...

REM Set the path to the application directory
set "APP_DIR=%~dp0"

REM Set the working directory to the POC root
cd /d "k:\anita\poc" || (
    echo ERROR: Could not change to POC directory.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist and activate it
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check for Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check required packages
echo Checking required packages...
python -m pip install -r requirements.txt >nul 2>&1

REM Run the setup and verification script
echo Running setup and verification script...
python automation_scripts\setup.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Setup and verification reported issues. Please resolve before continuing.
    pause
    exit /b 1
)

REM Run the git update script
echo Updating the project from Git...
python automation_scripts\gitupdate.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Git update reported issues. Please resolve before continuing.
    pause
    exit /b 1
)

REM Start the backend
echo Starting the backend...
start /B "" python app.py

REM Start the frontend
echo Starting the frontend...
cd frontend
start cmd /c "npm start"
cd ..

REM Wait for server to start
timeout /t 5 /nobreak >nul

REM Open browser for all relevant ports
start http://localhost:8000/
start http://localhost:5000/

echo.
echo ANITA is now running!
echo You can close this window once you're finished using the application.
echo To shut down the server, press Ctrl+C in this window.

pause
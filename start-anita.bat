REM filepath: k:\anita\poc\start-anita.bat
@echo off
echo Activating Python virtual environment...
call K:\anita\poc\venv\Scripts\activate.bat

echo Starting backend server...
start cmd /k "cd K:\anita\poc && python app.py"

echo Starting frontend server...
start cmd /k "cd K:\anita\poc\frontend && set NODE_OPTIONS=--openssl-legacy-provider && npm start"

echo ANITA servers starting up...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5000/splash.html
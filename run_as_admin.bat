@echo off
echo Launching ANITA BLE application with administrator privileges...
powershell -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"K:\anita\poc\automation_scripts\launchers\launch_anita.ps1\" -PythonExecutable \"K:\anita\poc\venv\Scripts\python.exe\"' -Verb RunAs"
echo If the UAC prompt appears, please select 'Yes' to grant administrator privileges.

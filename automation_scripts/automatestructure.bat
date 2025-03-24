@echo off
setlocal EnableDelayedExpansion

:: Parameters handling
if "%~1"=="/?" goto :help
if not "%~1"=="" (
    set "BASE_DIR=%~1"
) else (
    set "BASE_DIR=anita"
)

echo Creating folder structure in "%BASE_DIR%"...

:: Check if structure exists
if exist "%BASE_DIR%\" (
    echo.
    echo WARNING: Directory "%BASE_DIR%" already exists.
    choice /C YN /M "Do you want to continue and possibly overwrite existing content"
    if errorlevel 2 goto :end
    echo.
)

:: Create base directory
call :create_dir "%BASE_DIR%"

:: Create top-level directories
echo.
echo Creating top-level directories...
for %%D in (
    "archive"
    "backups"
    "installation_and_startup"
    "cli_application"
    "configuration_management"
    "databases"
    "diagnostics"
    "documents"
    "helpers"
    "frontend"
    "main_application"
    "testing"
    "reporting"
    "logging"
) do call :create_dir "%BASE_DIR%\%%D"

:: Create installation subdirectories
echo.
echo Creating installation subdirectories...
for %%D in (
    "automation_scripts"
    "setup_verification"
    "requirements"
) do call :create_dir "%BASE_DIR%\installation_and_startup\%%D"

:: Create configuration subdirectories
echo.
echo Creating configuration subdirectories...
for %%D in (
    "api_configuration"
    "card_configuration"
    "device_configuration"
    "global_configuration"
    "smartcard_configuration"
    "nfc_configuration"
    "logging_configuration"
) do call :create_dir "%BASE_DIR%\configuration_management\%%D"

:: Create diagnostic subdirectories
echo.
echo Creating diagnostic subdirectories...
for %%D in (
    "debugging"
    "diagnostic_reports"
    "diagnostic_scripts"
) do call :create_dir "%BASE_DIR%\diagnostics\%%D"

:: Create documentation subdirectories
echo.
echo Creating documentation subdirectories...
for %%D in (
    "technical_documentation"
    "testing_documentation"
    "configuration_documentation"
    "specifications_requirements"
    "user_guides"
) do call :create_dir "%BASE_DIR%\documents\%%D"

:: Create frontend subdirectories
echo.
echo Creating frontend subdirectories...
call :create_dir "%BASE_DIR%\frontend\public"
for %%D in (
    "static"
    "css"
    "js"
    "html"
    "templates"
    "images"
) do call :create_dir "%BASE_DIR%\frontend\public\%%D"

:: Create main application subdirectories
echo.
echo Creating main application subdirectories...
for %%D in (
    "apis"
    "models"
    "modules"
    "utilities"
    "router"
) do call :create_dir "%BASE_DIR%\main_application\%%D"

:: Create testing subdirectories
echo.
echo Creating testing subdirectories...
for %%D in (
    "uat_testing"
    "unit_testing"
) do call :create_dir "%BASE_DIR%\testing\%%D"

:: Create logging subdirectories
echo.
echo Creating logging subdirectories...
for %%D in (
    "console"
    "testing"
    "api"
    "transactions"
) do call :create_dir "%BASE_DIR%\logging\%%D"

echo.
echo Folder structure created successfully in "%BASE_DIR%".
goto :end

:create_dir
mkdir %1 2>nul
if exist %1 (
    echo [SUCCESS] Created directory %1
) else (
    echo [FAILED] Could not create directory %1
)
goto :eof

:help
echo.
echo USAGE: %~nx0 [base_directory_name]
echo.
echo Creates a standardized project directory structure.
echo If no base_directory_name is provided, "anita" will be used as default.
echo.
goto :end

:end
endlocal
